"""Enemigos: animales con hambre en un año de sequía que reaccionan al ruido (no son villanos).

Arañas: lentas, patrullan cerca de sus telarañas. El grito las aturde y las daña.
Escarabajos: acorazados y tercos; oyen los chillidos y van a investigar. Aguantan más.
Cazadores (ciempiés): rápidos, cazan con el oído; te persiguen al verte y pierden el rastro si te alejas.
   El grito solo los aturde un momento.
Jefe (Gran Ciempiés de la Mina): gigante, no se puede vencer. Solo se puede huir.
"""
import math
import random

from settings import NEST, SAFE_R

SPECS = {
    # spd: velocidad, hear: oído, det: vista, hp: vida, rad: radio, size: tamaño de dibujo, dmg: daño por contacto,
    # stun: cuánto les afecta el grito / el escudo, push: cuánto los empuja, lose: segundos hasta perder el rastro,
    # leash: distancia máxima a su casa al patrullar (None = libre)
    'spider': dict(spd=1.0, hear=1.0, det=1.0, hp=2, rad=12, size=1.0, dmg=1, stun=1.0, push=1.0, lose=2.5, leash=320),
    'beetle': dict(spd=.85, hear=1.7, det=.85, hp=4, rad=14, size=1.1, dmg=1, stun=.8, push=.45, lose=3.5, leash=None),
    'hunter': dict(spd=1.55, hear=2.2, det=1.35, hp=3, rad=13, size=1.0, dmg=1, stun=.3, push=.7, lose=1.3, leash=None),
    'boss':   dict(spd=1.0, hear=0.0, det=0.0, hp=10 ** 9, rad=40, size=3.0, dmg=2, stun=.12, push=0.0, lose=99, leash=None),
}
NAMES = {'spider': 'araña', 'beetle': 'escarabajo', 'hunter': 'cazador', 'boss': 'Gran Ciempiés'}
BOSS_SPEED = 178          # más lento que Mullo cargando crías (211) y mucho más que el impulso
BOSS_WAKE_T = 1.6        # tarda en despertar del todo: Mullo tiene un instante para huir
MAX_HUNTERS = 3


def pick_kind(weights, enemies=()):
    """Elige el tipo del próximo enemigo según los pesos del nivel (con tope de cazadores)."""
    hunters = sum(1 for e in enemies if e.kind == 'hunter')
    opts = [(k, w) for k, w in weights.items() if not (k == 'hunter' and hunters >= MAX_HUNTERS)]
    r, acc = random.random() * sum(w for _, w in opts), 0.0
    for k, w in opts:
        acc += w
        if r <= acc:
            return k
    return opts[-1][0]


