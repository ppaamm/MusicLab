import numpy as np
from .base import Signal

class Sine(Signal):
    def __init__(self, phase: float = 0.0, gain: float = 1.0):
        self.phase = float(phase)  # radians
        self.gain = float(gain)

    def render(self, freq: float, frames: int, sr: int = 44100) -> np.ndarray:
        out = np.empty(frames, dtype=np.float32)
        phase = self.phase
        twopi = 2 * np.pi
        inc = twopi * freq / sr
        
        for i in range(frames):
            phase += inc
            if phase >= twopi:
                phase -= twopi
            out[i] = np.sin(phase)
        self.phase = phase
        return out * self.gain

    def reset(self) -> None:
        self.phase = 0.0

class SawNaive(Signal):
    """Naive saw (aliased)."""
    #TODO: Replace with band-limited later.
    def __init__(self, phase: float = 0.0, gain: float = 1.0):
        self.gain = float(gain)
        self.phase = float(phase) % 1.0  # phase in [0,1)


    def render(self, freq: float, frames: int, sr: int = 44100) -> np.ndarray:
        out = np.empty(frames, dtype=np.float32)
        phase = self.phase
        inc = freq / sr
        for i in range(frames):
            phase += inc
            if phase >= 1.0:
                phase -= 1.0
            out[i] = 2.0 * phase - 1.0
        self.phase = phase
        return out * self.gain

    def reset(self) -> None:
        self.phase = 0.0

