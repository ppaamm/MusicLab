# instruments/instrument/poly.py

import numpy as np
import threading
from typing import List, Tuple, Callable
from .base import Instrument, Voice

class PolyInstrument(Instrument):
    """
    Keeps multiple voices per note to avoid clicks on retrigger.
    Sustain pedal supported. 1/sqrt(N) gain comp + master.
    """

    def __init__(self, voice_factory: Callable[[int, int], Voice], master: float = 0.6):
        self._vf = voice_factory
        # store (note, voice, pending_release_flag)
        self._voices: List[Tuple[int, Voice, bool]] = []
        self._lock = threading.Lock()
        self._sustain = False
        self.master = float(master)

    def note_on(self, note: int, velocity: int) -> None:
        v = self._vf(note, velocity)
        with self._lock:
            # append; DO NOT replace existing same-note voices
            self._voices.append((note, v, False))

    def note_off(self, note: int) -> None:
        with self._lock:
            for i, (n, v, pend) in enumerate(self._voices):
                if n == note:
                    if self._sustain:
                        self._voices[i] = (n, v, True)  # mark for release later
                    else:
                        v.note_off()

    def cc(self, control: int, value: int) -> None:
        if control != 64:  # sustain
            return
        pedal = value >= 64
        with self._lock:
            if self._sustain and not pedal:
                # pedal released -> trigger release on pendings
                for i, (n, v, pend) in enumerate(self._voices):
                    if pend:
                        v.note_off()
                        self._voices[i] = (n, v, False)
            self._sustain = pedal

    def render(self, frames: int, sr: int) -> np.ndarray:
        with self._lock:
            mix = np.zeros(frames, dtype=np.float32)
            alive: List[Tuple[int, Voice, bool]] = []
            for n, v, pend in self._voices:
                mix += v.render(frames, sr)
                if not v.finished():
                    alive.append((n, v, pend))
            self._voices = alive

            # 1/sqrt(N) comp + master
            numv = max(1, len(self._voices))
            mix *= (self.master / np.sqrt(numv))
            return mix

    def num_active_voices(self) -> int:
        with self._lock:
            return len(self._voices)
