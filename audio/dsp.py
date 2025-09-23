import numpy as np

def db_to_lin(db: float) -> float:
    return 10.0 ** (db / 20.0)

def soft_clip(x: np.ndarray, drive: float = 1.5) -> np.ndarray:
    return np.tanh(drive * x) / np.tanh(drive)
