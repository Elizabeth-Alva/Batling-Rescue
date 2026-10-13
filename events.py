"""Bus de eventos mínimo: desacopla quien genera ruido de quien lo escucha."""
from dataclasses import dataclass


@dataclass
class NoiseEvent:
    x: float
    y: float
    radius: float
    color: tuple = (255, 255, 255)
    source: str = ''            # 'pup' | 'screech' | 'impact'


@dataclass
class ImpactEvent:
    x: float
    y: float
    speed: float


class EventBus:
    def __init__(self):
        self._subs = {}

    def subscribe(self, cls, fn):
        self._subs.setdefault(cls, []).append(fn)

    def emit(self, evt):
        for fn in self._subs.get(type(evt), ()):
            fn(evt)
