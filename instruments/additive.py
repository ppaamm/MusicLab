import numpy as np
from dataclasses import dataclass
from . signals.compose import HarmonicStack
from . envelopes.adsr import ADSR
from . base import Voice, FrequencyInstrument
from . polyphonic import PolyFrequencyInstrument

@dataclass
class AdditiveFreqVoice(Voice):
    freq: float
    signal: HarmonicStack
    env: ADSR
    vel_amp: float

    def note_off(self) -> None:
        self.env.gate_off()

    def finished(self) -> bool:
        return self.env.finished()

    def render(self, frames: int, sr: int) -> np.ndarray:
        raw = self.signal.render(self.freq, frames, sr)
        env = self.env.render(frames, sr)
        return (raw * env * self.vel_amp).astype(np.float32)

class AdditiveFreqFactory:
    """
    Factory to build frequency-domain additive voices.
    """
    def __init__(
        self,
        amplitudes: np.ndarray,
        velocity_curve: float = 1.8,
        env_attack: float = 0.005,
        env_decay: float = 0.08,
        env_sustain: float = 0.6,
        env_release: float = 0.20,
    ):
        self.n_partials = amplitudes.shape[0]
        self.amplitudes = amplitudes / np.sum(np.abs(amplitudes))
        self.velocity_curve = float(velocity_curve)
        self.env_attack = float(env_attack)
        self.env_decay = float(env_decay)
        self.env_sustain = float(env_sustain)
        self.env_release = float(env_release)

    def voice(self, freq_hz: float, velocity: int) -> AdditiveFreqVoice:
        sig = HarmonicStack(self.amplitudes)
        env = ADSR(self.env_attack, self.env_decay, self.env_sustain, self.env_release)
        env.gate_on()
        vel_amp = (max(0, min(127, int(velocity))) / 127.0) ** self.velocity_curve
        return AdditiveFreqVoice(freq=float(freq_hz), signal=sig, env=env, vel_amp=vel_amp)

def make_additive_frequency(master: float = 0.6, **factory_kwargs) -> FrequencyInstrument:
    fac = AdditiveFreqFactory(**factory_kwargs)
    return PolyFrequencyInstrument(voice_factory=fac.voice, master=master)
