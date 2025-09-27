from typing import Protocol
import numpy as np
import matplotlib.pyplot as plt
import sounddevice as sd

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
        
        
    def play_sample(self, freq: float, T: float = 1.0, sr: int = 44100, blocking=True):
        
        # Ensure float32 in [-1, 1] to avoid clipping
        sig = self.render(freq, int(T * sr), sr)
        if sig.dtype != np.float32:
            # scale if values look like ints or outside [-1, 1]
            max_abs = np.max(np.abs(sig))
            if max_abs == 0:
                max_abs = 1.0
            if not np.issubdtype(sig.dtype, np.floating) or max_abs > 1.0:
                sig = (sig / max_abs).astype(np.float32)
            else:
                sig = sig.astype(np.float32)
        sd.play(sig, samplerate=sr, blocking=blocking)
