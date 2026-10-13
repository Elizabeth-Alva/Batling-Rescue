"""Interfaz: fuentes, dibujo de personajes, menú, fondo animado, HUD y minimapa."""
import math
import os
import random

import pygame

from settings import (IS_WEB, W, H, TAU, GOAL, SHIELD_T, SHIELD_CD, TILE, NEST, DASH_CD, C_TEXT, C_PURPLE,
                      C_PUP, C_GOLD, MAP_W, MAP_H)

F_S = F_M = F_L = F_XL = F_XS = None
KEY = (255, 0, 255)


def _font(size):
    """Arial en escritorio; en el navegador (o con BATLING_DEFAULT_FONT=1) la fuente incluida en pygame."""
    if not (IS_WEB or os.environ.get("BATLING_DEFAULT_FONT")):
        return pygame.font.SysFont("arial", size, bold=True)
    return pygame.font.Font(None, round(size * 1.3))


def init_fonts():
    global F_S, F_M, F_L, F_XL, F_XS
    F_XS, F_S, F_M, F_L, F_XL = (_font(s) for s in (15, 18, 28, 54, 92))


# ---------------------------------------------------------------- dibujo básico
_TEXT_CACHE = {}


def render_text(f, t, col):
    """Texto ya renderizado (se reutiliza: en el navegador renderizar fuentes cada frame es caro)."""
    key = (id(f), t, col)
    im = _TEXT_CACHE.get(key)
    if im is None:
        if len(_TEXT_CACHE) > 400:
            _TEXT_CACHE.clear()
        im = _TEXT_CACHE[key] = f.render(t, True, col)
    return im


def text(s, f, t, x, y, col=C_TEXT, center=False):
    im = render_text(f, t, col)
    s.blit(im, im.get_rect(center=(x, y)) if center else (x, y))


