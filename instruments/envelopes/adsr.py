import numpy as np
from enum import Enum, auto
from .base import Envelope

class ADSRState(Enum):
    IDLE = auto()      # No sound
    ATTACK = auto()    # Attack phase
    DECAY = auto()     # Decay phase
    SUSTAIN = auto()   # Sustain phase
    RELEASE = auto()   # Release phase


class ADSR(Envelope):
    """
    Attack/Decay/Sustain/Release envelope (block-by-block).
    Times are in seconds; sustain is a linear level in [0,1].
    """

    def __init__(self, attack=0.03, decay=0.08, sustain=0.7, release=0.20):
        self.a = float(attack)
        self.d = float(decay)
        self.s = float(sustain)
        self.r = float(release)

        # state
        self._state = ADSRState.IDLE
        self._t = 0.0                 # seconds elapsed within current state
        self._last_sr = None

        # cached stage lengths in samples (per sr)
        self._A = self._D = self._R = 1

        # current output level (last sample written) and release start level
        self._y = 0.0
        self._rel_start = 0.0

    # ---- control ----
    def gate_on(self) -> None:
        if self.a > 0:
            self._state = ADSRState.ATTACK
        elif self.d > 0:
            self._state = ADSRState.DECAY
        else:
            self._state = ADSRState.SUSTAIN
        self._t = 0.0
        self._y = 0.0

    def gate_off(self) -> None:
        self._rel_start = float(self._y)
        if self.r > 0:
            self._state = ADSRState.RELEASE
            self._t = 0.0
        else:
            self._state = ADSRState.IDLE
            self._t = 0.0
            self._y = 0.0

    def finished(self) -> bool:
        return self._state == ADSRState.IDLE

    # ---- internals ----
    def _prepare_for_sr(self, sr: int) -> None:
        if self._last_sr == sr:
            return
        self._A = max(1, int(self.a * sr))
        self._D = max(1, int(self.d * sr))
        self._R = max(1, int(self.r * sr))
        self._last_sr = sr

    def _render_attack(self, sr: int, remain: int) -> np.ndarray:
        elapsed = int(self._t * sr)
        left = self._A - elapsed
        n = min(remain, max(0, left))

        if self._A <= 1:
            seg = np.ones(n, dtype=np.float32)
        else:
            start = elapsed
            seg = (np.arange(start, start + n, dtype=np.float32) / (self._A - 1))

        if n > 0:
            self._y = float(seg[-1])
        self._t += n / sr

        if int(self._t * sr) >= self._A:
            self._state = ADSRState.DECAY
            self._t = 0.0
            self._y = 1.0  # exact transition
        return seg

    # ---- render ----
    def render(self, frames: int, sr: int) -> np.ndarray:
        self._prepare_for_sr(sr)
        out = np.zeros(frames, dtype=np.float32)

        idx = 0
        while idx < frames and self._state != ADSRState.IDLE:
            remain = frames - idx

            if self._state == ADSRState.ATTACK:
                seg = self._render_attack(sr, remain)
                n = seg.shape[0]
                if n:
                    out[idx:idx+n] = seg
                    idx += n

            elif self._state == ADSRState.DECAY:
                elapsed = int(self._t * sr)
                left = self._D - elapsed
                n = min(remain, max(0, left))

                if self._D <= 1:
                    seg = np.full(n, self.s, dtype=np.float32)
                else:
                    start = elapsed
                    # linear 1 -> sustain over D samples
                    seg = 1.0 + (self.s - 1.0) * (
                        np.arange(start, start + n, dtype=np.float32) / (self._D - 1)
                    )
                if n:
                    out[idx:idx+n] = seg
                    self._y = float(seg[-1])
                self._t += n / sr
                idx += n

                if int(self._t * sr) >= self._D:
                    self._state = ADSRState.SUSTAIN
                    self._t = 0.0
                    self._y = float(self.s)

            elif self._state == ADSRState.SUSTAIN:
                out[idx:] = self.s
                self._y = float(self.s)
                idx = frames  # until gate_off switches to RELEASE

            elif self._state == ADSRState.RELEASE:
                elapsed = int(self._t * sr)
                left = self._R - elapsed
                n = min(remain, max(0, left))

                if self._R <= 1:
                    seg = np.zeros(n, dtype=np.float32)
                else:
                    start = elapsed
                    # linear self._rel_start -> 0 over R samples
                    seg = self._rel_start * (
                        1.0 - (np.arange(start, start + n, dtype=np.float32) / (self._R - 1))
                    )
                if n:
                    out[idx:idx+n] = seg
                    self._y = float(seg[-1])
                self._t += n / sr
                idx += n

                if int(self._t * sr) >= self._R:
                    self._state = ADSRState.IDLE
                    self._t = 0.0
                    self._y = 0.0

        return out

