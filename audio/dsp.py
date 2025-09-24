import numpy as np

def db_to_lin(db: float) -> float:
    return 10.0 ** (db / 20.0)

def soft_clip(x: np.ndarray, drive: float = 1.5) -> np.ndarray:
    # Smooth limiter. drive ~ 1.2–2.0
    return np.tanh(drive * x) / np.tanh(drive)

def voice_count_comp(num_voices: int, base: float = 0.8) -> float:
    # -3 dB per doubling of active voices + headroom
    import math
    return base / math.sqrt(max(1, num_voices))
