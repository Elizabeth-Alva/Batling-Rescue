"""Vida tranquila de la cueva y efectos amables (apto para niños):

- Salamandras de cueva del Lago Negro: nadan despacio y a ratos se suben a una piedra flotante (que se hunde);
  si ven a un murciélago, a un bicho o les cae una gota cerca, se espantan y se sumergen.
- Enemigo vencido: se marea (estrellitas), da una vuelta y sale corriendo entre una nubecita de polvo. Sin sangre.
- Susto amable (nivel 1): una arañita baja de golpe colgada de su hilo frente a Mullo, se asusta ella sola
  y sube corriendo por su hilo. No hace daño; solo pone al jugador alerta (y da risa).
- Crías a salvo: descansan en el punto de entrega, se acomodan, bostezan y aletean.
"""
import math
import random

import pygame

import ui
from settings import NEST, NEST_R, TAU


# ---------------------------------------------------------------- salamandras de cueva
class Salamander:
    """Salamandra de cueva del Lago Negro: pálida, con manchitas cálidas. Nada tranquila y, cuando ve a
    un murciélago, se espanta: da un respingo, huye nadando rápido y se sumerge un rato."""
    COLORS = (((240, 218, 196), (236, 150, 92)), ((236, 222, 232), (214, 140, 170)), ((244, 226, 186), (226, 168, 70)))
    SEE = 170                       # a qué distancia ve a Mullo

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.ang = random.uniform(0, TAU)
        self.turn = random.uniform(-.6, .6)
        self.speed = random.uniform(14, 24)
        self.t = random.uniform(0, 9)
        self.rest = random.uniform(0, 3)
        self.body, self.spots = random.choice(self.COLORS)
        self.spot_pos = [(random.uniform(-8, 5), random.uniform(-2.2, 2.2)) for _ in range(4)]
        self.state, self.st = 'calm', 0.0          # calm -> (rest) / startle -> flee -> dive -> hidden -> calm
        self.threat = (x, y)
        self.goal = None                           # piedra flotante a la que va
        self.rest_for = 0.0
        self.alpha = 1.0
        self.ripples = []
        self.sub = 0.0                              # qué tanto se hundió con la piedra (0 = a flote)

    def _water(self, cave, x, y):
        return cave.is_water(x, y)

    def scare(self, x, y):
        """Algo la asustó (murciélago, bicho, gota): respingo y huye en sentido contrario."""
        if self.state in ('calm', 'rest'):
            self.state, self.st = 'startle', 0.0
            self.ang = math.atan2(self.y - y, self.x - x)
            self.threat = (x, y)
            self.goal = None

    def update(self, dt, cave, bat, threats=(), stones=()):
        """threats: otros que la espantan (bichos que caminan cerca de la orilla). stones: piedras flotantes."""
        self.t += dt
        self.st += dt
        for r in self.ripples:
            r[2] += dt
        self.ripples = [r for r in self.ripples if r[2] < 1.2]
        if self.state in ('calm', 'rest'):
            self.alpha = min(1.0, self.alpha + dt * 2)
            near = [(math.dist((self.x, self.y), (bat.x, bat.y)), bat.x, bat.y)]
            near += [(math.dist((self.x, self.y), (e.x, e.y)) * 1.25, e.x, e.y) for e in threats]
            d, tx, ty = min(near)
            if d < self.SEE:                                  # ¡un murciélago o un bicho! se espanta
                self.scare(tx, ty)
                return
        if self.state == 'rest':                              # descansa sobre una piedra (que se hunde)
            if self.st > self.rest_for:
                self.state, self.goal, self.rest = 'calm', None, random.uniform(3, 6)
                self.ang += math.pi * random.uniform(.6, 1.4)
                self.speed = random.uniform(16, 24)
            return
        if self.state == 'calm':
            if self.goal is None and stones and random.random() < dt * .12:      # va a subirse a una piedra
                st = min(stones, key=lambda o: math.dist((o.x, o.y), (self.x, self.y)))
                if math.dist((st.x, st.y), (self.x, self.y)) < 380 and st.sink < .1:
                    self.goal = st
            if self.goal is not None:
                gx, gy = self.goal.x, self.goal.y
                dd = math.dist((gx, gy), (self.x, self.y))
                if dd < 5:
                    self.x, self.y = gx + math.cos(self.ang) * 8, gy + math.sin(self.ang) * 8   # queda bien encima
                    self.state, self.st, self.rest_for = 'rest', 0.0, random.uniform(1.5, 3)
                    self.speed = 0
                    return
                want = math.atan2(gy - self.y, gx - self.x)
                diff = (want - self.ang + math.pi) % TAU - math.pi
                self.ang += max(-3 * dt, min(3 * dt, diff))
                nx, ny = self.x + math.cos(self.ang) * 26 * dt, self.y + math.sin(self.ang) * 26 * dt
                if self._water(cave, nx, ny):
                    self.x, self.y = nx, ny
                else:
                    self.goal = None
                self.speed = 26
                return
            self.rest -= dt
            if self.rest <= 0:
                self.rest = random.uniform(2, 5)
                self.turn = random.uniform(-.7, .7)
                self.speed = 0 if random.random() < .35 else random.uniform(14, 26)
            self.ang += self.turn * dt
            self._swim(dt, cave, self.speed)
        elif self.state == 'startle':                         # respingo: se queda tiesa y sacude la cola
            if self.st > .3:
                self.state, self.st = 'flee', 0.0
        elif self.state == 'flee':                            # huye nadando muy rápido
            tx, ty = self.threat
            target = math.atan2(self.y - ty, self.x - tx)
            diff = (target - self.ang + math.pi) % TAU - math.pi
            self.ang += max(-4 * dt, min(4 * dt, diff))
            self._swim(dt, cave, 130)
            if self.st > 1.0:                                 # y se sumerge
                self.state, self.st = 'dive', 0.0
                self.ripples.append([self.x, self.y, 0.0])
        elif self.state == 'dive':
            self.alpha = max(0.0, 1 - self.st / .4)
            if self.st > .4:
                self.state, self.st = 'hidden', 0.0
                self.hide_for = random.uniform(3, 5)
        elif self.state == 'hidden':                          # reaparece lejos del murciélago
            if self.st > self.hide_for:
                spot = self._far_water(cave, bat)
                if spot:
                    self.x, self.y = spot
                    self.ripples.append([self.x, self.y, 0.0])
                    self.state, self.st, self.alpha = 'calm', 0.0, 0.0
                else:
                    self.st = 0.0

    def _swim(self, dt, cave, sp):
        nx, ny = self.x + math.cos(self.ang) * sp * dt, self.y + math.sin(self.ang) * sp * dt
        if self._water(cave, nx, ny) and self._water(cave, nx + math.cos(self.ang) * 14, ny + math.sin(self.ang) * 14):
            self.x, self.y = nx, ny
        else:                                                 # orilla: da la vuelta
            self.ang += math.pi * random.uniform(.6, 1.0)

    def _far_water(self, cave, bat):
        for _ in range(60):
            i = random.randrange(cave.w * cave.h)
            if cave.water[i]:
                x, y = (i % cave.w) * 32 + 16, (i // cave.w) * 32 + 16
                if math.dist((x, y), (bat.x, bat.y)) > 320:
                    return x, y
        return None

    @property
    def visible(self):
        return self.state != 'hidden' and self.alpha > .05

    def draw(self, s, sx, sy, cam=None):
        for rx, ry, rt in self.ripples:                       # ondas al sumergirse / salir
            if cam:
                px, py = cam.apply(rx, ry)
                k = 1 - rt / 1.2
                pygame.draw.circle(s, (int(90 * k), int(120 * k), int(190 * k)), (int(px), int(py)), int(4 + 22 * rt), 1)
        if not self.visible:
            return
        a, t = self.ang, self.t
        scared = self.state in ('startle', 'flee')
        ca, sa = math.cos(a), math.sin(a)
        wav = 10 if self.state == 'flee' else (30 if self.state == 'startle' else (6 if self.speed else 2))
        amp = 1.6 if self.state == 'startle' else 1.0

        def P(px, py):
            return (sx + px * ca - py * sa, sy + px * sa + py * ca)
        k = self.alpha
        wet = self.sub * .8                                   # se hunde con la piedra: se ve bajo el agua
        WATER = (22, 30, 64)

        def tone(c, m=1.0):
            return tuple(int((v * m * (1 - wet) + w * wet) * k) for v, w in zip(c, WATER))
        body, dark, spot = tone(self.body), tone(self.body, .62), tone(self.spots)
        tail = [P(-7, 0)]                                     # cola larga que ondula
        for i in range(1, 8):
            tail.append(P(-7 - i * 3, math.sin(t * wav - i * .7) * i * .55 * amp))
        for i in range(len(tail) - 1):
            w = max(1, 4 - i // 2)
            pygame.draw.line(s, dark, tail[i], tail[i + 1], w + 1)
            pygame.draw.line(s, body, tail[i], tail[i + 1], w)
        for fx, sd in ((4, -1), (4, 1), (-4, -1), (-4, 1)):   # patitas con deditos
            swing = math.sin(t * wav * .8 + fx + sd) * (2.5 if self.speed or scared else .5)
            foot = P(fx - 2 + swing * sd, sd * 7)
            pygame.draw.line(s, dark, P(fx, sd * 2.5), foot, 2)
            pygame.draw.circle(s, body, (int(foot[0]), int(foot[1])), 1)
        poly = [P(8, 0), P(6, -3.4), P(-1, -3.6), P(-7, -2.2), P(-7, 2.2), P(-1, 3.6), P(6, 3.4)]
        pygame.draw.polygon(s, body, poly)
        pygame.draw.polygon(s, dark, poly, 1)
        for ox, oy in self.spot_pos:                          # manchitas cálidas
            px, py = P(ox, oy)
            pygame.draw.circle(s, spot, (int(px), int(py)), 1)
        hx, hy = P(9, 0)
        pygame.draw.ellipse(s, body, (hx - 4.5, hy - 4.5, 9, 9))
        er = 2 if scared else 1                               # ojos (se abren grandes del susto)
        for sd in (-1, 1):
            ex, ey = P(10.5, sd * 2.6)
            pygame.draw.circle(s, (20, 14, 20), (int(ex), int(ey)), er)
            if scared:
                s.fill((255, 255, 255), (int(ex) - 1, int(ey) - 1, 1, 1))


def spawn_salamanders(cave, n=6):
    water = [i for i in range(cave.w * cave.h) if cave.water[i]]
    out = []
    for _ in range(n * 6):
        if len(out) >= n or not water:
            break
        i = random.choice(water)
        x, y = (i % cave.w) * 32 + 16, (i // cave.w) * 32 + 16
        if math.dist((x, y), cave.echo or (0, 0)) > 120 and all(math.dist((x, y), (o.x, o.y)) > 250 for o in out):
            out.append(Salamander(x, y))
    return out


# ---------------------------------------------------------------- enemigo vencido
class Defeat:
    """Animación amable: estrellitas de mareo, una vuelta, y sale corriendo hasta perderse entre polvo."""
    DUR = 1.3

    def __init__(self, e, bx, by):
        self.e, self.t = e, 0.0
        d = math.dist((e.x, e.y), (bx, by)) or 1
        self.dx, self.dy = (e.x - bx) / d, (e.y - by) / d
        self.puffs = [(random.uniform(0, TAU), random.uniform(.6, 1.2)) for _ in range(7)]
        self.x0, self.y0 = e.x, e.y

    def update(self, dt):
        self.t += dt
        e = self.e
        e.anim += dt * (3 if self.t > .5 else .5)
        if self.t > .5:                                      # sale corriendo
            sp = 300 * dt
            e.x += self.dx * sp
            e.y += self.dy * sp
            e.face = math.atan2(self.dy, self.dx)
            e.segs = [(x + self.dx * sp, y + self.dy * sp) for x, y in e.segs]
        else:                                                # mareado: se tambalea y gira
            e.face += dt * 9
        return self.t < self.DUR

    def draw(self, s, cam):
        e, t = self.e, self.t
        sx, sy = cam.apply(e.x, e.y)
        if t > .5:
            spec = dict(e.spec)
            spec['size'] = e.spec['size'] * max(.2, 1 - (t - .5) / .8)
            real, e.spec = e.spec, spec
            ui.draw_enemy(s, sx, sy, e, cam)
            e.spec = real
        else:
            ui.draw_enemy(s, sx + math.sin(t * 40) * 2, sy, e, cam)

    def draw_fx(self, s, cam):
        """Estrellitas y nubecita de polvo (se dibujan sobre la oscuridad para que se vean)."""
        e, t = self.e, self.t
        if t < .7:
            hx, hy = cam.apply(e.x, e.y - 18 * e.spec['size'])
            for k in range(3):
                a = t * 9 + k * TAU / 3
                px, py = hx + math.cos(a) * 14, hy + math.sin(a) * 5
                ui.star(s, px, py, 4, (255, 230, 120))
        px, py = cam.apply(self.x0, self.y0)
        p = min(1, t / .8)
        for a, r in self.puffs:                               # polvito al arrancar
            if p < 1:
                g = int(170 * (1 - p))
                pygame.draw.circle(s, (g, g, int(g * .95)), (int(px + math.cos(a) * 26 * p * r), int(py + math.sin(a) * 18 * p * r)),
                                   max(1, int(7 * (1 - p) * r)))
        if t > 1.0:                                           # "puf" final al perderse de vista
            q = (t - 1.0) / .3
            ex, ey = cam.apply(e.x, e.y)
            g = int(200 * (1 - q))
            for k in range(5):
                a = k * TAU / 5
                pygame.draw.circle(s, (g, g, g), (int(ex + math.cos(a) * 10 * q), int(ey + math.sin(a) * 10 * q)), max(1, int(6 * (1 - q))))


# ---------------------------------------------------------------- susto amable
class DropSpider:
    """Arañita que baja colgada de su hilo justo enfrente de Mullo, rebota, la mira, se asusta ella sola y sube
    corriendo. Es solo un susto: no hace daño ni hace ruido para los bichos."""
    DROP, DANGLE, SCARED, FLEE = .32, 1.25, 1.75, 2.5

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.t = 0.0
        self.legs = random.uniform(0, 9)
        self.cues = set()                                    # sonidos ya disparados

    @property
    def done(self):
        return self.t > self.FLEE

    def update(self, dt):
        self.t += dt
        self.legs += dt * (9 if self.t > self.DANGLE else 2)
        out = []
        for key, at in (('boing', 0.0), ('eek', self.DANGLE), ('zip', self.SCARED)):
            if self.t >= at and key not in self.cues:
                self.cues.add(key)
                out.append(key)
        return out

    def _pose(self):
        """Altura sobre el suelo (px) y escala (más chica = más arriba, cerca del techo)."""
        t = self.t
        if t < self.DROP:                                    # cae de golpe
            q = t / self.DROP
            return -150 * (1 - q) ** 2, .6 + .4 * q
        if t < self.DANGLE:                                  # rebota en su hilo como resorte y se queda colgando
            q = t - self.DROP
            return -math.sin(q * 14) * 16 * math.exp(-q * 4), 1.0
        if t < self.SCARED:                                  # ¡se asusta! brinquito tieso
            q = (t - self.DANGLE) / (self.SCARED - self.DANGLE)
            return -10 * math.sin(math.pi * min(1, q * 3)) + math.sin(t * 70) * 1.2, 1.0
        q = min(1, (t - self.SCARED) / (self.FLEE - self.SCARED))   # sube corriendo por su hilo
        return -220 * q ** 1.6, 1.0 - .45 * q

    def draw(self, s, cam):
        h, k = self._pose()
        sx, sy = cam.apply(self.x, self.y)
        top = sy - 260
        by = sy + h
        if h > -150:                                         # sombrita en el suelo (más chica si está alta)
            r = max(3, 12 * (1 + h / 180))
            pygame.draw.ellipse(s, (6, 8, 8), (sx - r, sy + 8 - r * .35, 2 * r, r * .7))
        pygame.draw.line(s, (200, 214, 214), (sx, top), (sx, by - 6 * k), 1)          # hilo de seda
        scared = self.t >= self.DANGLE
        ui.draw_spider(s, sx, by, self.legs * (2.5 if scared else 1), .72 * k, math.pi / 2)
        # carita: ojos grandes que miran a Mullo y se abren del susto
        ex, ey = sx, by + 4.5 * k
        big = 2.6 if scared else 1.8
        for sd in (-1, 1):
            px, py = int(ex + sd * (3.6 if scared else 2.8) * k), int(ey)
            pygame.draw.circle(s, (250, 250, 245), (px, py), max(1, int(big * k + 1)))
            pygame.draw.circle(s, (20, 14, 20), (px, py + (0 if scared else 1)), max(1, int((big - 1.4) * k)))

    def draw_fx(self, s, cam):
        """'!' de sorpresa (sobre la oscuridad, para que se vea)."""
        if not (self.DANGLE <= self.t < self.SCARED + .2):
            return
        h, k = self._pose()
        sx, sy = cam.apply(self.x, self.y + h)
        q = min(1, (self.t - self.DANGLE) / .12)
        y0 = sy - 30 - 6 * q
        pygame.draw.line(s, (255, 236, 150), (sx + 14, y0), (sx + 14, y0 + 9 * q), 3)
        pygame.draw.circle(s, (255, 236, 150), (int(sx + 14), int(y0 + 14 * q)), 2)


# ---------------------------------------------------------------- crías a salvo en el punto de entrega
def _behavior_of(name):
    from story import PUPS
    for lv in PUPS.values():
        for nm, b in lv:
            if name and (nm == name or name in nm.split(' y ')):
                return b
    return 'inquieta'


class Resting:
    """Cría ya rescatada: se acomoda en el nido y reacciona a su manera.

    inquieta: da vueltitas de alegría · dormilona: se vuelve a dormir · llorona: deja de llorar y brinca feliz ·
    asustadiza: tiembla pegadita al centro del nido · eco: sigue repitiendo con ondas suaves · gemelas: juntitas.
    """

    def __init__(self, idx, total=4, name=None):
        self.name = name
        self.behavior = _behavior_of(name)
        a = -math.pi / 2 + TAU * idx / max(4, total) + random.uniform(-.2, .2)
        r = NEST_R * (.22 if self.behavior == 'asustadiza' else .38)
        self.x, self.y = NEST[0] + math.cos(a) * r, NEST[1] + math.sin(a) * r
        self.t = random.uniform(0, 6)
        self.flap_t = 0.0
        self.arrive = .6                                      # aterriza al llegar
        self.spin = 1.0 if self.behavior == 'inquieta' else 0.0     # vueltita al llegar
        self.hop = .4 if self.behavior == 'llorona' else 0.0

    def update(self, dt):
        self.t += dt
        self.arrive = max(0, self.arrive - dt)
        self.flap_t = max(0, self.flap_t - dt)
        self.spin = max(0, self.spin - dt)
        self.hop = max(0, self.hop - dt)
        b = self.behavior
        if b == 'dormilona' and self.arrive <= 0:                 # se queda dormida: casi no se mueve
            return
        if self.flap_t <= 0 and random.random() < dt * .25:
            self.flap_t = .5
        if b == 'inquieta' and self.spin <= 0 and random.random() < dt * .18:
            self.spin = 1.0
        if b == 'llorona' and self.hop <= 0 and random.random() < dt * .5:
            self.hop = .4

    def draw(self, s, cam):
        ox = oy = 0.0
        if self.spin > 0:                                     # vueltita en círculo
            a = (1 - self.spin) * TAU
            ox, oy = math.cos(a) * 7 - 7, math.sin(a) * 5
        if self.hop > 0:                                      # brinquito feliz
            oy -= math.sin(math.pi * self.hop / .4) * 6
        sx, sy = cam.apply(self.x + ox, self.y + oy - self.arrive * 30)
        breathe = math.sin(self.t * (1.2 if self.behavior == 'dormilona' else 2)) * 1.2
        busy = self.flap_t > 0 or self.arrive > 0 or self.spin > 0 or self.hop > 0
        flap = self.t * 22 if busy else 1.3 + .15 * math.sin(self.t * 2)
        lean = .35 * math.sin(self.spin * TAU) if self.spin > 0 else .1 * math.sin(self.t * .7)
        ui.draw_pup(s, sx, sy + breathe, flap, lean, name=self.name, t=self.t)

    def draw_fx(self, s, cam):
        sx, sy = cam.apply(self.x, self.y)
        ui.pup_extras(s, sx, sy, ui.PUP_LOOKS.get(self.name, {}), self.t)
        if self.behavior == 'llorona' and self.hop > 0:       # notita de alegría (ya no llora)
            q = 1 - self.hop / .4
            a = int(230 * math.sin(math.pi * q))
            x, y = sx + 10, sy - 16 - q * 10
            pygame.draw.circle(s, (a, int(a * .8), int(a * .9)), (int(x), int(y)), 2)
            pygame.draw.line(s, (a, int(a * .8), int(a * .9)), (x + 2, y), (x + 2, y - 7), 1)
