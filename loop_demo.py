from routing.bus import EventBus
from audio.engine import AudioEngine
from instruments.signals.additive.instrument import AdditiveInstrument
from sequencing.clock import Clock
from sequencing.sequencer import StepSequencer, Step
import time

if __name__ == "__main__":
    bus = EventBus()
    inst = AdditiveInstrument()
    engine = AudioEngine(inst, bus, sr=44100, blocksize=256, channels=1)
    engine.start()

    # 1-bar 16-step pattern at 120 BPM
    steps = [Step(pitch=69 + (i%4)*2, vel=20*(i%4)+25, gate=0.6) if i%4!=3 else Step(pitch=None) for i in range(16)]
    seq = StepSequencer(bus, steps, steps_per_beat=4)
    clock = Clock(bpm=60, ppq=24)
    clock.start(lambda: seq.on_tick(ppq=24))

    print("Loop running. Ctrl+C to quit.")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        clock.stop(); engine.stop()
