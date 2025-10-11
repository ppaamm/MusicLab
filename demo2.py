from routing.bus import EventBus
from audio.engine import AudioEngine
from instruments.additive import make_additive_poly
from sequencing.clock import Clock
from sequencing.sequencer import StepSequencer, Step
import time

SR = 44100
BLOCK = 256

if __name__ == "__main__":
    # Event bus
    bus = EventBus()

    # Instrument: additive poly synth
    inst = make_additive_poly(
        master=1.2,          # instrument-level gain
        n_partials=5,         # harmonics count
        power=2.0,            # 1/(k^power) rolloff
        env_attack=0.5,     # ADSR params
        env_decay=0.5,
        env_sustain=0.3,
        env_release=0.20,
        velocity_curve=1.8,
    )
    

    # Audio engine (must be the updated version that passes sr into instrument.render)
    engine = AudioEngine(inst, bus, sr=SR, blocksize=BLOCK, channels=1,
                         pre_gain=0.3, limiter_drive=1.15, meter_period=1.0)
    engine.start()

    # 1-bar 16-step pattern at 60 BPM (ppq=24), skipping every 4th step
    steps = [
        Step(pitch=69 + ((i) % 4) * 2, vel=min(127, 20 * (i % 4) + 25), gate=0.6)
        if i % 4 != 3 else Step(pitch=None)
        for i in range(16)
    ]
    seq = StepSequencer(bus, steps, steps_per_beat=4)

    clock = Clock(bpm=10, ppq=24)
    clock.start(lambda: seq.on_tick(ppq=24))

    print("Loop running. Ctrl+C to quit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        clock.stop()
        engine.stop()
