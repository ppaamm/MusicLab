from typing import Protocol
import matplotlib.pyplot as plt
import numpy as np

class Envelope(Protocol):
    def gate_on(self) -> None: ...
    def gate_off(self) -> None: ...
    def render(self, frames: int, sr: int = 44100) -> np.ndarray:
        """Return envelope amplitude for next `frames` samples (float32)."""
        ...
    def finished(self) -> bool:
        """True if envelope is at rest and voice can be freed."""
        ...

    def plot(self, t_total: float, t_gate_off: float, sr: int = 44100):
        """Plot from gate-on for `seconds` seconds, with optional gate-off at `t_gate_off`."""
        seconds = float(t_total)
        assert seconds > 0.0
        frames_total = int(seconds * sr)
    
        # gate-off frame (clamp to window)
        if t_gate_off is None:
            off_frame = None
        else:
            off_frame = int(t_gate_off * sr)
            if off_frame < 0: off_frame = 0
            if off_frame > frames_total: off_frame = frames_total
    
        y = np.zeros(frames_total, dtype=np.float32)
    
        # Start at gate-on
        self.gate_on()
    
        if off_frame is None or off_frame == frames_total:
            # No gate-off inside the window
            y[:] = self.render(frames_total, sr)
        elif off_frame == 0:
            # Immediate gate-off
            self.gate_off()
            y[:] = self.render(frames_total, sr)
        else:
            # Chunk 1: up to gate-off
            y[:off_frame] = self.render(off_frame, sr)
            # Gate-off exactly at boundary
            self.gate_off()
            # Chunk 2: release until the end
            y[off_frame:] = self.render(frames_total - off_frame, sr)
    
        # ---- plot ----
        t = np.arange(frames_total) / sr
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.plot(t, y, lw=1.2)
        ax.set_ylim(-0.05, 1.05)
        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Envelope")
        title = f"{self.__class__.__name__} (gate-on @0s"
        if t_gate_off is not None:
            title += f", gate-off @{t_gate_off:.3f}s"
        title += f", duration {seconds:.3f}s @ {sr}Hz)"
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        return fig, ax
