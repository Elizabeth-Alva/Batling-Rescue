"""Objetos del ambiente dibujados con más detalle (se pintan una sola vez en el fondo de la cueva).

Hongos luminosos, cristales, estalactitas, telarañas, piedritas, musgo, rastros, agua,
y en la mina: rieles, vigas, faroles y vagonetas.
"""
import math
import random

import pygame

TAU = math.tau


def mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


# ---------------------------------------------------------------- hongos
def mushroom(s, x, y, r, cap, glow, rnd):
    """Hongo en vista 3/4: tallo pálido, sombrero abombado con laminillas que brillan, motas y reflejo."""
    pygame.draw.ellipse(s, (6, 10, 10), (x - r * .9 + 2, y + r * .9, r * 1.8 + 2, r * .7))          # sombra
    stem = mix(glow, (220, 230, 220), .6)
    pygame.draw.rect(s, shade(stem, .55), (x - r * .32, y, r * .64 + 1, r * 1.15))
    pygame.draw.rect(s, shade(stem, .85), (x - r * .32, y, r * .3 + 1, r * 1.15))
    cw, ch = r * 2.1, r * 1.25
    pygame.draw.ellipse(s, glow, (x - cw / 2, y - ch * .2, cw, ch * .55))                           # laminillas
    pygame.draw.ellipse(s, shade(cap, .6), (x - cw / 2, y - ch * .75, cw, ch))
    pygame.draw.ellipse(s, cap, (x - cw * .44, y - ch * .72, cw * .86, ch * .78))
    pygame.draw.ellipse(s, mix(cap, glow, .45), (x - cw * .3, y - ch * .68, cw * .42, ch * .34))  # reflejo
    if r >= 4:
        for _ in range(rnd.randint(2, 3)):
            sx, sy = x + rnd.uniform(-.55, .55) * r, y - ch * rnd.uniform(.2, .5)
            pygame.draw.circle(s, mix(glow, (255, 255, 255), .55), (int(sx), int(sy)), max(1, r // 4))
    pygame.draw.arc(s, mix(glow, (255, 255, 255), .2), (x - cw / 2, y - ch * .75, cw, ch), math.pi * 1.05, math.pi * 1.95, 1)


def mushroom_cluster(s, x, y, cap, glow, rnd, big=False):
    n = rnd.randint(3, 5) if big else rnd.randint(2, 4)
    caps = sorted([(rnd.uniform(-10, 10), rnd.uniform(-8, 8), rnd.randint(5, 9) if big else rnd.randint(3, 5)) for _ in range(n)],
                  key=lambda c: c[1])                                   # de atrás hacia adelante
    for ox, oy, r in caps:
        mushroom(s, x + ox, y + oy, r, cap, glow, rnd)
    for _ in range(rnd.randint(3, 6)):                                                      # esporas brillantes
        a, d = rnd.uniform(0, TAU), rnd.uniform(10, 18)
        s.fill(mix(glow, (255, 255, 255), .4), (int(x + math.cos(a) * d), int(y + math.sin(a) * d), 1, 1))


# ---------------------------------------------------------------- cristales
def crystal_cluster(s, x, y, col, side, rnd):
    """Racimo de 2-4 prismas que salen de la pared (side: -1 pared a la izquierda, 1 a la derecha)."""
    pygame.draw.ellipse(s, (14, 12, 18), (x - 7, y - 4, 14, 9))                             # base de roca
    for _ in range(rnd.randint(2, 4)):
        ang = (0 if side < 0 else math.pi) + rnd.uniform(-.8, .8)
        L, w = rnd.uniform(8, 16), rnd.uniform(2.5, 4.2)
        ca, sa = math.cos(ang), math.sin(ang)
        bx, by = x + rnd.uniform(-3, 3), y + rnd.uniform(-3, 3)
        tip = (bx + ca * L, by + sa * L)
        l = (bx - sa * w, by + ca * w)
        r = (bx + sa * w, by - ca * w)
        m = (bx + ca * L * .72, by + sa * L * .72)
        pygame.draw.polygon(s, shade(col, .35), [l, r, (m[0] + sa * w * .7, m[1] - ca * w * .7), tip, (m[0] - sa * w * .7, m[1] + ca * w * .7)])
        pygame.draw.polygon(s, shade(col, .75), [(bx, by), r, (m[0] + sa * w * .7, m[1] - ca * w * .7), tip])      # cara iluminada
        pygame.draw.line(s, mix(col, (255, 255, 255), .55), (bx, by), tip, 1)
        s.fill(mix(col, (255, 255, 255), .8), (int(tip[0]), int(tip[1]), 2, 2))


# ---------------------------------------------------------------- roca
def stalactite(s, x, y0, h, dark, rim, rnd, down=True):
    """Estalactita (cuelga de la pared de arriba) o estalagmita (down=False), con volumen y gotita."""
    sd = 1 if down else -1
    w = rnd.uniform(4, 6.5)
    tip = (x + rnd.uniform(-1.5, 1.5), y0 + sd * h)
    pygame.draw.polygon(s, shade(dark, .7), [(x - w, y0), (x + w, y0), tip])
    pygame.draw.polygon(s, dark, [(x - w, y0), (x + w * .2, y0), tip])
    pygame.draw.line(s, rim, (x - w, y0), tip, 1)
    for k in (.35, .65):                                                                   # anillos de mineral
        yy = y0 + sd * h * k
        ww = w * (1 - k)
        pygame.draw.line(s, shade(rim, .7), (x - ww, yy), (x + ww * .6, yy), 1)
    if down and rnd.random() < .5:
        pygame.draw.circle(s, (150, 190, 220), (int(tip[0]), int(tip[1] + 3)), 1)


def cobweb(s, cx, cy, side, col, r):
    """Telaraña de esquina con hilos radiales e hilos curvos que cuelgan (semitransparente)."""
    tmp = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
    ox, oy = r + 2, r + 2
    a0, a1 = (math.pi / 2, math.pi) if side > 0 else (0, math.pi / 2)
    spokes = [a0 + (a1 - a0) * k / 6 for k in range(7)]
    for a in spokes:
        pygame.draw.aaline(tmp, (*col, 170), (ox, oy), (ox + math.cos(a) * r, oy + math.sin(a) * r))
    for rk in (.25, .45, .65, .85):
        for i in range(len(spokes) - 1):
            a, b = spokes[i], spokes[i + 1]
            p0 = (ox + math.cos(a) * r * rk, oy + math.sin(a) * r * rk)
            p1 = (ox + math.cos(b) * r * rk, oy + math.sin(b) * r * rk)
            mid = ((p0[0] + p1[0]) / 2 - math.cos((a + b) / 2) * r * .05, (p0[1] + p1[1]) / 2 - math.sin((a + b) / 2) * r * .05)
            pygame.draw.aalines(tmp, (*col, 120), False, [p0, mid, p1])
    pygame.draw.circle(tmp, (*col, 200), (int(ox + math.cos((a0 + a1) / 2) * r * .5), int(oy + math.sin((a0 + a1) / 2) * r * .5)), 1)
    s.blit(tmp, (cx - ox, cy - oy))


# ---------------------------------------------------------------- suelo
def pebble(s, x, y, r, base, rnd):
    pygame.draw.ellipse(s, (8, 8, 10), (x - r + 1, y - r * .7 + 2, 2 * r, 1.4 * r))
    pygame.draw.ellipse(s, base, (x - r, y - r * .7, 2 * r, 1.4 * r))
    pygame.draw.ellipse(s, mix(base, (255, 255, 255), .25), (x - r * .6, y - r * .55, r * .9, r * .6))


def floor_decal(s, x, y, theme, rnd):
    """Detalles del suelo según el escenario."""
    if theme == 'fungi':
        k = rnd.random()
        if k < .45:                                                                         # musgo
            for _ in range(5):
                pygame.draw.circle(s, rnd.choice(((52, 96, 70), (60, 112, 78), (46, 86, 64))),
                                   (int(x + rnd.uniform(-7, 7)), int(y + rnd.uniform(-5, 5))), rnd.randint(2, 4))
        elif k < .75:                                                                       # brotecitos
            for _ in range(3):
                bx, by = x + rnd.uniform(-6, 6), y + rnd.uniform(-4, 4)
                pygame.draw.line(s, (60, 110, 86), (bx, by), (bx + rnd.uniform(-2, 2), by - 4), 1)
                s.fill((120, 220, 170), (int(bx), int(by - 5), 1, 1))
        else:
            pebble(s, x, y, rnd.uniform(2, 4), (84, 98, 96), rnd)
    elif theme == 'lake':
        if rnd.random() < .5:                                                               # charquito que refleja
            pygame.draw.ellipse(s, (22, 26, 52), (x - 8, y - 3, 16, 7))
            pygame.draw.line(s, (60, 70, 120), (x - 4, y - 1), (x + 3, y - 1), 1)
        else:
            for _ in range(rnd.randint(2, 3)):
                pebble(s, x + rnd.uniform(-6, 6), y + rnd.uniform(-4, 4), rnd.uniform(2, 3.5), (74, 76, 112), rnd)
    else:
        k = rnd.random()
        if k < .4:                                                                          # carboncillo
            for _ in range(4):
                pygame.draw.polygon(s, (24, 20, 18), [(x + rnd.uniform(-6, 6) + dx, y + rnd.uniform(-4, 4) + dy)
                                                      for dx, dy in ((0, -2), (2, 1), (-2, 1))])
        elif k < .7:                                                                        # astilla de madera
            a = rnd.uniform(0, math.pi)
            pygame.draw.line(s, (96, 66, 40), (x - math.cos(a) * 7, y - math.sin(a) * 7), (x + math.cos(a) * 7, y + math.sin(a) * 7), 2)
        else:
            pebble(s, x, y, rnd.uniform(2, 4), (98, 82, 66), rnd)


def dry_patch(s, x, y, rnd, base=(92, 84, 70)):
    """Tierra reseca y agrietada: la sequía también llegó a la cueva."""
    w, h = rnd.randint(26, 40), rnd.randint(16, 26)
    pygame.draw.ellipse(s, base, (x - w / 2, y - h / 2, w, h))
    pygame.draw.ellipse(s, mix(base, (255, 255, 255), .12), (x - w / 2 + 3, y - h / 2 + 2, w - 6, h - 6))
    for _ in range(6):                                                  # grietas en forma de placas
        px, py = x + rnd.uniform(-w / 3, w / 3), y + rnd.uniform(-h / 3, h / 3)
        pts = [(px, py)]
        for _ in range(3):
            px, py = px + rnd.uniform(-7, 7), py + rnd.uniform(-5, 5)
            pts.append((px, py))
        pygame.draw.lines(s, mix(base, (0, 0, 0), .45), False, pts, 1)


def husk(s, x, y, rnd):
    """Restos secos de insectos (alas de polilla y caparazones vacíos): ya no queda comida."""
    if rnd.random() < .5:                                                # alas de polilla, pálidas
        a = rnd.uniform(0, TAU)
        for sd in (-1, 1):
            cx, cy = x + math.cos(a + sd * 1.2) * 3, y + math.sin(a + sd * 1.2) * 3
            pygame.draw.ellipse(s, (150, 140, 120), (cx - 3, cy - 2, 6, 4))
            pygame.draw.ellipse(s, (110, 100, 86), (cx - 3, cy - 2, 6, 4), 1)
    else:                                                                # caparacito vacío
        pygame.draw.ellipse(s, (80, 60, 40), (x - 3, y - 2, 7, 5))
        pygame.draw.line(s, (120, 96, 66), (x - 2, y), (x + 3, y), 1)
        for sd in (-1, 1):
            pygame.draw.line(s, (70, 52, 36), (x, y + sd * 2), (x + rnd.uniform(-4, 4), y + sd * 4), 1)


def mud_flat(s, x, y, rx, ry, base, rnd):
    """Charco que se secó: lodo claro partido en placas irregulares, con borde oscuro donde llegaba el agua."""
    p1, p2, p3 = rnd.uniform(0, TAU), rnd.uniform(0, TAU), rnd.uniform(0, TAU)
    seeds = []
    for _ in range(int(rx * ry / 80) + 4):
        a, r = rnd.uniform(0, TAU), math.sqrt(rnd.random()) * 1.05
        seeds.append((math.cos(a) * rx * r, math.sin(a) * ry * r, rnd.uniform(.08, .24)))
    crack, rim = mix(base, (0, 0, 0), .5), mix(base, (0, 0, 0), .22)
    W_, H_ = int(rx * 2 + 16), int(ry * 2 + 16)
    tmp = pygame.Surface((W_, H_), pygame.SRCALPHA)
    ox, oy = W_ / 2, H_ / 2
    for py in range(H_):
        dy = py - oy
        for px in range(W_):
            dx = px - ox
            ang = math.atan2(dy / ry, dx / rx)
            edge = 1 + .14 * math.sin(3 * ang + p1) + .08 * math.sin(5 * ang + p2) + .05 * math.sin(9 * ang + p3)
            e = (dx / rx) ** 2 + (dy / ry) ** 2
            if e > edge * 1.2:
                continue
            if e > edge:                                                # orilla vieja, más oscura
                tmp.set_at((px, py), (*rim, 200))
                continue
            d1 = d2 = 1e9
            k1 = 0
            for sx, sy, k in seeds:
                d = (dx - sx) ** 2 + ((dy - sy) * 1.3) ** 2
                if d < d1:
                    d1, d2, k1 = d, d1, k
                elif d < d2:
                    d2 = d
            gap = math.sqrt(d2) - math.sqrt(d1)
            if gap < 1.4:
                col = crack
            elif gap < 3.2:                                             # borde de la placa que se levanta
                col = mix(base, (250, 240, 215), k1 + .2)
            else:
                col = mix(base, (240, 225, 195), k1)
            tmp.set_at((px, py), col)
    s.blit(tmp, (x - ox, y - oy))
    for _ in range(rnd.randint(2, 3)):                                   # restos de insectos sobre el lodo
        husk(s, x + rnd.uniform(-rx * .55, rx * .55), y + rnd.uniform(-ry * .45, ry * .45), rnd)


def withered_mushroom(s, x, y, rnd):
    """Hongo marchito: tallo doblado, sombrero caído y sin brillo."""
    for _ in range(rnd.randint(2, 3)):
        ox, oy, r = x + rnd.uniform(-8, 8), y + rnd.uniform(-5, 5), rnd.randint(3, 6)
        lean = rnd.choice((-1, 1))
        pygame.draw.ellipse(s, (8, 8, 8), (ox - r + 2, oy + r * .8, r * 2, r * .6))
        stem = [(ox, oy + r * 1.1), (ox + lean * r * .3, oy + r * .3), (ox + lean * r * .9, oy - r * .1)]
        pygame.draw.lines(s, (104, 96, 82), False, stem, 2)
        hx, hy = stem[-1]
        cap = rnd.choice(((92, 78, 66), (84, 76, 70), (100, 88, 70)))
        pygame.draw.ellipse(s, mix(cap, (0, 0, 0), .4), (hx - r, hy - r * .2, r * 2, r * 1.1))           # sombrero caído
        pygame.draw.ellipse(s, cap, (hx - r * .85, hy - r * .25, r * 1.7, r * .8))
        pygame.draw.line(s, mix(cap, (0, 0, 0), .5), (hx - r * .5, hy + r * .1), (hx + r * .4, hy + r * .3), 1)   # arruga


def shell(s, x, y, rnd):
    """Conchita de caracol vacía que quedó en seco cuando bajó el agua."""
    r = rnd.uniform(2.5, 4)
    pygame.draw.circle(s, (20, 20, 30), (int(x + 1), int(y + 1)), int(r))
    pygame.draw.circle(s, (196, 188, 176), (int(x), int(y)), int(r))
    pygame.draw.arc(s, (120, 110, 100), (x - r * .6, y - r * .6, r * 1.2, r * 1.2), 0, 4.5, 1)


def algae_cluster(s, x, y, rnd):
    """Algas que brillan en la orilla del lago."""
    for _ in range(rnd.randint(3, 5)):
        ax, ay = x + rnd.uniform(-5, 5), y + rnd.uniform(-5, 5)
        pygame.draw.circle(s, (30, 110, 74), (int(ax), int(ay)), 2)
        s.fill((140, 255, 190), (int(ax), int(ay), 1, 1))
    pygame.draw.aaline(s, (40, 130, 90), (x - 6, y + 2), (x + 6, y - 2))


def trail_mark(s, x, y, kind, ang, k=1.0):
    """Rastros de las crías: piedritas movidas y rasguños. k > 1: más grandes y claros (los de Chispa)."""
    if k > 1:                                                         # mancha clara debajo: se distingue del suelo
        halo = pygame.Surface((int(30 * k), int(30 * k)), pygame.SRCALPHA)
        for r in range(int(15 * k), 0, -2):
            pygame.draw.circle(halo, (220, 200, 160, int(40 * (1 - r / (15 * k)))), (int(15 * k), int(15 * k)), r)
        s.blit(halo, (x - 15 * k, y - 15 * k))
    if kind == 'pebble':
        rnd = random.Random(int(x * 7 + y))
        for j in range(3):
            pebble(s, x + math.cos(ang + j * 2.1) * 4 * k, y + math.sin(ang + j * 2.1) * 4 * k, 2.4 * k,
                   (190, 186, 172) if k > 1 else (150, 150, 140), rnd)
    elif kind == 'claw':
        ca, sa = math.cos(ang), math.sin(ang)
        for j in (-4, 0, 4):
            ax, ay = x - sa * j * k, y + ca * j * k
            pts = [(ax - ca * 6 * k, ay - sa * 6 * k), (ax + ca * k - sa * .8 * k, ay + sa * k + ca * .8 * k), (ax + ca * 6 * k, ay + sa * 6 * k)]
            pygame.draw.lines(s, (24, 18, 16), False, pts, 2 if k <= 1 else 3)
            pygame.draw.lines(s, (196, 184, 160) if k > 1 else (130, 120, 108), False, [(p[0] + 1, p[1] + 1) for p in pts], 1 if k <= 1 else 2)
    else:
        for j in range(4):
            px, py = x + math.cos(ang + j * 1.6) * (2 + j) * k, y + math.sin(ang + j * 1.6) * (2 + j) * k
            pygame.draw.circle(s, (34, 28, 22), (int(px), int(py)), max(2, int(2 * k)))
            s.fill((110, 98, 80) if k > 1 else (70, 62, 50), (int(px) - 1, int(py) - 1, 1, 1))


# ---------------------------------------------------------------- mina
def rails(s, pts):
    if len(pts) < 3:
        return
    for i in range(1, len(pts) - 1):                                                       # durmientes con sombra y clavos
        (ax, ay), (bx, by) = pts[i - 1], pts[i + 1]
        d = math.hypot(bx - ax, by - ay) or 1
        nx, ny = -(by - ay) / d, (bx - ax) / d
        x, y = pts[i]
        pygame.draw.line(s, (16, 10, 6), (x - nx * 12 + 2, y - ny * 12 + 3), (x + nx * 12 + 2, y + ny * 12 + 3), 6)
        pygame.draw.line(s, (78, 52, 32), (x - nx * 12, y - ny * 12), (x + nx * 12, y + ny * 12), 6)
        pygame.draw.line(s, (104, 72, 44), (x - nx * 12, y - ny * 12 - 1), (x + nx * 12, y + ny * 12 - 1), 1)
        for sd in (-6, 6):
            s.fill((150, 140, 120), (int(x + nx * sd), int(y + ny * sd), 2, 2))
    for off in (-6, 6):
        line = []
        for i in range(len(pts)):
            (ax, ay), (bx, by) = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
            d = math.hypot(bx - ax, by - ay) or 1
            nx, ny = -(by - ay) / d, (bx - ax) / d
            line.append((pts[i][0] + nx * off, pts[i][1] + ny * off))
        pygame.draw.lines(s, (20, 16, 14), False, [(p[0] + 1, p[1] + 2) for p in line], 4)
        pygame.draw.lines(s, (92, 76, 64), False, line, 3)
        pygame.draw.lines(s, (180, 160, 140), False, line, 1)


def beam(s, x0, y0, x1, y1):
    """Viga de madera con veta, tornillos y postes en los extremos."""
    horiz = abs(y1 - y0) < abs(x1 - x0)
    pygame.draw.line(s, (12, 8, 4), (x0 + 3, y0 + 6), (x1 + 3, y1 + 6), 13)
    pygame.draw.line(s, (88, 58, 32), (x0, y0), (x1, y1), 12)
    for off, col in ((-4, (126, 88, 52)), (-1, (100, 68, 40)), (2, (78, 52, 30)), (4, (70, 46, 26))):
        a = (x0, y0 + off) if horiz else (x0 + off, y0)
        b = (x1, y1 + off) if horiz else (x1 + off, y1)
        pygame.draw.line(s, col, a, b, 1)
    for k in (.08, .5, .92):
        px, py = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
        pygame.draw.circle(s, (40, 36, 34), (int(px), int(py)), 3)
        pygame.draw.circle(s, (160, 150, 130), (int(px) - 1, int(py) - 1), 1)
    for px, py in ((x0, y0), (x1, y1)):                                                    # postes contra la pared
        pygame.draw.rect(s, (70, 46, 26), (px - 7, py - 7, 14, 14))
        pygame.draw.rect(s, (120, 84, 50), (px - 7, py - 7, 14, 14), 2)


def lantern(s, x, y):
    """Farol de minero apagado: jaula de metal, vidrio oscuro con reflejo y gancho."""
    pygame.draw.circle(s, (10, 8, 6), (int(x + 2), int(y + 3)), 8)
    pygame.draw.circle(s, (30, 28, 26), (int(x), int(y)), 7)
    pygame.draw.circle(s, (54, 58, 60), (int(x), int(y)), 5)
    for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
        pygame.draw.line(s, (120, 96, 62), (x, y), (x + math.cos(a) * 7, y + math.sin(a) * 7), 1)
    pygame.draw.circle(s, (140, 110, 70), (int(x), int(y)), 7, 2)
    pygame.draw.circle(s, (120, 96, 62), (int(x), int(y)), 2)
    s.fill((210, 205, 190), (int(x - 3), int(y - 3), 2, 2))


def cart(s, x, y, ang, sc=1.0, coal=True):
    """Vagoneta oxidada vista desde arriba, con manchas de óxido, remaches y carbón."""
    w, h = int(38 * sc), int(26 * sc)
    tmp = pygame.Surface((w + 10, h + 12), pygame.SRCALPHA)
    pygame.draw.rect(tmp, (0, 0, 0, 120), (7, 8, w, h), border_radius=5)                    # sombra
    for wx in (6, w - 6):
        for wy in (2, h + 4):
            pygame.draw.rect(tmp, (20, 16, 14), (wx, wy, 9, 5), border_radius=2)
    pygame.draw.rect(tmp, (110, 56, 32), (4, 4, w, h), border_radius=5)
    pygame.draw.rect(tmp, (52, 28, 18), (8, 8, w - 8, h - 8), border_radius=3)
    rnd = random.Random(int(x * 3 + y))
    if coal:
        for _ in range(int(9 * sc)):
            cx, cy = rnd.uniform(11, w - 3), rnd.uniform(11, h - 3)
            pygame.draw.circle(tmp, (22, 20, 22), (int(cx), int(cy)), rnd.randint(2, 4))
            tmp.fill((80, 80, 90), (int(cx) - 1, int(cy) - 1, 1, 1))
    for _ in range(4):                                                                      # manchas de óxido
        pygame.draw.circle(tmp, (150, 84, 40), (int(rnd.uniform(6, w)), int(rnd.choice((6, h + 2)))), 2)
    pygame.draw.rect(tmp, (176, 102, 58), (4, 4, w, h), 2, border_radius=5)
    for k in range(4):
        tmp.fill((200, 150, 100), (8 + k * (w - 10) // 3, 5, 2, 2))
        tmp.fill((200, 150, 100), (8 + k * (w - 10) // 3, h + 1, 2, 2))
    rot = pygame.transform.rotate(tmp, -math.degrees(ang))
    s.blit(rot, rot.get_rect(center=(int(x), int(y))))
