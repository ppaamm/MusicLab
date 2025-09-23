import sounddevice as sd
import numpy as np
from routing.bus import EventBus
from midi.messages import NoteOn, NoteOff, CC
from audio.dsp import soft_clip

class AudioEngine:
    def __init__(self, instrument, bus: EventBus, sr=44100, blocksize=256, channels=1):
        self.instrument = instrument
        self.bus = bus
        self.sr = sr
        self.stream = sd.OutputStream(
            channels=channels,
            samplerate=sr,
            blocksize=blocksize,
            callback=self._cb,
            latency='low'
        )

    def start(self):
        self.stream.start()

    def stop(self):
        self.stream.stop(); self.stream.close()

    def _apply_events(self):
        for e in self.bus.drain():
            if   isinstance(e, NoteOn):  self.instrument.note_on(e.note, e.velocity)
            elif isinstance(e, NoteOff): self.instrument.note_off(e.note)
            elif isinstance(e, CC):      self.instrument.cc(e.control, e.value)

    def _cb(self, outdata, frames, time_info, status):
        if status:  # xruns, etc.
            pass
        self._apply_events()
        mix = self.instrument.render(frames)

        # safety limiter + hard cap
        mix = soft_clip(mix, 1.5)
        peak = float(np.max(np.abs(mix)))
        if peak > 1.0:
            mix /= peak

        outdata[:, 0] = mix
        if outdata.shape[1] > 1:
            outdata[:, 1] = mix
