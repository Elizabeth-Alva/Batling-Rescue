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


def bat_sil(s, x, y, flap, sc=1.0, col=(8, 6, 14), rim=None, eyes=None, ang=0.0, notch=False, muzzle=None,
            scars=None, tuft=None):
    """Silueta de murciélago de frente: alas festoneadas con huesos de los dedos, orejas y ojos.
    notch: muesca en la oreja izquierda (Abuela Canela) · muzzle: color del hocico canoso ·
    scars: color de las cicatrices pequeñas de las alas · tuft: mechón entre las orejas (Chispa)."""
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
        if notch and sd < 0:                                          # oreja izquierda con muesca
            ear = [P(-1.5, -17), P(-8, -30), P(-8.6, -24), P(-6.8, -22.5), P(-9.6, -20), P(-10.5, -13)]
        else:
            ear = [P(sd * 1.5, -17), P(sd * 8, -30), P(sd * 10.5, -13)]
        pygame.draw.polygon(s, col, ear)
        if rim:
            pygame.draw.line(s, rim, ear[0], ear[1], max(1, int(sc)))
    if scars:                                                         # cicatrices pequeñas en las alas
        for sd, (px, py, qx, qy) in ((-1, (30, -6, 36, -1)), (1, (24, 2, 31, 6)), (-1, (16, 6, 21, 12)), (1, (40, -10, 44, -4)),
                                     (1, (14, 8, 18, 13)), (-1, (44, -12, 47, -7)), (1, (33, -2, 37, 3)), (-1, (24, 10, 28, 15)),
                                     (-1, (50, -6, 53, -2)), (1, (50, -8, 52, -3))):          # llenas de cicatrices
            pygame.draw.line(s, scars, P(sd * px, py - 8 * w), P(sd * qx, qy - 8 * w), max(1, int(sc * .9)))
    if muzzle:                                                        # hocico canoso
        mx, my = P(0, -10.5)
        pygame.draw.circle(s, muzzle, (int(mx), int(my)), max(1, int(2.6 * sc)))
    if tuft:                                                          # mechón entre las orejas
        for k, dx in enumerate((-1.6, 0, 1.6)):
            pygame.draw.line(s, tuft, P(dx * .6, -19), P(dx * 1.6 + math.sin(flap * .7 + k) * .8, -25), max(1, int(1.3 * sc)))
    if eyes:
        for sd in (-1, 1):                                            # ojos más grandes, con brillito
            ex, ey = P(sd * 2.9, -14.3)
            r = max(1, int(1.9 * sc))
            pygame.draw.circle(s, eyes, (int(ex), int(ey)), r)
            if sc >= 1.2:
                s.fill((255, 252, 236), (int(ex - r * .4), int(ey - r * .5), max(1, int(sc * .5)), max(1, int(sc * .5))))


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


# ------------------------------------------------------------------ personajes de las cinemáticas
# Abuela Canela: más grande que Mullo, pelaje gris canela, hocico canoso, muesca en la oreja izquierda,
# alas con cicatrices pequeñas y ojos ámbar ya opacos. Planea más de lo que aletea.
CANELA = dict(col=(84, 66, 62), fur=(140, 110, 94), belly=(204, 170, 136), rim=(236, 180, 128), eyes=(236, 184, 100),
              muzzle=(222, 214, 206), ear_in=(206, 140, 128), scars=(156, 132, 118), blush=(214, 130, 120))
MULLO_COL, MULLO_RIM, MULLO_EYES = (36, 22, 58), (200, 160, 255), (255, 196, 92)          # silueta violácea con borde lila y ojos ámbar
CHISPA_TUFT = (255, 160, 70)                                     # el mechón naranja de Chispa
# orden de las diez crías en los nidos de las cinemáticas (y su detalle propio)
NEST_NAMES = ('Chispa', 'Bruno', 'Lía', 'Nube', 'Tito', 'Eco', 'Mora', 'Paco', 'Bolillo', 'Pozolito')
PUP_MARKS = {'Chispa': ('tuft', CHISPA_TUFT), 'Lía': ('bow', (255, 120, 170)), 'Tito': ('ear', None),
             'Paco': ('spot', (245, 240, 250)), 'Bolillo': ('tuft', (250, 220, 160)), 'Pozolito': ('tuft', (255, 120, 90))}


def glide_flap(t, period=3.4, beat=1.1):
    """Fase de ala para planear: alas casi extendidas y, cada tanto, un aleteo lento y espaciado."""
    c = t % period
    if c < beat:
        return .2 + 1.15 * math.sin(math.pi * c / beat)
    return .2 + .08 * math.sin(t * 1.3)


