from routing.bus import EventBus
from audio.engine import AudioEngine
from sequencing.clock import Clock
from sequencing.sequencer import StepSequencer, Step
import time

from instruments.additive import make_additive_frequency
from instruments.midi import midi_to_freq_equal_tempered, MidiInstrumentAdapter

SR = 44100
BLOCK = 256

if __name__ == "__main__":
    # Event bus
    bus = EventBus()

    # Instrument: additive synth with a MIDI note API (wrapping the freq-based version)
    # You can swap midi_to_freq=... to try alternate tunings.
    inst = make_additive_frequency(
        master=1,           # instrument-level gain (might be hot; adjust if needed)
        partials = {1.: 1., 2.0: 0.3, 5.0: 0.7},
        env_attack=0.01,       # ADSR params
        env_decay=0.1,
        env_sustain=0.8,
        env_release=0.2,
        velocity_curve=1.5
    )
    
    
    midi_to_freq = lambda note: midi_to_freq_equal_tempered(note, n_tones=12)
    inst = MidiInstrumentAdapter(inst, midi_to_freq)
    
    # Audio engine (passes sr into instrument.render)
    engine = AudioEngine(
        inst, bus,
        sr=SR, blocksize=BLOCK, channels=1,
        pre_gain=0.3, limiter_drive=1.15, meter_period=1.0
    )
    engine.start()

    # 1-bar 16-step pattern at 60 BPM (ppq=24), skipping every 4th step
    steps = [
        Step(pitch=69 + ((i) % 4) * 2, vel=min(127, 20 * (i % 4) + 25), gate=0.6)
        if i % 4 != 3 else Step(pitch=None)
        for i in range(16)
    ]
    seq = StepSequencer(bus, steps, steps_per_beat=4)

    clock = Clock(bpm=60, ppq=24)
    clock.start(lambda: seq.on_tick(ppq=24))

    print("Loop running. Ctrl+C to quit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        clock.stop()
        engine.stop()
