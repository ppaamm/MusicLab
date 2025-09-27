import numpy as np
from typing import Sequence
from .base import Signal

class Sum(Signal):
    """Sum of child signals (no renormalization)."""
    def __init__(self, signals: Sequence[Signal], gains: Sequence[float] | None = None):
        self.children = list(signals)
        self.gains = list(gains) if gains is not None else [1.0]*len(self.children)

    def render(self, freq: float, frames: int, sr: int = 44100) -> np.ndarray:
        mix = np.zeros(frames, dtype=np.float32)
        for s, g in zip(self.children, self.gains):
            mix += s.render(freq, frames, sr) * g
        return mix

    def reset(self) -> None:
        for c in self.children:
            c.reset()

class Mix(Signal):
    """Weighted mix: sum(weights) should be <= 1 for headroom."""
    def __init__(self, signals: Sequence[Signal], weights: Sequence[float]):
        assert len(signals) == len(weights)
        self.children = list(signals)
        self.weights = np.asarray(weights, dtype=np.float32)

    def render(self, freq: float, frames: int, sr: int = 44100) -> np.ndarray:
        mix = np.zeros(frames, dtype=np.float32)
        for s, w in zip(self.children, self.weights):
            mix += s.render(freq, frames, sr) * w
        return mix

    def reset(self) -> None:
        for c in self.children: c.reset()



class RingMod(Signal):
    def __init__(self, a: Signal, b: Signal):
        self.a = a
        self.b = b
        
    def render(self, freq: float, frames: int, sr: int=44100) -> np.ndarray:
        return self.a.render(freq, frames, sr) * self.b.render(freq, frames, sr)
    
    def reset(self) -> None:
        self.a.reset(); self.b.reset()


class Detune(Signal):
    """Wrap a Signal, multiplying incoming freq by `ratio` (e.g., 1.01)."""
    def __init__(self, inner: Signal, ratio: float):
        self.inner = inner
        self.ratio = float(ratio)
        
    def render(self, freq: float, frames: int, sr: int=44100) -> np.ndarray:
        return self.inner.render(freq*self.ratio, frames, sr)
    
    def reset(self) -> None:
        self.inner.reset()
        
        

class HarmonicStack(Signal):
    """
    Additive sine stack at k*f0 with fixed amplitudes (L1-normalized).
    Keeps per-partial phase for continuity; uses incoming sr each call.
    """
    def __init__(self, amps: np.ndarray):
        amps = np.asarray(amps, dtype=np.float64)
        s = float(np.sum(np.abs(amps))) or 1.0
        self.amps = (amps / s).astype(np.float64)
        self.phases = np.zeros(len(self.amps), dtype=np.float64)

    def render(self, freq: float, frames: int, sr: int=44100) -> np.ndarray:
        twopi = 2 * np.pi
        out = np.zeros(frames, dtype=np.float32)
        phase = self.phases
        incs  = (twopi * (np.arange(1, len(self.amps)+1) * float(freq)) / float(sr))
        for i in range(frames):
            phase += incs
            # cheap wrap
            phase -= np.floor(phase / twopi) * twopi
            out[i] = np.sin(phase) @ self.amps
        self.phases = phase
        return out

    def reset(self) -> None:
        self.phases[:] = 0.0
