import numpy as np
from typing import Callable
from . base import MidiInstrument, FrequencyInstrument

def midi_to_freq_equal_tempered(note: int) -> float:
    """Default: standard 12-TET tuning (A4 = 440 Hz)."""
    return 440.0 * (2 ** ((int(note) - 69) / 12))

class MidiInstrumentAdapter(MidiInstrument):
    """
    Adapts any FrequencyInstrument to a MIDI-note API.
    The MIDI→frequency mapping is configurable via midi_to_freq.
    """

    def __init__(
        self,
        inner_instrument: FrequencyInstrument,
        midi_to_freq: Callable[[int], float] = midi_to_freq_equal_tempered
    ):
        """
        Parameters
        ----------
        inner : FrequencyInstrument
            The wrapped frequency-based instrument.
        midi_to_freq : Callable[[int], float]
            Function that converts MIDI note numbers to frequency (Hz).
            Default is standard equal-tempered A4=440 Hz.
        """
        self.inner_instrument = inner_instrument
        self._midi_to_freq = midi_to_freq

    def note_on(self, note: int, velocity: int) -> None:
        freq = self._midi_to_freq(note)
        self.inner_instrument.note_on(freq, velocity)

    def note_off(self, note: int) -> None:
        freq = self._midi_to_freq(note)
        self.inner_instrument.note_off(freq)

    def cc(self, control: int, value: int) -> None:
        self.inner_instrument.cc(control, value)

    def render(self, frames: int, sr: int) -> np.ndarray:
        return self.inner_instrument.render(frames, sr)

    def num_active_voices(self) -> int:
        return self.inner_instrument.num_active_voices()
