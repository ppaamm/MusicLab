import sounddevice as sd
import numpy as np
import threading, time, wave, queue

from routing.bus import EventBus
from midi.messages import NoteOn, NoteOff, CC
from audio.dsp import soft_clip
from audio.meter import AudioMeter

class AudioEngine:
    def __init__(self, instrument, bus: EventBus, sr=44100, blocksize=256, channels=1,
                 pre_gain=0.3, limiter_drive=1.3, meter_period=1.0,
                 record_to: str | None = None):
        self.instrument = instrument
        self.bus = bus
        self.sr = sr
        self.blocksize = blocksize
        self.channels = channels

        # Gain/limiter
        self.pre_gain = float(pre_gain)
        self.limiter_drive = float(limiter_drive)

        # Meter
        self.meter = AudioMeter(window_sec=meter_period)
        self._meter_period = meter_period
        self._meter_thread = None
        self._run_meter = False

        # Recording
        self._record_path = record_to
        self._rec_queue: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=64)
        self._rec_run = False
        self._rec_thread = None
        self._wav = None  # wave.Wave_write

        self.stream = sd.OutputStream(
            channels=channels,
            samplerate=sr,
            blocksize=blocksize,
            callback=self._cb,
            latency='low'
        )

    # ---------- Public ----------
    def start(self):
        self.stream.start()

        # Meter thread
        self._run_meter = True
        self._meter_thread = threading.Thread(target=self._meter_logger, daemon=True)
        self._meter_thread.start()

        # Recording writer thread
        if self._record_path:
            self._start_recording()

    def stop(self):
        # stop meter
        self._run_meter = False
        if self._meter_thread:
            self._meter_thread.join(timeout=0.2)

        # stop audio first
        self.stream.stop(); self.stream.close()

        # stop recording thread & close file
        if self._record_path:
            self._stop_recording()

    # ---------- Internals ----------
    def _apply_events(self):
        for e in self.bus.drain():
            if   isinstance(e, NoteOn):  self.instrument.note_on(e.note, e.velocity)
            elif isinstance(e, NoteOff): self.instrument.note_off(e.note)
            elif isinstance(e, CC):      self.instrument.cc(e.control, e.value)

    def _cb(self, outdata, frames, time_info, status):
        if status:
            # xruns etc.
            # print("[SD status]", status)
            pass

        self._apply_events()

        # Render instrument (already includes 1/sqrt(Nvoices) compensation)
        mix = self.instrument.render(frames, self.sr).astype(np.float32)  # mono float32 [-1,1]

        # Pre-gain for headroom
        if self.pre_gain != 1.0:
            mix = mix * self.pre_gain

        # Measure pre-limiter peak
        pre_peak = float(np.max(np.abs(mix))) if mix.size else 0.0

        # Safety limiter (soft clip)
        limited_before = mix.copy()
        mix = soft_clip(mix, drive=self.limiter_drive)

        # Detect if limiting changed samples
        limited = bool(np.any(np.abs(mix - limited_before) > 1e-7))

        # Final hard cap
        post_peak = float(np.max(np.abs(mix))) if mix.size else 0.0
        if post_peak > 1.0:
            mix = mix / post_peak
            post_peak = 1.0

        # Meter update (block RMS after limiting)
        block_rms = float(np.sqrt(np.mean(mix.astype(np.float64)**2))) if mix.size else 0.0
        self.meter.update(pre_peak=pre_peak, post_peak=post_peak, block_rms=block_rms,
                          limited=limited, frames=frames)

        # Output (mono to all channels)
        outdata[:, 0] = mix
        if outdata.shape[1] > 1:
            outdata[:, 1] = mix

        # ---- Recording enqueue (non-blocking) ----
        if self._record_path and self._rec_run:
            # prepare interleaved int16 frames for N channels
            if self.channels == 1:
                block = mix.copy()
            else:
                # duplicate mono to all channels
                block = np.tile(mix[:, None], (1, self.channels)).reshape(-1).astype(np.float32)

            # Convert to 16-bit PCM
            block = np.clip(block, -1.0, 1.0)
            pcm16 = (block * 32767.0).astype(np.int16)

            # If stereo and we didn't reshape yet, interleave:
            if self.channels > 1 and pcm16.ndim == 1 and pcm16.size == frames:
                # interleave identical channels
                pcm16 = np.repeat(pcm16, self.channels)

            try:
                self._rec_queue.put_nowait(pcm16.tobytes())
            except queue.Full:
                # drop if writer is behind (don't block audio)
                pass

    # --- logger thread: print every ~meter_period seconds ---
    def _meter_logger(self):
        while self._run_meter:
            time.sleep(self._meter_period)
            snap = self.meter.snapshot_and_reset()
            bar = self._bar(snap["peak_post_db"])
            lim = " LIM" if snap["limited_blocks"] > 0 else ""
            print(f"[Audio] peak(pre/post): {snap['peak_pre_db']:+6.1f} dBFS / {snap['peak_post_db']:+6.1f} dBFS | "
                  f"rms: {snap['rms_db']:+6.1f} dBFS | frames:{snap['frames']:5d} | blocks_limited:{snap['limited_blocks']:2d} {bar}{lim}")

    @staticmethod
    def _bar(db, floor=-60.0, ceil=0.0, width=20):
        # quick ASCII meter bar
        db = max(floor, min(ceil, db))
        fill = int((db - floor) / (ceil - floor) * width + 0.5)
        return " [" + ("#" * fill).ljust(width, ".") + "]"

    # ---------- Recording helpers ----------
    def _start_recording(self):
        # open wave file
        self._wav = wave.open(self._record_path, mode='wb')
        self._wav.setnchannels(self.channels)
        self._wav.setsampwidth(2)  # 16-bit
        self._wav.setframerate(self.sr)

        self._rec_run = True
        self._rec_thread = threading.Thread(target=self._rec_writer, daemon=True)
        self._rec_thread.start()
        print(f"[REC] Recording to {self._record_path}")

    def _stop_recording(self):
        self._rec_run = False
        if self._rec_thread:
            self._rec_thread.join(timeout=1.0)
            self._rec_thread = None
        if self._wav:
            try:
                self._wav.close()
            finally:
                self._wav = None
        # drain queue if any (optional)

    def _rec_writer(self):
        # consume blocks and write to disk
        while self._rec_run or not self._rec_queue.empty():
            try:
                data = self._rec_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self._wav.writeframes(data)
            except Exception as e:
                # if disk error, stop recording
                print(f"[REC] write error: {e}")
                self._rec_run = False
