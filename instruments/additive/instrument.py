import numpy as np
import threading
from typing import Dict
from .voice import Voice

SR = 44100

class AdditiveInstrument:
    def __init__(self, sr=SR):
        self.sr = sr
        self._voices: Dict[int, Voice] = {}
        self._lock = threading.Lock()
        self.master = 0.8  # instrument-level gain

    def note_on(self, note: int, velocity: int) -> None:
        with self._lock:
            self._voices[note] = Voice(self._midi_to_freq(note), velocity, sr=self.sr)

    def note_off(self, note: int) -> None:
        with self._lock:
            v = self._voices.get(note)
            if v: v.note_off()

    def render(self, frames: int) -> np.ndarray:
        with self._lock:
            mix = np.zeros(frames, dtype=np.float32)
            dead = []
            for key, v in self._voices.items():
                mix += v.render(frames)
                if v.finished():
                    dead.append(key)
            for key in dead:
                self._voices.pop(key, None)

            # voice-count comp here (instrument-level)
            numv = max(1, len(self._voices))
            mix *= (self.master / np.sqrt(numv))
            return mix

    def num_active_voices(self) -> int:
        with self._lock:
            return len(self._voices)


