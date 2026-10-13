"""Ilustraciones por código para la portada y las cinemáticas (cielos, siluetas, cuevas, la colonia y Mullo).

Si existe assets/escenas/<clave>.png (por ejemplo una imagen generada con IA, 960x640), la cinemática
usa esa imagen con un paneo lento en lugar de la ilustración por código.
"""
import math
import os
import random

import pygame

from settings import W, H, TAU

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def lerp(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(len(a)))


def gradient(w, h, stops):
    """Degradado vertical. stops = [(0..1, color), ...]"""
    s = pygame.Surface((w, h))
    for y in range(h):
        f = y / max(1, h - 1)
        for i in range(len(stops) - 1):
            if stops[i][0] <= f <= stops[i + 1][0]:
                k = (f - stops[i][0]) / max(1e-6, stops[i + 1][0] - stops[i][0])
                s.fill(lerp(stops[i][1], stops[i + 1][1], k), (0, y, w, 1))
                break
    return s


def glow(r, col, peak=1.0, exp=1.6):
    """Brillo radial para sumar con BLEND_RGB_ADD."""
    s = pygame.Surface((2 * r, 2 * r))
    for i in range(r, 0, -2):
        k = peak * (1 - i / r) ** exp
        pygame.draw.circle(s, tuple(min(255, int(c * k)) for c in col), (r, r), i)
    return s


def soft(r, col, a, exp=1.5):
    s = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
    for i in range(r, 0, -2):
        pygame.draw.circle(s, (*col, int(a * (1 - i / r) ** exp)), (r, r), i)
    return s


def ridge(w, h, base, amp, col, seed, rough=6, jag=.0):
    """Silueta de cerros / rocas: polígono con ruido suave (superficie con alfa)."""
    rnd = random.Random(seed)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    ph = [rnd.uniform(0, TAU) for _ in range(4)]
    fr = [rnd.uniform(.6, 1.4) * k for k in (1.5, 3.3, 7.1, 15.0)]
    pts = [(0, h)]
    for x in range(0, w + 8, 8):
        f = x / w
        y = base - amp * (.5 * math.sin(f * fr[0] + ph[0]) + .28 * math.sin(f * fr[1] + ph[1])
                          + .14 * math.sin(f * fr[2] + ph[2]) + .08 * math.sin(f * fr[3] + ph[3]))
        if jag:
            y += rnd.uniform(-jag, jag)
        pts.append((x, y))
    pts.append((w, h))
    pygame.draw.polygon(s, col, pts)
    return s


def stars(n, seed, area=(W, H * .6)):
    rnd = random.Random(seed)
    return [(rnd.uniform(0, area[0]), rnd.uniform(0, area[1]), rnd.uniform(.5, 1.6), rnd.uniform(0, TAU)) for _ in range(n)]


def draw_stars(s, st, t, alpha=1.0):
    for x, y, r, ph in st:
        k = alpha * (.55 + .45 * math.sin(t * 1.7 + ph))
        c = max(0, min(230, int(220 * k)))
        if r > 1.2:
            pygame.draw.circle(s, (c, c, min(255, c + 25)), (int(x), int(y)), 1)
        else:
            s.fill((c, c, min(255, c + 25)), (int(x), int(y), 1, 1))


