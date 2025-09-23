from dataclasses import dataclass

@dataclass(frozen=True)
class NoteOn:  
    note: int
    velocity: int
    channel: int = 0

@dataclass(frozen=True)
class NoteOff: 
    note: int
    velocity: int = 0
    channel: int = 0

@dataclass(frozen=True)
class CC:
    control: int
    value: int
    channel: int = 0
