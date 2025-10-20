from routing.bus import EventBus
from audio.engine import AudioEngine
from audio.mixer import Mixer
from sequencing.clock import Clock
from sequencing.sequencer import StepSequencer, Step
import time

from instruments.additive import make_spectral_frequency, PartialCharacteristics
from instruments.envelopes.adsr import ADSR
from instruments.midi import midi_to_freq_equal_tempered, MidiInstrumentAdapter

SR = 44100
BLOCK = 256

bus = EventBus()

# Build instruments

partials_lead = {
    1.00: PartialCharacteristics(1.0, 0.0, ADSR(0.01, 0.2, 0.7, 0.4)), 
    2.00: PartialCharacteristics(0.6, 0.0, ADSR(0.02, 0.12, 0.02, 0.25)),
    3.00: PartialCharacteristics(0.2, 0.0, ADSR(0.05, 0.10, 0.1, 0.8)),
    3.01: PartialCharacteristics(0.2, 0.0, ADSR(0.05, 0.05, 0.05, 0.7)),
}

lead = make_spectral_frequency(partials=partials_lead, master=0.8, velocity_curve=1.6)

midi_to_freq = lambda note: midi_to_freq_equal_tempered(note, n_tones=12)
lead = MidiInstrumentAdapter(lead, midi_to_freq)


partials_bass = {
    1.00: PartialCharacteristics(1.0, 0.0, ADSR(0.01, 0.08, 0.05, 0.4)), 
    2.00: PartialCharacteristics(0.1, 0.0, ADSR(0.02, 0.05, 0.02, 0.25)),
    3.00: PartialCharacteristics(0.2, 0.0, ADSR(0.05, 0.10, 0.1, 0.8)),
    4.01: PartialCharacteristics(0.2, 0.0, ADSR(0.05, 0.05, 0.05, 0.7)),
    4.1: PartialCharacteristics(0.2, 0.0, ADSR(0.05, 0.05, 0.05, 0.7)),
    4.15: PartialCharacteristics(0.2, 0.0, ADSR(0.05, 0.05, 0.05, 0.7)),
}

bass = make_spectral_frequency(partials=partials_bass, master=0.8, velocity_curve=1.6)
bass = MidiInstrumentAdapter(bass, midi_to_freq)




# Mixer with two tracks
mixer = Mixer()
mixer.add_track(0, bass, gain=1.0, pan=-1)   
mixer.add_track(0, lead, gain=1.0, pan=0)   

engine = AudioEngine(mixer, bus, sr=SR, blocksize=BLOCK, channels=2,  # try stereo to hear the pan
                     pre_gain=0.3, limiter_drive=1.15, meter_period=1.0, 
                     record_to="D:\\Music\\demo_mixer.wav")
engine.start()

# Two sequencers on two channels
steps_bass = [Step(pitch=45 + (i % 4) * 2, vel=85, gate=0.6) if i % 4 != 3 else Step(pitch=None) for i in range(16)]
steps_lead = [Step(pitch=69 + ((i*3) % 7), vel=95, gate=0.45) if i % 2 == 0 else Step(pitch=None) for i in range(16)]

seq_bass = StepSequencer(bus, steps_bass, steps_per_beat=4)
seq_lead = StepSequencer(bus, steps_lead, steps_per_beat=4)

clock = Clock(bpm=60, ppq=24)
clock.start(lambda: (seq_bass.on_tick(ppq=24), seq_lead.on_tick(ppq=24)))

print("Mixer demo running. Ctrl+C to quit.")
try:
    while True: time.sleep(1)
except KeyboardInterrupt:
    clock.stop()
    engine.stop()
