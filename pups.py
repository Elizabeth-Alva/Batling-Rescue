"""Crías perdidas: tienen nombre y carácter, chillan (y eso atrae enemigos)."""
import math
import random

from events import NoiseEvent
from settings import C_PUP

# solo algunas crías huyen de los bichos: la asustadiza y las inquietas. Las dormilonas siguen dormidas,
# las lloronas se quedan chillando en su sitio y las gemelas no pueden salir de su vagoneta.
FLEES = ('asustadiza', 'inquieta')
FLEE_SEE = 200                          # a qué distancia notan a un bicho
FLEE_LEASH = 150                        # no se alejan demasiado de su sitio (para que Mullo las encuentre)
INTERVAL_MULT = {'dormilona': 1.8, 'llorona': .6, 'inquieta': 1.0, 'asustadiza': 1.0, 'eco': 1.2, 'gemelas': .8}


def _blocked(cave, x, y):
    """Pared o agua: las crías no caminan por ahí."""
    return cave.solid_px(x, y) or cave.is_water(x, y)


class Pup:
    def __init__(self, x, y, name='Cría', behavior='inquieta', count=None):
        self.x, self.y = x, y
        self.home = (x, y)
        self.name, self.behavior = name, behavior
        self.count = count or (2 if behavior == 'gemelas' else 1)      # las gemelas cuentan como dos crías
        self.looks = [n.strip() for n in name.split(' y ')] if self.count > 1 else [name]   # aspecto de cada una
        self.t = random.uniform(.5, 2.5)
        self.ping = 0.0                      # tiempo restante de la flecha-guía en el HUD
        self.revealed = 0.0                  # tiempo restante marcada en el minimapa (por el grito)
        self.wander = None                   # destino de la cría inquieta / asustadiza
        self.wander_t = random.uniform(3, 7)
        self.say_t = random.uniform(2, 5)    # junto a Eco se oye el susurro de la Sala del Eco
        self.found = False                   # el jugador ya la vio de cerca (muestra su nombre)
        # animación: se mueven un poquito (pasitos, brincos y aleteos), no se quedan estáticas
        self.hop = 0.0                       # brinco en curso (s restantes)
        self.flap = random.uniform(0, 6)
        self.step_t = random.uniform(.6, 2.0)
        self.step = None
        self.lean = 0.0
        self.scared = 0.0                    # > 0 mientras huye de un bicho

    def update(self, dt, g):
        b = g.bat
        carried = b.carry is self
        self.t -= dt
        self.ping = max(0, self.ping - dt)
        self.revealed = max(0, self.revealed - dt)
        if not self.found and math.dist((self.x, self.y), (b.x, b.y)) < 170:
            self.found = True
        if self.t <= 0:
            p = g.diff
            self.t = p.pup_interval * INTERVAL_MULT.get(self.behavior, 1) * random.uniform(.8, 1.2) * (.7 if carried else 1)
            self.ping = 2.2
            self.hop = max(self.hop, .35)        # al chillar da un brinquito
            g.bus.emit(NoiseEvent(self.x, self.y, p.pup_noise_r * (.8 if carried else 1), C_PUP, 'pup'))
            g.sounds.play('squeak', (self.x, self.y), .9)
        self.hop = max(0.0, self.hop - dt)
        self.flap += dt * (22 if self.hop > 0 or carried else 5)
        if carried:
            return
        if self.behavior == 'eco':                       # la Sala del Eco: la cueva suena parecido a Mullo
            self.say_t -= dt
            if self.say_t <= 0:
                self.say_t = random.uniform(5, 8)
                if math.dist((self.x, self.y), (b.x, b.y)) < 420:
                    g.sounds.play('whisper', (self.x, self.y), .35)
        self.scared = max(0.0, self.scared - dt)
        if self.behavior in FLEES:
            self._wander(dt, g)
        if not self.wander:
            self._shuffle(dt, g)

    def _shuffle(self, dt, g):
        """Pasitos cortos alrededor de su sitio y, de vez en cuando, un brinco con aleteo."""
        self.step_t -= dt
        if self.step_t <= 0:
            self.step_t = random.uniform(.5, 1.6)
            r = 9 if self.behavior == 'gemelas' else 24
            a = random.uniform(0, math.tau)
            self.step = (self.home[0] + math.cos(a) * random.uniform(3, r), self.home[1] + math.sin(a) * random.uniform(2, r * .7))
            if random.random() < .5:
                self.hop = .35
        if self.step:
            dx, dy = self.step[0] - self.x, self.step[1] - self.y
            d = math.hypot(dx, dy)
            if d < 1:
                self.step = None
                return
            sp = min(d, (75 if self.hop > 0 else 32) * dt)
            nx, ny = self.x + dx / d * sp, self.y + dy / d * sp
            if not _blocked(g.cave, nx, ny):
                self.x, self.y = nx, ny
                self.lean = max(-.3, min(.3, dx / max(d, 1) * .3))
            else:
                self.step = None

    def sway(self, t):
        """Balanceo de cuerpo cuando está quieta (no se queda tiesa)."""
        return self.lean if self.step else .14 * math.sin(t * 2.6 + self.home[0])

    def lift(self):
        """Altura del brinco actual (px) para dibujarla."""
        return math.sin(math.pi * self.hop / .35) * 7 if self.hop > 0 else 0.0

    def _wander(self, dt, g):
        """Revolotea cerca de su sitio y, si ve un bicho cerca, se aleja de él (solo la asustadiza y las inquietas)."""
        cave = g.cave
        near = [e for e in g.enemies if e.kind != 'boss' and math.dist((e.x, e.y), (self.x, self.y)) < FLEE_SEE]
        if near:                                         # ¡un bicho! se aleja de él (sin irse muy lejos de su sitio)
            e = min(near, key=lambda e: math.dist((e.x, e.y), (self.x, self.y)))
            away = math.atan2(self.y - e.y, self.x - e.x)
            tx, ty = self.x, self.y
            for da in (0, .6, -.6, 1.2, -1.2, 1.7, -1.7):     # si hay pared, huye de lado
                a = away + da
                if not _blocked(cave, self.x + math.cos(a) * 30, self.y + math.sin(a) * 30):
                    tx, ty = self.x + math.cos(a) * 80, self.y + math.sin(a) * 80
                    break
            hx, hy = tx - self.home[0], ty - self.home[1]
            hd = math.hypot(hx, hy)
            if hd > FLEE_LEASH:
                tx, ty = self.home[0] + hx / hd * FLEE_LEASH, self.home[1] + hy / hd * FLEE_LEASH
            self.wander = (tx, ty)
            if self.scared <= 0:
                self.hop = .35                           # brinquito del susto
            self.scared = .6
        self.wander_t -= dt
        if self.wander is None and self.wander_t <= 0:
            self.wander_t = random.uniform(4, 8)
            a, r = random.uniform(0, math.tau), random.uniform(30, 90)
            self.wander = (self.home[0] + math.cos(a) * r, self.home[1] + math.sin(a) * r)
        if self.wander:
            dx, dy = self.wander[0] - self.x, self.wander[1] - self.y
            d = math.hypot(dx, dy)
            if d < 4:
                self.wander = None
                self.hop = .35
                return
            sp = (95 if self.scared > 0 else 55) * dt
            nx, ny = self.x + dx / d * sp, self.y + dy / d * sp
            if _blocked(cave, nx, ny):
                self.wander = None
                return
            self.x, self.y = nx, ny
