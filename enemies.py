"""Enemigos: arañas con IA de patrulla / investigación / persecución sobre la cueva."""
import math
import random

SPECS = {
    # spd: velocidad, hear: oído, det: detección visual, dmg: daño por contacto,
    # stun: cuánto les afecta el grito / el escudo (1 = normal)
    'spider':   dict(spd=1.0,  hear=1.0, det=1.0, hp=2, rad=12, size=1.0,  dmg=1, stun=1.0),
    'runner':   dict(spd=1.55, hear=0.8, det=1.0, hp=1, rad=10, size=0.8,  dmg=1, stun=1.0),
    'listener': dict(spd=0.85, hear=1.7, det=0.6, hp=3, rad=14, size=1.25, dmg=1, stun=1.0),
    # depredadores: más grandes, resistentes y letales
    'predator': dict(spd=0.95, hear=1.3, det=1.3, hp=5, rad=22, size=2.0,  dmg=1, stun=.55),
    'behemoth': dict(spd=0.85, hear=1.5, det=1.5, hp=8, rad=30, size=3.0,  dmg=2, stun=.35),
}
BIG = ('predator', 'behemoth')


def pick_kind(p, enemies=()):
    """Elige el tipo del próximo enemigo según la dificultad (con tope de depredadores)."""
    big = sum(1 for e in enemies if e.kind in BIG)
    r = random.random()
    if big < p.max_predators:
        if r < p.behemoth_chance:
            return 'behemoth'
        if r < p.behemoth_chance + p.predator_chance:
            return 'predator'
    r = random.random()
    if r < p.listener_chance:
        return 'listener'
    if r < p.listener_chance + p.runner_chance:
        return 'runner'
    return 'spider'


class Enemy:
    def __init__(self, x, y, kind='spider'):
        self.x, self.y, self.kind = x, y, kind
        self.spec = SPECS[kind]
        self.hp, self.state, self.target = self.spec['hp'], 'patrol', None
        self.wait = self.stun = self.lose = self.vx = self.vy = 0.0
        self.anim = random.random() * 9
        self.path, self.repath = [], random.random() * .6
        self.face = 0.0                       # hacia dónde mira (para dibujar a los grandes)

    @property
    def rad(self):
        return self.spec['rad']

    # ------------------------------------------------------------ ruido
    def hear(self, x, y, r, mult):
        if self.state == 'chase' or self.stun > 0:
            return
        if math.dist((self.x, self.y), (x, y)) < r * mult * self.spec['hear']:
            self.state, self.target, self.wait, self.path = 'inv', (x, y), 0.0, []

    # ------------------------------------------------------------ IA
    def update(self, dt, g):
        b, cave, p = g.bat, g.cave, g.diff
        d = math.dist((self.x, self.y), (b.x, b.y))
        self.anim += dt
        if self.stun > 0:
            self.stun -= dt
            self.vx *= .9
            self.vy *= .9
            self.x += self.vx * dt
            self.y += self.vy * dt
            cave.resolve(self, self.rad)
            return
        spec = self.spec
        exposed = b.exposed > 0 and d < p.expose_radius          # el sonar te delata a los cercanos
        if (d < p.detect_radius * spec['det'] or exposed) and self.state != 'chase':
            self.state, self.lose, self.path = 'chase', 0.0, []
            g.sounds.play('growl', (self.x, self.y), .8)
        goal, sp = None, 0.0
        if self.state == 'chase':
            goal, sp = (b.x, b.y), p.chase_speed * spec['spd']
            self.lose = self.lose + dt if (d > 350 and not exposed) else 0
            if self.lose > 2.5:
                self.state, self.target, self.path = 'patrol', None, []
        elif self.state == 'inv':
            goal, sp = self.target, p.investigate_speed * spec['spd']
            if math.dist((self.x, self.y), goal) < 18:
                self.wait, sp = self.wait + dt, 0
                if self.wait > 1.8:
                    self.state, self.target, self.path = 'patrol', None, []
            elif self.wait > 14:               # no llega (atascado): se rinde
                self.state, self.target, self.path = 'patrol', None, []
            else:
                self.wait += dt * .25
        else:
            sp, self.wait = p.patrol_speed * spec['spd'], self.wait + dt
            if not self.target or math.dist((self.x, self.y), self.target) < 18 or self.wait > 8:
                self.target, self.wait, self.path = cave.near_spot(self.x, self.y, 520), 0.0, []
            goal = self.target
        if goal and sp:
            self._move(dt, goal, sp, cave)
        else:
            self.vx = self.vy = 0
        cave.resolve(self, self.rad)

    def _move(self, dt, goal, sp, cave):
        pos = (self.x, self.y)
        if cave.los(pos, goal):
            wp, self.path = goal, []
        else:
            self.repath -= dt
            if self.repath <= 0 or not self.path:
                self.repath = .6 + random.random() * .2
                self.path = cave.path(pos, goal) or []
            while len(self.path) > 1 and (math.dist(pos, self.path[0]) < 14 or cave.los(pos, self.path[1])):
                self.path.pop(0)
            wp = self.path[0] if self.path else goal
        dx, dy = wp[0] - self.x, wp[1] - self.y
        n = math.hypot(dx, dy) or 1
        self.vx, self.vy = dx / n * sp, dy / n * sp
        self.face = math.atan2(dy, dx)
        self.x += self.vx * dt
        self.y += self.vy * dt
