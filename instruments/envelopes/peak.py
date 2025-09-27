import numpy as np
from enum import Enum, auto
from .base import Envelope


class PeakEnvelope(Envelope):
    """
    Peak, independent of the gate off
    """

    def __init__(self, attack=0.03, release=0.20):
        assert(attack >= 0)
        assert(release >= 0)
        self.a = float(attack)
        self.r = float(release)
        self._finished = True


    def gate_on(self) -> None:
        self._t = 0.0
        self._finished = False

    def gate_off(self) -> None:
        pass

    def finished(self) -> bool:
        return self._finished

    def _math_render(self, t: float) -> float:
        if t < 0:
            return 0.0
        if self.a > 0.0 and t < self.a:
            return t / self.a
        if self.r > 0.0 and t < self.a + self.r:
            return 1.0 - (t - self.a) / self.r
        return 0.0


    def render(self, frames: int, sr: int) -> np.ndarray:
        out = np.zeros(frames, dtype=np.float32)
        if self._finished or frames <= 0:
            return out

        dt = 1.0 / float(sr)
        t = self._t

        # Compute each sample by calling _math_render(t)
        # TODO: Make it more optimal
        for i in range(frames):
            out[i] = self._math_render(t)
            t += dt

        # Advance internal time
        self._t = t

        # Mark finished when past end of one-shot
        total = max(0.0, self.a) + max(0.0, self.r)
        if total == 0.0 or self._t >= total:
            self._finished = True

        return out

