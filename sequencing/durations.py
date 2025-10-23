def beats_to_ticks(beats: float, ppq: int) -> int:
    return max(1, int(round(beats * ppq)))

def half(ppq: int) -> int:
    return beats_to_ticks(2.0, ppq)

def quarter(ppq: int) -> int:
    return beats_to_ticks(1.0, ppq)

def eigth(ppq: int) -> int:
    return beats_to_ticks(0.5, ppq)

def sixteenth(ppq: int) -> int:  
    return beats_to_ticks(0.25, ppq)

def dotted(beats: float) -> float:
    return beats * 1.5

def triplet(beats: float) -> float:
    return beats / 3.0 * 2.0  # e.g., quarter-triplet = 2/3 beat
