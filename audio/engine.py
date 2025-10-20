# audio/engine.py
import sounddevice as sd
import numpy as np
import threading
import wave, queue
from typing import Optional

from routing.bus import EventBus
from audio.dsp import soft_clip
from audio.meter import AudioMeter
from audio.mixer import Mixer


class AudioEngine:
    def __init__(self, mixer: Mixer, bus: EventBus, sr=44100, blocksize=256, channels=1,
                 pre_gain=0.3, limiter_drive=1.3, meter_period=1.0,
                 record_to: Optional[str] = None):
        self.mixer = mixer
        self.bus = bus
        self.sr = int(sr)
        self.blocksize = int(blocksize)
        self.channels = int(channels)

        # processing
        self.pre_gain = float(pre_gain)
        self.limiter_drive = float(limiter_drive)

        # metering
        self.meter = AudioMeter(window_sec=meter_period)
        self._meter_period = float(meter_period)
        self._meter_thread: Optional[threading.Thread] = None

        # coordinated shutdown
        self._stop_evt = threading.Event()
        
        # recording
        self._record_path = record_to
        self._rec_queue: "queue.Queue[bytes]" = queue.Queue(maxsize=64)
        self._rec_run = False
        self._rec_thread: Optional[threading.Thread] = None
        self._wav: Optional[wave.Wave_write] = None

        # audio stream
        self.stream = sd.OutputStream(
            channels=self.channels,
            samplerate=self.sr,
            blocksize=self.blocksize,
            callback=self._cb,
            latency='low'
        )

    ###########################################################################
    ##                              LIFECYCLE                                ##
    ###########################################################################
    def start(self):
        self._stop_evt.clear()
        self.stream.start()

        # meter thread (non-daemon: we join it)
        self._meter_thread = threading.Thread(target=self._meter_logger, name="AudioMeterThread")
        self._meter_thread.start()

        # recording
        if self._record_path:
            self._start_recording()

    def stop(self):
        # tell threads to stop
        self._stop_evt.set()

        # stop audio first to stop callbacks quickly
        # abort() is immediate; stop() drains—abort helps kill callback loop promptly
        try:
            self.stream.abort()
        except Exception:
            pass
        try:
            self.stream.stop()
        except Exception:
            pass
        try:
            self.stream.close()
        except Exception:
            pass

        # join meter
        if self._meter_thread:
            self._meter_thread.join(timeout=2.0)
            if self._meter_thread.is_alive():
                print("[Engine] WARNING: meter thread still alive after join()")
            self._meter_thread = None

        # stop recording
        if self._record_path:
            self._stop_recording()
        print("[Engine] stop() called")


    ###########################################################################
    ##                           AUDIO CALL BACK                             ##
    ###########################################################################
    
    def _cb(self, outdata, frames, time_info, status):
        # if we are stopping, output silence and return—do not do work
        if self._stop_evt.is_set():
            outdata.fill(0)
            return

        # route events to mixer
        self.mixer.route_events(self.bus.drain())

        # render
        mix = self.mixer.render(frames, self.sr, channels=self.channels).astype(np.float32)

        # pre-gain
        if self.pre_gain != 1.0:
            mix *= self.pre_gain

        # limiter
        pre_peak = float(np.max(np.abs(mix))) if mix.size else 0.0
        mix_lim = soft_clip(mix, drive=self.limiter_drive)

        post_peak = float(np.max(np.abs(mix_lim))) if mix_lim.size else 0.0
        if post_peak > 1.0:
            mix_lim /= post_peak
            post_peak = 1.0

        # meter (after limiting)
        block_rms = float(np.sqrt(np.mean(mix_lim.astype(np.float64)**2))) if mix_lim.size else 0.0
        limited = bool(np.any(np.abs(mix_lim - mix) > 1e-7))
        self.meter.update(pre_peak=pre_peak, post_peak=post_peak, block_rms=block_rms,
                          limited=limited, frames=frames)

        # write to device
        if self.channels == 1:
            outdata[:, 0] = mix_lim
            if outdata.shape[1] > 1:
                outdata[:, 1] = mix_lim
        else:
            outdata[:, :2] = mix_lim[:, :2]

        # enqueue for recording (non-blocking)
        if self._record_path and self._rec_run and not self._stop_evt.is_set() :
            blk = mix_lim
            blk = np.clip(blk, -1.0, 1.0)
            if self.channels == 1:
                pcm16 = (blk * 32767.0).astype(np.int16).tobytes()
            else:
                pcm16 = (blk * 32767.0).astype(np.int16).ravel(order='C').tobytes()
            try:
                self._rec_queue.put_nowait(pcm16)
            except queue.Full:
                # drop; never block audio
                pass

    ###########################################################################
    ##                           METERING THREAD                             ##
    ###########################################################################
    def _meter_logger(self):
        period = self._meter_period
        
        while True:
            # wait() returns True if event was set during timeout—exit promptly
            if self._stop_evt.wait(timeout=period):
                break
            if self._stop_evt.is_set():
                break
            
            snap = self.meter.snapshot_and_reset()
            bar = self._bar(snap["peak_post_db"])
            lim = " LIM" if snap["limited_blocks"] > 0 else ""
            print(f"[Audio] peak(pre/post): {snap['peak_pre_db']:+6.1f} dBFS / "
                  f"{snap['peak_post_db']:+6.1f} dBFS | rms: {snap['rms_db']:+6.1f} dBFS | "
                  f"frames:{snap['frames']:5d} | blocks_limited:{snap['limited_blocks']:2d} {bar}{lim}")

    @staticmethod
    def _bar(db, floor=-60.0, ceil=0.0, width=20):
        db = max(floor, min(ceil, db))
        fill = int((db - floor) / (ceil - floor) * width + 0.5)
        return " [" + ("#" * fill).ljust(width, ".") + "]"


    ###########################################################################
    ##                              RECORDING                                ##
    ###########################################################################
    
    def _start_recording(self):
        self._wav = wave.open(self._record_path, mode='wb')
        self._wav.setnchannels(self.channels)
        self._wav.setsampwidth(2)  # 16-bit
        self._wav.setframerate(self.sr)

        self._rec_run = True
        self._rec_thread = threading.Thread(target=self._rec_writer)
        self._rec_thread.start()
        print(f"[REC] Recording to {self._record_path}")

    def _stop_recording(self):
        self._rec_run = False
        if self._rec_thread:
            self._rec_thread.join()
            self._rec_thread = None
        if self._wav:
            try:
                self._wav.close()
            finally:
                self._wav = None

    def _rec_writer(self):
        # drain until told to stop AND queue is empty
        while self._rec_run or not self._rec_queue.empty():
            try:
                data = self._rec_queue.get(timeout=0.25)
            except queue.Empty:
                # also exit promptly if engine is stopping and no data
                if self._stop_evt.is_set():
                    break
                continue
            try:
                self._wav.writeframes(data)
            except Exception as e:
                print(f"[REC] write error: {e}")
                self._rec_run = False