def _quad(a, c, b, n=5):
    """Puntos de una curva cuadrática de a a b con control c."""
    out = []
    for i in range(1, n + 1):
        t = i / n
        out.append(((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t * t * b[0],
                    (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t * t * b[1]))
    return out


def bat_sil(s, x, y, flap, sc=1.0, col=(8, 6, 14), rim=None, eyes=None, ang=0.0):
    """Silueta de murciélago de frente: alas festoneadas con huesos de los dedos, orejas y ojos."""
    w = math.sin(flap)
    ca, sa = math.cos(ang), math.sin(ang)

    def P(px, py):
        px, py = px * sc, py * sc
        return (x + px * ca - py * sa, y + px * sa + py * ca)

    bone = lerp(col, (255, 255, 255), .1)
    lw = max(1, int(1.2 * sc))
    for sd in (-1, 1):
        S, Wr, T = (sd * 5, -6), (sd * 26, -22 - 16 * w), (sd * 60, -2 - 30 * w)
        trail = [(sd * 49, 13 - 20 * w), (sd * 35, 21 - 12 * w), (sd * 19, 23 - 5 * w), (sd * 6, 14)]
        pts = [S, Wr] + _quad(Wr, (sd * 44, -21 - 24 * w), T, 4)
        prev = T
        for p in trail:                                               # festones del borde de fuga
            mx, my = (prev[0] + p[0]) / 2, (prev[1] + p[1]) / 2
            cx, cy = mx + (Wr[0] - mx) * .32, my + (Wr[1] - my) * .32
            pts += _quad(prev, (cx, cy), p, 4)
            prev = p
        poly = [P(*p) for p in pts]
        pygame.draw.polygon(s, col, poly)
        for p in [T] + trail[:3]:                                      # huesos de los dedos
            pygame.draw.line(s, bone, P(*Wr), P(*p), lw)
        pygame.draw.line(s, bone, P(*S), P(*Wr), lw + 1)
        if rim:
            pygame.draw.lines(s, rim, False, [P(*S), P(*Wr)] + [P(*q) for q in _quad(Wr, (sd * 44, -21 - 24 * w), T, 4)], max(1, int(1.6 * sc)))
    body = [P(0, -6), P(6, -2), P(7, 8), P(4, 17), P(0, 20), P(-4, 17), P(-7, 8), P(-6, -2)]
    pygame.draw.polygon(s, col, body)
    hx, hy = P(0, -14)
    pygame.draw.circle(s, col, (int(hx), int(hy)), max(2, int(7 * sc)))
    for sd in (-1, 1):
        ear = [P(sd * 1.5, -17), P(sd * 8, -30), P(sd * 10.5, -13)]
        pygame.draw.polygon(s, col, ear)
        if rim:
            pygame.draw.line(s, rim, ear[0], ear[1], max(1, int(sc)))
    if eyes:
        for sd in (-1, 1):
            ex, ey = P(sd * 2.8, -14.5)
            pygame.draw.circle(s, eyes, (int(ex), int(ey)), max(1, int(1.5 * sc)))


def colony(s, t, cx, cy, n=40, spread=(160, 70), seed=3, col=(10, 8, 16), sc=.32, stream=0.0, dirx=1.0):
    """Colonia de murciélagos: remolino alrededor de (cx, cy); con stream > 0 salen en una cinta."""
    rnd = random.Random(seed)
    for i in range(n):
        ph, sp, rr = rnd.uniform(0, TAU), rnd.uniform(.4, 1.0), rnd.uniform(.3, 1.0)
        if stream and i < n * stream:
            p = ((t * .12 * sp + i / n) % 1)
            x = cx + dirx * p * W * 1.1 + math.sin(t * 2 + i) * 18
            y = cy - p * H * .45 + math.sin(t * 1.5 + ph) * 22 * (1 + p)
            k = sc * (1 + p * .6)
        else:
            a = t * sp * 1.2 + ph
            x = cx + math.cos(a) * spread[0] * rr
            y = cy + math.sin(a * 1.3) * spread[1] * rr
            k = sc * (.7 + .3 * rr)
        bat_sil(s, x, y, t * 14 + i, k, col)


# ------------------------------------------------------------------ escenas
class Shot:
    """Ilustración animada. build() crea las capas fijas; draw() compone cada frame."""
    sky = ((20, 20, 50), (60, 40, 90))

    def __init__(self):
        self.layers = {}
        self.build()

    def build(self):
        pass

    def draw(self, s, t, dur):
        pass


def _sky(stops_a, stops_b, k, cache, key):
    """Cielo que cambia de color: mezcla dos degradados precalculados."""
    if key not in cache:
        cache[key] = (gradient(W, H, stops_a), gradient(W, H, stops_b))
    a, b = cache[key]
    out = a.copy()
    b.set_alpha(int(255 * max(0, min(1, k))))
    out.blit(b, (0, 0))
    return out


def cave_mouth_frame(w, h, hole, col=(6, 5, 10), rim=None, seed=1):
    """Pared de roca que llena la pantalla con una boca de cueva (hueco transparente)."""
    rnd = random.Random(seed)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((*col, 255))
    cx, cy, rx, ry = hole
    pts = []
    for i in range(64):
        a = TAU * i / 64
        r = 1 + .08 * math.sin(a * 3 + 1) + .05 * math.sin(a * 7 + 2) + rnd.uniform(-.03, .03)
        pts.append((cx + math.cos(a) * rx * r, cy + math.sin(a) * ry * r * (1 if math.sin(a) < 0 else .8)))
    pygame.draw.polygon(s, (0, 0, 0, 0), pts)
    if rim:
        pygame.draw.lines(s, rim, True, pts, 3)
    for _ in range(14):                                                 # estalactitas en el borde superior
        a = rnd.uniform(math.pi * 1.1, math.pi * 1.9)
        bx, by = cx + math.cos(a) * rx * .95, cy + math.sin(a) * ry * .95
        hh = rnd.uniform(20, 70)
        pygame.draw.polygon(s, (*col, 255), [(bx - 10, by - 4), (bx + 10, by - 4), (bx + rnd.uniform(-4, 4), by + hh)])
    return s


class Dusk(Shot):
    """Apertura: atardecer de sequía fuera de la cueva; la colonia vuela y Mullo se aleja."""

    def build(self):
        L = self.layers
        L['sun'] = glow(150, (255, 150, 70), 1.0, 1.8)
        L['far'] = ridge(W, H, 430, 70, (70, 36, 60), 11)
        L['mid'] = ridge(W, H, 480, 60, (40, 20, 36), 12)
        cliff = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.polygon(cliff, (16, 9, 18), [(560, H), (600, 300), (660, 190), (760, 140), (880, 120), (W, 110), (W, H)])
        pygame.draw.ellipse(cliff, (60, 26, 30), (696, 296, 178, 158), 3)
        pygame.draw.ellipse(cliff, (3, 2, 5), (700, 300, 170, 150))
        pygame.draw.ellipse(cliff, (0, 0, 0), (725, 330, 120, 100))
        pygame.draw.lines(cliff, (120, 60, 50), False, [(600, 300), (660, 190), (760, 140), (880, 120), (W, 110)], 2)
        L['cliff'] = cliff
        ground = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.polygon(ground, (34, 18, 20), [(0, 560), (300, 540), (620, 555), (W, 540), (W, H), (0, H)])
        rnd = random.Random(5)
        for _ in range(26):                                             # tierra agrietada por la sequía
            x, y = rnd.uniform(0, W), rnd.uniform(565, H - 6)
            pts = [(x, y)]
            for _ in range(4):
                x, y = x + rnd.uniform(8, 26), y + rnd.uniform(-6, 6)
                pts.append((x, y))
            pygame.draw.lines(ground, (18, 8, 10), False, pts, 2)
        tree = [(120, 560), (128, 470), (110, 430), (128, 470), (150, 420), (138, 395), (150, 420), (170, 440)]
        pygame.draw.lines(ground, (14, 6, 10), False, tree, 6)
        pygame.draw.lines(ground, (14, 6, 10), False, [(128, 470), (96, 455), (84, 430)], 4)
        L['ground'] = ground
        L['cache'] = {}

    def draw(self, s, t, dur):
        k = t / max(1, dur)
        sky = _sky([(0, (60, 30, 90)), (.5, (200, 90, 90)), (.8, (255, 160, 90)), (1, (255, 190, 120))],
                   [(0, (24, 16, 60)), (.5, (110, 50, 100)), (.8, (200, 90, 80)), (1, (230, 120, 80))], k, self.layers['cache'], 'd')
        s.blit(sky, (0, 0))
        sy = 380 + 50 * k
        s.blit(self.layers['sun'], (300 - 150, sy - 150), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.circle(s, (255, 200, 140), (300, int(sy)), 46)
        s.blit(self.layers['far'], (-int(t * 3), 0))
        s.blit(self.layers['far'], (W - int(t * 3), 0))
        s.blit(self.layers['mid'], (0, 0))
        colony(s, t, 560, 190, 30, (170, 60), 8, (12, 6, 14), .3)
        s.blit(self.layers['cliff'], (0, 0))
        s.blit(self.layers['ground'], (0, 0))
        p = min(1, t / max(1, dur - .5))                                # Mullo sale de la cueva y se aleja
        x = 780 - 820 * p
        y = 370 - 200 * math.sin(p * math.pi * .9)
        bat_sil(s, x, y, t * 9, 1.6 - .9 * p, (8, 4, 10), (255, 150, 90), (255, 210, 120))


class Leaving(Shot):
    """«Ya vuelvo. Quédense quietas»: desde el nido, Mullo se va hacia la boca de la cueva."""

    def build(self):
        L = self.layers
        L['frame'] = cave_mouth_frame(W, H, (W / 2, 250, 320, 160), (10, 7, 14), (150, 90, 120), 3)
        L['far'] = ridge(W, H, 330, 40, (70, 34, 70), 21)
        L['ledge'] = ridge(W, H, 470, 24, (18, 12, 22), 22)
        L['cache'] = {}
        L['stars'] = stars(50, 4, (W, 330))

    def draw(self, s, t, dur):
        k = t / max(1, dur)
        sky = _sky([(0, (40, 20, 70)), (.6, (150, 70, 100)), (1, (230, 120, 90))],
                   [(0, (16, 12, 44)), (.6, (70, 36, 90)), (1, (140, 70, 90))], k, self.layers['cache'], 'l')
        s.blit(sky, (0, 0))
        draw_stars(s, self.layers['stars'], t, k)
        s.blit(self.layers['far'], (0, 0))
        p = min(1, t / max(1, dur - 1))
        x, y = W / 2 + 60 * math.sin(p * 3), 400 - 210 * p
        bat_sil(s, x, y, t * 10, 2.0 - 1.6 * p, (6, 4, 10), (230, 140, 160), (255, 210, 120))
        s.blit(self.layers['frame'], (0, 0))
        s.blit(self.layers['ledge'], (0, 0))
        nest_with_pups(s, W / 2, 482, t, 10, awake=True)


def draw_nest(s, cx, cy, rx, ry, seed=7):
    """Nido tejido de ramitas: borde grueso en capas, forro suave de pelusa y musgo, una pluma y hojitas.
    rx = ry para verlo desde arriba (en el juego); ry < rx para verlo de lado (en las cinemáticas)."""
    rnd = random.Random(seed)
    k = ry / rx
    pygame.draw.ellipse(s, (8, 6, 6), (cx - rx * 1.08 + 4, cy - ry * 1.08 + 7, rx * 2.16, ry * 2.16))    # sombra
    pygame.draw.ellipse(s, (62, 44, 30), (cx - rx, cy - ry, rx * 2, ry * 2))
    twigs = ((78, 56, 38), (98, 72, 48), (122, 92, 60), (146, 112, 74))
    for layer in range(3):                                              # ramitas entretejidas en tres capas
        for _ in range(48):
            a = rnd.uniform(0, TAU)
            r = rnd.uniform(.66, 1.0) - layer * .04
            x0, y0 = cx + math.cos(a) * rx * r, cy + math.sin(a) * ry * r
            d = a + math.pi / 2 + rnd.uniform(-.45, .45)
            L = rx * rnd.uniform(.22, .42)
            x1, y1 = x0 + math.cos(d) * L, y0 + math.sin(d) * L * k
            col = twigs[min(3, layer + rnd.randint(0, 1))]
            pygame.draw.line(s, col, (x0, y0), (x1, y1), 3 if layer == 0 else 2)
            if rnd.random() < .25:                                      # ramita que se bifurca
                pygame.draw.line(s, col, ((x0 + x1) / 2, (y0 + y1) / 2),
                                 ((x0 + x1) / 2 + math.cos(d + .7) * L * .4, (y0 + y1) / 2 + math.sin(d + .7) * L * .4 * k), 1)
    ix, iy = rx * .62, ry * .62                                         # hueco con forro suave
    pygame.draw.ellipse(s, (54, 40, 32), (cx - ix, cy - iy, ix * 2, iy * 2))
    pygame.draw.ellipse(s, (92, 76, 64), (cx - ix * .92, cy - iy * .86, ix * 1.84, iy * 1.8))
    pygame.draw.ellipse(s, (72, 58, 48), (cx - ix * .7, cy - iy * .45, ix * 1.4, iy * 1.3))
    for _ in range(36):                                                 # pelusa y musgo
        a, r = rnd.uniform(0, TAU), rnd.uniform(.3, .9)
        x, y = cx + math.cos(a) * ix * r, cy + math.sin(a) * iy * r
        col = rnd.choice(((124, 106, 92), (110, 96, 84), (70, 104, 70), (140, 124, 110)))
        pygame.draw.circle(s, col, (int(x), int(y)), rnd.randint(1, 3))
    for _ in range(4):                                                  # hojitas secas
        a = rnd.uniform(0, TAU)
        x, y = cx + math.cos(a) * rx * .85, cy + math.sin(a) * ry * .85
        pygame.draw.ellipse(s, (120, 110, 50), (x - 5, y - 3 * k - 1, 10, 6 * k + 2))
    a = rnd.uniform(0, TAU)                                             # una pluma
    x, y = cx + math.cos(a) * rx * .7, cy + math.sin(a) * ry * .7
    pygame.draw.line(s, (220, 214, 200), (x - 9, y + 4 * k), (x + 9, y - 4 * k), 3)
    pygame.draw.line(s, (160, 150, 140), (x - 9, y + 4 * k), (x + 9, y - 4 * k), 1)
    for _ in range(18):                                                 # brillos del borde de arriba
        a = rnd.uniform(math.pi * 1.1, math.pi * 1.9)
        x, y = cx + math.cos(a) * rx * .9, cy + math.sin(a) * ry * .9
        pygame.draw.line(s, (176, 140, 96), (x - 4, y), (x + 4, y + rnd.uniform(-2, 2)), 1)


_NEST_CACHE = {}


def nest_with_pups(s, cx, cy, t, n, awake=True, sleeping=False, look=0.0):
    """Nido de ramitas con n crías (ojos brillantes si están despiertas)."""
    key = ('nest', int(cx), int(cy))
    img = _NEST_CACHE.get(key)
    if img is None:
        img = _NEST_CACHE[key] = pygame.Surface((340, 110), pygame.SRCALPHA)
        draw_nest(img, 170, 55, 150, 38)
    s.blit(img, (cx - 170, cy + 4 - 55))
    for i in range(n):
        px = cx - 110 + (220 / max(1, n - 1)) * i if n > 1 else cx
        py = cy - 6 + (i % 2) * 8 + math.sin(t * 3 + i) * 1.5
        bat_sil(s, px, py, 1.0 + .2 * math.sin(t * 2 + i), .55, (30, 20, 32))
        if awake:
            blink = (t * .7 + i * .37) % 4 < 3.85
            if blink:
                for sd in (-1, 1):
                    pygame.draw.circle(s, (255, 200, 230), (int(px + sd * 1.6 + look * 1.5), int(py - 7.5)), 1)
        if sleeping:
            ph = (t + i) % 3
            from ui import text, F_XS
            text(s, F_XS, 'z', px + 6 + ph * 4, py - 18 - ph * 8, (170, 160, 210))


class CaveInterior(Shot):
    """Interior: boca de la cueva arriba a la izquierda (color del cielo según el acto), luz que entra y el nido."""
    sky_stops = [(0, (8, 12, 40)), (1, (20, 34, 92))]
    light_col = (90, 110, 200)

    def build(self):
        L = self.layers
        L['bg'] = gradient(W, H, [(0, (20, 18, 36)), (.55, (10, 9, 20)), (1, (3, 2, 6))])
        L['sky'] = gradient(W, H, self.sky_stops)
        L['stars'] = stars(40, 9, (440, 300))
        L['rock'] = cave_mouth_frame(W, H, (250, 200, 190, 120), (12, 10, 22), lerp(self.light_col, (0, 0, 0), .35), 6)
        L['back'] = ridge(W, H, 430, 50, (16, 13, 28), 30)
        L['ledge'] = ridge(W, H, 470, 26, (22, 18, 34), 31)
        beam = pygame.Surface((W, H), pygame.SRCALPHA)                 # haz de luz que entra por la boca
        pygame.draw.polygon(beam, (*self.light_col, 28), [(150, 230), (360, 220), (760, 520), (400, 540)])
        pygame.draw.polygon(beam, (*self.light_col, 22), [(200, 230), (320, 225), (640, 520), (470, 530)])
        L['beam'] = beam
        rnd = random.Random(13)
        L['dust'] = [(rnd.uniform(200, 760), rnd.uniform(230, 530), rnd.uniform(.3, 1)) for _ in range(40)]

    def draw(self, s, t, dur):
        L = self.layers
        s.blit(L['bg'], (0, 0))
        s.blit(L['sky'], (0, 0), (0, 0, 460, 340))
        draw_stars(s, L['stars'], t)
        pygame.draw.circle(s, (225, 230, 255), (180, 150), 18)                      # luna creciente
        pygame.draw.circle(s, L['sky'].get_at((180, 140)), (171, 145), 17)
        s.blit(L['rock'], (0, 0))
        s.blit(L['back'], (0, 0))
        s.blit(L['beam'], (0, 0))
        for x, y, z in L['dust']:
            yy = y + math.sin(t * .6 + x) * 10
            c = int(70 + 90 * z * (.6 + .4 * math.sin(t + x)))
            s.fill((c, c, min(255, c + 30)), (int(x + math.sin(t * .4 + y) * 12), int(yy), 2, 2))
        s.blit(L['ledge'], (0, 0))
        self.extra(s, t, dur)

    def extra(self, s, t, dur):
        pass


class EmptyNest(CaveInterior):
    sky_stops = [(0, (6, 10, 34)), (1, (20, 34, 92))]

    def extra(self, s, t, dur):
        nest_with_pups(s, 560, 478, t, 0)
        for k in range(6):                                                          # garras que bajan
            x, y = 700 + k * 36, 486 + k * 9
            for d in (-5, 0, 5):
                pygame.draw.line(s, (120, 110, 130), (x + d, y - 7), (x + d + 6, y + 5), 2)
        p = min(1, t / 3.0)
        x = 250 + (470 - 250) * p
        y = 200 + (420 - 200) * p - 90 * math.sin(p * math.pi)
        bat_sil(s, x, y, t * (10 if p < 1 else 2), .7 + .9 * p, (6, 4, 10), (120, 140, 230), (255, 210, 120))


class Debate(CaveInterior):
    sky_stops = [(0, (6, 10, 34)), (1, (20, 34, 92))]

    def build(self):
        super().build()
        self.layers['abyss'] = glow(300, (10, 70, 60), .7)

    def extra(self, s, t, dur):
        s.blit(self.layers['abyss'], (W - 600, H - 300), special_flags=pygame.BLEND_RGB_ADD)
        rnd = random.Random(2)
        for _ in range(18):                                                         # hongos lejanos allá abajo
            x, y = rnd.uniform(420, W - 60), rnd.uniform(500, 535)
            k = .5 + .5 * math.sin(t * 2 + x)
            pygame.draw.circle(s, (int(40 + 60 * k), int(170 + 80 * k), int(140 + 60 * k)), (int(x), int(y)), 2)
        bat_sil(s, 440, 410, 1.5 + .1 * math.sin(t), 1.9, (6, 4, 10), (120, 140, 230), (255, 210, 120))
        if t > 2.0:                                                                 # el chillido que conoce
            for k in range(3):
                p = ((t - 2.0) * .5 + k / 3) % 1
                pygame.draw.circle(s, lerp((255, 150, 210), (14, 12, 26), p), (760, 560), int(10 + 260 * p), 2)


class NestThree(CaveInterior):
    sky_stops = [(0, (16, 18, 60)), (1, (60, 50, 120))]
    light_col = (120, 110, 210)

    def extra(self, s, t, dur):
        nest_with_pups(s, 560, 478, t, 3, awake=False, sleeping=True)
        bat_sil(s, 360, 420, 1.2, 1.6, (6, 4, 10), (140, 130, 230), (255, 210, 120))
        for k in range(3):
            p = ((t * .45 + k / 3) % 1)
            pygame.draw.circle(s, lerp((255, 150, 210), (14, 12, 26), p), (W // 2 + 200, H + 80), int(100 + 260 * p), 2)


class Descent(Shot):
    """Primer punto de giro: Mullo baja por el descenso hacia el lago."""

    def build(self):
        L = self.layers
        L['bg'] = gradient(W, H, [(0, (6, 22, 24)), (.6, (6, 8, 30)), (1, (2, 2, 14))])
        rnd = random.Random(4)
        wall = pygame.Surface((W, H * 2), pygame.SRCALPHA)
        for side in (0, 1):
            pts = [(0 if side == 0 else W, 0)]
            for y in range(0, H * 2 + 40, 40):
                x = (180 + 60 * math.sin(y * .01) + rnd.uniform(-20, 20)) if side == 0 else (W - 180 - 60 * math.cos(y * .012) - rnd.uniform(-20, 20))
                pts.append((x, y))
            pts.append((0 if side == 0 else W, H * 2))
            pygame.draw.polygon(wall, (8, 12, 18), pts)
            pygame.draw.lines(wall, (40, 90, 90) if side == 0 else (50, 60, 110), False, pts[1:-1], 2)
        for _ in range(60):
            x = rnd.choice((rnd.uniform(150, 260), rnd.uniform(W - 260, W - 150)))
            y = rnd.uniform(0, H * 2)
            pygame.draw.circle(wall, (60, 200, 170) if y < H else (90, 110, 220), (int(x), int(y)), 2)
        L['wall'] = wall
        L['lake'] = glow(260, (40, 60, 160), .6, 1.4)

    def draw(self, s, t, dur):
        s.blit(self.layers['bg'], (0, 0))
        s.blit(self.layers['lake'], (W // 2 - 260, H - 200), special_flags=pygame.BLEND_RGB_ADD)
        off = int((t * 140) % H)
        s.blit(self.layers['wall'], (0, -off))
        bat_sil(s, W / 2 + math.sin(t * 1.3) * 60, 260 + math.sin(t * 2) * 20, t * 6, 1.7, (6, 4, 10), (90, 150, 200), (255, 210, 120), ang=math.pi + .2 * math.sin(t))


class Lake(Shot):
    """Lago Negro: agua quieta, islotes, niebla baja y algas; Mullo vuela bajo."""

    def build(self):
        L = self.layers
        L['bg'] = gradient(W, H, [(0, (4, 4, 14)), (.45, (10, 10, 34)), (.5, (6, 8, 24)), (1, (2, 3, 10))])
        L['isl'] = ridge(W, H, 300, 26, (12, 12, 26), 41, jag=2)
        rnd = random.Random(9)
        L['algae'] = [(rnd.uniform(0, W), rnd.uniform(330, H)) for _ in range(70)]
        L['mist'] = [soft(rnd.randint(120, 200), (120, 130, 190), 38) for _ in range(5)]
        L['refl'] = [(rnd.uniform(0, W), rnd.uniform(330, H), rnd.uniform(20, 90)) for _ in range(40)]

    def draw(self, s, t, dur):
        L = self.layers
        s.blit(L['bg'], (0, 0))
        s.blit(L['isl'], (0, 0))
        for x, y, w in L['refl']:
            yy = y + math.sin(t + x) * 2
            pygame.draw.line(s, (30, 36, 80), (x, yy), (x + w, yy), 1)
        for x, y in L['algae']:
            k = .5 + .5 * math.sin(t * 1.4 + x)
            pygame.draw.circle(s, (int(40 + 60 * k), int(140 + 100 * k), int(90 + 60 * k)), (int(x), int(y)), 1 + (k > .7))
        for i, m in enumerate(L['mist']):
            x = (i * 260 + t * 18 * (1 + i % 2)) % (W + 400) - 200
            s.blit(m, (x - m.get_width() / 2, 300 + i * 40 - m.get_height() / 2))
        p = (t / max(1, dur))
        x, y = -80 + (W + 160) * p, 230 + 20 * math.sin(t * 2)
        bat_sil(s, x, y, t * 9, 1.4, (4, 4, 10), (110, 120, 220), (255, 210, 120))
        bat_sil(s, x, 2 * 320 - y + 40, t * 9, 1.4, (14, 16, 40), None, None, ang=math.pi)  # reflejo en el agua
        for i, bx in enumerate((700, 820)):                            # escarabajos en la orilla: también oyen
            if (t + i * 1.3) % 4 < 3:
                for sd in (-4, 4):
                    pygame.draw.circle(s, (230, 120, 60), (bx + sd, 292 + i * 6), 2)


class EchoRoom(Shot):
    """La Sala del Eco: la voz de Mullo vuelve deformada; Eco la repite con voz chiquita."""

    def build(self):
        L = self.layers
        L['bg'] = gradient(W, H, [(0, (6, 4, 20)), (.6, (16, 12, 44)), (1, (4, 4, 14))])
        L['island'] = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.ellipse(L['island'], (20, 18, 36), (260, 420, 440, 120))
        pygame.draw.ellipse(L['island'], (70, 70, 130), (260, 420, 440, 120), 2)
        L['glow'] = glow(240, (90, 70, 200), .55)

    def draw(self, s, t, dur):
        s.blit(self.layers['bg'], (0, 0))
        s.blit(self.layers['glow'], (W // 2 - 240, 230), special_flags=pygame.BLEND_RGB_ADD)
        for k in range(6):                                                   # ecos que rebotan y se deforman
            p = ((t * .35 + k / 6) % 1)
            r = int(30 + 420 * p)
            col = lerp((190, 170, 255), (0, 0, 0), p)
            rect = pygame.Rect(0, 0, r * 2, int(r * 1.2)).move(W // 2 - r, 420 - int(r * .6))
            pygame.draw.ellipse(s, col, rect.inflate(int(math.sin(t * 3 + k) * 30), 0), 2)
        s.blit(self.layers['island'], (0, 0))
        bat_sil(s, 410, 440, 1.2 + .2 * math.sin(t * 2), 1.7, (6, 4, 10), (170, 150, 255), (255, 210, 120))
        bat_sil(s, 560, 470, 1.0 + .3 * math.sin(t * 6), .7, (30, 20, 40), (240, 160, 210), (255, 220, 240))


class Mine(Shot):
    """Mina Vieja: vigas que se alejan, rieles, vagonetas, lámparas apagadas, polvo ámbar."""
    gate = False

    def build(self):
        L = self.layers
        L['bg'] = gradient(W, H, [(0, (8, 5, 3)), (.5, (24, 14, 8)), (1, (6, 4, 2))])
        tunnel = pygame.Surface((W, H), pygame.SRCALPHA)
        vx, vy = W / 2, 300
        for i in range(9, 0, -1):                                              # marcos de madera en perspectiva
            k = (i / 9) ** 1.6
            w, h = 40 + 860 * k, 30 + 520 * k
            x0, y0 = vx - w / 2, vy - h * .55
            col = lerp((20, 12, 6), (110, 72, 40), k)
            th = max(2, int(22 * k))
            pygame.draw.rect(tunnel, col, (x0, y0, th, h))
            pygame.draw.rect(tunnel, col, (x0 + w - th, y0, th, h))
            pygame.draw.rect(tunnel, col, (x0 - th, y0, w + 2 * th, th))
            if i % 3 == 0:                                                     # lámpara apagada colgando
                lx, ly = vx, y0 + th + 18 * k
                pygame.draw.line(tunnel, (30, 20, 12), (lx, y0 + th), (lx, ly), max(1, int(2 * k)))
                pygame.draw.circle(tunnel, (40, 34, 28), (int(lx), int(ly + 6 * k)), max(2, int(9 * k)))
                pygame.draw.circle(tunnel, (120, 96, 60), (int(lx), int(ly + 6 * k)), max(2, int(9 * k)), 1)
        for sd in (-1, 1):                                                     # rieles
            pygame.draw.line(tunnel, (120, 96, 72), (vx + sd * 8, vy + 8), (vx + sd * 260, H), 4)
        for i in range(1, 12):
            k = (i / 11) ** 1.8
            y = vy + 8 + (H - vy - 8) * k
            w = 16 + 520 * k
            pygame.draw.line(tunnel, (60, 38, 22), (vx - w / 2, y), (vx + w / 2, y), max(1, int(8 * k)))
        L['tunnel'] = tunnel
        L['glow'] = glow(320, (120, 70, 30), .7)
        rnd = random.Random(12)
        L['dust'] = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(.2, 1)) for _ in range(60)]

    def draw(self, s, t, dur):
        L = self.layers
        s.blit(L['bg'], (0, 0))
        s.blit(L['glow'], (W // 2 - 320, 300 - 320), special_flags=pygame.BLEND_RGB_ADD)
        s.blit(L['tunnel'], (0, 0))
        from map import draw_cart
        draw_cart(s, 210, 470, -.3, 2.6)
        for x, y, z in L['dust']:
            yy = (y + t * 12 * z) % H
            c = int(80 + 90 * z)
            s.fill((c, int(c * .75), int(c * .45)), (int(x + math.sin(t + y) * 8), int(yy), 2, 2))
        if self.gate:                                                          # ojos de cazadores en la oscuridad
            for i, (ex, ey) in enumerate(((440, 280), (520, 310), (470, 330))):
                if (t + i * .9) % 3 < 2.2:
                    for sd in (-5, 5):
                        pygame.draw.circle(s, (220, 60, 40), (ex + sd, ey), 2)
        p = min(1, t / max(1, dur))
        bat_sil(s, 700 - 300 * p, 200 + 60 * p, t * 9, 1.6 - .9 * p, (8, 4, 4), (230, 150, 80), (255, 210, 120))


class MineGate(Mine):
    gate = True


class DawnNest(Shot):
    """Resolución: amanecer naranja en la boca de la cueva; la colonia empieza a salir; las crías dudan."""

    def build(self):
        L = self.layers
        L['frame'] = cave_mouth_frame(W, H, (W / 2, 250, 340, 170), (12, 7, 8), (220, 120, 60), 14)
        L['sky'] = gradient(W, H, [(0, (110, 60, 120)), (.45, (240, 120, 80)), (.7, (255, 180, 100)), (1, (255, 210, 140))])
        L['sun'] = glow(220, (255, 160, 80), 1.0)
        L['ledge'] = ridge(W, H, 470, 24, (20, 11, 12), 22)

    def draw(self, s, t, dur):
        L = self.layers
        s.blit(L['sky'], (0, 0))
        s.blit(L['sun'], (W // 2 - 220, 360 - 220 - t * 6), special_flags=pygame.BLEND_RGB_ADD)
        colony(s, t, W / 2, 240, 40, (230, 70), 5, (20, 10, 12), .3, stream=.5, dirx=1)
        s.blit(L['frame'], (0, 0))
        s.blit(L['ledge'], (0, 0))
        nest_with_pups(s, W / 2 + 60, 482, t, 10, awake=True, look=math.sin(t * 3))
        bat_sil(s, W / 2 - 240, 420, t * 5, 1.5, (8, 4, 6), (255, 160, 90), (255, 210, 120))


class TrueVoice(Shot):
    """La voz verdadera: anillos dorados claros frente a ecos grises; las diez crías la reconocen."""

    def build(self):
        L = self.layers
        L['bg'] = gradient(W, H, [(0, (60, 30, 50)), (.6, (150, 70, 60)), (1, (40, 20, 20))])
        L['glow'] = glow(260, (255, 170, 80), .8)

    def draw(self, s, t, dur):
        L = self.layers
        s.blit(L['bg'], (0, 0))
        s.blit(L['glow'], (W // 2 - 260, 250 - 260), special_flags=pygame.BLEND_RGB_ADD)
        rnd = random.Random(3)
        for k in range(5):                                                      # susurros falsos (grises, deformes)
            p = ((t * .25 + k / 5) % 1)
            cx, cy = rnd.uniform(100, W - 100), rnd.uniform(100, 300)
            pygame.draw.ellipse(s, lerp((110, 100, 120), (0, 0, 0), p), (cx - 120 * p, cy - 60 * p, 240 * p + 2, 120 * p + 2), 1)
        for k in range(4):                                                      # su voz verdadera (dorada, clara)
            p = ((t * .5 + k / 4) % 1)
            pygame.draw.circle(s, lerp((255, 220, 140), (60, 30, 20), p), (W // 2, 250), int(20 + 380 * p), 3)
        bat_sil(s, W // 2, 250, t * 4, 2.6, (10, 4, 6), (255, 190, 110), (255, 230, 150))
        n_lit = min(10, int(t * 2.2))
        for i in range(10):
            a = math.pi * (.15 + .7 * i / 9)
            x, y = W // 2 - math.cos(a) * 340, 500 - math.sin(a) * 70
            bat_sil(s, x, y, 1 + .3 * math.sin(t * 5 + i), .7, (24, 12, 16), (255, 170, 120) if i < n_lit else None)
            if i < n_lit:
                for sd in (-1, 1):
                    pygame.draw.circle(s, (255, 230, 160), (int(x + sd * 1.8), int(y - 9)), 1)


class Departure(Shot):
    """Imagen final: la colonia sale hacia su nuevo refugio; Mullo con sus diez crías cerca."""

    def build(self):
        L = self.layers
        L['sky'] = gradient(W, H, [(0, (90, 70, 140)), (.4, (240, 130, 90)), (.65, (255, 190, 110)), (1, (255, 220, 160))])
        L['sun'] = glow(260, (255, 180, 90), 1.0)
        L['far'] = ridge(W, H, 470, 50, (130, 70, 70), 51)
        L['mid'] = ridge(W, H, 520, 50, (60, 30, 36), 52)
        cliff = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.polygon(cliff, (24, 12, 16), [(0, H), (0, 160), (90, 150), (220, 210), (300, 330), (330, H)])
        pygame.draw.ellipse(cliff, (4, 2, 4), (120, 330, 150, 140))
        L['cliff'] = cliff

    def draw(self, s, t, dur):
        L = self.layers
        s.blit(L['sky'], (0, 0))
        sy = 470 - t * 10
        s.blit(L['sun'], (640 - 260, sy - 260), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.circle(s, (255, 230, 170), (640, int(sy)), 54)
        s.blit(L['far'], (0, 0))
        s.blit(L['mid'], (0, 0))
        colony(s, t, 200, 400, 60, (80, 40), 6, (30, 14, 18), .3, stream=1.0, dirx=1)
        s.blit(L['cliff'], (0, 0))
        p = (t * .07) % 1
        x, y = 260 + p * 700, 360 - p * 200
        bat_sil(s, x, y, t * 9, 1.3, (20, 8, 10), (255, 200, 120), (255, 230, 150))
        for i in range(10):
            ox, oy = -40 - (i % 5) * 22, 30 + (i // 5) * 18 + math.sin(t * 3 + i) * 6
            bat_sil(s, x + ox, y + oy, t * 14 + i, .45, (26, 10, 14))


class Gallery(Shot):
    """Galerías de los Hongos: hongos luminosos, rastros en el suelo y una cortina de telarañas que el grito rompe."""
    rings = 'screech'

    def build(self):
        L = self.layers
        L['bg'] = gradient(W, H, [(0, (4, 16, 18)), (.5, (8, 34, 36)), (1, (3, 12, 12))])
        L['back'] = ridge(W, H, 200, 40, (6, 22, 24), 81)
        L['floor'] = ridge(W, H, 470, 20, (10, 30, 30), 82)
        rnd = random.Random(83)
        L['fungi'] = [(rnd.choice((rnd.uniform(20, 260), rnd.uniform(W - 260, W - 20))), rnd.uniform(140, 520), rnd.uniform(4, 11))
                      for _ in range(40)]
        L['trail'] = [(140 + k * 52 + rnd.uniform(-8, 8), 500 - k * 6 + rnd.uniform(-5, 5), k % 3) for k in range(12)]
        L['fg'] = glow(46, (40, 220, 170), .9)

    def draw(self, s, t, dur):
        L = self.layers
        s.blit(L['bg'], (0, 0))
        s.blit(L['back'], (0, 0))
        for x, y, r in L['fungi']:
            k = .65 + .35 * math.sin(t * 1.4 + x)
            s.blit(L['fg'], (x - 46, y - 46), special_flags=pygame.BLEND_RGB_ADD)
            pygame.draw.circle(s, (int(24 * k), int(110 * k), int(90 * k)), (int(x), int(y)), int(r))
            pygame.draw.circle(s, (130, 255, 210), (int(x - r / 3), int(y - r / 3)), max(1, int(r / 3)))
        s.blit(L['floor'], (0, 0))
        for x, y, kind in L['trail']:                                   # piedritas, garras y guano
            if kind == 0:
                for d in (-5, 0, 5):
                    pygame.draw.circle(s, (150, 160, 150), (int(x + d), int(y + abs(d) * .4)), 3)
            elif kind == 1:
                for d in (-5, 0, 5):
                    pygame.draw.line(s, (120, 140, 135), (x + d, y - 6), (x + d + 6, y + 6), 2)
            else:
                for d in range(3):
                    pygame.draw.circle(s, (34, 30, 24), (int(x + d * 5), int(y + d % 2 * 3)), 3)
        self.extra(s, t, dur)

    def extra(self, s, t, dur):
        cx, cy = 720, 330
        torn = t > 2.6
        col = (190, 210, 205)
        for a in range(0, 360, 30):                                     # cortina de telarañas
            r = math.radians(a)
            L = 170 if not torn else 170 * max(.15, 1 - (t - 2.6) * .6)
            pygame.draw.line(s, col, (cx, cy), (cx + math.cos(r) * L, cy + math.sin(r) * L), 1)
        for rr in range(30, 180, 28):
            if torn and rr > 170 * max(.15, 1 - (t - 2.6) * .6):
                continue
            pygame.draw.circle(s, col, (cx, cy), rr, 1)
        p = min(1, t / 2.6)
        bx, by = 260 + 280 * p, 300 + 20 * math.sin(t * 2)
        if 1.8 < t < 3.8:                                                # el grito
            for k in range(3):
                q = ((t - 1.8) * .9 + k / 3) % 1
                pygame.draw.circle(s, lerp((170, 235, 255), (8, 30, 32), q), (int(bx), int(by)), int(20 + 200 * q), 2)
        bat_sil(s, bx, by, t * 9, 1.5, (4, 8, 10), (120, 255, 210), (255, 210, 120))


class Whisper(Gallery):
    """El susurro plantado: ondas violetas y deformes suben desde abajo."""

    def extra(self, s, t, dur):
        for k in range(5):
            q = ((t * .3 + k / 5) % 1)
            r = int(30 + 360 * q)
            rect = pygame.Rect(0, 0, r * 2 + int(math.sin(t * 2 + k) * 40), int(r * .7)).move(0, 0)
            rect.center = (W // 2, H + 40 - int(q * 160))
            pygame.draw.ellipse(s, lerp((200, 170, 255), (8, 30, 32), q), rect, 2)
        bat_sil(s, W // 2 - 60, 290, 1.3 + .1 * math.sin(t), 1.9, (4, 8, 10), (180, 160, 255), (255, 210, 120))


class LowPoint(Shot):
    """El punto más bajo: Mullo colgada, agotada; por una grieta entra la primera luz gris."""

    def build(self):
        L = self.layers
        L['bg'] = gradient(W, H, [(0, (8, 8, 22)), (1, (2, 2, 8))])
        roof = pygame.Surface((W, H), pygame.SRCALPHA)
        rnd = random.Random(91)
        pts = [(0, 0)] + [(x, 150 + 30 * math.sin(x * .013) + rnd.uniform(-8, 8)) for x in range(0, W + 20, 20)] + [(W, 0)]
        pygame.draw.polygon(roof, (12, 12, 26), pts)
        pygame.draw.lines(roof, (60, 62, 110), False, pts[1:-1], 2)
        L['roof'] = roof
        beam = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.polygon(beam, (170, 175, 200, 34), [(610, 120), (640, 120), (460, H), (330, H)])
        pygame.draw.polygon(beam, (190, 195, 220, 26), [(618, 120), (632, 120), (420, H), (370, H)])
        L['beam'] = beam
        L['water'] = ridge(W, H, 500, 8, (6, 8, 22), 92)

    def draw(self, s, t, dur):
        L = self.layers
        s.blit(L['bg'], (0, 0))
        s.blit(L['water'], (0, 0))
        s.blit(L['beam'], (0, 0))
        s.blit(L['roof'], (0, 0))
        pygame.draw.line(s, (200, 200, 220), (612, 132), (638, 132), 2)       # la grieta
        sway = math.sin(t * .9) * .06
        bat_sil(s, 420, 250, -1.4, 1.6, (6, 6, 14), (150, 155, 210), (255, 210, 120) if int(t * .5) % 4 else None, ang=math.pi + sway)
        d = (t * .8) % 1                                                         # gota
        pygame.draw.circle(s, (120, 130, 200), (520, int(170 + d * 330)), 2)


class MineFar(Lake):
    """Desde el lago se ve la boca de la mina; de ahí vienen los últimos chillidos."""

    def draw(self, s, t, dur):
        super().draw(s, t, 1e9)
        x, y = 760, 250
        pygame.draw.rect(s, (8, 6, 4), (x - 50, y - 60, 100, 70))
        pygame.draw.rect(s, (110, 72, 40), (x - 56, y - 66, 12, 76))
        pygame.draw.rect(s, (110, 72, 40), (x + 44, y - 66, 12, 76))
        pygame.draw.rect(s, (130, 86, 48), (x - 64, y - 74, 128, 12))
        for k in range(3):
            q = ((t * .45 + k / 3) % 1)
            pygame.draw.circle(s, lerp((255, 150, 210), (6, 8, 24), q), (x, y - 20), int(10 + 160 * q), 2)


class Escape(Mine):
    """Huida: Mullo con las gemelas vuela hacia la luz del amanecer; detrás, los ojos del gigante."""

    def build(self):
        super().build()
        self.layers['dawn'] = glow(260, (255, 170, 80), 1.0)

    def draw(self, s, t, dur):
        L = self.layers
        s.blit(L['bg'], (0, 0))
        s.blit(L['dawn'], (W // 2 - 260, 300 - 260), special_flags=pygame.BLEND_RGB_ADD)
        s.blit(L['tunnel'], (0, 0))
        for x, y, z in L['dust']:
            xx = (x + t * 60 * z) % W
            s.fill((200, 160, 110), (int(xx), int(y), 3, 1))                  # corriente de aire
        p = min(1, t / max(1, dur))
        bx, by = 480 - 40 * p, 330 - 30 * p
        bat_sil(s, bx, by, t * 13, 1.3 - .5 * p, (10, 6, 4), (255, 190, 110), (255, 220, 140))
        for k in (-1, 1):
            bat_sil(s, bx + k * 9, by + 22, t * 15 + k, .45 - .15 * p, (40, 20, 18))
        mx, my = 480, 540 - 20 * math.sin(t * 2)                           # el gigante detrás
        for sd in (-1, 1):
            a = .9 + .25 * math.sin(t * 6)
            pygame.draw.polygon(s, (60, 14, 14), [(mx + sd * 40, my - 30), (mx + sd * (120 - 30 * a), my - 150),
                                                  (mx + sd * 70, my - 40)])
            pygame.draw.circle(s, (255, 60, 40), (mx + sd * 34, my - 50), 9)
            pygame.draw.circle(s, (255, 200, 120), (mx + sd * 34, my - 52), 3)


SHOTS = {'gallery': Gallery, 'whisper': Whisper, 'low_point': LowPoint, 'mine_far': MineFar, 'escape': Escape,
         'dusk': Dusk, 'leaving': Leaving, 'empty_nest': EmptyNest, 'debate': Debate, 'nest_three': NestThree,
         'descent': Descent, 'lake': Lake, 'echo_room': EchoRoom, 'mine_gate': MineGate, 'mine': Mine,
         'dawn_nest': DawnNest, 'true_voice': TrueVoice, 'departure': Departure}


class ImageShot(Shot):
    """Escena con imagen externa (p. ej. generada con IA): paneo lento tipo Ken Burns."""

    def __init__(self, path):
        img = pygame.image.load(path)
        try:
            img = img.convert()
        except pygame.error:
            pass
        k = max(W / img.get_width(), H / img.get_height()) * 1.08
        self.img = pygame.transform.smoothscale(img, (int(img.get_width() * k), int(img.get_height() * k)))
        super().__init__()

    def draw(self, s, t, dur):
        p = min(1, t / max(1, dur))
        ex, ey = self.img.get_width() - W, self.img.get_height() - H
        s.blit(self.img, (-int(ex * (.2 + .6 * p)), -int(ey * (.5 - .3 * p))))


def make_shot(key):
    for ext in ('png', 'jpg', 'jpeg', 'webp'):
        path = os.path.join(ASSET_DIR, 'escenas', f'{key}.{ext}')
        if os.path.exists(path):
            try:
                return ImageShot(path)
            except Exception:
                break
    return SHOTS[key]()


# ------------------------------------------------------------------ portada
class Cover:
    """Portada animada: la boca de la cueva enmarca un cielo de madrugada, la colonia, y Mullo al frente."""

    def __init__(self):
        self.sky = gradient(W, H, [(0, (8, 8, 30)), (.45, (40, 22, 80)), (.7, (130, 60, 110)), (.85, (240, 120, 80)), (1, (255, 180, 110))])
        self.stars = stars(110, 77, (W, 330))
        self.moon = glow(120, (150, 140, 255), .6)
        self.far = ridge(W, H, 470, 40, (54, 28, 64), 61)
        self.frame = cave_mouth_frame(W, H, (W / 2, 300, 420, 260), (6, 4, 10), (90, 60, 120), 66)
        self.floor = ridge(W, H, 560, 26, (5, 3, 8), 67)
        rnd = random.Random(70)
        self.fungi = [(rnd.choice((rnd.uniform(20, 200), rnd.uniform(W - 200, W - 20))), rnd.uniform(380, H - 20), rnd.uniform(3, 7))
                      for _ in range(26)]
        self.fglow = glow(40, (40, 220, 170), .8)
        self.pups = [(rnd.choice((rnd.uniform(30, 230), rnd.uniform(W - 230, W - 30))), rnd.uniform(470, 535), rnd.uniform(0, TAU))
                     for _ in range(10)]
        self.mullo_glow = glow(220, (120, 80, 220), .55)

    def draw(self, s, t, mullo_y=360):
        s.blit(self.sky, (0, 0))
        draw_stars(s, self.stars, t)
        s.blit(self.moon, (W // 2 + 290 - 120, 250 - 120), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.circle(s, (235, 232, 255), (W // 2 + 290, 250), 24)
        pygame.draw.circle(s, self.sky.get_at((W // 2 + 280, 240)), (W // 2 + 279, 243), 22)
        s.blit(self.far, (0, 0))
        colony(s, t * .8, W / 2, 250, 30, (300, 80), 4, (14, 8, 22), .26)
        for k in range(3):                                                      # ondas de ecolocación
            p = ((t * .35 + k / 3) % 1)
            pygame.draw.circle(s, lerp((150, 130, 255), (8, 6, 20), p), (W // 2, mullo_y), int(60 + 520 * p), 2)
        s.blit(self.frame, (0, 0))
        for x, y, r in self.fungi:
            k = .6 + .4 * math.sin(t * 1.5 + x)
            s.blit(self.fglow, (x - 40, y - 40), special_flags=pygame.BLEND_RGB_ADD)
            pygame.draw.circle(s, (int(30 * k), int(150 * k), int(120 * k)), (int(x), int(y)), int(r))
            pygame.draw.circle(s, (120, 255, 210), (int(x - r / 3), int(y - r / 3)), max(1, int(r / 3)))
        s.blit(self.floor, (0, 0))
        for x, y, ph in self.pups:                                              # diez pares de ojitos en la oscuridad
            if (t * .6 + ph) % 4 < 3.7:
                for sd in (-3, 3):
                    pygame.draw.circle(s, (255, 150, 210), (int(x + sd), int(y)), 2)
        s.blit(self.mullo_glow, (W // 2 - 220, mullo_y - 220), special_flags=pygame.BLEND_RGB_ADD)
        bob = math.sin(t * 1.6) * 8
        bat_sil(s, W // 2, mullo_y + bob, 1.1 + .35 * math.sin(t * 3.2), 3.4, (6, 4, 12), (190, 150, 255), (255, 214, 110))
