import mido, threading
from midi.messages import NoteOn, NoteOff, CC
from routing.bus import EventBus

def start_midi_listener(bus: EventBus, port_name_substr="Roland"):
    def run():
        inp = None
        names = mido.get_input_names()
        for n in names:
            if port_name_substr in n or "MIDI" in n:
                inp = n; break
        if not inp and names: inp = names[0]
        if not inp: 
            print("No MIDI inputs found."); return
        print("MIDI in:", inp)
        
        with mido.open_input(inp) as port:
            for msg in port:
                if msg.type == 'note_on' and msg.velocity > 0:
                    bus.post(NoteOn(msg.note, msg.velocity, getattr(msg, 'channel', 0)))
                elif msg.type in ('note_off',) or (msg.type == 'note_on' and msg.velocity == 0):
                    bus.post(NoteOff(msg.note, 0, getattr(msg, 'channel', 0)))
                elif msg.type == 'control_change':
                    bus.post(CC(msg.control, msg.value, getattr(msg, 'channel', 0)))

    th = threading.Thread(target=run, daemon=True); th.start()
    return th



def midi_to_freq(note: int) -> float:
    return 440.0 * (2 ** ((note - 69) / 12))