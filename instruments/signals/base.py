from typing import Protocol
import numpy as np
import matplotlib.pyplot as plt

class Signal(Protocol):
    """A stateful, unlimited-time signal generator."""
    def render(self, freq: float, frames: int, sr: int = 44100) -> np.ndarray:
        """Return `frames` samples (float32 mono), advancing internal state."""
        ...
        
    def reset(self) -> None:
        """Reset internal state/phase (optional)."""
        ...
        
    def plot(self, freq: float, frames: int, sr: int = 44100) -> None:
        """
        Render `frames` samples and plot them.
        """
        y = self.render(freq, frames)
        t = np.arange(frames) / sr
        plt.figure(figsize=(8, 3))
        plt.plot(t, y, lw=1.2)
        plt.title(f"{self.__class__.__name__} ({freq:.1f} Hz)")
        plt.xlabel("Time [s]")
        plt.ylabel("Amplitude")
        plt.grid(True, alpha=0.3)
        plt.show()