def canela_sil(s, x, y, t, sc=1.25, rim=None, talk=False, hang=False, look=0.0, perch=None):
    """La Abuela Canela. hang=True: colgada boca abajo con las alas cerradas (como descansan los murciélagos
    reales) y solo mueve la cabeza cuando habla. Si no, vuela planeando con aleteos lentos."""
    c = CANELA
    rim = rim or c['rim']
    if not hang:                                                      # en vuelo: planea, alas con cicatrices
        bat_sil(s, x, y, glide_flap(t), sc, (98, 78, 72), rim, None, notch=True, scars=c['scars'])
        pygame.draw.ellipse(s, c['fur'], (x - 6 * sc, y - 6 * sc, 12 * sc, 22 * sc))          # cuerpo gris canela
        pygame.draw.ellipse(s, c['belly'], (x - 3 * sc, y - 2 * sc, 6 * sc, 14 * sc))
        hx, hy = x, y - 14 * sc
        for sd in (-1, 1):                                            # orejas rosadas por dentro (la izquierda con muesca)
            pygame.draw.polygon(s, c['ear_in'], [(hx + sd * 2.6 * sc, hy - 3.5 * sc), (hx + sd * 6.6 * sc, hy - 12.5 * sc),
                                                 (hx + sd * 7.6 * sc, hy + .5 * sc)])
        pygame.draw.circle(s, c['fur'], (int(hx), int(hy)), max(2, int(6.2 * sc)))
        pygame.draw.circle(s, rim, (int(hx), int(hy)), max(2, int(6.2 * sc)), max(1, int(sc * .5)))
        pygame.draw.ellipse(s, c['muzzle'], (hx - 3 * sc, hy + .8 * sc, 6 * sc, 4 * sc))      # hocico canoso
        pygame.draw.circle(s, (56, 36, 34), (int(hx), int(hy + 1.6 * sc)), max(1, int(.8 * sc)))
        for sd in (-1, 1):
            ex, ey = hx + sd * 2.6 * sc, hy - 1.4 * sc
            pygame.draw.circle(s, c['eyes'], (int(ex), int(ey)), max(1, int(1.5 * sc)))
            pygame.draw.circle(s, (230, 220, 200), (int(ex), int(ey)), max(1, int(1.5 * sc)), 1)   # ojos ya opacos
            pygame.draw.circle(s, c['blush'], (int(hx + sd * 4.4 * sc), int(hy + 1.6 * sc)), max(1, int(1.1 * sc)))
        return
    nod = (.13 * math.sin(t * 6.5) + .05 * math.sin(t * 11)) if talk else .03 * math.sin(t * .8)
    a = math.pi + look * .3 + nod                                     # boca abajo, como en el Word

    def P(px, py):                                                    # cuerpo (sin rotar)
        return (x + px * sc, y + py * sc)
    sway = math.sin(t * .9) * .8
    if perch:                                                         # saliente de roca de donde cuelga
        pygame.draw.ellipse(s, perch, (x - 9 * sc, y - 4.5 * sc, 18 * sc, 5.5 * sc))
    for sd in (-1, 1):                                                # patitas con garras agarradas a la roca
        fx, fy = P(sd * 2.2, .2)
        pygame.draw.line(s, c['col'], P(sd * 2.6, 4.5), (fx, fy), max(2, int(1.8 * sc)))
        pygame.draw.line(s, c['col'], (fx, fy), P(sd * 3.6, -.4), max(1, int(sc)))

    def wing(sd):                                                     # cada ala plegada, con el borde festoneado
        pts = [P(sway * .1, 4)]
        for i in range(13):
            q = i / 12
            wq = (math.sin(math.pi * min(1, q * 1.05)) ** .75) * 13 + 2.5
            pts.append(P(sd * wq + sway * q, 4 + q * 34))
        for i in range(4, -1, -1):                                    # festones abajo
            q = i / 4
            pts.append(P(sd * (2 + 9 * q) + sway, 38 + 2.2 * math.sin(q * math.pi * 2) ** 2))
        return pts
    for sd in (-1, 1):
        w_ = wing(sd)
        pygame.draw.polygon(s, c['col'], w_)
        pygame.draw.lines(s, rim if sd < 0 else lerp(rim, c['col'], .45), False, w_[1:14], max(1, int(1.1 * sc)))
    belly = [P(sway * .3 - 5.5, 9), P(sway * .3 + 5.5, 9), P(sway * .8 + 6.5, 28), P(sway * .9, 38), P(sway * .8 - 6.5, 28)]
    pygame.draw.polygon(s, c['fur'], belly)                           # pancita de pelo suave
    pygame.draw.polygon(s, c['belly'], [P(sway * .4 - 3, 13), P(sway * .4 + 3, 13), P(sway * .8 + 3.6, 27), P(sway * .9, 34),
                                        P(sway * .8 - 3.6, 27)])
    bone = lerp(c['col'], (255, 240, 220), .22)
    for sd in (-1, 1):                                                # dedos plegados, pulgares y cicatrices
        pygame.draw.line(s, bone, P(sd * 8 + sway * .2, 8), P(sd * 10 + sway * .7, 33), max(1, int(sc * .8)))
        tx, ty = P(sd * 7.5 + sway * .25, 9)
        pygame.draw.circle(s, bone, (int(tx), int(ty)), max(1, int(1.1 * sc)))
        pygame.draw.line(s, c['scars'], P(sd * 12 + sway * .4, 16), P(sd * 13 + sway * .5, 19.5), max(1, int(sc * .8)))
    hx, hy = P(sway, 46)
    ca, sa = math.cos(a), math.sin(a)

    def Hd(px, py):                                                   # cabeza (gira un poco al hablar)
        px, py = px * sc, py * sc
        return (hx + px * ca - py * sa, hy + px * sa + py * ca)
    for k in range(12):                                               # cuello esponjado de pelo
        aa = k * TAU / 12
        fx, fy = P(sway + math.cos(aa) * 8, 37.5 + math.sin(aa) * 3)
        pygame.draw.circle(s, c['fur'], (int(fx), int(fy)), max(2, int(3 * sc)))
    for sd in (-1, 1):                                                # orejas grandes (hacia abajo), rosadas por dentro
        if sd < 0:
            ear = [Hd(-1, -5), Hd(-10, -19), Hd(-11, -13), Hd(-8.6, -11.8), Hd(-12, -8.5), Hd(-11.5, 0)]
        else:
            ear = [Hd(1, -5), Hd(10, -19), Hd(11.5, 0)]
        pygame.draw.polygon(s, c['fur'], ear)
        pygame.draw.lines(s, rim, False, ear[1:], max(1, int(sc * .8)))
        inner = [Hd(sd * 4, -6), Hd(sd * 9, -15.5), Hd(sd * 9.6, -4)]
        pygame.draw.polygon(s, c['ear_in'], inner)
    hr = max(3, int(9 * sc))
    pygame.draw.circle(s, c['fur'], (int(hx), int(hy)), hr)
    pygame.draw.circle(s, rim, (int(hx), int(hy)), hr, max(1, int(sc * .6)))
    mx, my = Hd(0, 3.8)
    pygame.draw.ellipse(s, (192, 182, 172), (mx - 3 * sc, my - 2 * sc, 6 * sc, 4 * sc))             # hocico canoso
    for sd in (-1, 1):                                                # mejillas rosadas (cara amable)
        bx_, by_ = Hd(sd * 5.6, 1.6)
        pygame.draw.circle(s, c['blush'], (int(bx_), int(by_)), max(1, int(1.4 * sc)))
    nx_, ny_ = Hd(0, 5.4)
    pygame.draw.circle(s, (56, 36, 34), (int(nx_), int(ny_)), max(1, int(1.1 * sc)))               # nariz
    if talk and math.sin(t * 9) > -.2:                                # la boca se abre al hablar
        ox, oy = Hd(0, 7.6)
        pygame.draw.ellipse(s, (60, 22, 24), (ox - 1.7 * sc, oy - 1 * sc, 3.4 * sc, (1.2 + .9 * math.sin(t * 9)) * sc + 1))
    else:                                                             # sonrisa tranquila
        p1, p2, p3 = Hd(-1.8, 7), Hd(0, 7.9), Hd(1.8, 7)
        pygame.draw.lines(s, (70, 40, 38), False, [p1, p2, p3], 1)
    blink = (t % 4.3) < .14
    for sd in (-1, 1):                                                # ojos ámbar, sabios, con párpado
        ex, ey = Hd(sd * 3.4, -1.4)
        er = max(2, int(2 * sc))
        if blink:
            pygame.draw.line(s, (70, 50, 46), (ex - er, ey), (ex + er, ey), max(1, int(sc * .6)))
            continue
        pygame.draw.circle(s, c['eyes'], (int(ex), int(ey)), er)
        pygame.draw.circle(s, (50, 34, 26), (int(ex), int(ey)), max(1, int(er * .55)))
        pygame.draw.circle(s, (232, 222, 204), (int(ex), int(ey)), er, max(1, int(sc * .45)))   # ojos ya opacos
        s.fill((255, 250, 235), (int(ex) - 1, int(ey) - 1, max(1, int(sc * .7)), max(1, int(sc * .7))))
        lx, ly = Hd(sd * 3.4, -1.4 - 3.1)                             # párpado suave: ojitos sonrientes
        pygame.draw.circle(s, c['fur'], (int(lx), int(ly)), er)


def air_wisps(s, t, seed, n, rect, d=(1, 0), col=(200, 205, 220), speed=60, life=4.0, length=26):
    """Corrientes de aire: rizos suaves que avanzan en la dirección d dentro de rect (sigue el aire)."""
    rnd = random.Random(seed)
    x0, y0, w, h = rect
    dx, dy = d
    nx, ny = -dy, dx
    for i in range(n):
        ph, px, py, k = rnd.uniform(0, life), rnd.uniform(0, 1), rnd.uniform(0, 1), rnd.uniform(.6, 1.2)
        q = ((t + ph) % life) / life
        bx = x0 + (px * w + dx * speed * k * life * q) % w
        by = y0 + (py * h + dy * speed * k * life * q) % h
        fade = math.sin(math.pi * q)
        pts = []
        for j in range(6):
            u = j / 5
            wob = math.sin(u * 5 + t * 2 + i) * 4
            pts.append((bx - dx * length * u + nx * wob, by - dy * length * u + ny * wob))
        pygame.draw.lines(s, lerp((0, 0, 0), col, fade * .9), False, pts, 1)


def draw_molt(s, x, y, ang, length=150, alpha=170, seed=5):
    """La piel vieja de Xolthar: silueta pálida y vacía de dieciséis segmentos, quieta (una muda no se anima)."""
    rnd = random.Random(seed)
    pad = int(length * .35)
    tw, th = int(length + 2 * pad), int(length * .6 + 2 * pad)
    tmp = pygame.Surface((tw, th), pygame.SRCALPHA)
    cx, cy = tw / 2, th / 2
    n = 16
    pts, rads = [], []
    for i in range(n):
        u = i / (n - 1)
        pts.append((cx + (.5 - u) * length, cy + math.sin(u * 4.2 + 1) * length * .06))
        rads.append(length * .05 * (1 - .4 * u))                    # 40 % más chica hacia la cola
    nrm = []
    for i in range(n):
        ax, ay = pts[max(0, i - 1)]
        bx, by = pts[min(n - 1, i + 1)]
        d = math.hypot(bx - ax, by - ay) or 1
        nrm.append((-(by - ay) / d, (bx - ax) / d))
    pale, edge = (216, 206, 184, int(alpha * .78)), (242, 234, 216, min(255, alpha + 40))
    hollow, seam = (92, 84, 76, int(alpha * .5)), (170, 160, 140, alpha)
    for i in range(n):                                                # patitas vacías, encogidas
        px, py = pts[i]
        for sd in (-1, 1):
            nx, ny = nrm[i][0] * sd, nrm[i][1] * sd
            k = rads[i] * (1.9 + rnd.uniform(-.2, .3))
            ex, ey = px + nx * k + rnd.uniform(-3, 3), py + ny * k
            pygame.draw.line(tmp, edge, (px + nx * rads[i] * .8, py + ny * rads[i] * .8), (ex, ey), 1)
            pygame.draw.line(tmp, edge, (ex, ey), (ex + rnd.uniform(-5, 5), ey + ny * 3), 1)
    left = [(px + nx * r, py + ny * r) for (px, py), (nx, ny), r in zip(pts, nrm, rads)]
    right = [(px - nx * r, py - ny * r) for (px, py), (nx, ny), r in zip(pts, nrm, rads)]
    pygame.draw.polygon(tmp, pale, left + right[::-1])
    inner = [(px + nx * r * .42, py + ny * r * .42) for (px, py), (nx, ny), r in zip(pts, nrm, rads)]
    inner2 = [(px - nx * r * .42, py - ny * r * .42) for (px, py), (nx, ny), r in zip(pts, nrm, rads)]
    pygame.draw.polygon(tmp, hollow, inner[1:] + inner2[1:][::-1])  # está vacía: se ve el hueco
    for i in range(1, n):                                             # costuras entre segmentos
        pygame.draw.line(tmp, seam, left[i], right[i], 1)
    pygame.draw.lines(tmp, edge, False, left, 1)
    pygame.draw.lines(tmp, edge, False, right, 1)
    for i in (5, 10):                                                 # rasgaduras
        a0, a1 = left[i], left[i + 1]
        pygame.draw.polygon(tmp, (0, 0, 0, 0), [a0, a1, ((a0[0] + a1[0]) / 2 - nrm[i][0] * rads[i] * .6,
                                                          (a0[1] + a1[1]) / 2 - nrm[i][1] * rads[i] * .6)])
    hx, hy = pts[0]
    hr = length * .065
    head = pygame.Rect(0, 0, int(hr * 2.1), int(hr * 2.2))
    head.center = (int(hx + hr * .7), int(hy))
    pygame.draw.ellipse(tmp, pale, head)
    pygame.draw.ellipse(tmp, edge, head, 1)
    for sd in (-1, 1):                                                # cuencas vacías y pinzas sueltas
        pygame.draw.circle(tmp, hollow, (int(hx + hr * .95), int(hy + sd * hr * .45)), max(1, int(hr * .28)))
        pygame.draw.lines(tmp, edge, False, [(hx + hr * 1.5, hy + sd * hr * .4), (hx + hr * 2.4, hy + sd * hr * .95),
                                             (hx + hr * 2.8, hy + sd * hr * .3)], 2)
    rot = pygame.transform.rotate(tmp, -math.degrees(ang))
    s.blit(rot, rot.get_rect(center=(int(x), int(y))))


