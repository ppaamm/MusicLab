import numpy as np
from typing import Dict
from .voice import Voice
import threading

SR = 44100

class AdditiveInstrument:
    def __init__(self, sr=SR, n_partials=10):
        self.sr = sr
        self.n_partials = n_partials
        self._voices: Dict[int, Voice] = {}
        self._lock = threading.Lock()
        self.master = 0.8

    def note_on(self, note: int, velocity: int) -> None:
        with self._lock:
            self._voices[note] = Voice(self._midi_to_freq(note), velocity, sr=self.sr)

    def note_off(self, note: int) -> None:
        with self._lock:
            v = self._voices.get(note)
            if v: v.note_off()

    def cc(self, control: int, value: int) -> None:
        # sustain, modwheel, etc. Hook as you like.
        pass

    def render(self, frames: int) -> np.ndarray:
        with self._lock:
            mix = np.zeros(frames, dtype=np.float32)
            dead = []
            for n, v in self._voices.items():
                mix += v.render(frames)
                if v.finished():
                    dead.append(n)
            for n in dead:
                self._voices.pop(n, None)

            # voice-count compensation
            numv = max(1, len(self._voices))
            mix *= (self.master / np.sqrt(numv))
            return mix

    def num_active_voices(self) -> int:
        with self._lock:
            return len(self._voices)

    @staticmethod
    def _midi_to_freq(note: int) -> float:
        return 440.0 * (2 ** ((note - 69) / 12))
