import numpy as np
from typing import Dict, Callable, List, Tuple
from dataclasses import dataclass
from . signals.compose import SpectralStack
from . envelopes.base import Envelope
from . envelopes.adsr import ADSR
from . base import Voice, FrequencyInstrument
import threading
import copy

@dataclass
class AdditiveFreqVoice(Voice):
    freq: float
    signal: SpectralStack
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
        partials: Dict[float, float],
        velocity_curve: float = 1.8,
        env_attack: float = 0.005,
        env_decay: float = 0.08,
        env_sustain: float = 0.6,
        env_release: float = 0.20,
    ):
        self.n_partials = len(partials)
        self.partials = partials
        self.velocity_curve = float(velocity_curve)
        self.env_attack = float(env_attack)
        self.env_decay = float(env_decay)
        self.env_sustain = float(env_sustain)
        self.env_release = float(env_release)

    def voice(self, freq_hz: float, velocity: int) -> AdditiveFreqVoice:
        sig = SpectralStack(self.partials)
        env = ADSR(self.env_attack, self.env_decay, self.env_sustain, self.env_release)
        env.gate_on()
        vel_amp = (max(0, min(127, int(velocity))) / 127.0) ** self.velocity_curve
        return AdditiveFreqVoice(freq=float(freq_hz), signal=sig, env=env, vel_amp=vel_amp)






def make_additive_frequency(master: float = 0.6, **factory_kwargs) -> FrequencyInstrument:
    fac = AdditiveFreqFactory(**factory_kwargs)
    return PolyFrequencyInstrument(voice_factory=fac.voice, master=master)






class PolyFrequencyInstrument(FrequencyInstrument):
    """
    Keeps multiple voices per note to avoid clicks on retrigger.
    Sustain pedal supported. 
    1/sqrt(N) gain comp + master, where N = nb of voices
    """

    def __init__(self, voice_factory: Callable[[int, int], Voice], 
                 master: float = 0.6, alpha: float = 0.05):
        self._vf = voice_factory
        # store (note, voice, pending_release_flag)
        self._voices: List[Tuple[int, Voice, bool]] = []
        self._lock = threading.Lock()
        self._sustain = False
        self.master = float(master)
        self._last_gain = self.master
        self.alpha = alpha
        self._pending_release: set[float] = set()

    def note_on(self, freq_hz: int, velocity: int) -> None:
        v = self._vf(float(freq_hz), int(velocity))
            
        with self._lock:
            self._voices.append((freq_hz, v, False))
            self._pending_release.discard(freq_hz)
            

    def note_off(self, freq_hz: float) -> None:
        f = float(freq_hz)
        with self._lock:
            for i, (freq, v, pending) in enumerate(self._voices):
                if abs(freq - f) < 1e-6 and not pending:
                    if self._sustain:
                        self._voices[i] = (freq, v, True)
                    else:
                        v.note_off()
      

    def cc(self, control: int, value: int) -> None:
        if control != 64:  # sustain
            return
        pedal = value >= 64
        with self._lock:
            if self._sustain and not pedal:
                for f in list(self._pending_release):
                    v = self._voices.get(f)
                    if v is not None:
                        v.note_off()    
                self._pending_release.clear()
            self._sustain = pedal



    def _smoothing_gain(self, target_gain):
        """
        Smoothes gain changes
        """
        return (1 - self.alpha) * self._last_gain + self.alpha * target_gain
        

    def render(self, frames: int, sr: int) -> np.ndarray:
        with self._lock:
            mix = np.zeros(frames, dtype=np.float32)
            n_start = max(1, len(self._voices))
            
            alive: List[Tuple[float, Voice, bool]] = []

            for freq, v, pending in self._voices:
                mix += v.render(frames, sr)
                if not v.finished():
                    alive.append((freq, v, pending))
            self._voices = alive
            
            gain = self._smoothing_gain(self.master / np.sqrt(n_start))
            self._last_gain = gain
            mix *= gain
            return mix

    def num_active_voices(self) -> int:
        with self._lock:
            return len(self._voices)



@dataclass
class PartialCharacteristics:
    amplitude: float
    phase: SpectralStack
    env: Envelope



@dataclass
class SpectralVoice(Voice):
    freq: float
    bank: SpectralStack                   # oscillator bank (amp+phase only)
    partial_envs: Dict[float, Envelope]   # key: ratio -> envelope
    vel_amp: float = 1.0

    def note_off(self) -> None:
        for env in self.partial_envs.values():
            env.gate_off()
    
    def finished(self) -> bool:
        # voice ends when all partial envelopes finished
        return not self.partial_envs or all(e.finished() for e in self.partial_envs.values())

    def render(self, frames: int, sr: int) -> np.ndarray:
        Y, ratios = self.bank.render_partials(self.freq, frames, sr)   # shape (P, frames)
        if Y.size == 0:
            return np.zeros(frames, dtype=np.float32)

        # apply per-partial envelopes
        for i, r in enumerate(ratios):
            env = self.partial_envs.get(r)
            if env is None:
                # if no specific envelope provided, treat as constant 1
                continue
            Y[i, :] *= env.render(frames, sr)

        out = Y.sum(axis=0).astype(np.float32)
        return out * float(self.vel_amp)
    


def _clone_env(e: Envelope) -> Envelope:
    """Try deepcopy; fall back to ADSR(a,d,s,r)-style reconstruction if needed."""
    try:
        return copy.deepcopy(e)
    except Exception:
        # minimal generic fallback for simple ADSR-like envelopes
        cls = e.__class__
        attrs = {k: getattr(e, k) for k in ("a", "d", "s", "r") if hasattr(e, k)}
        return cls(**attrs) if attrs else cls()
    


def make_spectral_frequency(
    partials: Dict[float, PartialCharacteristics],   # ratio -> characteristics
    master: float = 0.6,
    velocity_curve: float = 1.8,
) -> FrequencyInstrument:
    
    #partials_sorted = dict(sorted(partials.items(), key=lambda kv: kv[0]))
    partials_sorted = dict([ (r, (ch.amplitude, ch.phase)) for r, ch in partials.items() ])

    def voice_factory(freq_hz: float, velocity: int) -> SpectralVoice:
        # IMPORTANT: fresh oscillator bank per voice
        bank = SpectralStack(partials_sorted)

        # /!\ IMPORTANT: fresh envelope instances per voice
        partial_envs: Dict[float, Envelope] = {}
        if partials:
            for ratio, characteristic in partials.items():
                e = _clone_env(characteristic.env)
                e.gate_on()
                partial_envs[float(ratio)] = e

        # velocity mapping
        v = max(0, min(127, int(velocity))) / 127.0
        vel_amp = v ** float(velocity_curve)

        return SpectralVoice(freq=float(freq_hz), 
                             bank=bank, 
                             partial_envs=partial_envs, 
                             vel_amp=vel_amp)

    return PolyFrequencyInstrument(voice_factory=voice_factory, master=master)