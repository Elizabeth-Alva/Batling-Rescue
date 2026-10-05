"""Interfaz: fuentes, dibujo de personajes, menú, fondo animado, HUD y minimapa."""
import math
import random

import pygame

from settings import (W, H, TAU, GOAL, SHIELD_T, SHIELD_CD, TILE, NEST, SONAR_EXPOSE_T, SCREECH_CD, C_TEXT, C_PURPLE, C_GREEN,
                      C_PUP, MAP_W, MAP_H)

F_S = F_M = F_L = F_XL = F_XS = None


def init_fonts():
    global F_S, F_M, F_L, F_XL, F_XS
    F_XS = pygame.font.SysFont("arial", 15, bold=True)
    F_S = pygame.font.SysFont("arial", 18, bold=True)
    F_M = pygame.font.SysFont("arial", 28, bold=True)
    F_L = pygame.font.SysFont("arial", 54, bold=True)
    F_XL = pygame.font.SysFont("arial", 92, bold=True)


# ---------------------------------------------------------------- dibujo básico
def text(s, f, t, x, y, col=C_TEXT, center=False):
    im = f.render(t, True, col)
    s.blit(im, im.get_rect(center=(x, y)) if center else (x, y))


def make_glow(f, t, col, blur=5, pad=26):
    """Superficie con el texto desenfocado (para sumar detrás del texto nítido)."""
    g = f.render(t, True, col)
    big = pygame.Surface((g.get_width() + 2 * pad, g.get_height() + 2 * pad), pygame.SRCALPHA)
    big.blit(g, (pad, pad))
    sm = pygame.transform.smoothscale(big, (max(1, big.get_width() // blur), max(1, big.get_height() // blur)))
    return pygame.transform.smoothscale(sm, big.get_size())


def heart(s, x, y, col):
    pygame.draw.circle(s, col, (x - 5, y), 6)
    pygame.draw.circle(s, col, (x + 5, y), 6)
    pygame.draw.polygon(s, col, [(x - 11, y + 2), (x + 11, y + 2), (x, y + 15)])


def draw_bat(s, x, y, flap, sc=1.0, col=(40, 30, 60), body=(55, 42, 80), edge=(95, 75, 130)):
    w = math.sin(flap)
    for sd in (-1, 1):
        pts = [(x + sd * 6 * sc, y - 2 * sc), (x + sd * 30 * sc, y - 14 * sc - w * 12 * sc),
               (x + sd * 40 * sc, y + 4 * sc - w * 16 * sc), (x + sd * 28 * sc, y + 6 * sc - w * 4 * sc),
               (x + sd * 20 * sc, y + 14 * sc - w * 2 * sc), (x + sd * 10 * sc, y + 8 * sc)]
        pygame.draw.polygon(s, col, pts)
        pygame.draw.polygon(s, edge, pts, max(1, int(2 * sc)))
    pygame.draw.ellipse(s, body, (x - 8 * sc, y - 12 * sc, 16 * sc, 26 * sc))
    for sd in (-1, 1):
        pygame.draw.polygon(s, body, [(x + sd * 3 * sc, y - 10 * sc), (x + sd * 9 * sc, y - 22 * sc), (x + sd * 10 * sc, y - 8 * sc)])
        pygame.draw.circle(s, (255, 220, 90), (int(x + sd * 3.5 * sc), int(y - 6 * sc)), max(1, int(2 * sc)))


def draw_bat_tilted(s, x, y, flap, tilt, sc=1.0):
    """Murciélago inclinado (en radianes) según hacia dónde gira."""
    if abs(tilt) < .02:
        return draw_bat(s, x, y, flap, sc)
    tmp = pygame.Surface((130, 100), pygame.SRCALPHA)
    draw_bat(tmp, 65, 50, flap, sc)
    rot = pygame.transform.rotate(tmp, -math.degrees(tilt))
    s.blit(rot, rot.get_rect(center=(int(x), int(y))))


def draw_pup(s, x, y, t, sc=.55):
    draw_bat(s, x, y, t * 9, sc, (120, 70, 100), (150, 95, 125), (190, 120, 160))


SPIDER_LOOK = {   # patas, cuerpo, borde
    'spider':   ((8, 6, 10), (22, 16, 24), (60, 40, 60)),
    'runner':   ((30, 8, 8), (50, 14, 16), (140, 44, 44)),
    'listener': ((12, 14, 16), (30, 32, 38), (100, 120, 130)),
    'behemoth': ((20, 4, 10), (44, 8, 18), (190, 30, 60)),
}


def draw_spider(s, x, y, anim, kind='spider', size=1.0):
    legs, body, edge = SPIDER_LOOK[kind]
    for k in range(8):
        a = TAU * k / 8 + math.sin(anim * (11 if kind == 'runner' else 8) + k) * .25
        pygame.draw.lines(s, legs, False, [(x, y), (x + math.cos(a) * 14 * size, y + math.sin(a) * 14 * size - 4),
                                           (x + math.cos(a) * 24 * size, y + math.sin(a) * 24 * size)], 3)
    pygame.draw.circle(s, body, (int(x), int(y)), int(13 * size))
    pygame.draw.circle(s, edge, (int(x), int(y)), int(13 * size), 2)
    if kind == 'listener':
        for sd in (-1, 1):
            pygame.draw.circle(s, edge, (int(x + sd * 10 * size), int(y - 11 * size)), 5, 2)


def draw_scorpion(s, x, y, anim, face, size):
    """Depredador: escorpión cavernario con pinzas y cola con aguijón (mira hacia `face`)."""
    k = size * .9
    ca, sa = math.cos(face), math.sin(face)

    def P(px, py):
        return (x + (px * ca - py * sa) * k, y + (px * sa + py * ca) * k)

    leg, body, edge = (90, 52, 24), (128, 70, 34), (235, 150, 60)
    for sd in (-1, 1):
        for i, lx in enumerate((-8, -2, 5, 11)):
            w = math.sin(anim * 7 + i * 1.7 + sd) * 4
            pygame.draw.lines(s, leg, False, [P(lx, sd * 6), P(lx + w * .5, sd * 16), P(lx + 5 + w, sd * 22)], max(2, int(k * 1.6)))
    tail = [P(-14, 0)]
    for i in range(1, 6):                                   # cola arqueada que se balancea
        a = anim * 2.5 + i * .5
        tail.append(P(-14 - i * 5.5, math.sin(a) * 4 - i * i * .6 * math.sin(anim)))
    pygame.draw.lines(s, edge, False, tail, max(2, int(k * 2)))
    pygame.draw.circle(s, (230, 60, 50), tail[-1], max(3, int(k * 2.4)))
    pygame.draw.polygon(s, body, [P(-14, 0), P(-6, -9), P(8, -8), P(15, 0), P(8, 8), P(-6, 9)])
    pygame.draw.polygon(s, edge, [P(-14, 0), P(-6, -9), P(8, -8), P(15, 0), P(8, 8), P(-6, 9)], 2)
    for sd in (-1, 1):                                      # pinzas
        arm = [P(10, sd * 6), P(22, sd * 11)]
        pygame.draw.lines(s, edge, False, arm, max(2, int(k * 2)))
        claw = [P(22, sd * 11), P(32, sd * 7), P(29, sd * 15)]
        pygame.draw.polygon(s, body, claw)
        pygame.draw.polygon(s, edge, claw, 2)


def draw_enemy(s, x, y, e):
    if e.kind == 'predator':
        draw_scorpion(s, x, y, e.anim, e.face, e.spec['size'])
    else:
        draw_spider(s, x, y, e.anim, e.kind, e.spec['size'])
        if e.kind == 'behemoth':                            # espinas dorsales
            for k in range(7):
                a = TAU * k / 7 + .3
                pygame.draw.polygon(s, (190, 30, 60), [(x + math.cos(a - .18) * 38, y + math.sin(a - .18) * 38),
                                                       (x + math.cos(a + .18) * 38, y + math.sin(a + .18) * 38),
                                                       (x + math.cos(a) * 52, y + math.sin(a) * 52)])
            pygame.draw.circle(s, (44, 8, 18), (int(x), int(y)), 36)
            pygame.draw.circle(s, (190, 30, 60), (int(x), int(y)), 36, 3)


def arrow(s, cx, cy, ang, col, sz=11):
    pts = [(cx + math.cos(ang) * sz * 1.4, cy + math.sin(ang) * sz * 1.4),
           (cx + math.cos(ang + 2.5) * sz, cy + math.sin(ang + 2.5) * sz),
           (cx + math.cos(ang - 2.5) * sz, cy + math.sin(ang - 2.5) * sz)]
    pygame.draw.polygon(s, col, pts)
    pygame.draw.polygon(s, (0, 0, 0), pts, 1)


# ---------------------------------------------------------------- menú
class Menu:
    def __init__(self, items, cx, y0, gap=64, w=380, h=50):
        self.items, self.sel, self.t = items, 0, 0.0
        self.rects = [pygame.Rect(cx - w // 2, y0 + i * gap, w, h) for i in range(len(items))]

    def handle(self, ev, sounds):
        """Devuelve el índice elegido o None."""
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % len(self.items)
                sounds.play('menu_move')
            elif ev.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % len(self.items)
                sounds.play('menu_move')
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                sounds.play('menu_select')
                return self.sel
        elif ev.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self.rects):
                if r.collidepoint(ev.pos) and i != self.sel:
                    self.sel = i
                    sounds.play('menu_move')
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i, r in enumerate(self.rects):
                if r.collidepoint(ev.pos):
                    self.sel = i
                    sounds.play('menu_select')
                    return i
        return None

    def draw(self, s, dt):
        self.t += dt
        for i, (label, r) in enumerate(zip(self.items, self.rects)):
            on = i == self.sel
            box = pygame.Surface(r.size, pygame.SRCALPHA)
            pulse = .5 + .5 * math.sin(self.t * 5)
            if on:
                pygame.draw.rect(box, (110, 70, 190, 150 + int(40 * pulse)), box.get_rect(), border_radius=14)
                pygame.draw.rect(box, (200, 160, 255, 255), box.get_rect(), 2, border_radius=14)
            else:
                pygame.draw.rect(box, (20, 14, 34, 150), box.get_rect(), border_radius=14)
                pygame.draw.rect(box, (80, 64, 110, 200), box.get_rect(), 1, border_radius=14)
            s.blit(box, r)
            text(s, F_M, label, r.centerx, r.centery, (255, 255, 255) if on else (170, 155, 195), True)
            if on:
                draw_bat(s, r.left + 34, r.centery + 2, self.t * 9, .4)
                draw_bat(s, r.right - 34, r.centery + 2, self.t * 9 + 1, .4)


# ---------------------------------------------------------------- fondo animado (título / instrucciones)
class Backdrop:
    """Cueva en capas con parallax, murciélagos, ojos que parpadean y ondas de sonar."""

    def __init__(self):
        self.t = 0.0
        self.base = pygame.Surface((W, H))
        for y in range(H):
            f = y / H
            pygame.draw.line(self.base, (int(8 + 14 * f), int(6 + 8 * f), int(18 + 14 * f)), (0, y), (W, y))
        glow = pygame.Surface((W, H), pygame.SRCALPHA)
        for r in range(380, 0, -8):
            pygame.draw.circle(glow, (90, 50, 160, int(48 * (1 - r / 380) ** 1.6)), (W // 2, 190), r)
        self.base.blit(glow, (0, 0))
        self.layers = [(self._layer(n, sz, col), spd) for n, sz, col, spd in
                       ((9, (60, 150), (14, 10, 24), 8), (11, (80, 190), (10, 7, 18), 20), (8, (110, 250), (5, 4, 10), 44))]
        self.bats = [[random.uniform(-100, W), random.uniform(60, 330), random.uniform(60, 130) * random.choice((1, -1)),
                      random.uniform(.5, 1.1), random.uniform(0, 6)] for _ in range(4)]
        self.eyes = [[random.randint(40, W - 40), random.randint(H - 210, H - 60), random.uniform(0, 6)] for _ in range(5)]
        self.dust = [[random.uniform(0, W), random.uniform(0, H), random.uniform(6, 22), random.uniform(.4, 1.4)] for _ in range(60)]
        self.fx = pygame.Surface((W, H), pygame.SRCALPHA)

    @staticmethod
    def _layer(n, size, col):
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        for _ in range(n):
            x, hh, bw = random.randint(0, W), random.randint(*size), random.randint(30, 80)
            for ox in (0, -W):
                pygame.draw.polygon(s, col, [(x + ox - bw // 2, -2), (x + ox + bw // 2, -2), (x + ox, hh)])
            x, hh, bw = random.randint(0, W), random.randint(size[0] // 2, int(size[1] * .8)), random.randint(30, 80)
            for ox in (0, -W):
                pygame.draw.polygon(s, col, [(x + ox - bw // 2, H + 2), (x + ox + bw // 2, H + 2), (x + ox, H - hh)])
        return s

    def update(self, dt):
        self.t += dt
        for b in self.bats:
            b[0] += b[2] * dt
            if b[0] > W + 120 or b[0] < -120:
                b[0] = -100 if b[2] > 0 else W + 100
                b[1] = random.uniform(60, 330)
        for d in self.dust:
            d[1] -= d[2] * dt
            d[0] += math.sin(self.t + d[3]) * 6 * dt
            if d[1] < 0:
                d[1], d[0] = H, random.uniform(0, W)

    def draw(self, s, sonar_at=(W // 2, 190)):
        s.blit(self.base, (0, 0))
        fx = self.fx
        fx.fill((0, 0, 0, 0))
        for k in range(3):                                    # ondas de sonar periódicas
            p = ((self.t + k * 1.1) % 3.3) / 3.3
            pygame.draw.circle(fx, (110, 150, 230, int(110 * (1 - p))), sonar_at, int(40 + 700 * p), 2)
        s.blit(fx, (0, 0))
        for lay, spd in self.layers[:2]:
            ox = int((self.t * spd) % W)
            s.blit(lay, (-ox, 0))
            s.blit(lay, (W - ox, 0))
        for b in self.bats:
            wob = math.sin(self.t * .8 + b[4]) * 25
            draw_bat(s, b[0], b[1] + wob, self.t * 10 + b[4], b[3] * (1 if b[2] > 0 else 1), (28, 20, 44), (36, 28, 56), (70, 55, 105))
        for e in self.eyes:
            ph = (self.t + e[2]) % 7
            if ph < 3.2:
                a = int(255 * min(1, ph, 3.2 - ph))
                for sd in (-6, 6):
                    pygame.draw.circle(s, (min(255, a), int(a * .15), int(a * .12)), (int(e[0] + sd), int(e[1])), 3)
        lay, spd = self.layers[2]
        ox = int((self.t * spd) % W)
        s.blit(lay, (-ox, 0))
        s.blit(lay, (W - ox, 0))
        for d in self.dust:
            c = int(60 + 40 * math.sin(self.t * 2 + d[3] * 5))
            s.fill((c, c - 10, c + 20), (int(d[0]), int(d[1]), 2, 2))


# ---------------------------------------------------------------- HUD
def bar(s, x, y, w, frac, col, label):
    text(s, F_XS, label, x, y - 1)
    x += 72
    pygame.draw.rect(s, (30, 28, 36), (x, y, w, 12), border_radius=3)
    pygame.draw.rect(s, col, (x, y, max(0, w * min(1, frac)), 12), border_radius=3)
    pygame.draw.rect(s, (90, 85, 105), (x, y, w, 12), 1, border_radius=3)


def draw_hud(s, g):
    b = g.bat
    for i in range(5):
        heart(s, 28 + i * 30, 24, (220, 50, 80) if i < b.hp else (60, 30, 40))
    bar(s, 14, 48, 100, 1 - g.cd / SCREECH_CD, (120, 210, 255), 'GRITO')
    ready = 1 - b.sonar_cd / g.diff.sonar_cd
    bar(s, 14, 68, 100, ready, (110, 160, 255) if ready >= 1 else (70, 90, 150), 'SONAR')
    if b.shield_t > 0:                                     # barra = tiempo de escudo que queda
        bar(s, 14, 88, 100, b.shield_t / SHIELD_T, (170, 235, 255), 'ESCUDO')
    else:
        rdy = 1 - b.shield_cd / SHIELD_CD
        bar(s, 14, 88, 100, rdy, (90, 200, 160) if rdy >= 1 else (60, 110, 100), 'ESCUDO')
    tx = f'Crías: {g.rescued}/{GOAL}'
    text(s, F_M, tx, W - 20 - F_M.size(tx)[0], 12)
    danger = f'Peligro: {g.diff.level}'
    flash = g.danger_flash > 0 and int(g.t * 10) % 2
    text(s, F_S, danger, W - 20 - F_S.size(danger)[0], 48, (255, 230, 120) if flash else (255, 150, 120))
    if b.exposed > 0:                                      # contrapartida del sonar
        if int(g.t * 4) % 2 or b.exposed < 1:
            text(s, F_M, '¡EXPUESTO!', W // 2, 44, (255, 80, 80), True)
        pygame.draw.rect(s, (255, 60, 60), (W // 2 - 80, 66, 160 * b.exposed / SONAR_EXPOSE_T, 4))
    if g.t < 10:
        text(s, F_S, 'Sigue los chillidos rosados · Q sonar · E escudo · Espacio grito · B brillo', (W - 220) // 2, H - 24, (200, 190, 215), True)
    draw_minimap(s, g)
    draw_guides(s, g)


def draw_minimap(s, g):
    cave, b = g.cave, g.bat
    mw, mh = MAP_W * 2, MAP_H * 2
    x0, y0 = W - mw - 14, H - mh - 14
    panel = pygame.Surface((mw + 8, mh + 8), pygame.SRCALPHA)
    panel.fill((0, 0, 8, 190))
    s.blit(panel, (x0 - 4, y0 - 4))
    s.blit(cave.minimap, (x0, y0))
    pygame.draw.rect(s, (110, 95, 140), (x0 - 4, y0 - 4, mw + 8, mh + 8), 1)
    k = 2 / TILE
    pygame.draw.circle(s, (170, 120, 70), (int(x0 + NEST[0] * k), int(y0 + NEST[1] * k)), 4)
    r = b.sonar_radius
    if r is not None and b.sonar_strength > 0:             # el sonar descubre crías y enemigos en el minimapa
        ox, oy = b.sonar_origin
        for p in g.pups:
            if math.dist((p.x, p.y), (ox, oy)) < r and p is not b.carry:
                pygame.draw.circle(s, C_PUP, (int(x0 + p.x * k), int(y0 + p.y * k)), 3)
        for e in g.enemies:
            if math.dist((e.x, e.y), (ox, oy)) < r:
                pygame.draw.circle(s, (255, 60, 60), (int(x0 + e.x * k), int(y0 + e.y * k)), 4 if e.kind in ('predator', 'behemoth') else 2)
    pygame.draw.circle(s, (255, 235, 120), (int(x0 + b.x * k), int(y0 + b.y * k)), 3)


def draw_guides(s, g):
    """Flechas en el borde: hacia las crías que acaban de chillar y hacia el nido si llevas una."""
    b, cam = g.bat, g.camera
    targets = [(p.x, p.y, C_PUP) for p in g.pups if p.ping > 0 and p is not b.carry]
    if b.carry:
        targets.append((NEST[0], NEST[1], C_GREEN))
    for x, y, col in targets:
        sx, sy = cam.apply(x, y)
        if 0 <= sx <= W and 0 <= sy <= H:
            continue
        cx, cy = W / 2, H / 2
        ang = math.atan2(sy - cy, sx - cx)
        k = min((W / 2 - 34) / abs(math.cos(ang) or 1e-6), (H / 2 - 34) / abs(math.sin(ang) or 1e-6))
        arrow(s, cx + math.cos(ang) * k, cy + math.sin(ang) * k, ang, col)
