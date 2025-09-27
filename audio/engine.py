import sounddevice as sd
import numpy as np
import threading, time

from routing.bus import EventBus
from midi.messages import NoteOn, NoteOff, CC
from audio.dsp import soft_clip
from audio.meter import AudioMeter

class AudioEngine:
    def __init__(self, instrument, bus: EventBus, sr=44100, blocksize=256, channels=1,
                 pre_gain=0.3, limiter_drive=1.3, meter_period=1.0):
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

        self.stream = sd.OutputStream(
            channels=channels,
            samplerate=sr,
            blocksize=blocksize,
            callback=self._cb,
            latency='low'
        )

    def start(self):
        self.stream.start()
        # Start a small logger thread
        self._run_meter = True
        self._meter_thread = threading.Thread(target=self._meter_logger, daemon=True)
        self._meter_thread.start()

    def stop(self):
        self._run_meter = False
        if self._meter_thread:
            self._meter_thread.join(timeout=0.1)
        self.stream.stop(); self.stream.close()

    def _apply_events(self):
        for e in self.bus.drain():
            if   isinstance(e, NoteOn):  self.instrument.note_on(e.note, e.velocity)
            elif isinstance(e, NoteOff): self.instrument.note_off(e.note)
            elif isinstance(e, CC):      self.instrument.cc(e.control, e.value)

    def _cb(self, outdata, frames, time_info, status):
        if status:
            # xruns etc.
            pass

        self._apply_events()

        # Render instrument (already includes 1/sqrt(Nvoices) compensation)
        mix = self.instrument.render(frames, self.sr)  # float32 mono

        # Pre-gain for headroom
        if self.pre_gain != 1.0:
            mix = mix * self.pre_gain

        # Measure pre-limiter peak
        pre_peak = float(np.max(np.abs(mix))) if mix.size else 0.0

        # Safety limiter (soft clip)
        limited_before = mix.copy()
        mix = soft_clip(mix, drive=self.limiter_drive)

        # Detect if limiting actually changed samples
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
