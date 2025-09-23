import queue
from typing import Union
from midi.messages import NoteOn, NoteOff, CC

Event = Union[NoteOn, NoteOff, CC]

class EventBus:
    def __init__(self, maxsize=1024) -> None:
        self.q = queue.Queue(maxsize=maxsize)

    def post(self, e: Event) -> None:
        self.q.put_nowait(e)

    def drain(self, max_events=128):
        evs = []
        try:
            while len(evs) < max_events:
                evs.append(self.q.get_nowait())
        except queue.Empty:
            pass
        return evs
