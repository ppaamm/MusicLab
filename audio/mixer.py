from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple
import numpy as np
import threading

# Events (same shape your bus posts)
from midi.messages import NoteOn, NoteOff, CC

@dataclass
class Track:
    # Instrument must implement MidiInstrument: note_on, note_off, cc
    # TODO: change that to make it more general?
    instrument: object       
    gain: float = 1.0        
    pan: float = 0.0         # -1 = left, 0 = center, +1 = right
    mute: bool = False
    solo: bool = False

class Mixer:
    """
    Thread-safe mixer. Routes events by `channel` to tracks and renders a mixed buffer.
    Tracks are indexed by MIDI channel (int).
    """
    def __init__(self):
        self._tracks: Dict[int, Track] = {}
        self._lock = threading.Lock()


    ###########################################################################
    ##                        TRACK MANAGEMENT                              ##
    ###########################################################################

    def add_track(self, channel: int, instrument: object, *, gain: float = 1.0, pan: float = 0.0) -> None:
        with self._lock:
            self._tracks[int(channel)] = Track(instrument=instrument, 
                                               gain=float(gain), 
                                               pan=float(pan))

    def remove_track(self, channel: int) -> None:
        with self._lock:
            self._tracks.pop(int(channel), None)

    def set_gain(self, channel: int, gain: float) -> None:
        with self._lock:
            if ch := self._tracks.get(int(channel)):
                ch.gain = float(gain)

    def set_pan(self, channel: int, pan: float) -> None:
        with self._lock:
            if ch := self._tracks.get(int(channel)):
                ch.pan = float(max(-1.0, min(1.0, pan)))

    def set_mute(self, channel: int, mute: bool) -> None:
        with self._lock:
            if ch := self._tracks.get(int(channel)):
                ch.mute = bool(mute)

    def set_solo(self, channel: int, solo: bool) -> None:
        with self._lock:
            if ch := self._tracks.get(int(channel)):
                ch.solo = bool(solo)

    
    ###########################################################################
    ##                          EVENT ROUTING                                ##
    ###########################################################################

    def route_event(self, e: object) -> None:
        """
        Forward a single NoteOn/NoteOff/CC to the track matching e.channel (default 0 if missing).
        """
        ch = getattr(e, "channel", 0)
        inst = None
        with self._lock:
            tr = self._tracks.get(int(ch))
            if tr:
                inst = tr.instrument
        if inst is None:
            return
        if isinstance(e, NoteOn):
            inst.note_on(e.note, e.velocity)
        elif isinstance(e, NoteOff):
            inst.note_off(e.note)
        elif isinstance(e, CC):
            inst.cc(e.control, e.value)

    def route_events(self, events: Iterable[object]) -> None:
        for e in events:
            self.route_event(e)

    ###########################################################################
    ##                             RENDERING                                 ##
    ###########################################################################
    
    @staticmethod
    def _pan_gains(pan: float) -> Tuple[float, float]:
        """
        Equal-power pan law. pan ∈ [-1..+1] -> (gL, gR).
        """
        p = max(-1.0, min(1.0, pan))
        # map [-1..+1] -> [0..1] angle
        angle = (p + 1.0) * 0.25 * np.pi  # 0..pi/2
        gL = np.cos(angle)
        gR = np.sin(angle)
        return float(gL), float(gR)

    def render(self, frames: int, sr: int, channels: int = 1) -> np.ndarray:
        """
        Sum all tracks into mono (channels==1) or stereo (channels==2).
        Assumes each instrument.render(frames, sr) returns mono np.float32.
        """
        if channels not in (1, 2):
            raise ValueError("Only mono or stereo mixing supported currently.")

        # snapshot tracks outside of audio work
        with self._lock:
            tracks = list(self._tracks.items())  # [(ch, Track), ...]
            any_solo = any(t.solo for _, t in tracks)

        if channels == 1:
            mix = np.zeros(frames, dtype=np.float32)
        else:
            mix = np.zeros((frames, 2), dtype=np.float32)

        for ch, tr in tracks:
            if tr.mute:
                continue
            if any_solo and not tr.solo:
                continue

            buf = tr.instrument.render(frames, sr).astype(np.float32)  # mono
            if channels == 1:
                mix += tr.gain * buf
            else:
                gL, gR = self._pan_gains(tr.pan)
                mix[:, 0] += tr.gain * gL * buf
                mix[:, 1] += tr.gain * gR * buf

        return mix