class Enemy:
    def __init__(self, x, y, kind='spider', home=None):
        self.x, self.y, self.kind = x, y, kind
        self.spec = SPECS[kind]
        self.home = home or (x, y)
        self.hp, self.state, self.target = self.spec['hp'], 'patrol', None
        self.wait = self.stun = self.lose = self.vx = self.vy = 0.0
        self.anim = random.random() * 9
        self.path, self.repath = [], random.random() * .6
        self.face = random.uniform(0, math.tau)       # hacia dónde mira
        n, gap = (7, 8) if kind == 'hunter' else (16, 17) if kind == 'boss' else (0, 0)
        self.gap = gap
        self.segs = [(x - math.cos(self.face) * gap * i, y - math.sin(self.face) * gap * i) for i in range(n)]

    @property
    def rad(self):
        return self.spec['rad']

    # ------------------------------------------------------------ ruido
    def hear(self, x, y, r, mult):
        if self.state in ('chase', 'sleep', 'return') or self.stun > 0:
            return
        if math.dist((self.x, self.y), (x, y)) < r * mult * self.spec['hear']:
            self.state, self.target, self.wait, self.path = 'inv', (x, y), 0.0, []

    def hit_by_screech(self, bx, by):
        """El grito: aturde siempre; daña a arañas, escarabajos y cazadores (al jefe no)."""
        d = math.dist((self.x, self.y), (bx, by)) or 1
        if self.kind != 'boss':
            self.hp -= 1
        self.stun = max(self.stun, (1.9 if self.kind != 'hunter' else 1.0) * self.spec['stun'] + .15)
        k = 260 * self.spec['push']
        self.vx, self.vy = (self.x - bx) / d * k, (self.y - by) / d * k
        if self.kind == 'hunter' and self.state == 'chase':
            self.state, self.path = 'inv', []
            self.target = (bx, by)

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
            self._finish(cave)
            return
        spec = self.spec
        bat_safe = math.dist((b.x, b.y), NEST) < SAFE_R or cave.in_secret(b.x, b.y)    # nido o sala secreta
        if (d < p.detect_radius * spec['det'] and self.state != 'chase' and not bat_safe and cave.los((self.x, self.y), (b.x, b.y), False)
                and not (hasattr(g, 'hidden_by_curtain') and g.hidden_by_curtain((self.x, self.y), (b.x, b.y)))):
            self.state, self.lose, self.path = 'chase', 0.0, []
            g.sounds.play('growl', (self.x, self.y), .7)
            if hasattr(g, 'spotted'):                      # aviso: "te vieron"
                g.spotted(self)
        goal, sp = None, 0.0
        if self.state == 'chase':
            goal, sp = (b.x, b.y), p.chase_speed * spec['spd']
            far = 300 if self.kind == 'hunter' else 350
            self.lose = self.lose + dt * (3 if bat_safe else 1) if (d > far or bat_safe) else 0
            if self.lose > spec['lose']:
                self.state, self.target, self.path = 'patrol', None, []
        elif self.state == 'inv':
            goal, sp = self.target, p.investigate_speed * spec['spd']
            patience = 3.5 if self.kind == 'beetle' else 1.8          # los escarabajos son tercos
            if math.dist((self.x, self.y), goal) < 18:
                self.wait, sp = self.wait + dt, 0
                if self.wait > patience:
                    self.state, self.target, self.path = 'patrol', None, []
            elif self.wait > 14:               # no llega (atascado o al otro lado del agua): se rinde
                self.state, self.target, self.path = 'patrol', None, []
            else:
                self.wait += dt * .25
        else:
            sp, self.wait = p.patrol_speed * spec['spd'], self.wait + dt
            if not self.target or math.dist((self.x, self.y), self.target) < 18 or self.wait > 8:
                if spec['leash']:
                    self.target = cave.near_spot(*self.home, spec['leash'])
                else:
                    self.target = cave.near_spot(self.x, self.y, 520)
                self.wait, self.path = 0.0, []
            goal = self.target
        if goal and sp:
            self._move(dt, goal, sp, cave)
        else:
            self.vx = self.vy = 0
        self._finish(cave)

    def _finish(self, cave):
        """Colisión, zona segura (nadie entra al punto de entrega) y cuerpo segmentado."""
        cave.resolve(self, self.rad, walk=True)
        dx, dy = self.x - NEST[0], self.y - NEST[1]
        dn = math.hypot(dx, dy) or 1
        if dn < SAFE_R + self.rad:
            self.x, self.y = NEST[0] + dx / dn * (SAFE_R + self.rad), NEST[1] + dy / dn * (SAFE_R + self.rad)
            cave.resolve(self, self.rad, walk=True)
        if self.segs:
            self.segs[0] = (self.x, self.y)
            for i in range(1, len(self.segs)):
                px, py = self.segs[i - 1]
                sx, sy = self.segs[i]
                ddx, ddy = sx - px, sy - py
                n = math.hypot(ddx, ddy) or 1
                if n > self.gap:
                    self.segs[i] = (px + ddx / n * self.gap, py + ddy / n * self.gap)

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


class Boss(Enemy):
    """El Gran Ciempiés de la Mina: duerme junto a la vagoneta y despierta cuando Mullo toma a las gemelas."""

    def __init__(self, x, y):
        super().__init__(x, y, 'boss')
        self.state = 'sleep'
        self.lair = (x, y)
        self.face = -math.pi / 2
        self.waking = 0.0
        n = len(self.segs)                                     # duerme enroscado alrededor de su cabeza
        self.segs = [(x + math.cos(-math.pi / 2 - 1.0 - i * .42) * (28 + i * 2.6) - math.cos(-math.pi / 2 - 1.0) * 28,
                      y + math.sin(-math.pi / 2 - 1.0 - i * .42) * (28 + i * 2.6) - math.sin(-math.pi / 2 - 1.0) * 28)
                     for i in range(n)]
        self.segs[0] = (x, y)

    def wake(self):
        if self.state in ('sleep', 'return'):
            self.waking = BOSS_WAKE_T if self.state == 'sleep' else 0.0
            self.state, self.path = 'chase', []
            return True
        return False

    def hear(self, *a):
        pass

    def hit_by_screech(self, bx, by):
        self.stun = max(self.stun, self.spec['stun'])

    def update(self, dt, g):
        self.anim += dt * (.25 if self.state == 'sleep' else 1)
        if self.stun > 0:
            self.stun -= dt
            self._finish(g.cave)
            return
        b = g.bat
        if self.state == 'sleep':
            return
        if self.waking > 0:                                   # se sacude y ruge antes de perseguir
            self.waking -= dt
            self.anim += dt * 3
            return
        if self.state == 'chase':
            if (math.dist((b.x, b.y), NEST) < SAFE_R and not b.carry) or g.cave.in_secret(b.x, b.y):   # a salvo o escondida: vuelve a su guarida
                self.state, self.path = 'return', []
            else:
                self._move(dt, (b.x, b.y), BOSS_SPEED, g.cave)
        elif self.state == 'return':
            if math.dist((self.x, self.y), self.lair) < 30:
                self.state = 'sleep'
            else:
                self._move(dt, self.lair, BOSS_SPEED * .6, g.cave)
        self._finish(g.cave)
