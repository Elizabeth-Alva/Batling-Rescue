"""Objetos interactivos del escenario (apto para niños, sin texto en pantalla):

- Cortina de raíces secas: cuelga de lado a lado en los pasajes. Se aparta cuando Mullo la cruza y se vuelve a
  cerrar detrás de ella. Los bichos la cruzan más despacio y no ven a través de ella cuando está cerrada.
- Piedra flotante (Lago Negro): se mece sobre el agua; cuando una salamandra se sube, se hunde con un "plop"
  y vuelve a flotar cuando se va.
- Lata colgada (Mina Vieja): si Mullo la golpea o la alcanza el grito, se columpia y suena varias veces;
  los bichos cercanos van a ver qué pasó y Mullo puede escabullirse por otro lado.
"""
import math
import random

import pygame

from decor import mix
from settings import TAU


def _seg_cross(a, b, c, d):
    """¿Se cruzan los segmentos ab y cd?"""
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


# ---------------------------------------------------------------- cortina de raíces secas
class DryCurtain:
    """Raíces secas que cuelgan del techo de un pasaje. Cada hebra es un resorte: se aparta al paso y vuelve."""
    PALETTES = {'fungi': ((92, 74, 52), (150, 122, 84), (176, 150, 96)),
                'lake': ((84, 76, 66), (138, 126, 104), (160, 150, 120)),
                'mine': ((96, 70, 44), (156, 116, 72), (190, 140, 80))}
    REACH = 42                       # a qué distancia empuja a las hebras quien pasa

    def __init__(self, a, b, theme='fungi'):
        self.a, self.b = a, b                                        # extremos (en las paredes)
        L = math.dist(a, b)
        self.ux, self.uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        self.nx, self.ny = -self.uy, self.ux                         # normal (hacia donde se cruza)
        self.dark, self.mid, self.light = self.PALETTES.get(theme, self.PALETTES['fungi'])
        n = max(14, int(L / 3))
        vertical = abs(self.uy) > .7                                 # cortina a lo largo de un pasaje horizontal
        self.strands = []
        for i in range(n):
            f = (i + random.uniform(.2, .8)) / n
            ax, ay = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
            # punta en reposo: cuelga hacia abajo y un poco hacia los lados (forma un fleco con volumen)
            side = random.gauss(0, 8) if vertical else random.uniform(-3, 3)
            ln = random.uniform(12, 26) if vertical else random.uniform(16, 30)
            self.strands.append(dict(ax=ax, ay=ay, ox=0.0, oy=0.0, vx=0.0, vy=0.0, rx=side, ln=ln,
                                     w=random.choice((1, 1, 1, 2)), ph=random.uniform(0, TAU), leaf=random.random() < .3,
                                     knot=random.uniform(.35, .7), bend=random.uniform(-2, 2),
                                     col=random.choice((self.dark, self.mid, self.mid, self.light))))
        self.strands.sort(key=lambda s_: s_['ay'] + s_['ln'])        # de atrás hacia adelante
        self.mid_pt = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        self.half = L / 2
        self.open = 0.0                                              # qué tanto está abierta (0 = cerrada)
        self.rustle_cd = 0.0

    def near(self, x, y, r=0):
        """¿El punto está dentro de la franja de la cortina?"""
        dx, dy = x - self.mid_pt[0], y - self.mid_pt[1]
        along, across = dx * self.ux + dy * self.uy, dx * self.nx + dy * self.ny
        return abs(along) < self.half + r and abs(across) < 18 + r

    def blocks_view(self, p, q):
        """Cerrada, no deja ver a través (los bichos no ven a Mullo del otro lado). Si alguien la está
        cruzando justo ahí, las hebras apartadas dejan un hueco."""
        if not _seg_cross(p, q, self.a, self.b):
            return False
        (x1, y1), (x2, y2) = p, q
        dx, dy = x2 - x1, y2 - y1
        ex, ey = self.b[0] - self.a[0], self.b[1] - self.a[1]
        den = dx * ey - dy * ex
        if abs(den) < 1e-9:
            return True
        tt = ((self.a[0] - x1) * ey - (self.a[1] - y1) * ex) / den
        cx, cy = x1 + dx * tt, y1 + dy * tt
        return self.gap_at(cx, cy) < 8

    def gap_at(self, x, y):
        """Qué tan apartadas están las hebras cerca de (x, y) (px)."""
        near = [math.hypot(s['ox'], s['oy']) for s in self.strands if math.dist((s['ax'], s['ay']), (x, y)) < 22]
        return sum(near) / len(near) if near else 99

    def push(self, x, y, vx, vy, strength, dt):
        """Algo pasa cerca: aparta las hebras hacia los lados y en el sentido del movimiento."""
        hit = False
        for s in self.strands:
            tx, ty = s['ax'] + s['rx'] * .5, s['ay'] + s['ln'] * .5
            d = math.dist((tx, ty), (x, y))
            if d < self.REACH:
                k = (1 - d / self.REACH) * strength
                dx, dy = (tx - x) / (d or 1), (ty - y) / (d or 1)
                s['vx'] += (dx * 2200 + vx * 4) * k * dt
                s['vy'] += (dy * 1400 + vy * 3) * k * dt
                hit = hit or k > .2
        return hit

    def update(self, dt, movers):
        """movers: lista de (x, y, vx, vy, fuerza)."""
        busy = False
        for x, y, vx, vy, k in movers:
            if self.near(x, y, 30):
                busy = self.push(x, y, vx, vy, k, dt) or busy
        spread = 0.0
        for s in self.strands:                                       # resorte amortiguado: vuelven a cerrar
            s['vx'] += (-s['ox'] * 38) * dt
            s['vy'] += (-s['oy'] * 38) * dt
            s['vx'] *= max(0, 1 - 5.5 * dt)
            s['vy'] *= max(0, 1 - 5.5 * dt)
            s['ox'] = max(-40, min(40, s['ox'] + s['vx'] * dt))
            s['oy'] = max(-34, min(34, s['oy'] + s['vy'] * dt))
            s['ph'] += dt
            spread += math.hypot(s['ox'], s['oy'])
        self.open = min(1.0, max(math.hypot(s_['ox'], s_['oy']) for s_ in self.strands) / 20)   # hueco más abierto
        self.rustle_cd = max(0, self.rustle_cd - dt)
        if busy and self.rustle_cd <= 0:
            self.rustle_cd = .45
            return True                                              # para sonar
        return False

    def draw(self, s, cam, t):
        ax, ay = cam.apply(*self.a)
        bx, by = cam.apply(*self.b)
        if not hasattr(self, '_shadow'):                             # sombra en el suelo (se nota que cuelga del techo)
            xs = [p[0] for p in (self.a, self.b)]
            ys = [p[1] for p in (self.a, self.b)]
            w_, h_ = int(max(xs) - min(xs) + 60), int(max(ys) - min(ys) + 70)
            sh = pygame.Surface((w_, h_), pygame.SRCALPHA)
            ox_, oy_ = min(xs) - 30, min(ys) - 20
            for k in range(6):
                pygame.draw.line(sh, (0, 0, 0, 22), (self.a[0] - ox_, self.a[1] - oy_ + 22 + k * 2),
                                 (self.b[0] - ox_, self.b[1] - oy_ + 22 + k * 2), 10 + 4 * k)
            self._shadow = (sh, ox_, oy_)
        sh, ox_, oy_ = self._shadow
        s.blit(sh, cam.apply(ox_, oy_))
        # raíz gruesa de la que cuelgan (anclada en las paredes, con nudos)
        pygame.draw.line(s, (20, 14, 10), (ax, ay + 3), (bx, by + 3), 6)
        pygame.draw.line(s, self.dark, (ax, ay), (bx, by), 5)
        L = max(1, math.dist((ax, ay), (bx, by)))
        for k in range(int(L // 14)):                                 # raíz trenzada con nudos
            f0, f1 = k * 14 / L, min(1, (k * 14 + 9) / L)
            p0 = (ax + (bx - ax) * f0 + self.nx * 1.5, ay + (by - ay) * f0 + self.ny * 1.5)
            p1 = (ax + (bx - ax) * f1 - self.nx * 1.5, ay + (by - ay) * f1 - self.ny * 1.5)
            pygame.draw.line(s, self.mid, p0, p1, 2)
        for st in self.strands:
            x0, y0 = cam.apply(st['ax'], st['ay'])
            sway = math.sin(t * 1.3 + st['ph']) * 1.6                 # la corriente de aire las mece
            ex = x0 + st['rx'] + st['ox'] + sway
            ey = y0 + st['ln'] + st['oy'] * .6
            mx = x0 + st['rx'] * .4 + st['ox'] * .5 + st['bend'] + sway * .5
            my = y0 + st['ln'] * .5 + st['oy'] * .3
            pts = [(x0, y0), (mx, my), (ex, ey)]
            pygame.draw.lines(s, (14, 10, 8), False, [(px + 1, py + 2) for px, py in pts], st['w'] + 1)   # sombrita
            pygame.draw.lines(s, st['col'], False, pts, st['w'])
            if st['w'] > 1:
                pygame.draw.line(s, mix(st['col'], (255, 240, 200), .3), (x0, y0), (mx, my), 1)
            kx, ky = mx + (ex - mx) * st['knot'], my + (ey - my) * st['knot']       # ramita lateral
            pygame.draw.line(s, st['col'], (kx, ky), (kx + (3 if st['ph'] > 3 else -3), ky + 3), 1)
            if st['leaf']:                                           # hojita seca al final
                lx, ly = ex, ey
                pygame.draw.polygon(s, (130, 92, 48), [(lx, ly), (lx - 2.5, ly + 3), (lx, ly + 7), (lx + 2.5, ly + 3)])
                pygame.draw.line(s, (84, 58, 30), (lx, ly), (lx, ly + 7), 1)
            else:
                pygame.draw.circle(s, mix(st['col'], (255, 240, 200), .4), (int(ex), int(ey)), 1)
        for p in (self.a, self.b):                                   # anclas en la roca
            px, py = cam.apply(*p)
            pygame.draw.circle(s, self.dark, (int(px), int(py)), 4)
            pygame.draw.circle(s, self.mid, (int(px) - 1, int(py) - 1), 2)


# ---------------------------------------------------------------- piedra flotante
class FloatStone:
    """Piedra pómez plana que flota en el lago; se hunde cuando una salamandra se le sube."""

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.r = random.uniform(17, 22)
        self.ph = random.uniform(0, TAU)
        self.sink = 0.0                                              # 0 = flotando, 1 = hundida
        self.load = 0.0                                              # tiempo que lleva con alguien encima
        self.ripples = []
        self.shape = [(math.cos(a) * random.uniform(.8, 1.08), math.sin(a) * random.uniform(.62, .8))
                      for a in [k * TAU / 9 + random.uniform(-.15, .15) for k in range(9)]]
        self.holes = [(random.uniform(-.5, .5), random.uniform(-.35, .35), random.uniform(1, 2)) for _ in range(5)]
        self.col = random.choice(((176, 170, 160), (186, 174, 156), (166, 166, 178)))

    def update(self, dt, riders):
        """riders: salamandras (u otros) que están encima. Devuelve True cuando se hunde (para el 'plop')."""
        self.ph += dt
        for r in self.ripples:
            r[0] += dt
        self.ripples = [r for r in self.ripples if r[0] < 1.3]
        on = any(math.dist((o.x, o.y), (self.x, self.y)) < self.r + 4 for o in riders)
        plop = False
        if on:
            self.load += dt
            before = self.sink
            self.sink = min(1.0, self.sink + dt * 2.2)
            if before < .5 <= self.sink:
                plop = True
                self.ripples += [[0.0], [-.25]]
        else:
            self.load = 0.0
            before = self.sink
            self.sink = max(0.0, self.sink - dt * .7)               # sube despacio
            if before > .2 >= self.sink:
                self.ripples.append([0.0])
        return plop

    def draw(self, s, cam):
        sx, sy = cam.apply(self.x, self.y + math.sin(self.ph * 1.6) * 1.2 * (1 - self.sink))
        for (rt,) in self.ripples:                                   # ondas
            if rt > 0:
                k = 1 - rt / 1.3
                rr = self.r + 4 + rt * 26
                pygame.draw.ellipse(s, (int(80 * k), int(110 * k), int(180 * k)), (sx - rr, sy - rr * .55, rr * 2, rr * 1.1), 1)
        k = 1 - self.sink * .75
        r = self.r * (1 - self.sink * .25)
        if self.sink < .95:
            pygame.draw.ellipse(s, (16, 22, 44), (sx - r - 2, sy - r * .45 + 3, r * 2 + 4, r * 1.2))   # sombra en el agua
            pts = [(sx + px * r, sy + py * r) for px, py in self.shape]
            top = tuple(int(c * k + 30 * (1 - k)) for c in self.col)
            pygame.draw.polygon(s, mix(top, (0, 0, 0), .35), [(px, py + 2) for px, py in pts])
            pygame.draw.polygon(s, top, pts)
            for hx, hy, hr in self.holes:                            # poros de la piedra
                pygame.draw.circle(s, mix(top, (0, 0, 0), .3), (int(sx + hx * r), int(sy + hy * r)), int(hr))
            pygame.draw.arc(s, mix(top, (255, 255, 255), .35), (sx - r * .8, sy - r * .6, r * 1.6, r * 1.1), .4, 2.6, 1)
            if self.sink > .05:                                      # el agua le pasa por encima
                wa = pygame.Surface((int(r * 2.4), int(r * 1.8)), pygame.SRCALPHA)
                pygame.draw.ellipse(wa, (24, 34, 74, int(200 * self.sink)), wa.get_rect())
                s.blit(wa, (sx - wa.get_width() / 2, sy - wa.get_height() / 2))
        pygame.draw.ellipse(s, (60, 80, 140), (sx - r - 1, sy - r * .62, r * 2 + 2, r * 1.3), 1)            # borde de agua


# ---------------------------------------------------------------- lata colgada
class HangingCan:
    """Lata vieja colgada de un brazo de madera clavado en la pared de la mina."""
    RING_T = 4.2                     # cuánto rato sigue sonando al columpiarse
    NOISE_R = 560                    # hasta dónde la oyen los bichos

    def __init__(self, wall, anchor):
        self.wall, self.anchor = wall, anchor                        # punto en la pared y punta del brazo
        self.ang, self.vang = 0.0, 0.0                               # columpio
        self.ring = 0.0                                              # tiempo que le queda sonando
        self.clang_t = 0.0
        self.cd = 0.0
        self.hits = 0
        self.dir = random.choice((-1, 1))
        self.col = random.choice(((176, 70, 56), (70, 110, 150), (190, 150, 60)))

    @property
    def pos(self):
        L = 26
        return (self.anchor[0] + math.sin(self.ang) * L, self.anchor[1] + math.cos(self.ang) * L * .55 + 6)

    def strike(self, from_x, from_y, power=1.0):
        """Golpe (Mullo pasa encima o le llega el grito). Devuelve True si empieza a sonar."""
        if self.cd > 0:
            return False
        px, py = self.pos
        side = 1 if px >= from_x else -1
        self.vang += side * 6.5 * power
        self.ring, self.cd, self.clang_t = self.RING_T, 1.0, 0.0
        self.hits += 1
        return True

    def update(self, dt):
        """Devuelve True en cada 'clanc' (para el sonido y el ruido que atrae bichos)."""
        self.cd = max(0, self.cd - dt)
        self.vang += -self.ang * 26 * dt                             # péndulo
        self.vang *= max(0, 1 - (.9 if self.ring > 0 else 2.2) * dt)
        if self.ring > 0:                                            # mientras suena, se sigue meciendo
            self.vang += math.sin(self.ring * 5) * 2.2 * dt * self.dir
        self.ang = max(-1.1, min(1.1, self.ang + self.vang * dt))
        self.ring = max(0, self.ring - dt)
        self.clang_t -= dt
        if self.ring > 0 and self.clang_t <= 0:
            self.clang_t = .7
            return True
        return False

    def draw(self, s, cam, t):
        wx, wy = cam.apply(*self.wall)
        ax, ay = cam.apply(*self.anchor)
        pygame.draw.line(s, (24, 16, 10), (wx, wy + 3), (ax, ay + 3), 5)          # brazo de madera
        pygame.draw.line(s, (110, 76, 44), (wx, wy), (ax, ay), 4)
        pygame.draw.line(s, (150, 108, 64), (wx, wy - 1), (ax, ay - 1), 1)
        pygame.draw.circle(s, (70, 70, 76), (int(ax), int(ay)), 2)                  # clavo
        cx, cy = cam.apply(*self.pos)
        pygame.draw.line(s, (170, 160, 140), (ax, ay), (cx, cy - 6), 1)              # cordel
        tilt = math.degrees(-self.ang) * .8
        can = pygame.Surface((16, 20), pygame.SRCALPHA)               # lata: cilindro con etiqueta y óxido
        body = self.col
        pygame.draw.rect(can, mix(body, (0, 0, 0), .35), (2, 3, 12, 15), border_radius=2)
        pygame.draw.rect(can, body, (3, 3, 9, 15), border_radius=2)
        pygame.draw.rect(can, (210, 205, 190), (3, 8, 9, 4))                       # etiqueta clara
        pygame.draw.line(can, mix(body, (0, 0, 0), .2), (4, 10), (10, 10), 1)
        pygame.draw.ellipse(can, (190, 190, 196), (2, 1, 12, 5))                  # tapa de metal
        pygame.draw.ellipse(can, (120, 120, 128), (2, 1, 12, 5), 1)
        pygame.draw.circle(can, (130, 80, 40), (11, 15), 1)                       # puntito de óxido
        pygame.draw.line(can, (250, 250, 250), (4, 4), (4, 16), 1)                # brillo
        can = pygame.transform.scale(can, (21, 26))
        rot = pygame.transform.rotate(can, tilt)
        s.blit(rot, rot.get_rect(center=(int(cx), int(cy + 2))))

    def draw_fx(self, s, cam):
        """Rayitas de sonido (se dibujan sobre la oscuridad para que se vean)."""
        cx, cy = cam.apply(*self.pos)
        if self.ring > 0:                                            # "clanc": rayitas de sonido
            k = (self.clang_t % .7) / .7
            if k > .45:
                q = (k - .45) / .55
                for sd in (-1, 1):
                    for i in range(3):
                        a = -math.pi / 2 + sd * (.6 + i * .35)
                        r0, r1 = 12 + 8 * (1 - q), 18 + 8 * (1 - q)
                        col = (int(255 * q), int(225 * q), int(140 * q))
                        pygame.draw.line(s, col, (cx + math.cos(a) * r0, cy + math.sin(a) * r0),
                                         (cx + math.cos(a) * r1, cy + math.sin(a) * r1), 2)
