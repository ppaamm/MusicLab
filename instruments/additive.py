import numpy as np
from dataclasses import dataclass
from typing import Callable
from . signals.compose import HarmonicStack
from . envelopes.base import Envelope
from . envelopes.adsr import ADSR
from . envelopes.peak import PeakEnvelope
from . base import Voice
from . polyphonic import PolyInstrument

def midi_to_freq(note: int) -> float:
    return 440.0 * (2 ** ((note - 69) / 12))

def apply_micro_fade(buf: np.ndarray, sr: int, fade_ms: float = 1.0) -> None:
    """In-place short linear fade-in/out to prevent clicks."""
    n = len(buf)
    k = min(n, int(sr * fade_ms * 0.001))
    if k <= 1:
        return
    ramp = np.linspace(0.0, 1.0, k, dtype=buf.dtype)
    buf[:k] *= ramp
    buf[-k:] *= ramp[::-1]


@dataclass
class AdditiveVoice(Voice):
    """Voice = harmonic signal × envelope × velocity gain."""
    freq: float
    signal: HarmonicStack
    env: Envelope
    vel_amp: float

    def note_off(self) -> None:
        self.env.gate_off()

    def finished(self) -> bool:
        return self.env.finished()

    def render(self, frames: int, sr: int) -> np.ndarray:
        raw = self.signal.render(self.freq, frames, sr)      # <- signals API
        env = self.env.render(frames, sr)                    # <- envelopes API
        out = (raw * env * self.vel_amp).astype(np.float32)

        # Apply a 3 ms fade to kill clicks
        apply_micro_fade(out, sr, fade_ms=3.0)

        return out

class AdditiveInstrumentFactory:
    """
    Factory for creating additive voices with a given partial law and envelope settings.
    Use with PolyInstrument: PolyInstrument(voice_factory=factory.voice, master=0.6)
    """
    def __init__(
        self,
        n_partials: int = 8,
        power: float = 6.0,           # amplitude law: 1/(k^power)
        velocity_curve: float = 1.8,  # vel amp = (vel/127)^curve
        env_attack: float = 0.005,
        #env_decay: float = 0.08,
        #env_sustain: float = 0.6,
        env_release: float = 0.20,
    ):
        self.n_partials = int(n_partials)
        self.power = float(power)
        self.velocity_curve = float(velocity_curve)
        self.env_attack = float(env_attack)
        #self.env_decay = float(env_decay)
        #self.env_sustain = float(env_sustain)
        self.env_release = float(env_release)

    def _amps(self) -> np.ndarray:
        amps = np.array([1.0 / ((k+1) ** self.power) for k in range(self.n_partials)], dtype=np.float64)
        s = float(np.sum(np.abs(amps))) or 1.0
        return amps / s

    def voice(self, note: int, velocity: int) -> AdditiveVoice:
        f0 = midi_to_freq(note)
        sig = HarmonicStack(self._amps())                # phase kept inside, freq passed each render
        # env = ADSR(attack=self.env_attack,
        #            decay=self.env_decay,
        #            sustain=self.env_sustain,
        #            release=self.env_release)
        env = PeakEnvelope(self.env_attack, self.env_release)
        env.gate_on()
        vel_amp = (max(0, min(127, velocity)) / 127.0) ** self.velocity_curve
        return AdditiveVoice(freq=f0, signal=sig, env=env, vel_amp=vel_amp)

def make_additive_poly(master: float = 0.6, **factory_kwargs) -> PolyInstrument:
    """
    Convenience: create a PolyInstrument configured for additive synthesis.
    Example:
        inst = make_additive_poly(master=0.5, n_partials=6, power=6.0)
    """
    factory = AdditiveInstrumentFactory(**factory_kwargs)
    return PolyInstrument(voice_factory=factory.voice, master=master)
