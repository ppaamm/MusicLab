import time
import threading
import mido

from routing.bus import EventBus
from midi.messages import NoteOn, NoteOff, CC
from audio.engine import AudioEngine
from instruments.additive import make_additive_poly


def start_midi_listener(bus: EventBus, port_hint: str = "Roland"):
    """
    Open a MIDI input (prefer one containing `port_hint`) and forward events to the EventBus.
    Returns the thread object (daemon).
    """
    def _runner():
        # Pick a MIDI port
        names = mido.get_input_names()
        if not names:
            print("[MIDI] No MIDI inputs found.")
            return
        chosen = None
        for n in names:
            if port_hint.lower() in n.lower():
                chosen = n
                break
        if chosen is None:
            chosen = names[0]
        print(f"[MIDI] Using input: {chosen}")

        # Forward messages into the bus
        try:
            with mido.open_input(chosen) as port:
                for msg in port:
                    t = msg.type
                    if t == "note_on" and msg.velocity > 0:
                        bus.post(NoteOn(msg.note, msg.velocity, getattr(msg, "channel", 0)))
                    elif t == "note_off" or (t == "note_on" and msg.velocity == 0):
                        bus.post(NoteOff(msg.note, 0, getattr(msg, "channel", 0)))
                    elif t == "control_change":
                        bus.post(CC(msg.control, msg.value, getattr(msg, "channel", 0)))
                    # (Optional) Pitch bend, aftertouch, etc., can be added here.
        except Exception as e:
            print(f"[MIDI] Listener stopped: {e}")

    th = threading.Thread(target=_runner, daemon=True)
    th.start()
    return th


def main():
    SR = 44100
    BLOCK = 256

    # Event bus
    bus = EventBus()

    # Instrument (safe defaults to avoid saturation)
    inst = make_additive_poly(
        master=0.55,          # instrument-level gain
        n_partials=6,         # number of harmonics
        power=6.0,            # 1/(k^power) rolloff
        env_attack=0.005,
        env_release=0.20,
        velocity_curve=1.8,
    )

    # Audio engine (passes sr into instrument.render)
    engine = AudioEngine(
        inst, bus,
        sr=SR, blocksize=BLOCK, channels=1,
        pre_gain=0.30,        # extra headroom
        limiter_drive=1.15,   # gentle safety
        meter_period=1.0
    )
    engine.start()

    # MIDI input from Roland
    start_midi_listener(bus, port_hint="Roland")

    print("Play your Roland! (Ctrl+C to quit)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping…")
    finally:
        engine.stop()


if __name__ == "__main__":
    main()