def make_glow(f, t, col, blur=5, pad=26):
    """Superficie con el texto desenfocado (para sumar detrás del texto nítido)."""
    g = f.render(t, True, col)
    big = pygame.Surface((g.get_width() + 2 * pad, g.get_height() + 2 * pad), pygame.SRCALPHA)
    big.blit(g, (pad, pad))
    sm = pygame.transform.smoothscale(big, (max(1, big.get_width() // blur), max(1, big.get_height() // blur)))
    return pygame.transform.smoothscale(sm, big.get_size())


def star(s, x, y, r, col):
    """Estrellita de cinco puntas (mareo)."""
    pts = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * .45
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    pygame.draw.polygon(s, col, pts)


def half_heart(s, x, y, col):
    """Mitad izquierda de un corazón."""
    tmp = pygame.Surface((24, 20), pygame.SRCALPHA)
    heart(tmp, 12, 5, col)
    s.blit(tmp, (x - 12, y - 5), (0, 0, 12, 20))


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


PUP_FUR = ((120, 70, 100), (150, 95, 125), (190, 120, 160))
# cada cría se reconoce de un vistazo: color de pelaje, ojos y un detalle propio
PUP_LOOKS = {
    'Chispa':   dict(fur=PUP_FUR, eyes='big', tuft=(255, 170, 80)),                                # mechón naranja
    'Bruno':    dict(fur=((106, 76, 78), (138, 102, 98), (178, 140, 128)), eyes='closed', zzz=True, chubby=True),
    'Lía':      dict(fur=((140, 72, 110), (178, 100, 142), (222, 140, 182)), eyes='big', tears=True, bow=(255, 120, 170)),
    'Nube':     dict(fur=((150, 140, 176), (186, 176, 206), (228, 218, 242)), eyes='big', tremble=True, fluff=True),
    'Tito':     dict(fur=PUP_FUR, eyes='big', tears=True, bent_ear=True),
    'Eco':      dict(fur=((88, 80, 132), (120, 110, 168), (160, 150, 212)), eyes='normal', echo=True),
    'Mora':     dict(fur=((96, 50, 90), (126, 70, 116), (172, 100, 162)), eyes='sleepy', zzz=True),
    'Pipo':     dict(fur=PUP_FUR, eyes='big', spot=True),                                           # manchita blanca
    'Bolillo':  dict(fur=((150, 110, 70), (186, 146, 100), (226, 186, 132)), eyes='big', tuft=(250, 220, 160)),
    'Pozolito': dict(fur=((138, 60, 62), (174, 86, 82), (216, 122, 112)), eyes='big', tuft=(255, 120, 90)),
}


def _pup_body(s, x, y, flap, sc, lk, t, cry):
    col, body, edge = lk.get('fur', PUP_FUR)
    if lk.get('tremble'):
        x += math.sin(t * 60) * .8
    if lk.get('fluff'):                                                  # pelito esponjado alrededor
        for k in range(8):
            a = k * TAU / 8
            pygame.draw.circle(s, edge, (int(x + math.cos(a) * 7 * sc), int(y + 2 * sc + math.sin(a) * 10 * sc)), max(2, int(4 * sc)))
    draw_bat(s, x, y, flap, sc, col, body, edge)
    if lk.get('chubby'):                                                 # pancita redonda
        pygame.draw.ellipse(s, body, (x - 10 * sc, y - 6 * sc, 20 * sc, 20 * sc))
        pygame.draw.ellipse(s, edge, (x - 6 * sc, y, 12 * sc, 11 * sc))
    if lk.get('bent_ear'):                                               # orejita doblada hacia un lado
        pygame.draw.polygon(s, edge, [(x + 6 * sc, y - 16 * sc), (x + 9 * sc, y - 21 * sc), (x + 15 * sc, y - 15 * sc)])
    if lk.get('tuft'):                                                   # mechón entre las orejas
        tc = lk['tuft']
        for i, dx in enumerate((-2, 0, 2)):
            sway = math.sin(t * 6 + i) * 1.5 * sc
            pygame.draw.line(s, tc, (x + dx * sc, y - 11 * sc), (x + (dx * 2.5) * sc + sway, y - 19 * sc), max(1, int(2 * sc)))
    if lk.get('spot'):                                                   # manchita blanca en la frente
        pygame.draw.circle(s, (245, 240, 250), (int(x), int(y - 9 * sc)), max(1, int(2.6 * sc)))
    if lk.get('bow'):                                                    # moñito
        bc = lk['bow']
        bx, by = x - 6 * sc, y - 12 * sc
        pygame.draw.polygon(s, bc, [(bx, by), (bx - 4 * sc, by - 3 * sc), (bx - 4 * sc, by + 3 * sc)])
        pygame.draw.polygon(s, bc, [(bx, by), (bx + 4 * sc, by - 3 * sc), (bx + 4 * sc, by + 3 * sc)])
        pygame.draw.circle(s, (255, 230, 240), (int(bx), int(by)), 1)
    eyes = lk.get('eyes', 'normal')
    blink = (t * 1.7 + x * .01) % 4 < .12
    for sd in (-1, 1):
        ex, ey = x + sd * 3.5 * sc, y - 6 * sc
        if eyes == 'closed' or blink or (eyes == 'sleepy' and (t % 5) < 2.5):    # dormida: rayita curva
            pygame.draw.circle(s, body, (int(ex), int(ey)), max(2, int(2.6 * sc)))
            pygame.draw.line(s, (40, 26, 40), (ex - 2, ey), (ex + 1.5, ey + .5), 1)
        elif eyes == 'big':                                              # ojos grandes y brillantes
            pygame.draw.circle(s, (255, 230, 120), (int(ex), int(ey)), max(2, int(3.2 * sc)))
            pygame.draw.circle(s, (40, 24, 30), (int(ex), int(ey) + 1), 1)
            s.fill((255, 255, 255), (int(ex) - 1, int(ey) - 1, 1, 1))
    if cry and lk.get('tears'):                                          # lagrimitas cuando chilla
        for sd in (-1, 1):
            q = (t * 2.5 + (sd + 1) * .3) % 1
            pygame.draw.circle(s, (150, 210, 255), (int(x + sd * 5 * sc + sd * q * 3), int(y - 4 * sc + q * 10)), 1)


def pup_extras(s, x, y, lk, t, cry=False):
    """Detalles que flotan alrededor de la cría (se dibujan sobre la oscuridad): zzz, ondas de eco."""
    if lk.get('zzz'):
        for i in range(2):
            q = (t * .5 + i * .5) % 1
            a = int(200 * math.sin(math.pi * q))
            zx, zy = x + 14 + q * 8, y - 8 - q * 12
            sz = 3 + q * 3
            col = (a, a, int(a * 1.1) if a * 1.1 < 255 else 255)
            pygame.draw.lines(s, col, False, [(zx - sz, zy - sz), (zx + sz, zy - sz), (zx - sz, zy + sz), (zx + sz, zy + sz)], 1)
    if lk.get('echo'):                                                   # Eco repite: ondas suaves
        q = (t * .8) % 1
        a = int(170 * (1 - q))
        for sd in (-1, 1):
            r = 8 + q * 12
            pygame.draw.arc(s, (int(a * .7), int(a * .7), a), (x - r, y - 8 - r, 2 * r, 2 * r),
                            (-.5 if sd > 0 else math.pi - .5), (.5 if sd > 0 else math.pi + .5), 1)


def draw_pup(s, x, y, flap, lean=0.0, sc=.55, name=None, t=0.0, cry=False):
    """Cría: flap es la fase del aleteo; lean la inclina al dar pasitos; name le da su aspecto propio."""
    lk = PUP_LOOKS.get(name, {})
    if abs(lean) < .03:
        return _pup_body(s, x, y, flap, sc, lk, t, cry)
    tmp = pygame.Surface((70, 56), pygame.SRCALPHA)
    _pup_body(tmp, 35, 28, flap, sc, lk, t, cry)
    rot = pygame.transform.rotate(tmp, -math.degrees(lean))
    s.blit(rot, rot.get_rect(center=(int(x), int(y))))


SPIDER_LOOK = ((8, 6, 10), (24, 18, 26), (70, 48, 70))      # patas, cuerpo, borde


def draw_spider(s, x, y, anim, size=1.0, face=0.0):
    legs, body, edge = SPIDER_LOOK
    for k in range(8):
        a = TAU * k / 8 + .2 + math.sin(anim * 8 + k) * .25
        pygame.draw.lines(s, legs, False, [(x, y), (x + math.cos(a) * 14 * size, y + math.sin(a) * 14 * size - 4),
                                           (x + math.cos(a) * 24 * size, y + math.sin(a) * 24 * size)], 3)
    ax, ay = x - math.cos(face) * 7 * size, y - math.sin(face) * 7 * size        # abdomen
    pygame.draw.circle(s, body, (int(ax), int(ay)), int(12 * size))
    pygame.draw.circle(s, edge, (int(ax), int(ay)), int(12 * size), 2)
    pygame.draw.line(s, (120, 60, 90), (ax - 4 * size, ay), (ax + 4 * size, ay), 2)      # marca en el lomo
    hx, hy = x + math.cos(face) * 6 * size, y + math.sin(face) * 6 * size
    pygame.draw.circle(s, body, (int(hx), int(hy)), int(7 * size))
    pygame.draw.circle(s, edge, (int(hx), int(hy)), int(7 * size), 1)


def draw_beetle(s, x, y, anim, face, size=1.1):
    """Escarabajo acorazado visto desde arriba (élitros con brillo metálico)."""
    k = size
    ca, sa = math.cos(face), math.sin(face)

    def P(px, py):
        return (x + (px * ca - py * sa) * k, y + (px * sa + py * ca) * k)

    leg = (20, 18, 30)
    for sd in (-1, 1):
        for i, lx in enumerate((-6, 1, 8)):
            w = math.sin(anim * 9 + i * 2 + sd) * 3
            pygame.draw.lines(s, leg, False, [P(lx, sd * 8), P(lx + w, sd * 15), P(lx + 4 + w, sd * 20)], 3)
    pygame.draw.lines(s, leg, False, [P(15, -3), P(22, -8), P(26, -6)], 2)        # antenas
    pygame.draw.lines(s, leg, False, [P(15, 3), P(22, 8), P(26, 6)], 2)
    shell = [P(-15, 0), P(-11, -10), P(2, -12), P(11, -8), P(13, 0), P(11, 8), P(2, 12), P(-11, 10)]
    pygame.draw.polygon(s, (26, 44, 60), shell)
    pygame.draw.polygon(s, (90, 150, 170), shell, 2)
    pygame.draw.line(s, (10, 18, 26), P(-15, 0), P(9, 0), 2)                         # separación de los élitros
    pygame.draw.line(s, (150, 210, 220), P(-6, -6), P(4, -8), 2)                       # brillo
    head = [P(11, -6), P(17, -4), P(18, 4), P(11, 6)]
    pygame.draw.polygon(s, (18, 26, 36), head)


def draw_centipede(s, e, cam, boss=False):
    """Cazador (ciempiés) o el Gran Ciempiés: cuerpo segmentado que sigue a la cabeza."""
    segs = e.segs
    seg_col = (70, 26, 18) if not boss else (54, 18, 22)
    edge = (200, 90, 50) if not boss else (220, 70, 60)
    sleeping = boss and e.state == 'sleep'
    for i in range(len(segs) - 1, -1, -1):
        sx, sy = cam.apply(*segs[i])
        if i + 1 < len(segs):
            nx, ny = cam.apply(*segs[i + 1])
        else:
            nx, ny = cam.apply(*segs[i - 1]) if i else (sx - 1, sy)
            nx, ny = 2 * sx - nx, 2 * sy - ny
        ang = math.atan2(sy - ny, sx - nx)
        r = (6 if not boss else 15) * (1 - .35 * i / max(1, len(segs)))
        for sd in (-1, 1):                                                   # patas
            w = math.sin(e.anim * (16 if not boss else 6) + i * 1.3 + sd) * .5
            la = ang + sd * (math.pi / 2 + w * .6)
            L = r * 2.0
            pygame.draw.line(s, (30, 14, 10), (sx, sy), (sx + math.cos(la) * L, sy + math.sin(la) * L), 2 if not boss else 4)
        pygame.draw.circle(s, seg_col, (int(sx), int(sy)), int(r))
        pygame.draw.circle(s, edge, (int(sx), int(sy)), int(r), 2 if not boss else 3)
        if boss and i % 2 == 0:
            pygame.draw.circle(s, (120, 40, 40), (int(sx), int(sy)), int(r * .45))
    hx, hy = cam.apply(e.x, e.y)
    a = e.face
    hr = 8 if not boss else 22
    pygame.draw.circle(s, (40, 12, 10), (int(hx), int(hy)), hr)
    pygame.draw.circle(s, edge, (int(hx), int(hy)), hr, 2)
    for sd in (-1, 1):                                                      # pinzas / antenas
        b = a + sd * .5
        pygame.draw.lines(s, edge, False, [(hx + math.cos(a) * hr * .7, hy + math.sin(a) * hr * .7),
                                           (hx + math.cos(b) * hr * 1.7, hy + math.sin(b) * hr * 1.7),
                                           (hx + math.cos(a + sd * .1) * hr * 2.0, hy + math.sin(a + sd * .1) * hr * 2.0)],
                          2 if not boss else 4)
    if boss:
        if sleeping:                                                        # ojos cerrados y "Z"
            for sd in (-1, 1):
                ex, ey = hx + math.cos(a + sd * .6) * hr * .6, hy + math.sin(a + sd * .6) * hr * .6
                pygame.draw.line(s, (200, 120, 90), (ex - 4, ey), (ex + 4, ey), 2)
            ph = (e.anim * 2) % 3
            text(s, F_S, 'z', hx + 26 + ph * 6, hy - 30 - ph * 10, (200, 180, 160))
            text(s, F_XS, 'z', hx + 40 + ph * 5, hy - 46 - ph * 8, (160, 140, 130))


_BOSS_GLOW = {}


def _boss_glow(r):
    g = _BOSS_GLOW.get(r)
    if g is None:
        g = _BOSS_GLOW[r] = pygame.Surface((2 * r, 2 * r))
        for i in range(r, 0, -2):
            k = (1 - i / r) ** 1.6
            pygame.draw.circle(g, (int(200 * k), int(26 * k), int(14 * k)), (r, r), i)
    return g


def draw_boss(s, e, cam):
    """El Gran Ciempiés de la Mina: coraza negra con vetas rojas, púas, patas afiladas y mandíbulas enormes."""
    segs, t = e.segs, e.anim
    awake = e.state != 'sleep'
    waking = getattr(e, 'waking', 0) > 0
    jx = (random.uniform(-3, 3) if waking else 0)
    pulse = .5 + .5 * math.sin(t * (7 if awake else 1.5))
    breathe = 1 + (.04 * math.sin(t * 2) if not awake else 0)
    n = len(segs)
    pts = [cam.apply(*p) for p in segs]
    pts = [(x + jx, y) for x, y in pts]
    if awake:                                                                 # aura roja al despertar
        gl = _boss_glow(150)
        hx, hy = pts[0]
        s.blit(gl, (hx - 150, hy - 150), special_flags=pygame.BLEND_RGB_ADD)
    for i in range(n - 1, -1, -1):
        sx, sy = pts[i]
        ox, oy = pts[i + 1] if i + 1 < n else (2 * sx - pts[i - 1][0], 2 * sy - pts[i - 1][1])
        ang = math.atan2(sy - oy, sx - ox)
        ca, sa = math.cos(ang), math.sin(ang)
        r = 19 * (1 - .4 * i / n) * breathe
        pygame.draw.ellipse(s, (6, 3, 3), (sx - r + 6, sy - r * .8 + 9, 2 * r, 1.6 * r))      # sombra
        for sd in (-1, 1):                                                   # patas articuladas y afiladas
            w = math.sin(t * (9 if awake else 1.2) + i * 1.1 + sd) * .45
            la = ang + sd * (math.pi / 2 + w * .5)
            kx, ky = sx + math.cos(la) * r * 1.6, sy + math.sin(la) * r * 1.6
            fa = la - sd * .7
            tx, ty = kx + math.cos(fa) * r * 1.3, ky + math.sin(fa) * r * 1.3
            pygame.draw.line(s, (52, 14, 12), (sx, sy), (kx, ky), 5)
            pygame.draw.line(s, (90, 22, 18), (kx, ky), (tx, ty), 3)
            pygame.draw.circle(s, (230, 80, 50), (int(tx), int(ty)), 2)
        def P(px, py):
            return (sx + px * ca - py * sa, sy + px * sa + py * ca)
        plate = [P(-r * .8, 0), P(-r * .45, -r * 1.05), P(r * .55, -r * 1.1), P(r * .9, 0), P(r * .55, r * 1.1), P(-r * .45, r * 1.05)]
        for sd in (-1, 1):                                                   # púas laterales
            pygame.draw.polygon(s, (36, 8, 10), [P(-r * .2, sd * r * .9), P(r * .3, sd * r * .95), P(-r * .7, sd * r * 1.75)])
            pygame.draw.polygon(s, (170, 40, 30), [P(-r * .2, sd * r * .9), P(r * .3, sd * r * .95), P(-r * .7, sd * r * 1.75)], 1)
        pygame.draw.polygon(s, (24, 6, 8), plate)
        seam = (int(120 + 135 * pulse), int(20 + 30 * pulse), 18) if awake else (90, 20, 16)
        pygame.draw.polygon(s, seam, plate, 2)
        pygame.draw.line(s, seam, P(-r * .3, -r * .7), P(-r * .3, r * .7), 2)                  # veta brillante
        pygame.draw.line(s, (70, 30, 30), P(r * .1, -r * .8), P(r * .45, -r * .2), 2)           # brillo de la coraza
    hx, hy = pts[0]
    a = e.face
    ca, sa = math.cos(a), math.sin(a)

    def H(px, py):
        return (hx + px * ca - py * sa, hy + px * sa + py * ca)

    hr = 27
    open_ = .35 + .35 * math.sin(t * (10 if awake else 1.0))                  # mandíbulas que se abren y cierran
    for sd in (-1, 1):
        base = H(hr * .6, sd * hr * .5)
        mid = H(hr * 1.5, sd * hr * (.9 + open_))
        tip = H(hr * 2.2, sd * hr * (.15 + open_ * .5))
        pygame.draw.lines(s, (40, 8, 8), False, [base, mid, tip], 9)
        pygame.draw.lines(s, (210, 70, 40), False, [base, mid, tip], 3)
        pygame.draw.circle(s, (255, 200, 140), (int(tip[0]), int(tip[1])), 3)
        ant = [H(hr * .7, sd * hr * .3), H(hr * 1.8, sd * hr * (1.4 + .3 * math.sin(t * 3 + sd))),
               H(hr * 2.6, sd * hr * (2.2 + .5 * math.sin(t * 2 + sd)))]
        pygame.draw.lines(s, (120, 36, 26), False, ant, 2)
    head = [H(-hr * .7, 0), H(-hr * .3, -hr), H(hr * .7, -hr * .85), H(hr * 1.05, 0), H(hr * .7, hr * .85), H(-hr * .3, hr)]
    pygame.draw.polygon(s, (20, 4, 6), head)
    pygame.draw.polygon(s, (230, 60, 40) if awake else (120, 30, 24), head, 3)
    for sd in (-1, 1):                                                        # cuatro ojos
        for k, (ex, ey, er) in enumerate(((hr * .45, hr * .42, 6), (hr * .15, hr * .62, 3))):
            px, py = H(ex, sd * ey)
            if awake:
                pygame.draw.circle(s, (255, 40 + int(60 * pulse), 20), (int(px), int(py)), er)
                pygame.draw.circle(s, (255, 230, 160), (int(px), int(py)), max(1, er // 3))
            else:                                                             # dormido: rendijas rojas
                pygame.draw.line(s, (int(140 + 60 * pulse), 30, 20), (px - er, py), (px + er, py), 2)
    if not awake:
        ph = (t * 2) % 3
        text(s, F_S, 'z', hx + 30 + ph * 6, hy - 36 - ph * 10, (200, 160, 150))
        text(s, F_XS, 'z', hx + 46 + ph * 5, hy - 52 - ph * 8, (160, 120, 110))


def draw_enemy(s, x, y, e, cam=None):
    if e.kind == 'beetle':
        draw_beetle(s, x, y, e.anim, e.face, e.spec['size'])
    elif e.kind == 'boss':
        draw_boss(s, e, cam)
    elif e.kind == 'hunter':
        draw_centipede(s, e, cam)
    else:
        draw_spider(s, x, y, e.anim, e.spec['size'], e.face)


def arrow(s, cx, cy, ang, col, sz=11):
    pts = [(cx + math.cos(ang) * sz * 1.4, cy + math.sin(ang) * sz * 1.4),
           (cx + math.cos(ang + 2.5) * sz, cy + math.sin(ang + 2.5) * sz),
           (cx + math.cos(ang - 2.5) * sz, cy + math.sin(ang - 2.5) * sz)]
    pygame.draw.polygon(s, col, pts)
    pygame.draw.polygon(s, (0, 0, 0), pts, 1)


# ---------------------------------------------------------------- menú
class Menu:
    def __init__(self, items, cx, y0, gap=64, w=380, h=50, horizontal=False):
        self.items, self.sel, self.t = items, 0, 0.0
        self.horizontal = horizontal
        if horizontal:
            x0 = cx - (len(items) * w + (len(items) - 1) * (gap - w)) // 2
            self.rects = [pygame.Rect(x0 + i * gap, y0, w, h) for i in range(len(items))]
        else:
            self.rects = [pygame.Rect(cx - w // 2, y0 + i * gap, w, h) for i in range(len(items))]

    def handle(self, ev, sounds):
        """Devuelve el índice elegido o None."""
        if ev.type == pygame.KEYDOWN:
            if ev.key in ((pygame.K_LEFT, pygame.K_a) if self.horizontal else (pygame.K_UP, pygame.K_w)):
                self.sel = (self.sel - 1) % len(self.items)
                sounds.play('menu_move')
            elif ev.key in ((pygame.K_RIGHT, pygame.K_d) if self.horizontal else (pygame.K_DOWN, pygame.K_s)):
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
            text(s, F_S if self.horizontal else F_M, label, r.centerx, r.centery, (255, 255, 255) if on else (170, 155, 195), True)
            if on and not self.horizontal:
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
        self.ring_col = (110, 150, 230)
        self.bats = [[random.uniform(-100, W), random.uniform(60, 330), random.uniform(60, 130) * random.choice((1, -1)),
                      random.uniform(.5, 1.1), random.uniform(0, 6)] for _ in range(4)]
        self.eyes = [[random.randint(40, W - 40), random.randint(H - 210, H - 60), random.uniform(0, 6)] for _ in range(5)]
        self.dust = [[random.uniform(0, W), random.uniform(0, H), random.uniform(6, 22), random.uniform(.4, 1.4)] for _ in range(60)]

    @staticmethod
    def _layer(n, size, col):
        """Devuelve (franja_superior, franja_inferior, alto_sup, alto_inf): solo el área que ocupan las rocas.
        Cada franja mide el doble de ancho para poder desplazarla con un único blit sin tener que envolver."""
        top_h, bot_h = size[1] + 4, int(size[1] * .8) + 4
        top, bot = pygame.Surface((2 * W, top_h)), pygame.Surface((2 * W, bot_h))
        for srf in (top, bot):                          # colorkey: más barato que el alfa por píxel
            srf.fill(KEY)
            srf.set_colorkey(KEY)
        for _ in range(n):
            x, hh, bw = random.randint(0, W), random.randint(*size), random.randint(30, 80)
            for ox in (0, W):
                pygame.draw.polygon(top, col, [(x + ox - bw // 2, -2), (x + ox + bw // 2, -2), (x + ox, hh)])
            x, hh, bw = random.randint(0, W), random.randint(size[0] // 2, int(size[1] * .8)), random.randint(30, 80)
            for ox in (0, W):
                pygame.draw.polygon(bot, col, [(x + ox - bw // 2, bot_h + 2), (x + ox + bw // 2, bot_h + 2), (x + ox, bot_h - hh)])
        return top, bot, top_h, bot_h

    def _blit_layer(self, s, layer, spd):
        top, bot, th, bh = layer
        ox = int((self.t * spd) % W)
        s.blit(top, (0, 0), (ox, 0, W, th))
        s.blit(bot, (0, H - bh), (ox, 0, W, bh))

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
        for k in range(3):                                    # ondas de sonar periódicas (directas, sin capa alfa)
            p = ((self.t + k * 1.1) % 3.3) / 3.3
            pygame.draw.circle(s, tuple(int(c * .5 * (1 - p)) + 10 for c in self.ring_col), sonar_at, int(40 + 700 * p), 2)
        for lay, spd in self.layers[:2]:
            self._blit_layer(s, lay, spd)
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
        self._blit_layer(s, lay, spd)
        for d in self.dust:
            c = int(60 + 40 * math.sin(self.t * 2 + d[3] * 5))
            s.fill((c, c - 10, c + 20), (int(d[0]), int(d[1]), 2, 2))


# ---------------------------------------------------------------- HUD
_PANELS = {}


def panel(s, rect, alpha=170, border=(110, 95, 150)):
    """Panel translúcido con borde redondeado (se cachea por tamaño)."""
    key = (rect[2], rect[3], alpha, border)
    p = _PANELS.get(key)
    if p is None:
        p = _PANELS[key] = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
        pygame.draw.rect(p, (4, 3, 12, alpha), p.get_rect(), border_radius=10)
        pygame.draw.rect(p, (*border, 200), p.get_rect(), 1, border_radius=10)
    s.blit(p, rect[:2])


def bar(s, x, y, w, frac, col, label, ready_col=None):
    text(s, F_XS, label, x, y - 2, (220, 210, 235))
    x += 70
    pygame.draw.rect(s, (30, 28, 36), (x, y, w, 10), border_radius=3)
    full = frac >= 1
    pygame.draw.rect(s, (ready_col or col) if full else tuple(int(c * .6) for c in col),
                     (x, y, max(0, w * min(1, frac)), 10), border_radius=3)
    pygame.draw.rect(s, (90, 85, 105), (x, y, w, 10), 1, border_radius=3)


def pup_icon(s, x, y, state, t):
    """Carita de cría para el contador: 'safe' a salvo, 'carry' en brazos, 'lost' perdida."""
    x, y = int(x), int(y)
    if state == 'safe':
        body, edge, eye = (200, 120, 165), (255, 190, 225), (40, 20, 30)
    elif state == 'carry':
        body, edge, eye = (240, 180, 90), (255, 230, 160), (40, 20, 10)
        y += int(math.sin(t * 8) * 1.5)
    else:
        body, edge, eye = (30, 26, 42), (80, 70, 105), None
    for sd in (-1, 1):
        ear = [(x + sd * 2, y - 4), (x + sd * 7, y - 11), (x + sd * 7, y - 2)]
        pygame.draw.polygon(s, body, ear)
        pygame.draw.polygon(s, edge, ear, 1)
    pygame.draw.circle(s, body, (x, y), 6)
    pygame.draw.circle(s, edge, (x, y), 6, 1)
    if eye:
        for sd in (-1, 1):
            pygame.draw.circle(s, eye, (x + sd * 2, y - 1), 1)


def draw_hud(s, g):
    b, t = g.bat, g.t
    # --- izquierda: vidas y habilidades
    panel(s, (8, 8, 214, 108))
    for i in range(5):                                     # corazones (pueden ir de medio en medio)
        fill = max(0.0, min(1.0, b.hp - i))
        heart(s, 28 + i * 28, 26, (60, 30, 40))
        if fill >= 1:
            heart(s, 28 + i * 28, 26, (230, 60, 90))
        elif fill > 0:
            half_heart(s, 28 + i * 28, 26, (230, 60, 90))
    bar(s, 18, 50, 120, 1 - g.cd / g.cd_max, (120, 210, 255), 'GRITO', (170, 235, 255))
    bar(s, 18, 70, 120, 1 - b.dash_cd / DASH_CD, (255, 200, 120), 'IMPULSO')
    if b.shield_t > 0:
        bar(s, 18, 90, 120, b.shield_t / SHIELD_T, (170, 235, 255), 'ESCUDO')
    else:
        bar(s, 18, 90, 120, 1 - b.shield_cd / SHIELD_CD, (90, 200, 160), 'ESCUDO')
    # --- centro: reloj de la noche (medianoche -> amanecer)
    cfg = g.cfg
    frac = min(1, g.t / cfg['duration'])
    minutes = cfg['start_min'] + (cfg['end_min'] - cfg['start_min']) * frac
    cw = 236
    cx0 = W // 2 - cw // 2
    panel(s, (cx0, 8, cw, 56))
    night = g.night_strip
    s.blit(night, (cx0 + 12, 42))
    mx = cx0 + 12 + int(night.get_width() * minutes / 360)
    pygame.draw.line(s, (255, 255, 255), (mx, 38), (mx, 52), 2)
    end_x = cx0 + 12 + int(night.get_width() * cfg['end_min'] / 360)
    pygame.draw.line(s, (255, 120, 120), (end_x, 40), (end_x, 50), 1)
    left = max(0, cfg['duration'] - g.t)
    low = left < 30
    col = (255, 120, 110) if low and int(t * 4) % 2 else (240, 230, 255)
    from story import clock_text
    text(s, F_M, clock_text(minutes), cx0 + 12, 9, col)
    text(s, F_XS, f'{cfg["act"]} · faltan {int(left // 60)}:{int(left % 60):02d}', cx0 + cw - 12 - F_XS.size(f'{cfg["act"]} · faltan {int(left // 60)}:{int(left % 60):02d}')[0], 17, (190, 180, 215))
    # --- derecha: crías
    panel(s, (W - 222, 8, 214, 56))
    states = []
    for i in range(GOAL):
        states.append('safe' if i < g.rescued else 'lost')
    if b.carry:
        for k in range(b.carry.count):
            if g.rescued + k < GOAL:
                states[g.rescued + k] = 'carry'
    for i, st in enumerate(states):
        pup_icon(s, W - 204 + i * 20, 30, st, t + i)
    tx = f'Crías a salvo: {g.rescued}/{GOAL}'
    text(s, F_XS, tx, W - 214, 43, C_PUP if g.rescued else (200, 190, 215))
    draw_minimap(s, g)
    draw_guides(s, g)


def draw_minimap(s, g, big=False):
    cave, b = g.cave, g.bat
    sc = 6 if big else 2
    mw, mh = MAP_W * sc, MAP_H * sc
    if big:
        x0, y0 = (W - mw) // 2, (H - mh) // 2 + 10
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((0, 0, 8, 150))
        s.blit(veil, (0, 0))
        mm = pygame.transform.scale(cave.minimap, (mw, mh))
    else:
        x0, y0 = W - mw - 14, H - mh - 14
        mm = cave.minimap
    panel(s, (x0 - 6, y0 - 6, mw + 12, mh + 12), 200)
    s.blit(mm, (x0, y0))
    k = sc / TILE
    P = lambda x, y: (int(x0 + x * k), int(y0 + y * k))
    pygame.draw.circle(s, C_GOLD, P(*NEST), 6 if big else 4)
    pygame.draw.circle(s, (255, 255, 255), P(*NEST), 6 if big else 4, 1)
    t = g.t
    for p in g.pups:                                             # el grito revela a las crías
        if p.revealed > 0 and p is not b.carry:
            pulse = .5 + .5 * math.sin(t * 8)
            r = (6 if big else 3) + int(pulse * (3 if big else 2))
            pygame.draw.circle(s, C_PUP, P(p.x, p.y), r)
            pygame.draw.circle(s, (255, 255, 255), P(p.x, p.y), r + 2, 1)
            if big:
                text(s, F_XS, p.name, P(p.x, p.y)[0] + 10, P(p.x, p.y)[1] - 8, C_PUP)
    if g.reveal_t > 0:
        for e in g.enemies:
            if math.dist((e.x, e.y), g.echo_origin) < 700 or e.kind == 'boss':
                pygame.draw.circle(s, (255, 70, 70), P(e.x, e.y), (5 if e.kind == 'boss' else 2) * (2 if big else 1))
    for e in g.enemies:
        if e.kind == 'boss' and e.state in ('chase', 'return'):
            pygame.draw.circle(s, (255, 60, 60), P(e.x, e.y), 8 if big else 5)
    pygame.draw.circle(s, (255, 235, 120), P(b.x, b.y), 5 if big else 3)
    pygame.draw.circle(s, (0, 0, 0), P(b.x, b.y), 5 if big else 3, 1)
    if big:
        text(s, F_M, 'MAPA DE LA CUEVA', W // 2, y0 - 34, C_PURPLE, True)
        text(s, F_XS, 'Amarillo: Mullo  ·  Dorado: punto de entrega  ·  Rosa: crías marcadas por el grito  ·  M: cerrar',
             W // 2, y0 + mh + 22, (210, 200, 230), True)
    else:
        text(s, F_XS, 'M: mapa', x0, y0 - 22, (150, 140, 175))


def draw_guides(s, g):
    """Flechas en el borde: hacia las crías que acaban de chillar y hacia el punto de entrega si llevas una."""
    b, cam = g.bat, g.camera
    targets = [(p.x, p.y, C_PUP) for p in g.pups if (p.ping > 0 or p.revealed > 0) and p is not b.carry]
    if b.carry:
        targets.append((NEST[0], NEST[1], C_GOLD))
    for x, y, col in targets:
        sx, sy = cam.apply(x, y)
        if 0 <= sx <= W and 0 <= sy <= H:
            continue
        cx, cy = W / 2, H / 2
        ang = math.atan2(sy - cy, sx - cx)
        k = min((W / 2 - 34) / abs(math.cos(ang) or 1e-6), (H / 2 - 34) / abs(math.sin(ang) or 1e-6))
        arrow(s, cx + math.cos(ang) * k, cy + math.sin(ang) * k, ang, col)


def make_night_strip(w=212, h=8):
    """Barra del cielo de la noche: azul oscuro -> violeta -> naranja (amanecer)."""
    stops = [(0, (14, 22, 70)), (.4, (40, 30, 100)), (.72, (110, 56, 140)), (.9, (230, 110, 80)), (1, (255, 170, 80))]
    s = pygame.Surface((w, h))
    for x in range(w):
        f = x / (w - 1)
        for i in range(len(stops) - 1):
            if stops[i][0] <= f <= stops[i + 1][0]:
                a, b = stops[i], stops[i + 1]
                k = (f - a[0]) / (b[0] - a[0])
                s.fill(tuple(int(a[1][j] + (b[1][j] - a[1][j]) * k) for j in range(3)), (x, 0, 1, h))
                break
    pygame.draw.rect(s, (200, 190, 230), s.get_rect(), 1)
    return s
