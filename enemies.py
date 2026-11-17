"""Enemigos: animales con hambre en un año de sequía que reaccionan al ruido (no son villanos).

Arañas: lentas, patrullan cerca de sus telarañas. El grito las aturde y las daña.
Escarabajos: acorazados y tercos; oyen los chillidos y van a investigar. Aguantan más.
Cazadores (ciempiés): rápidos, cazan con el oído; te persiguen al verte y pierden el rastro si te alejas.
   El grito solo los aturde un momento.
Jefe (Xolthar, el Gran Ciempiés de la Mina): territorial, no cruel; no se puede vencer, solo esquivar.
"""
import math
import random

from settings import NEST, SAFE_R

SPECS = {
    # spd: velocidad, hear: oído, det: vista, hp: vida, rad: radio, size: tamaño de dibujo, dmg: daño por contacto,
    # stun: cuánto les afecta el grito / el escudo, push: cuánto los empuja, lose: segundos hasta perder el rastro,
    # leash: distancia máxima a su casa al patrullar (None = libre)
    'spider': dict(spd=1.0, hear=1.0, det=1.0, hp=2, rad=12, size=1.0, dmg=1, stun=1.0, push=1.0, lose=2.5, leash=320,
                   calm=.6),                  # calm: tranquila camina más lento; al verte, a toda velocidad
    'beetle': dict(spd=.85, hear=1.7, det=.85, hp=4, rad=14, size=1.1, dmg=1, stun=.8, push=.45, lose=3.5, leash=None),
    'hunter': dict(spd=1.55, hear=2.2, det=1.35, hp=3, rad=13, size=1.0, dmg=1, stun=.3, push=.7, lose=1.3, leash=None),
    'boss':   dict(spd=1.0, hear=0.0, det=0.0, hp=10 ** 9, rad=40, size=3.0, dmg=2, stun=.12, push=0.0, lose=99, leash=None),
}
NAMES = {'spider': 'araña', 'beetle': 'escarabajo', 'hunter': 'cazador', 'boss': 'Xolthar'}
BOSS_SPEED = 178          # más lento que Mullo cargando crías (211) y mucho más que el impulso
BOSS_WAKE_T = 1.6        # tarda en despertar del todo: Mullo tiene un instante para huir
# Si se queda muy atrás o se atora, rompe el piso y sale cerca de Mullo (siempre DETRÁS de ella y con aviso)
BURROW_FAR = 640         # px: «muy atrás»
BURROW_FAR_T = 2.2       # s que tiene que pasar así de lejos
BURROW_STUCK = 2.4       # s casi sin avanzar (atorado)
BURROW_CD = 7.0          # s entre una salida y la siguiente
DIVE_T, WARN_T, EMERGE_T = .75, 1.0, .6
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
        self.gait = random.random()                   # ciclos de paso (las patas siguen lo que avanza el cuerpo)
        self._gx, self._gy = x, y
        self.path, self.repath = [], random.random() * .6
        self.idle = 0.0                               # segundos quieto (los cazadores se acicalan las pinzas)
        self.flip_t, self._stunned = 1.0, False       # escarabajo aturdido: tiempo desde que se volteó
        self.face = random.uniform(0, math.tau)       # hacia dónde mira
        n, gap = (7, 8) if kind == 'hunter' else (16, 17) if kind == 'boss' else (0, 0)
        self.gap = gap
        self.segs = [(x - math.cos(self.face) * gap * i, y - math.sin(self.face) * gap * i) for i in range(n)]

    STRIDE = 13.0                                     # px que avanza el cuerpo por ciclo de paso (pasos cortos)

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
        moved = math.hypot(self.x - self._gx, self.y - self._gy)
        self._gx, self._gy = self.x, self.y
        self.gait += min(moved, 30) / self.STRIDE + dt * .12      # quieta: solo acomoda las patas de vez en cuando
        if self.stun > 0:
            if not self._stunned:
                self._stunned, self.flip_t = True, 0.0
            self.flip_t += dt
            self.idle = 0.0
            self.stun -= dt
            self.vx *= .9
            self.vy *= .9
            self.x += self.vx * dt
            self.y += self.vy * dt
            self._finish(cave)
            return
        self._stunned = False
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
            goal, sp = self.target, p.investigate_speed * spec['spd'] * spec.get('calm', 1.0)
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
            sp, self.wait = p.patrol_speed * spec['spd'] * spec.get('calm', 1.0), self.wait + dt
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
        self.idle = self.idle + dt if (self.vx == 0 and self.vy == 0 and self.state != 'chase') else 0.0
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
            budget = getattr(cave, 'path_budget', 99)          # pocas búsquedas por cuadro (va más fluido)
            if (self.repath <= 0 or not self.path) and budget > 0:
                cave.path_budget = budget - 1
                self.repath = .8 + random.random() * .4
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
    """Xolthar, el Gran Ciempiés de la Mina: duerme enroscado junto a las vagonetas y despierta cuando Mullo toma
    a las gemelas. En cuanto ella las deja en el nido, regresa a su guarida y se vuelve a dormir."""

    def __init__(self, x, y):
        super().__init__(x, y, 'boss')
        self.state = 'sleep'
        self.lair = (x, y)
        self.face = -math.pi / 2
        self.waking = 0.0
        self.stir = 0.0                                        # se remueve dormido (oyó ruido cerca): advertencia
        n = len(self.segs)                                     # duerme enroscado alrededor de su cabeza
        self.segs = [(x + math.cos(-math.pi / 2 - 1.0 - i * .42) * (28 + i * 2.6) - math.cos(-math.pi / 2 - 1.0) * 28,
                      y + math.sin(-math.pi / 2 - 1.0 - i * .42) * (28 + i * 2.6) - math.sin(-math.pi / 2 - 1.0) * 28)
                     for i in range(n)]
        self.segs[0] = (x, y)
        self.noise_hits = 0                                    # gritos de Mullo cerca mientras duerme (al 3.º despierta)
        self.angry = False                                     # lo despertaron a gritos: ya no deja de seguirla
        self.burrow = None                                     # rompe el piso: {'phase', 't', 'hole', 'target', ...}
        self.burrow_cd = 0.0
        self.far_t = 0.0
        self._stuck_ref, self._stuck_t = (x, y), 0.0

    # ------------------------------------------------------------ rompe el piso
    @property
    def underground(self):
        """True mientras no se le puede tocar (bajo tierra o entrando/saliendo del agujero)."""
        bw = self.burrow
        return bw is not None and not (bw['phase'] == 'emerge' and bw['t'] > .2)

    def hidden_from(self):
        """Punto del agujero por el que entra o sale: los segmentos que están ahí no se dibujan (están bajo tierra)."""
        bw = self.burrow
        if bw is None:
            return None
        return bw['hole'] if bw['phase'] == 'dive' else bw.get('target')

    def _start_burrow(self, g):
        self.burrow = dict(phase='dive', t=0.0, hole=(self.x, self.y), target=None, home=False)
        self.vx = self.vy = 0.0
        g.boss_event('dive', self.x, self.y)

    def _burrow_update(self, dt, g):
        bw, b = self.burrow, g.bat
        bw['t'] += dt
        safe = (math.dist((b.x, b.y), NEST) < SAFE_R and not b.carry) or g.cave.in_secret(b.x, b.y)
        if safe and not self.angry:
            bw['home'] = True                                  # Mullo ya está a salvo: saldrá en su guarida
        if bw['phase'] == 'dive':                              # se mete: el cuerpo entra al agujero como un tren
            hx, hy = bw['hole']
            sp = 520 * dt
            segs = []
            for sx, sy in self.segs:
                d = math.hypot(hx - sx, hy - sy)
                segs.append((hx, hy) if d <= sp else (sx + (hx - sx) / d * sp, sy + (hy - sy) / d * sp))
            self.segs = segs
            if bw['t'] >= DIVE_T:
                bw['phase'], bw['t'] = 'under', 0.0
                bw['dur'] = 1.1
                g.boss_event('under', hx, hy)
        elif bw['phase'] == 'under':                           # viaja bajo tierra (se ve y se oye el retumbo)
            goal = self.lair if bw['home'] else (b.x, b.y)
            k = min(1.0, bw['t'] / bw['dur'])
            hx, hy = bw['hole']
            self.x, self.y = hx + (goal[0] - hx) * k * .85, hy + (goal[1] - hy) * k * .85
            g.boss_event('trail', self.x, self.y)
            if bw['t'] >= bw['dur']:
                tgt = (self.lair[0], self.lair[1]) if bw['home'] else g.emerge_spot(self)
                bw['target'] = tgt or bw['hole']
                bw['phase'], bw['t'] = 'warn', 0.0
                g.boss_event('warn', *bw['target'])
        elif bw['phase'] == 'warn':                            # el piso se agrieta: aviso antes de salir
            if bw['t'] >= (WARN_T * .5 if bw['home'] else WARN_T):
                tx, ty = bw['target']
                self.x, self.y = tx, ty
                self.segs = [(tx, ty)] * len(self.segs)
                self.face = math.atan2(b.y - ty, b.x - tx)
                bw['phase'], bw['t'] = 'emerge', 0.0
                g.boss_event('emerge', tx, ty)
        elif bw['phase'] == 'emerge':                          # sale del piso y el cuerpo lo sigue
            if not bw['home']:
                self._move(dt, (b.x, b.y), BOSS_SPEED * 1.15, g.cave)
            self._finish(g.cave)
            if bw['t'] >= EMERGE_T:
                self.burrow, self.burrow_cd, self.far_t = None, BURROW_CD, 0.0
                self._stuck_ref, self._stuck_t = (self.x, self.y), 0.0
                if bw['home']:
                    self.state, self.path = 'return', []

    def _check_burrow(self, dt, g):
        """¿Se quedó muy atrás o está atorado? Entonces rompe el piso. Nunca cerca del nido."""
        b = g.bat
        self.burrow_cd = max(0.0, self.burrow_cd - dt)
        d = math.dist((self.x, self.y), (b.x, b.y))
        self.far_t = self.far_t + dt if d > BURROW_FAR else 0.0
        if math.dist((self.x, self.y), self._stuck_ref) > 60:
            self._stuck_ref, self._stuck_t = (self.x, self.y), 0.0
        else:
            self._stuck_t += dt
        if self.burrow_cd > 0 or math.dist((b.x, b.y), NEST) < SAFE_R + 260:
            return False
        if self.far_t > BURROW_FAR_T or (self._stuck_t > BURROW_STUCK and d > 220):
            self._start_burrow(g)
            return True
        return False

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
        self.stir = max(0.0, self.stir - dt)
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
        if self.burrow is not None:                           # rompiendo el piso / bajo tierra
            self._burrow_update(dt, g)
            return
        if self.state == 'chase':
            safe = (math.dist((b.x, b.y), NEST) < SAFE_R and not b.carry) or g.cave.in_secret(b.x, b.y)
            if safe and not self.angry:                        # a salvo o escondida: vuelve a su guarida
                self.state, self.path = 'return', []
            elif safe:                                         # furioso: se queda rondando afuera (al nido no entra)
                self._move(dt, (b.x, b.y), BOSS_SPEED * .7, g.cave)
            elif hasattr(g, 'emerge_spot') and self._check_burrow(dt, g):
                return
            else:
                self._move(dt, (b.x, b.y), BOSS_SPEED, g.cave)
        elif self.state == 'return':
            if math.dist((self.x, self.y), self.lair) < 30:
                self.state = 'sleep'
            else:
                self._move(dt, self.lair, BOSS_SPEED * .6, g.cave)
        self._finish(g.cave)
