import numpy as np
from typing import Sequence, Dict, Tuple, List
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

        
        
        
class SpectralStack(Signal):
    """
    Additive sine stack at k*f0 with fixed amplitudes (L1-normalized).
    Keeps per-partial phase for continuity; uses incoming sr each call.
    """
    def __init__(self, partials: Dict[float, Tuple[float, float]],):
        # S = sum(partials.values())
        # self.partials = {k : v / S for k, v in partials.items()}
        # self.phases = {k : 0. for k, v in partials.items()}
        
        items = sorted(partials.items(), key=lambda kv: kv[0])   # deterministic order
        self.ratios = np.array([k for k, _ in items], dtype=np.float64)
        
        self.amps    = np.array([v[0] for _, v in items], dtype=np.float64)
        S = float(np.sum(np.abs(self.amps)))
        self.amps /= S
        
        self._phi0   = np.array([v[1] for _, v in items], dtype=np.float64)
        self.phases  = np.mod(self._phi0, 2.0 * np.pi)
        
        
        
        
    def render_partials(self, freq: float, frames: int, sr: int
                        ) -> Tuple[np.ndarray, List[float]]:
        """
        Return a matrix of per-partial oscillator samples (already scaled by 
        per-partial amplitude), shape (P, frames), and the list of ratios used 
        (active subset under Nyquist).
        """
        two_pi = 2.0 * np.pi
        
        outP = np.zeros((np.sum(self.ratios.size), frames), dtype=np.float32)
        if frames <= 0 or self.ratios.size == 0:
            return outP[:0, :], []

        f0 = float(freq); nyq = 0.5 * float(sr)
        f_partials = self.ratios * f0
        active = (f_partials > 0.0) & (f_partials < nyq)
        if not np.any(active):
            return outP[:0, :], []

        ratios = self.ratios[active]
        amps   = self.amps[active]
        phi    = self.phases[active]
        inc    = (two_pi * f_partials[active]) / float(sr)

        P = ratios.size
        Y = np.empty((P, frames), dtype=np.float32)
        n = np.arange(frames, dtype=np.float64)

        # vectorized per-partial phase ramps
        # phi_k[n] = phi0_k + n * inc_k
        phi_mat = phi[:, None] + n[None, :] * inc[:, None]
        phi_mat = phi_mat - np.floor(phi_mat / two_pi) * two_pi
        Y[:] = (np.sin(phi_mat) * amps[:, None]).astype(np.float32)

        # advance phases by frames samples
        self.phases[active] = (phi + frames * inc) % two_pi
        return Y, list(ratios)
        
        

    def render(self, freq: float, frames: int, sr: int = 44100) -> np.ndarray:
        """
        Sum of sinusoids at frequencies k * freq with amplitudes self.partials[k].
        This render is probably not the one to be used directly, since envelopes 
        should be applied on each frequency individually, on not on the whole
        signal. 
        """
        Y, _ = self.render_partials(freq, frames, sr)
        return Y.sum(axis=0) if Y.size else np.zeros(frames, dtype=np.float32)
    
    
    def reset(self) -> None:
        """Reset all stored phases to the initial phases."""
        self._phi = np.mod(self._phi0, 2.0 * np.pi)
