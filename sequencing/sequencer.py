from dataclasses import dataclass
from typing import List
from midi.messages import NoteOn, NoteOff
from routing.bus import EventBus

@dataclass
class Step:
    pitch: int | None  # None = rest
    vel: int = 100
    gate: float = 0.5  # fraction of step

class StepSequencer:
    def __init__(self, bus: EventBus, steps: List[Step], 
                 steps_per_beat=4, 
                 channel: int = 0, 
                 loop: bool = True):
        self.bus = bus
        self.steps = steps
        self.channel = int(channel)
        self.loop = bool(loop)
        
        self.idx = 0
        self.steps_per_beat = steps_per_beat
        self.tick_count = 0

    def on_tick(self, ppq=24):
        ticks_per_step = ppq // self.steps_per_beat
        gate_ticks = int(ticks_per_step * (self.steps[self.idx].gate if self.steps[self.idx].pitch is not None else 0))

        if self.tick_count % ticks_per_step == 0:
            s = self.steps[self.idx]
            if s.pitch is not None:
                self.bus.post(NoteOn(s.pitch, s.vel, self.channel))
        if gate_ticks and (self.tick_count % ticks_per_step) == gate_ticks:
            s = self.steps[self.idx]
            if s.pitch is not None:
                self.bus.post(NoteOff(s.pitch, self.channel))
        if (self.tick_count % ticks_per_step) == (ticks_per_step - 1):
            self.idx = (self.idx + 1) % len(self.steps)

        self.tick_count += 1
