import threading, time

class Clock:
    def __init__(self, bpm=120.0, ppq=24):
        self.bpm = bpm; self.ppq = ppq; self.running = False
        self._th = None

    def start(self, tick_fn):
        self.running = True
        spb = 60.0 / self.bpm
        spt = spb / self.ppq   # seconds per tick
        def run():
            next_t = time.perf_counter()
            while self.running:
                tick_fn()
                next_t += spt
                sleep = next_t - time.perf_counter()
                if sleep > 0: time.sleep(sleep)
        self._th = threading.Thread(target=run, daemon=True); self._th.start()

    def stop(self):
        self.running = False
