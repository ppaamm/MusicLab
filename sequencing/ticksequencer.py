from dataclasses import dataclass
from typing import Optional
from typing import List, Optional
from midi.messages import NoteOn, NoteOff
from routing.bus import EventBus

@dataclass
class TickStep:
    pitch: Optional[int]          # None = rest
    vel: int = 90                 # 0..127
    duration_ticks: int = 24      # how long this step "occupies" the timeline (in clock ticks)
    gate: float = 0.9             # fraction of duration_ticks the note is held (0..1)
    
    

class TickSequencer:
    def __init__(self, bus: EventBus, steps: List[TickStep], *,
                 channel: int = 0, loop: bool = True):
        self.bus = bus
        self.steps = steps
        self.channel = int(channel)
        self.loop = bool(loop)

        self._idx = -1                 # no step yet; first tick will start step 0
        self._ticks_left_in_step = 0
        self._pending_note: Optional[int] = None
        self._gate_ticks_left = 0

    def reset(self):
        self._idx = -1
        self._ticks_left_in_step = 0
        self._pending_note = None
        self._gate_ticks_left = 0

    def _start_next_step(self) -> None:
        # advance index & wrap
        self._idx += 1
        if self._idx >= len(self.steps):
            if not self.loop or not self.steps:
                # leave idx at end; nothing to do; on_tick will just return
                self._idx = len(self.steps) - 1
                self._ticks_left_in_step = 0
                return
            self._idx = 0

        st = self.steps[self._idx]
        self._ticks_left_in_step = max(1, int(st.duration_ticks))

        # fire NoteOn if not a rest
        if st.pitch is not None:
            gate_ticks = max(1, int(round(st.gate * self._ticks_left_in_step)))
            self.bus.post(NoteOn(st.pitch, st.vel, channel=self.channel))
            self._pending_note = st.pitch
            self._gate_ticks_left = gate_ticks
        else:
            self._pending_note = None
            self._gate_ticks_left = 0

    def on_tick(self, *, ppq: int):
        # 1) Start a new step if needed
        if self._ticks_left_in_step <= 0:
            if not self.steps:
                return
            self._start_next_step()
            # If we just started a step and there are still 0 ticks (empty list / loop off), bail
            if self._ticks_left_in_step <= 0:
                return

        # 2) Handle NoteOff timing (happens after any NoteOn on the same tick)
        if self._pending_note is not None and self._gate_ticks_left > 0:
            self._gate_ticks_left -= 1
            if self._gate_ticks_left == 0:
                self.bus.post(NoteOff(self._pending_note, channel=self.channel))
                self._pending_note = None

        # 3) Consume one tick of the current step
        self._ticks_left_in_step -= 1