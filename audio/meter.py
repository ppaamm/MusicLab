import threading, math

_EPS = 1e-12

def lin_to_dbfs(x: float) -> float:
    return 20.0 * math.log10(max(_EPS, x))

class AudioMeter:
    """
    Real-time meter with ~1s windows.
    Called from audio callback (update) and from a logger thread (snapshot).
    """
    def __init__(self, window_sec: float = 1.0):
        self.window_sec = window_sec
        self.lock = threading.Lock()
        self.reset_locked()

    def reset_locked(self):
        # accumulators for current window
        self.frames = 0
        self.sum_sq = 0.0
        self.peak_post = 0.0       # post-limiter peak in this window
        self.peak_pre = 0.0        # pre-limiter peak in this window
        self.limiter_engaged = 0   # how many blocks had limiting

    def update(self, pre_peak: float, post_peak: float, block_rms: float, limited: bool, frames: int):
        # Called from the audio callback
        with self.lock:
            self.frames += frames
            self.sum_sq += (block_rms * block_rms) * frames
            if post_peak > self.peak_post: self.peak_post = post_peak
            if pre_peak  > self.peak_pre:  self.peak_pre  = pre_peak
            if limited: self.limiter_engaged += 1

    def snapshot_and_reset(self):
        # Called from a non-RT thread every ~1s
        with self.lock:
            if self.frames > 0:
                rms_lin = math.sqrt(self.sum_sq / self.frames)
            else:
                rms_lin = 0.0
            snap = {
                "peak_post_lin": self.peak_post,
                "peak_pre_lin":  self.peak_pre,
                "rms_lin":       rms_lin,
                "peak_post_db":  lin_to_dbfs(self.peak_post),
                "peak_pre_db":   lin_to_dbfs(self.peak_pre),
                "rms_db":        lin_to_dbfs(rms_lin),
                "limited_blocks": self.limiter_engaged,
                "frames": self.frames,
            }
            self.reset_locked()
            return snap
