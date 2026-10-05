"""Crías perdidas: chillan periódicamente (y eso atrae enemigos)."""
import random

from events import NoiseEvent
from settings import C_PUP


class Pup:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.t = random.uniform(.5, 2.5)
        self.ping = 0.0                      # tiempo restante de la flecha-guía en el HUD

    def update(self, dt, g):
        self.t -= dt
        self.ping = max(0, self.ping - dt)
        if self.t <= 0:
            carried = g.bat.carry is self
            p = g.diff
            self.t = p.pup_interval * random.uniform(.8, 1.2) * (.7 if carried else 1)
            self.ping = 2.2
            g.bus.emit(NoiseEvent(self.x, self.y, p.pup_noise_r * (.8 if carried else 1), C_PUP, 'pup'))
            g.sounds.play('squeak', (self.x, self.y), .9)
