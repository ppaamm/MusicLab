import numpy as np
import threading
from typing import List, Tuple, Callable
from .base import FrequencyInstrument, Voice


class PolyFrequencyInstrument(FrequencyInstrument):
    """
    Keeps multiple voices per note to avoid clicks on retrigger.
    Sustain pedal supported. 
    1/sqrt(N) gain comp + master, where N = nb of voices
    """

    def __init__(self, voice_factory: Callable[[int, int], Voice], 
                 master: float = 0.6, alpha: float = 0.25):
        self._vf = voice_factory
        # store (note, voice, pending_release_flag)
        self._voices: List[Tuple[int, Voice, bool]] = []
        self._lock = threading.Lock()
        self._sustain = False
        self.master = float(master)
        self._last_gain = self.master
        self.alpha = alpha
        self._pending_release: set[float] = set()

    def note_on(self, freq_hz: int, velocity: int) -> None:
        v = self._vf(float(freq_hz), int(velocity))
            
        with self._lock:
            self._voices.append((freq_hz, v, False))
            self._pending_release.discard(freq_hz)
            

    def note_off(self, freq_hz: float) -> None:
        f = float(freq_hz)
        with self._lock:
            for i, (freq, v, pending) in enumerate(self._voices):
                if abs(freq - f) < 1e-6 and not pending:
                    if self._sustain:
                        self._voices[i] = (freq, v, True)
                    else:
                        v.note_off()
                
                
                

    def cc(self, control: int, value: int) -> None:
        if control != 64:  # sustain
            return
        pedal = value >= 64
        with self._lock:
            if self._sustain and not pedal:
                for f in list(self._pending_release):
                    v = self._voices.get(f)
                    if v is not None:
                        v.note_off()
                self._pending_release.clear()
            self._sustain = pedal



    def _smoothing_gain(self, target_gain):
        """
        Smoothes gain changes
        """
        return (1 - self.alpha) * self._last_gain + self.alpha * target_gain
        

    def render(self, frames: int, sr: int) -> np.ndarray:
        with self._lock:
            mix = np.zeros(frames, dtype=np.float32)
            n_start = max(1, len(self._voices))
            
            alive: List[Tuple[float, Voice, bool]] = []

            for freq, v, pending in self._voices:
                mix += v.render(frames, sr)
                if not v.finished():
                    alive.append((freq, v, pending))
            self._voices = alive
            
            gain = self._smoothing_gain(self.master / np.sqrt(n_start))
            self._last_gain = gain
            mix *= gain
            return mix

    def num_active_voices(self) -> int:
        with self._lock:
            return len(self._voices)
