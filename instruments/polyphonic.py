import numpy as np
import threading
from typing import Dict, Callable, Set
from .base import Instrument, Voice

class PolyInstrument(Instrument):
    """
    Generic polyphonic instrument. Supply a voice_factory(note, velocity) -> Voice.
    - Note-offs can be held by sustain (CC 64).
    - Master gain + 1/sqrt(Nvoices) compensation.
    """

    def __init__(self, voice_factory: Callable[[int, int], Voice], master: float = 0.6):
        self._vf = voice_factory
        self._voices: Dict[int, Voice] = {}
        self._lock = threading.Lock()
        self._sustain = False
        self._pending_release: Set[int] = set()
        self.master = float(master)

    # --- MIDI-like API ---
    def note_on(self, note: int, velocity: int) -> None:
        with self._lock:
            self._voices[note] = self._vf(note, velocity)
            # if a note was pending release, re-trigger replaces it
            self._pending_release.discard(note)

    def note_off(self, note: int) -> None:
        with self._lock:
            v = self._voices.get(note)
            if v is None:
                return
            if self._sustain:
                self._pending_release.add(note)   # release later
            else:
                v.note_off()

    def cc(self, control: int, value: int) -> None:
        if control != 64:  # sustain pedal
            return
        pedal = value >= 64
        with self._lock:
            if self._sustain and not pedal:
                # pedal released: flush pending releases
                for n in list(self._pending_release):
                    v = self._voices.get(n)
                    if v is not None:
                        v.note_off()
                self._pending_release.clear()
            self._sustain = pedal

    # --- audio ---
    def render(self, frames: int, sr: int) -> np.ndarray:
        with self._lock:
            mix = np.zeros(frames, dtype=np.float32)
            dead = []
            for n, v in self._voices.items():
                mix += v.render(frames, sr)
                if v.finished():
                    dead.append(n)
            for n in dead:
                self._voices.pop(n, None)
                self._pending_release.discard(n)

            # voice-count gain comp (1/sqrt(N)) + master gain
            numv = max(1, len(self._voices))
            mix *= (self.master / np.sqrt(numv))
            return mix

    def num_active_voices(self) -> int:
        with self._lock:
            return len(self._voices)