def xolthar_sil(s, t, hx, hy, ang, sc=1.0, awake=True, n=16, glow_img=None):
    """Xolthar en las cinemáticas: dieciséis segmentos que siguen a la cabeza como un tren, coraza negra con
    vetas rojas, púas, patas articuladas en ola y mandíbulas enormes; despierto, ojos y brillo rojos."""
    pts = []
    gap = 15 * sc
    for i in range(n):
        u = i * gap
        wave = math.sin(i * .55 - t * (5 if awake else .5)) * 10 * sc * min(1, i / 3)
        pts.append((hx - math.cos(ang) * u - math.sin(ang) * wave, hy - math.sin(ang) * u + math.cos(ang) * wave))
    if glow_img is not None and awake:
        s.blit(glow_img, (hx - glow_img.get_width() / 2, hy - glow_img.get_height() / 2), special_flags=pygame.BLEND_RGB_ADD)
    pulse = .5 + .5 * math.sin(t * 7)
    vein = (int(150 + 100 * pulse), 30, 22) if awake else (110, 26, 20)
    for i in range(n - 1, -1, -1):
        px, py = pts[i]
        qx, qy = pts[i - 1] if i else (px + math.cos(ang), py + math.sin(ang))
        a = math.atan2(qy - py, qx - px)
        r = 13 * sc * (1 - .4 * i / n)
        for sd in (-1, 1):                                            # patas en ola (de la cabeza a la cola)
            w = math.sin(t * (12 if awake else 1.2) - i * .7 + (0 if sd > 0 else math.pi)) * .5
            la = a + sd * (math.pi / 2 + w * .5)
            kx, ky = px + math.cos(la) * r * 1.6, py + math.sin(la) * r * 1.6
            fa = la - sd * .8
            pygame.draw.line(s, (40, 10, 10), (px, py), (kx, ky), max(2, int(3 * sc)))
            pygame.draw.line(s, (90, 22, 18), (kx, ky), (kx + math.cos(fa) * r * 1.1, ky + math.sin(fa) * r * 1.1), max(1, int(2 * sc)))
        ca, sa = math.cos(a), math.sin(a)
        for sd in (-1, 1):                                            # púas
            tip = (px - ca * r * .6 - sa * sd * r * 1.7, py - sa * r * .6 + ca * sd * r * 1.7)
            pygame.draw.polygon(s, (30, 6, 8), [(px - sa * sd * r * .8, py + ca * sd * r * .8),
                                                (px + ca * r * .4 - sa * sd * r * .9, py + sa * r * .4 + ca * sd * r * .9), tip])
        pygame.draw.circle(s, (20, 5, 7), (int(px), int(py)), int(r))
        pygame.draw.circle(s, vein, (int(px), int(py)), int(r), max(1, int(2 * sc)))
        pygame.draw.line(s, vein, (px - sa * r * .6, py + ca * r * .6), (px + sa * r * .6, py - ca * r * .6), max(1, int(sc)))
    ca, sa = math.cos(ang), math.sin(ang)

    def H(px, py):
        px, py = px * sc, py * sc
        return (hx + px * ca - py * sa, hy + px * sa + py * ca)
    op = .35 + .35 * math.sin(t * (10 if awake else 1))
    for sd in (-1, 1):                                                # mandíbulas
        base, mid, tip = H(10, sd * 8), H(26, sd * (14 + op * 10)), H(38, sd * (3 + op * 6))
        pygame.draw.lines(s, (36, 8, 8), False, [base, mid, tip], max(3, int(7 * sc)))
        pygame.draw.lines(s, (210, 70, 40), False, [base, mid, tip], max(1, int(2 * sc)))
    head = [H(-12, 0), H(-5, -17), H(12, -15), H(18, 0), H(12, 15), H(-5, 17)]
    pygame.draw.polygon(s, (18, 4, 6), head)
    pygame.draw.polygon(s, (230, 60, 40) if awake else (110, 30, 24), head, max(1, int(2 * sc)))
    for sd in (-1, 1):
        for ex, ey, er in ((8, 7, 4.5), (3, 11, 2.4)):
            px, py = H(ex, sd * ey)
            if awake:
                pygame.draw.circle(s, (255, 50 + int(70 * pulse), 24), (int(px), int(py)), max(1, int(er * sc)))
                pygame.draw.circle(s, (255, 230, 170), (int(px), int(py)), max(1, int(er * sc / 3)))
            else:
                pygame.draw.line(s, (150, 40, 26), (px - er * sc, py), (px + er * sc, py), max(1, int(sc)))


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
    step = int(40 * max(0, min(1, k)))                              # solo se recalcula cuando cambia de paso
    last = cache.get((key, 'last'))
    if last is None or last[0] != step:
        a, b = cache[key]
        out = a.copy()
        b.set_alpha(int(255 * step / 40))
        out.blit(b, (0, 0))
        cache[(key, 'last')] = last = (step, out)
    return last[1]


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

    k0, k1 = 0.0, 1.0                                                  # avance del atardecer en la toma
    canela = True

    def draw(self, s, t, dur):
        k = self.k0 + (self.k1 - self.k0) * min(1, t / max(1, dur))
        sky = _sky([(0, (60, 30, 90)), (.5, (200, 90, 90)), (.8, (255, 160, 90)), (1, (255, 190, 120))],
                   [(0, (24, 16, 60)), (.5, (110, 50, 100)), (.8, (200, 90, 80)), (1, (230, 120, 80))], k, self.layers['cache'], 'd')
        s.blit(sky, (0, 0))
        sy = 380 + 50 * k
        s.blit(self.layers['sun'], (300 - 150, sy - 150), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.circle(s, (255, 200, 140), (300, int(sy)), 46)
        s.blit(self.layers['far'], (-int(t * 3), 0))
        s.blit(self.layers['far'], (W - int(t * 3), 0))
        s.blit(self.layers['mid'], (0, 0))
        self.flock(s, t)
        s.blit(self.layers['cliff'], (0, 0))
        s.blit(self.layers['ground'], (0, 0))
        a = t * .55                                                     # Mullo busca comida cerca... y no encuentra
        x, y = 560 + math.cos(a) * 230, 300 + math.sin(a * 1.6) * 70
        if self.canela:
            canela_sil(s, 200 + 90 * math.sin(t * .18), 150 + 24 * math.sin(t * .36), t, 1.6)   # vuela despacio, planea
        bat_sil(s, x, y, t * 9, 1.15 + .2 * math.sin(a), MULLO_COL, MULLO_RIM, MULLO_EYES, ang=.25 * math.sin(a))
        self.extra(s, t, x, y)

    def flock(self, s, t):
        colony(s, t, 560, 190, 30, (170, 60), 8, (12, 6, 14), .3)       # la colonia sale junta, sin dispersarse

    def extra(self, s, t, x, y):
        pass


class Search(Dusk):
    """Mullo busca alimento cerca de la cueva y no encuentra nada: la colonia ya se alejó y el cielo se apaga."""
    k0, k1 = .55, .9
    canela = False

    def flock(self, s, t):
        colony(s, t, 150, 210, 14, (90, 30), 21, (14, 8, 16), .16)       # la colonia, ya lejos

    def extra(self, s, t, x, y):
        q = (t * .55) % 1                                                # olfatea / ecolocaliza: ondas que vuelven vacías
        pygame.draw.circle(s, lerp((210, 190, 255), (40, 20, 50), q), (int(x), int(y)), int(10 + 120 * q), 1)


class NestView(Shot):
    """Desde dentro de la cueva: la boca enmarca el cielo y en primer plano el nido con las diez crías."""

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
        bat_sil(s, x, y, t * 10, 2.0 - 1.6 * p, MULLO_COL, MULLO_RIM, MULLO_EYES)
        s.blit(self.layers['frame'], (0, 0))
        s.blit(self.layers['ledge'], (0, 0))
        nest_with_pups(s, W / 2, 482, t, 10, awake=True, look=.6 * math.sin(t))


def dead_tree(s, x, ground, sc=1.0, col=(16, 8, 12), rim=None):
    """Árbol seco de la sequía con una rama larga y horizontal (ahí cuelga la colonia a descansar).
    Devuelve los puntos de la rama donde se pueden colgar murciélagos."""
    def P(px, py):
        return (x + px * sc, ground + py * sc)
    trunk = [P(-14, 0), P(-9, -120), P(-12, -190), P(-3, -260), P(6, -190), P(10, -120), P(16, 0)]
    pygame.draw.polygon(s, col, trunk)
    branch = [P(-3, -235), P(80, -250), P(170, -246), P(260, -256), P(330, -248)]
    pygame.draw.lines(s, col, False, branch, max(3, int(9 * sc)))
    pygame.draw.lines(s, col, False, [P(-6, -200), P(-60, -228), P(-110, -224)], max(2, int(7 * sc)))
    pygame.draw.lines(s, col, False, [P(170, -246), P(200, -290), P(230, -300)], max(2, int(5 * sc)))
    pygame.draw.lines(s, col, False, [P(-60, -228), P(-80, -270)], max(2, int(4 * sc)))
    pygame.draw.lines(s, col, False, [P(260, -256), P(290, -285)], max(2, int(4 * sc)))
    if rim:
        pygame.draw.lines(s, rim, False, [(px, py - 4 * sc) for px, py in branch], max(1, int(sc)))
    return [P(px, -248 + 4 * math.sin(px * .05)) for px in (40, 95, 150, 205, 250, 300)]


class Outside(Shot):
    """Afuera de la cueva, al atardecer de la sequía: campo seco, acantilado con la cueva y un árbol seco."""
    tree = (150, 560, 1.0)

    def build(self):
        L = self.layers
        L['sky'] = gradient(W, H, [(0, (52, 28, 86)), (.45, (176, 82, 94)), (.75, (250, 150, 88)), (1, (255, 196, 128))])
        L['sun'] = glow(150, (255, 150, 70), 1.0, 1.8)
        L['far'] = ridge(W, H, 440, 60, (82, 40, 62), 11)
        L['mid'] = ridge(W, H, 490, 50, (46, 22, 38), 12)
        cliff = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.polygon(cliff, (18, 10, 20), [(700, H), (730, 330), (780, 230), (860, 190), (W, 170), (W, H)])
        pygame.draw.ellipse(cliff, (3, 2, 5), (800, 340, 120, 110))
        pygame.draw.ellipse(cliff, (150, 70, 70), (796, 336, 128, 118), 2)
        pygame.draw.lines(cliff, (150, 80, 70), False, [(730, 330), (780, 230), (860, 190), (W, 170)], 2)
        L['cliff'] = cliff
        ground = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.polygon(ground, (32, 16, 20), [(0, 560), (300, 545), (620, 556), (W, 540), (W, H), (0, H)])
        rnd = random.Random(5)
        for _ in range(26):                                             # tierra agrietada por la sequía
            x, y = rnd.uniform(0, W), rnd.uniform(565, H - 6)
            pts = [(x, y)]
            for _ in range(4):
                x, y = x + rnd.uniform(8, 26), y + rnd.uniform(-6, 6)
                pts.append((x, y))
            pygame.draw.lines(ground, (16, 8, 10), False, pts, 2)
        tx, ty, tsc = self.tree
        L['perches'] = dead_tree(ground, tx, ty, tsc, (16, 8, 12), (170, 80, 60))
        L['ground'] = ground

    def back(self, s, t, dur):
        L = self.layers
        s.blit(L['sky'], (0, 0))
        sy = 380 + 30 * min(1, t / max(1, dur))
        s.blit(L['sun'], (560 - 150, sy - 150), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.circle(s, (255, 206, 150), (560, int(sy)), 40)
        s.blit(L['far'], (0, 0))
        s.blit(L['mid'], (0, 0))
        s.blit(L['cliff'], (0, 0))
        s.blit(L['ground'], (0, 0))


class CanelaShot(Outside):
    """La Abuela Canela, colgada boca abajo con las alas cerradas en el árbol seco, avisa que no hay comida y que
    antes del amanecer se mudan; la colonia la escucha y empieza a salir a cazar."""
    tree = (60, 640, 1.9)

    def draw(self, s, t, dur):
        L = self.layers
        self.back(s, t, dur)
        colony(s, t, 640, 200, 18, (200, 60), 31, (34, 16, 26), .26)            # las demás ya salen a cazar
        perches = L['perches']
        for i, (px, py) in enumerate(perches):
            if i in (1, 3):
                continue
            _hanging_bat(s, px, py, 1.25, t + i * 1.7, (34, 18, 26), (210, 130, 100))
        bx, by = perches[1]
        canela_sil(s, bx, by - 4, t, 3.0, hang=True, talk=True, look=.4, perch=None)
        mx, my = perches[3]
        hanging_mullo(s, mx, my, t, 1.55, max(0, math.sin(t * 1.1)) ** 6)


def _hanging_bat(s, x, y, sc, t, col=(22, 14, 22), rim=(110, 70, 80)):
    """Murciélago cualquiera de la colonia colgado boca abajo (silueta sencilla)."""
    sway = math.sin(t * .9) * .6
    pts = []
    for i in range(12):
        q = i / 11
        wq = math.sin(math.pi * q) ** .8 * 9 + 2
        pts.append((x - wq * sc + sway * q, y + q * 30 * sc))
    for i in range(11, -1, -1):
        q = i / 11
        wq = math.sin(math.pi * q) ** .8 * 9 + 2
        pts.append((x + wq * sc + sway * q, y + q * 30 * sc))
    pygame.draw.polygon(s, col, pts)
    pygame.draw.lines(s, rim, False, pts[:12], 1)
    hx, hy = x + sway, y + 35 * sc
    pygame.draw.circle(s, col, (int(hx), int(hy)), max(2, int(6 * sc)))
    for sd in (-1, 1):
        pygame.draw.polygon(s, col, [(hx + sd * 2 * sc, hy + 3 * sc), (hx + sd * 7 * sc, hy + 14 * sc), (hx + sd * 8 * sc, hy)])


class Leaving(Shot):
    """Mullo ya está afuera de la cueva: sale por la boca del acantilado y se aleja volando sobre el campo seco,
    mientras cae la noche. Mira una vez hacia atrás."""

    def build(self):
        L = self.layers
        L['cache'] = {}
        L['stars'] = stars(70, 14, (W, 380))
        L['far'] = ridge(W, H, 450, 60, (52, 30, 64), 15)
        L['mid'] = ridge(W, H, 500, 50, (30, 18, 36), 16)
        cliff = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.polygon(cliff, (14, 8, 18), [(560, H), (600, 300), (660, 190), (760, 140), (880, 120), (W, 110), (W, H)])
        pygame.draw.ellipse(cliff, (110, 60, 90), (696, 296, 178, 158), 3)
        pygame.draw.ellipse(cliff, (3, 2, 5), (700, 300, 170, 150))
        pygame.draw.ellipse(cliff, (0, 0, 0), (725, 330, 120, 100))
        pygame.draw.lines(cliff, (120, 76, 110), False, [(600, 300), (660, 190), (760, 140), (880, 120), (W, 110)], 2)
        L['cliff'] = cliff
        ground = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.polygon(ground, (24, 14, 20), [(0, 560), (300, 540), (620, 555), (W, 540), (W, H), (0, H)])
        rnd = random.Random(17)
        for _ in range(26):                                             # tierra agrietada por la sequía
            x, y = rnd.uniform(0, W), rnd.uniform(565, H - 6)
            pts = [(x, y)]
            for _ in range(4):
                x, y = x + rnd.uniform(8, 26), y + rnd.uniform(-6, 6)
                pts.append((x, y))
            pygame.draw.lines(ground, (12, 6, 10), False, pts, 2)
        tree = [(120, 560), (128, 470), (110, 430), (128, 470), (150, 420), (138, 395), (150, 420), (170, 440)]
        pygame.draw.lines(ground, (10, 4, 8), False, tree, 6)
        pygame.draw.lines(ground, (10, 4, 8), False, [(128, 470), (96, 455), (84, 430)], 4)
        L['ground'] = ground
        L['moon'] = glow(110, (150, 140, 230), .55)
        L['mouth'] = glow(90, (120, 70, 60), .5)

    def draw(self, s, t, dur):
        L = self.layers
        k = min(1, t / max(1, dur))
        sky = _sky([(0, (44, 26, 80)), (.55, (130, 60, 100)), (.85, (220, 110, 80)), (1, (240, 140, 90))],
                   [(0, (10, 10, 36)), (.55, (40, 26, 76)), (.85, (100, 50, 90)), (1, (150, 70, 80))], k, L['cache'], 'o')
        s.blit(sky, (0, 0))
        draw_stars(s, L['stars'], t, .3 + .7 * k)                     # aparecen las estrellas
        my = 150 - 30 * k
        s.blit(L['moon'], (220 - 110, my - 110), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.circle(s, (232, 230, 255), (220, int(my)), 20)
        pygame.draw.circle(s, sky.get_at((210, max(0, int(my) - 8))), (211, int(my) - 5), 19)    # luna creciente
        s.blit(L['far'], (0, 0))
        s.blit(L['mid'], (0, 0))
        colony(s, t, 260, 230, 14, (160, 50), 9, (20, 10, 22), .18)    # la colonia caza a lo lejos
        s.blit(L['cliff'], (0, 0))
        s.blit(L['mouth'], (785 - 90, 375 - 90), special_flags=pygame.BLEND_RGB_ADD)
        s.blit(L['ground'], (0, 0))
        p = min(1, t / max(1, dur - .5))                                # sale de la boca y se aleja (con curva)
        e = p * p * (3 - 2 * p)
        x = 785 - 900 * e
        y = 375 - 230 * math.sin(e * math.pi * .8) - 40 * e
        look = math.exp(-((p - .35) / .08) ** 2)                        # voltea una vez hacia la cueva
        sc = 1.7 - 1.25 * e
        bat_sil(s, x, y, t * (11 - 3 * e), sc, MULLO_COL, MULLO_RIM, MULLO_EYES, ang=-.25 + .45 * look)
        if look > .3:                                                   # sus ojos brillan al mirar atrás
            g = int(120 * look)
            pygame.draw.circle(s, (g, int(g * .8), int(g * .3)), (int(x), int(y - 14 * sc)), max(2, int(6 * sc)), 1)


class Goodbye(NestView):
    """«Ya vuelvo. Quédense quietas»: Mullo flota en el borde del nido frente a sus diez crías."""

    def draw(self, s, t, dur):
        L = self.layers
        k = .25
        sky = _sky([(0, (40, 20, 70)), (.6, (150, 70, 100)), (1, (230, 120, 90))],
                   [(0, (16, 12, 44)), (.6, (70, 36, 90)), (1, (140, 70, 90))], k, L['cache'], 'l')
        s.blit(sky, (0, 0))
        draw_stars(s, L['stars'], t, k)
        s.blit(L['far'], (0, 0))
        s.blit(L['frame'], (0, 0))
        s.blit(L['ledge'], (0, 0))
        nest_with_pups(s, W / 2 + 70, 482, t, 10, awake=True, look=-.8)
        hover = math.sin(t * 2.1) * 6
        bat_sil(s, W / 2 - 230, 392 + hover, 1.0 + .5 * math.sin(t * 13), 1.8, MULLO_COL, MULLO_RIM, MULLO_EYES, ang=.12)


class Advice(Outside):
    """Afuera, en el árbol seco: la Abuela Canela, colgada boca abajo, les da un consejo a todos los grandes
    (las crías no están: se quedaron en el nido). Mullo, en la rama junto a ella, escucha con atención."""
    tree = (60, 640, 1.9)

    def draw(self, s, t, dur):
        L = self.layers
        self.back(s, t, dur)
        air_wisps(s, t, 3, 12, (300, 160, 600, 300), (.9, .3), (250, 220, 200), 40)   # el aire debe salir
        perches = L['perches']
        for i, (px, py) in enumerate(perches):
            if i in (1, 3):
                continue
            _hanging_bat(s, px, py, 1.25, t + i * 1.7, (34, 18, 26), (210, 130, 100))   # los grandes escuchan
        bx, by = perches[1]
        canela_sil(s, bx, by - 4, t, 3.0, hang=True, talk=True, look=.7, perch=None)
        mx, my = perches[3]
        nod = max(0, math.sin(t * 1.4)) ** 6                               # Mullo escucha y asiente
        hanging_mullo(s, mx, my, t, 1.55, nod)
        for k in range(2):                                                 # dos más llegan volando a escuchar
            fx = 620 + 110 * k + 20 * math.sin(t * .8 + k)
            bat_sil(s, fx, 300 + 40 * k + 10 * math.sin(t * 1.3 + k), t * 9 + k, .9, (34, 18, 26), (210, 130, 100))


def curled_centipede(s, cx, cy, sc, t, body=(34, 12, 16), vein=(170, 44, 32)):
    """Un ciempiés gigante dormido y enroscado (como lo cuenta la Abuela): dieciséis segmentos en espiral."""
    breathe = 1 + .04 * math.sin(t * 1.6)
    pts = []
    for i in range(16):
        a = -1.2 + i * .52
        r = (14 + i * 3.2) * sc * breathe
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r * .8))
    for i in range(15, -1, -1):
        px, py = pts[i]
        rr = 10 * sc * (1 - .4 * i / 16)
        for sd in (-1, 1):                                                  # patitas casi quietas
            la = -1.2 + i * .52 + sd * 1.3 + .1 * math.sin(t * .8 + i)
            pygame.draw.line(s, body, (px, py), (px + math.cos(la) * rr * 1.7, py + math.sin(la) * rr * 1.4), max(1, int(2 * sc)))
        pygame.draw.circle(s, body, (int(px), int(py)), int(rr))
        pygame.draw.circle(s, vein, (int(px), int(py)), int(rr), max(1, int(1.5 * sc)))
    hx, hy = pts[0]
    for sd in (-1, 1):                                                      # ojos cerrados
        pygame.draw.line(s, (220, 120, 90), (hx - 4 * sc + sd * 5 * sc, hy), (hx + 1 * sc + sd * 5 * sc, hy), max(1, int(sc)))
    q = (t * .6) % 1                                                        # zzz
    from ui import text, F_S
    text(s, F_S, 'z', hx - 30 * sc - q * 10, hy - 20 * sc - q * 16, (240, 220, 210))


class Tale(Advice):
    """La Abuela cuenta la historia del ciempiés gigante: en una nube de cuento aparece dormido y enroscado."""

    def draw(self, s, t, dur):
        super().draw(s, t, dur)
        k = min(1, max(0, (t - .6) / 1.4))
        if k <= 0:
            return
        L = self.layers
        b = L.get('bubble')
        if b is None:
            b = L['bubble'] = pygame.Surface((380, 250), pygame.SRCALPHA)
        b.fill((0, 0, 0, 0))
        for ox, oy, r in ((190, 130, 100), (110, 140, 70), (270, 140, 72), (150, 80, 70), (240, 82, 66), (190, 175, 70)):
            pygame.draw.circle(b, (255, 236, 220, 46), (ox, oy), r)
        for ox, oy, r in ((190, 130, 100), (110, 140, 70), (270, 140, 72), (150, 80, 70), (240, 82, 66), (190, 175, 70)):
            pygame.draw.circle(b, (255, 226, 200, 70), (ox, oy), r, 2)
        curled_centipede(b, 190, 132, 2.0, t)
        b.set_alpha(int(235 * k))
        s.blit(b, (430, 110))
        px, py = L['perches'][1]                                            # burbujitas desde la Abuela
        for i, (fx, fy, r) in enumerate(((px + 90, py + 70, 6), (px + 130, py + 40, 9), (px + 175, py + 10, 12))):
            if k > i * .25:
                pygame.draw.circle(s, (255, 226, 200), (int(fx), int(fy)), r, 2)


def hanging_mullo(s, x, y, t, sc, nod=0.0):
    """Mullo colgada boca abajo en la rama: alas cerradas violetas con borde lila y ojos ámbar."""
    sway = math.sin(t * .9) * .6
    pts = []
    for i in range(14):
        q = i / 13
        wq = math.sin(math.pi * q) ** .8 * 10 + 2
        pts.append((x - wq * sc + sway * q, y + q * 30 * sc))
    for i in range(13, -1, -1):
        q = i / 13
        wq = math.sin(math.pi * q) ** .8 * 10 + 2
        pts.append((x + wq * sc + sway * q, y + q * 30 * sc))
    pygame.draw.polygon(s, MULLO_COL, pts)
    pygame.draw.lines(s, MULLO_RIM, True, pts, max(1, int(sc)))
    hx, hy = x + sway, y + (36 + 2 * nod) * sc
    for sd in (-1, 1):                                                     # orejas grandes y puntiagudas (hacia abajo)
        ear = [(hx + sd * 2 * sc, hy + 3 * sc), (hx + sd * 9 * sc, hy + 17 * sc), (hx + sd * 10 * sc, hy)]
        pygame.draw.polygon(s, MULLO_COL, ear)
        pygame.draw.line(s, MULLO_RIM, ear[1], ear[2], max(1, int(sc)))
    pygame.draw.circle(s, MULLO_COL, (int(hx), int(hy)), max(2, int(6.5 * sc)))
    pygame.draw.circle(s, MULLO_RIM, (int(hx), int(hy)), max(2, int(6.5 * sc)), 1)
    for sd in (-1, 1):
        pygame.draw.circle(s, MULLO_EYES, (int(hx + sd * 2.6 * sc), int(hy + .5 * sc)), max(1, int(1.6 * sc)))



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


def pup_col(name, k=.8):
    """Color de pelaje de cada cría (el mismo que en el juego), para que se reconozcan en las cinemáticas."""
    from ui import PUP_LOOKS, PUP_FUR
    fur = PUP_LOOKS.get(name, {}).get('fur', PUP_FUR)
    return tuple(int(v * k) for v in fur[1])


def pup_sil(s, x, y, flap, sc, name, t, lit=True, rim=None):
    """Cría en las cinemáticas: su color de pelaje, cabeza grande y redonda, ojitos rosados, cachetitos y su rasgo."""
    from ui import PUP_LOOKS, tuft_belly
    lk = PUP_LOOKS.get(name, {})
    col = pup_col(name)
    light = lerp(col, (255, 255, 255), .22)
    bat_sil(s, x, y, flap, sc, col, rim or lerp(col, (255, 230, 240), .45), None)
    if lk.get('chubby'):                                                  # pancita redonda
        pygame.draw.ellipse(s, light, (x - 6.5 * sc, y - 1 * sc, 13 * sc, 15 * sc))
    if lk.get('fluff'):                                                   # pelito esponjado
        for k in range(10):
            a = k * TAU / 10
            pygame.draw.circle(s, lerp(col, (255, 255, 255), .32), (int(x + math.cos(a) * 8 * sc), int(y + 5 * sc + math.sin(a) * 9 * sc)), max(1, int(2.6 * sc)))
    if lk.get('tuft'):                                                    # mechón esponjado en la pancita
        tuft_belly(s, x, y + 6 * sc, max(.7, sc * 1.2), PUP_MARKS[name][1], t)
    hx, hy = x, y - 15 * sc
    hr = max(3, int(8.5 * sc))
    for sd in (-1, 1):                                                    # orejas grandes, rosadas por dentro
        ear = [(hx + sd * 2.5 * sc, hy - 5 * sc), (hx + sd * 9 * sc, hy - 17 * sc), (hx + sd * 10 * sc, hy + 1 * sc)]
        pygame.draw.polygon(s, col, ear)
        pygame.draw.polygon(s, (230, 150, 186), [(hx + sd * 4.5 * sc, hy - 5 * sc), (hx + sd * 8.6 * sc, hy - 13 * sc), (hx + sd * 9 * sc, hy - 1 * sc)])
    pygame.draw.circle(s, col, (int(hx), int(hy)), hr)
    pygame.draw.circle(s, lerp(col, (255, 230, 240), .45), (int(hx), int(hy)), hr, 1)
    pygame.draw.ellipse(s, light, (hx - 3.6 * sc, hy + 1 * sc, 7.2 * sc, 5 * sc))
    sleepy = lk.get('eyes') in ('closed', 'sleepy') and not lit
    for sd in (-1, 1):
        ex, ey = hx + sd * 3.4 * sc, hy - .6 * sc
        er = max(1, int(2.5 * sc))
        if sleepy or ((t * .7 + x * .01) % 4) > 3.85:
            pygame.draw.arc(s, (60, 30, 50), (ex - er, ey - er, 2 * er, 2 * er), math.pi * 1.05, math.pi * 1.95, max(1, int(sc * .6)))
        else:
            pygame.draw.circle(s, (255, 200, 230), (int(ex), int(ey)), er)       # ojitos rosados
            pygame.draw.circle(s, (54, 26, 44), (int(ex), int(ey)), max(1, int(er * .6)))
            s.fill((255, 255, 255), (int(ex - er * .3), int(ey - er * .4), 1, 1))
        pygame.draw.circle(s, (240, 120, 160), (int(hx + sd * 5.6 * sc), int(hy + 2.6 * sc)), max(1, int(1.4 * sc)))
    mx, my = hx, hy + 3.2 * sc                                            # sonrisita
    pygame.draw.lines(s, (70, 34, 52), False, [(mx - 2 * sc, my), (mx - 1 * sc, my + 1 * sc), (mx, my), (mx + 1 * sc, my + 1 * sc), (mx + 2 * sc, my)], 1)
    if lk.get('tears') and lit:                                          # lagrimitas
        q = (t * 1.3) % 1
        for sd in (-1, 1):
            pygame.draw.circle(s, (150, 210, 255), (int(hx + sd * 4 * sc), int(hy + 2 * sc + q * 6 * sc)), max(1, int(sc * .8)))
    pup_mark(s, x, y, name, t, sc)


def pup_mark(s, px, py, name, t, sc=.55):
    """El detalle de cada cría sobre su silueta, grande para que se note: mechón, moño, oreja doblada o manchita."""
    kind, col = PUP_MARKS.get(name, (None, None))
    u = max(sc, .6) * 1.35
    if kind == 'tuft':                                                   # (el mechón va en la pancita: ver pup_sil)
        pass
    elif kind == 'bow':
        bx, by = px - 7 * u, py - 22 * u
        for sd in (-1, 1):
            pygame.draw.polygon(s, col, [(bx, by), (bx + sd * 6, by - 4), (bx + sd * 6, by + 4)])
        pygame.draw.circle(s, (255, 230, 240), (int(bx), int(by)), 2)
    elif kind == 'ear':
        pts = [(px + 3 * u, py - 17 * u), (px + 12 * u, py - 23 * u), (px + 13 * u, py - 14 * u)]
        pygame.draw.polygon(s, (190, 130, 160), pts)
    elif kind == 'spot':
        pygame.draw.circle(s, col, (int(px), int(py - 14 * u)), 3)


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
        nm = NEST_NAMES[i] if i < len(NEST_NAMES) else None
        pup_sil(s, px + look * 1.5 * (i % 2), py - 4, 1.0 + .2 * math.sin(t * 2 + i), .74, nm, t + i, lit=awake)
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
        sc = .7 + .9 * p
        bat_sil(s, x, y, t * (10 if p < 1 else 2), sc, MULLO_COL, MULLO_RIM, MULLO_EYES)
        if p < 1:                                                                   # trae poca comida: una polillita
            draw_moth(s, x, y + 26 * sc, t, sc * 1.5)
        else:                                                                       # lo deja en el piso... ¡y se va corriendo!
            r = max(0.0, t - 3.6)
            gx = x + 34 * sc + 160 * r ** 1.3
            hop = abs(math.sin(r * 9)) * 6 * min(1, r * 3)
            if gx < W + 30:
                draw_moth(s, gx, y + 30 * sc - hop, t, sc * 1.3, still=r <= 0, run=r)
                if 0 < r < 1.5:                                                      # polvito de la carrera
                    for k in range(3):
                        q = (r * 3 + k / 3) % 1
                        pygame.draw.circle(s, (90, 84, 96), (int(gx - 14 - q * 20), int(y + 30 * sc + 4 - q * 6)), max(1, int(3 * (1 - q))))


def draw_moth(s, x, y, t, sc=1.0, still=False, run=0.0):
    """Un grillito (toda la comida que Mullo pudo encontrar en la sequía), de lado: cuerpo verde olivo con
    rayitas, cabecita con ojo brillante, alitas dobladas, pata de salto y antenas largas.
    run > 0: las patitas corren (se va corriendo)."""
    kick = math.sin(t * 9) * .25 if not still else 0.0
    body, light, dark = (128, 150, 70), (176, 196, 104), (70, 86, 36)
    pygame.draw.ellipse(s, dark, (x - 10 * sc, y - 3 * sc, 17 * sc, 6.4 * sc))           # sombra / contorno
    pygame.draw.ellipse(s, body, (x - 9.4 * sc, y - 2.6 * sc, 16 * sc, 5.4 * sc))         # abdomen
    pygame.draw.ellipse(s, light, (x - 7 * sc, y - 2.4 * sc, 10 * sc, 2 * sc))            # brillo
    for i in range(3):                                                                    # rayitas
        pygame.draw.line(s, dark, (x - 6 * sc + i * 3 * sc, y - 1.6 * sc), (x - 6.6 * sc + i * 3 * sc, y + 2 * sc), 1)
    wing = [(x - 1 * sc, y - 2.6 * sc), (x - 11 * sc, y - 3.4 * sc), (x - 9 * sc, y - 1 * sc)]     # alitas dobladas
    pygame.draw.polygon(s, (150, 140, 90), wing)
    pygame.draw.polygon(s, dark, wing, 1)
    hx, hy = x + 7.5 * sc, y - 1.2 * sc
    pygame.draw.circle(s, dark, (int(hx), int(hy)), max(2, int(3.4 * sc)))
    pygame.draw.circle(s, body, (int(hx), int(hy)), max(2, int(3 * sc)))                  # cabecita
    pygame.draw.circle(s, (30, 26, 16), (int(hx + 1 * sc), int(hy - .6 * sc)), max(1, int(1.1 * sc)))   # ojito
    s.fill((255, 255, 240), (int(hx + .6 * sc), int(hy - 1.2 * sc), 1, 1))
    sway = math.sin(t * 6) * 1.5 * sc
    pygame.draw.lines(s, dark, False, [(hx + 1 * sc, hy - 2.4 * sc), (hx + 6 * sc, hy - 9 * sc + sway), (hx + 12 * sc, hy - 10 * sc + sway)], 1)
    pygame.draw.lines(s, dark, False, [(hx, hy - 2.6 * sc), (hx + 3 * sc, hy - 10 * sc - sway), (hx + 6 * sc, hy - 14 * sc - sway)], 1)
    knee = (x - 2 * sc, y - 7 * sc - kick * 4 * sc)                                      # pata de salto
    pygame.draw.lines(s, dark, False, [(x - 1 * sc, y + 1 * sc), knee, (x - 9 * sc, y + 4.5 * sc)], max(1, int(1.6 * sc)))
    for k, dx in enumerate((2, 4.5)):                                                     # patitas delanteras
        step = math.sin(run * 30 + k * math.pi) * 1.8 * sc if run else 0
        pygame.draw.line(s, dark, (x + dx * sc, y + 2 * sc), (x + (dx + 1.5) * sc + step, y + 5.5 * sc), 1)


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
        bat_sil(s, 440, 410, 1.5 + .1 * math.sin(t), 1.9, MULLO_COL, MULLO_RIM, MULLO_EYES)
        if t > 2.0:                                                                 # el chillido que conoce
            for k in range(3):
                p = ((t - 2.0) * .5 + k / 3) % 1
                pygame.draw.circle(s, lerp((255, 150, 210), (14, 12, 26), p), (760, 560), int(10 + 260 * p), 2)


class NestThree(CaveInterior):
    sky_stops = [(0, (16, 18, 60)), (1, (60, 50, 120))]
    light_col = (120, 110, 210)

    def extra(self, s, t, dur):
        nest_with_pups(s, 560, 478, t, 3, awake=False, sleeping=True)
        bat_sil(s, 360, 420, 1.2, 1.6, MULLO_COL, MULLO_RIM, MULLO_EYES)
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
        bat_sil(s, W / 2 + math.sin(t * 1.3) * 60, 260 + math.sin(t * 2) * 20, t * 6, 1.7, MULLO_COL, MULLO_RIM, MULLO_EYES, ang=math.pi + .2 * math.sin(t))


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
        L['sala'] = [(rnd.uniform(140, W - 140), rnd.uniform(380, 560), rnd.uniform(0, 6), rnd.choice((-1, 1))) for _ in range(5)]

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
        for sx_, sy_, ph, dr in L['sala']:                             # salamandras: se hunden al verla pasar
            near = x > sx_ - 160
            q = 0.0 if not near else min(1, (x - sx_ + 160) / 90)
            if q < 1:
                draw_salamander(s, sx_ + math.sin(t * .4 + ph) * 18 * dr, sy_, t + ph, dr, 1 - q)
            if 0 < q < 1 or (q >= 1 and x - sx_ < 260):
                rr = int(6 + 30 * min(1, (x - sx_ + 70) / 200))
                pygame.draw.ellipse(s, (40, 50, 110), (sx_ - rr, sy_ - rr * .35, 2 * rr, rr * .7), 1)
        bat_sil(s, x, y, t * 9, 1.4, MULLO_COL, MULLO_RIM, MULLO_EYES)
        bat_sil(s, x, 2 * 320 - y + 40, t * 9, 1.4, (14, 16, 40), None, None, ang=math.pi)  # reflejo en el agua
        for i, bx in enumerate((700, 820)):                            # escarabajos en la orilla: también oyen
            if (t + i * 1.3) % 4 < 3:
                for sd in (-4, 4):
                    pygame.draw.circle(s, (230, 120, 60), (bx + sd, 292 + i * 6), 2)


def draw_salamander(s, x, y, t, dr=1, k=1.0, sc=1.7):
    """Salamandra del Lago Negro sobre el agua (pálida, con manchitas cálidas); k < 1 se va hundiendo."""
    if k <= .02:
        return
    body = lerp((22, 30, 64), (232, 214, 194), k)
    spot = lerp((22, 30, 64), (232, 150, 92), k)
    pts = [(x - dr * 16 * sc + dr * i * 4 * sc, y + math.sin(t * 4 - i) * 1.5 * sc) for i in range(9)]
    for i in range(len(pts) - 1):
        pygame.draw.line(s, body, pts[i], pts[i + 1], max(1, int((1 + i * .5) * sc)))
    for fx in (-6, 6):                                                  # patitas
        pygame.draw.line(s, body, (x + dr * fx * sc, y), (x + dr * (fx - 3) * sc, y + 4 * sc), max(1, int(sc)))
    pygame.draw.ellipse(s, body, (x + dr * 16 * sc - 6 * sc, y - 4 * sc, 12 * sc, 8 * sc))
    for i in (3, 5, 7):
        pygame.draw.circle(s, spot, (int(pts[i][0]), int(pts[i][1] - sc)), max(1, int(sc)))
    pygame.draw.circle(s, (20, 14, 20), (int(x + dr * 19 * sc), int(y - sc)), max(1, int(sc)))


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
        air_wisps(s, t, 11, 10, (0, 120, 380, 300), (1, .35), (170, 160, 230), 55)          # el aire entra a la sala
        air_wisps(s, t, 12, 10, (W - 380, 120, 380, 300), (-1, .35), (170, 160, 230), 55)
        for k in range(6):                                                   # ecos que rebotan y se deforman
            p = ((t * .35 + k / 6) % 1)
            r = int(30 + 420 * p)
            col = lerp((190, 170, 255), (0, 0, 0), p)
            rect = pygame.Rect(0, 0, r * 2, int(r * 1.2)).move(W // 2 - r, 420 - int(r * .6))
            pygame.draw.ellipse(s, col, rect.inflate(int(math.sin(t * 3 + k) * 30), 0), 2)
        s.blit(self.layers['island'], (0, 0))
        bat_sil(s, 410, 440, 1.2 + .2 * math.sin(t * 2), 1.7, MULLO_COL, MULLO_RIM, MULLO_EYES)
        bat_sil(s, 560, 470, 1.0 + .3 * math.sin(t * 6), .7, (30, 20, 40), (240, 160, 210), (255, 220, 240))


class Mine(Shot):
    """Mina Vieja: vigas que se alejan, rieles, vagonetas, lámparas apagadas, polvo ámbar y, al fondo, los ojos
    rojos de los cazadores (en la oscuridad solo se les ven los ojos)."""
    gate = True

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
        self.floor_extra(s, t, dur)
        for x, y, z in L['dust']:
            yy = (y + t * 12 * z) % H
            c = int(80 + 90 * z)
            s.fill((c, int(c * .75), int(c * .45)), (int(x + math.sin(t + y) * 8), int(yy), 2, 2))
        if self.gate:                                                          # ojos de cazadores en la oscuridad
            for i, (ex, ey) in enumerate(((440, 280), (520, 310), (470, 330))):
                if (t + i * .9) % 3 < 2.2:
                    for sd in (-5, 5):
                        pygame.draw.circle(s, (220, 60, 40), (ex + sd, ey), 2)
        self.mullo(s, t, dur)

    def floor_extra(self, s, t, dur):
        pass

    def mullo(self, s, t, dur):
        p = min(1, t / max(1, dur))
        bat_sil(s, 700 - 300 * p, 200 + 60 * p, t * 9, 1.6 - .9 * p, MULLO_COL, MULLO_RIM, MULLO_EYES)


class MineGate(Mine):
    """La entrada de la mina: ojos de cazadores y, en el suelo, una piel vieja de ciempiés tan larga como una vagoneta."""
    gate = True

    def floor_extra(self, s, t, dur):
        draw_molt(s, 500, 462, .1, 330, 200)

    def mullo(self, s, t, dur):
        p = min(1, t / 3.5)
        e = p * p * (3 - 2 * p)                                           # llega y se detiene a mirarla
        bat_sil(s, 760 - 210 * e, 230 + 120 * e + 6 * math.sin(t * 2), t * (9 if p < 1 else 6), 1.5 - .3 * e, MULLO_COL, MULLO_RIM, MULLO_EYES, ang=.25 * e)


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
        q = min(1, t / 7)                                               # la Abuela sale al final, la última
        canela_sil(s, W / 2 + 120 + 160 * q, 190 - 60 * q + 8 * math.sin(t * .9), t, 1.7 - .5 * q, (255, 170, 100))
        s.blit(L['ledge'], (0, 0))
        nest_with_pups(s, W / 2 + 60, 482, t, 10, awake=True, look=-.6 + .4 * math.sin(t * 2.5))   # dudan y miran
        p = min(1, t / 3.5)
        e = p * p * (3 - 2 * p)                                           # Mullo sale del nido hacia la boca
        mx, my = W / 2 + 60 + 120 * e, 430 - 230 * e
        look = max(0, (t - 3.0)) * 2                                      # se detiene y voltea a verlas
        bat_sil(s, mx, my + 6 * math.sin(t * 2), t * (11 - 4 * e), 1.5 - .3 * e, MULLO_COL, MULLO_RIM, MULLO_EYES,
                ang=math.pi * .08 * min(1, look) * (1 if int(t) % 2 else -1) if t > 3 else 0)


class ReturnNest(CaveInterior):
    """Mullo regresa al nido de siempre con las gemelas; las otras ocho la esperan y por fin están las diez."""
    sky_stops = [(0, (60, 40, 110)), (1, (200, 110, 110))]                  # la boca ya se pinta de amanecer
    light_col = (230, 150, 120)

    def extra(self, s, t, dur):
        p = min(1, t / 3.2)
        e = p * p * (3 - 2 * p)
        n = 10 if p >= 1 else 8
        nest_with_pups(s, 560, 478, t, n, awake=True, look=-.8 if p < 1 else .4 * math.sin(t * 3))
        if p < 1:                                                       # llega volando con Bolillo y Pozolito
            x = 250 + (520 - 250) * e
            y = 200 + (400 - 200) * e - 80 * math.sin(e * math.pi)
            sc = .8 + .8 * e
            bat_sil(s, x, y, t * 11, sc, MULLO_COL, MULLO_RIM, MULLO_EYES)
            for k in (-1, 1):
                pup_sil(s, x + k * 14 * sc, y + 26 * sc, t * 15 + k, .42 * sc + .1, 'Bolillo' if k < 0 else 'Pozolito', t + k)
        else:                                                           # se posa junto al nido, feliz
            bat_sil(s, 400, 410 + 4 * math.sin(t * 2), 1.0 + .3 * math.sin(t * 3), 1.6, MULLO_COL, MULLO_RIM, MULLO_EYES)


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
        bat_sil(s, W // 2, 250, t * 4, 2.6, MULLO_COL, MULLO_RIM, MULLO_EYES)
        order = [4, 3, 5, 2, 6, 1, 7, 0, 8, 9]                            # Chispa (al centro) y luego las demás
        names = ['Pozolito', 'Tito', 'Nube', 'Bruno', 'Chispa', 'Lía', 'Eco', 'Mora', 'Paco', 'Bolillo']
        lit = {}
        if t > 1.2:
            lit[4] = 1.2
        for j, i in enumerate(order[1:]):
            if t > 2.4 + j * .32:
                lit[i] = 2.4 + j * .32
        for i in range(10):
            a = math.pi * (.15 + .7 * i / 9)
            x, y = W // 2 - math.cos(a) * 340, 500 - math.sin(a) * 70
            on = i in lit
            if on:                                                      # contestan y vuelan hacia su mamá
                k = min(1, max(0, t - lit[i] - 1.2) / 2.4)
                k = k * k * (3 - 2 * k)
                tx, ty = W // 2 + (i - 4.5) * 34, 340 + abs(i - 4.5) * 8
                x, y = x + (tx - x) * k, y + (ty - y) * k + math.sin(t * 4 + i) * 3 * k
            hop = math.sin(min(1, (t - 1.2) / .35) * math.pi) * 10 if i == 4 and 1.2 < t < 1.55 else 0
            if on:
                pup_sil(s, x, y - hop, 1 + .3 * math.sin(t * 5 + i), .78, names[i], t + i, True, (255, 190, 140))
            else:
                bat_sil(s, x, y - hop, 1 + .3 * math.sin(t * 5 + i), .78, (40, 22, 30), None)
        if t > 1.2:                                                     # el chillido de Chispa, el primero
            q = ((t - 1.2) * .7) % 1
            x4, y4 = W // 2 - math.cos(math.pi * (.15 + .7 * 4 / 9)) * 340, 500 - math.sin(math.pi * (.15 + .7 * 4 / 9)) * 70
            pygame.draw.circle(s, lerp((255, 160, 210), (40, 20, 20), q), (int(x4), int(y4)), int(8 + 60 * q), 2)


class Departure(Shot):
    """Imagen final: antes del amanecer la colonia parte completa hacia su nuevo refugio; Mullo con sus diez crías."""

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
        sy = 560 - min(t, 40) * 1.5                                        # antes del amanecer: el sol aún no sale
        s.blit(L['sun'], (640 - 260, sy - 260), special_flags=pygame.BLEND_RGB_ADD)
        s.blit(L['far'], (0, 0))
        s.blit(L['mid'], (0, 0))
        colony(s, t, 200, 400, 60, (80, 40), 6, (30, 14, 18), .3, stream=1.0, dirx=1)
        s.blit(L['cliff'], (0, 0))
        p = (t * .07) % 1
        x, y = 260 + p * 700, 360 - p * 200
        bat_sil(s, x, y, t * 9, 1.3, MULLO_COL, MULLO_RIM, MULLO_EYES)
        for i in range(10):
            ox, oy = -40 - (i % 5) * 22, 30 + (i // 5) * 18 + math.sin(t * 3 + i) * 6
            pup_sil(s, x + ox, y + oy, t * 14 + i, .5, NEST_NAMES[i], t + i)
        canela_sil(s, x - 170, y + 40 + 8 * math.sin(t * .9), t, 1.55, (255, 190, 130))       # planea, aletea poco


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
        for x, y, kind in L['trail']:                                   # piedritas movidas y rasguños
            if kind % 2 == 0:
                for d in (-5, 0, 5):
                    pygame.draw.circle(s, (170, 180, 170), (int(x + d), int(y + abs(d) * .4)), 3)
            else:
                for d in (-5, 0, 5):
                    pygame.draw.line(s, (150, 170, 165), (x + d, y - 6), (x + d + 6, y + 6), 2)
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
        bat_sil(s, bx, by, t * 9, 1.5, MULLO_COL, MULLO_RIM, MULLO_EYES)


class Whisper(Gallery):
    """El susurro plantado: ondas violetas y deformes suben desde abajo."""

    def extra(self, s, t, dur):
        air_wisps(s, t, 21, 12, (200, 300, 560, 340), (0, -1), (180, 170, 240), 35)
        for k in range(5):
            q = ((t * .3 + k / 5) % 1)
            r = int(30 + 360 * q)
            rect = pygame.Rect(0, 0, r * 2 + int(math.sin(t * 2 + k) * 40), int(r * .7)).move(0, 0)
            rect.center = (W // 2, H + 40 - int(q * 160))
            pygame.draw.ellipse(s, lerp((200, 170, 255), (8, 30, 32), q), rect, 2)
        bat_sil(s, W // 2 - 60, 290, 1.3 + .1 * math.sin(t), 1.9, MULLO_COL, MULLO_RIM, MULLO_EYES)


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
        self.layers['red'] = glow(220, (170, 24, 12), .8)

    def draw(self, s, t, dur):
        L = self.layers
        s.blit(L['bg'], (0, 0))
        s.blit(L['dawn'], (W // 2 - 260, 300 - 260), special_flags=pygame.BLEND_RGB_ADD)
        s.blit(L['tunnel'], (0, 0))
        air_wisps(s, t, 41, 30, (60, 120, W - 120, 470), (0, -1), (240, 214, 170), 90, 3.0, 30)    # sigue el aire
        p = min(1, t / max(1, dur))
        bx, by = 480 - 40 * p, 330 - 30 * p
        bat_sil(s, bx, by, t * 13, 1.3 - .5 * p, MULLO_COL, MULLO_RIM, MULLO_EYES)
        for k in (-1, 1):
            pup_sil(s, bx + k * 11, by + 24, t * 15 + k, .5 - .15 * p, 'Bolillo' if k < 0 else 'Pozolito', t + k)
        xolthar_sil(s, t, 470 + 40 * math.sin(t * 1.3), 452 - 14 * math.sin(t * 2), -math.pi / 2 + .3 * math.sin(t * 1.3),
                    2.0, True, glow_img=L['red'])                             # Xolthar detrás


SHOTS = {'gallery': Gallery, 'whisper': Whisper, 'low_point': LowPoint, 'mine_far': MineFar, 'escape': Escape,
         'dusk': Dusk, 'leaving': Leaving, 'empty_nest': EmptyNest, 'debate': Debate, 'nest_three': NestThree,
         'descent': Descent, 'lake': Lake, 'echo_room': EchoRoom, 'mine_gate': MineGate, 'mine': Mine,
         'dawn_nest': DawnNest, 'true_voice': TrueVoice, 'departure': Departure,
         'canela': CanelaShot, 'goodbye': Goodbye, 'advice': Advice, 'tale': Tale, 'return_nest': ReturnNest,
         'search': Search}


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
