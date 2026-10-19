"""Iluminación: penumbra con el color de cada escenario, luz propia, memoria de lo recorrido, balizas y ecolocación.

Todo el cálculo de luz se hace en un mapa de 1/2 de resolución (SW x SH) y se amplía una sola vez:
la luz es suave, así que no se nota, y evita varias mezclas de pantalla completa por frame
(muy caras en el navegador con WebAssembly).
"""
import math

import pygame

from settings import (W, H, TILE, NEST, SHIELD_R, BRIGHTNESS_LEVELS, SCREECH_R, ECHO_FLASH_T)

S = 2                                  # factor de reducción del mapa de luz
SW, SH = W // S, H // S
SUB = pygame.BLEND_RGBA_SUB
ADD = pygame.BLEND_RGB_ADD
K = (0, 0, 0)
# penumbra de cada escenario: (color, cambio de opacidad, color del brillo del punto de entrega)
# Cada nivel está más oscuro que el anterior (se baja más y más en la cueva); para compensar, la luz de Mullo
# se achica un poco y los objetos que brillan (cristales, hongos, algas) alumbran más y se ven de más lejos.
AMBIENT = {
    'fungi': ((4, 20, 22), -18, (255, 170, 90)),      # verde azulado: luz tenue y segura
    'lake': ((3, 5, 22), 36, (150, 170, 255)),         # índigo casi negro
    'mine': ((12, 7, 3), 56, (255, 160, 80)),          # marrón y ámbar oscuro, casi sin luz
}
BAT_SCALE = {'fungi': 1.0, 'lake': .9, 'mine': .82}      # radio de la luz propia de Mullo
OBJ_SCALE = {'fungi': 1.0, 'lake': 1.2, 'mine': 1.5}     # cuánto alumbran los objetos que brillan
FUNGUS_GLOW = {'fungi': (70, 230, 170), 'lake': (70, 210, 160), 'mine': (255, 170, 70)}   # en la mina: madera podrida que brilla


def radial(r, peak=255, exp=1.3, rgb=(255, 255, 255), step=2):
    """Disco de luz: opaco en el centro y cayendo suavemente hasta 0 en el borde.
    Para restar de la oscuridad se usa rgb=(0, 0, 0): BLEND_RGBA_SUB resta también el color,
    y así solo cambia la opacidad sin desteñir el tinte ambiente."""
    s = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
    for i in range(r, 0, -step):
        pygame.draw.circle(s, (*rgb, int(peak * (1 - i / r) ** exp)), (r, r), i)
    return s


def faded(surf, alpha):
    t = surf.copy()
    t.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    return t


def glow_rgb(r, col, peak=1.0, exp=1.0):
    """Brillo de color para sumar (BLEND_RGB_ADD): el color se apaga hacia el borde, sobre negro."""
    s = pygame.Surface((2 * r, 2 * r))
    for i in range(r, 0, -1):
        k = peak * (1 - i / r) ** exp
        pygame.draw.circle(s, tuple(min(255, int(c * k)) for c in col), (r, r), i)
    return s


def make_vignette():
    sm = pygame.Surface((48, 32), pygame.SRCALPHA)
    for y in range(32):
        for x in range(48):
            d = math.hypot((x - 23.5) / 24, (y - 15.5) / 16)
            sm.set_at((x, y), (0, 0, 0, int(max(0, min(1, (d - .6) / .6)) ** 1.4 * 150)))
    return pygame.transform.smoothscale(sm, (SW, SH))


def ring(c, x, y, r, col, a, width=2):
    """Anillo tenue directo sobre el lienzo (sin capa alfa de pantalla completa): color atenuado por a (0-1)."""
    if r < 1 or a <= 0:
        return
    pygame.draw.circle(c, tuple(min(255, int(ch * a)) for ch in col), (int(x), int(y)), int(r), width)


class Lighting:
    def __init__(self, crystals, fungi=(), theme='fungi', algae=()):
        self.crystals, self.fungi, self.algae = crystals, list(fungi), list(algae)
        self.amb_rgb, self.amb_off, nest_col = AMBIENT[theme]
        self.theme = theme
        self.small = pygame.Surface((SW, SH), pygame.SRCALPHA)
        self.up = pygame.Surface((W, H), pygame.SRCALPHA)
        # luces que se RESTAN de la oscuridad (solo opacidad)
        bs, o = BAT_SCALE[theme], OBJ_SCALE[theme]
        self.bat_lights = {lv[2]: radial(int(lv[2] * bs) // S, 255, .8, K, 1) for lv in BRIGHTNESS_LEVELS}
        self.L_NEST = radial(210 // S, 255, 1.0, K, 1)
        self.L_PUP = faded(radial(60 // S, 255, 1.0, K, 1), 150)
        self.L_CRY = faded(radial(int(70 * o) // S, 255, 1.0, K, 1), min(255, int(110 * o)))
        self.L_FUN = faded(radial(int(36 * o) // S, 255, 1.0, K, 1), min(255, int(110 * o)))
        # brillos de color que se SUMAN (balizas visibles de lejos)
        self.glow = {col: glow_rgb(int(70 * o) // S, col, 1.0) for col in {c[2] for c in crystals}}
        self.fun_glow = glow_rgb(int(36 * o) // S, FUNGUS_GLOW[theme], .9)
        self.L_ALG = faded(radial(int(26 * o) // S, 255, 1.0, K, 1), min(255, int(70 * o)))
        self.alg_glow = glow_rgb(int(26 * o) // S, (60, 200, 120), .55)
        self.nest_glows = [glow_rgb(210 // S, nest_col, .45 + .2 * k / 5) for k in range(6)]
        self.dawn_glows = [glow_rgb(300 // S, (255, 170, 90), .55 + .25 * k / 5) for k in range(6)]
        self.L_DAWN = radial(300 // S, 255, 1.0, K, 1)
        self.L_ECHO = {}
        self.aura = glow_rgb(70 // S, (150, 160, 255), .35)
        self.vig = make_vignette()
        self._mem_key, self._mem_img = None, None          # imagen ampliada de la memoria (se recalcula solo si cambia)
        self._flick = {}                                   # luz del murciélago con distintos parpadeos (precalculadas)

    def _memory(self, d, cam, cave):
        """Aclara tenuemente los tiles ya recorridos, para orientarte por dónde pasaste."""
        tx0, ty0 = int(cam.x) // TILE, int(cam.y) // TILE
        rect = pygame.Rect(tx0, ty0, W // TILE + 2, H // TILE + 2).clip(pygame.Rect(0, 0, cave.w, cave.h))
        if rect.w <= 0 or rect.h <= 0:
            return
        key = (rect.x, rect.y, rect.w, rect.h, cave.mem_version)
        if key != self._mem_key:
            tile_s = TILE // S
            self._mem_img = pygame.transform.smoothscale(cave.mem.subsurface(rect), (rect.w * tile_s, rect.h * tile_s))
            self._mem_key = key
        d.blit(self._mem_img, ((rect.x * TILE - int(cam.x)) // S, (rect.y * TILE - int(cam.y)) // S), special_flags=SUB)

    def apply(self, c, g, t):
        """Oscurece el lienzo c y añade los brillos de color. g es la escena de juego."""
        cam, b = g.camera, g.bat
        _, ambient, radius = BRIGHTNESS_LEVELS[g.game.brightness]
        ambient = max(120, min(252, ambient + self.amb_off))
        d = self.small
        d.fill((*self.amb_rgb, ambient))
        if g.echo_t > 0:                       # ecolocación: el grito "dibuja" un momento lo que rodea a Mullo
            k = g.echo_t / ECHO_FLASH_T
            r = int((SCREECH_R * 2.4 * (1 - k * .55)) / S)
            ox, oy = cam.apply(*g.echo_origin)
            key = (r // 4, int(k * 6))
            surf = self.L_ECHO.get(key)
            if surf is None:
                if len(self.L_ECHO) > 60:
                    self.L_ECHO.clear()
                surf = self.L_ECHO[key] = faded(radial(max(4, key[0] * 4), 255, .5, K, 2), int(200 * min(1, k * 1.3)))
            hw = surf.get_width() // 2
            d.blit(surf, (round(ox / S) - hw, round(oy / S) - hw), special_flags=SUB)
        self._memory(d, cam, g.cave)
        step = round(3 * math.sin(t * 9) * math.sin(t * 3.1))      # parpadeo suave en 7 pasos (-3..3)
        lb = self._flick.get((radius, step))
        if lb is None:
            base = self.bat_lights[radius]
            sz = int(base.get_width() * (1 + .01 * step))
            lb = self._flick[(radius, step)] = pygame.transform.scale(base, (sz, sz)) if step else base
        bx, by = cam.apply(b.x, b.y)
        hw = lb.get_width() // 2
        d.blit(lb, (round(bx / S) - hw, round(by / S) - hw), special_flags=SUB)
        nx, ny = cam.apply(*NEST)
        dawn = self.theme == 'mine'
        near_nest = cam.visible(*NEST, 340 if dawn else 260)
        if near_nest:
            ln = self.L_DAWN if dawn else self.L_NEST
            hw = ln.get_width() // 2
            d.blit(ln, (round(nx / S) - hw, round(ny / S) - hw), special_flags=SUB)
        for p in g.pups:
            if p is not b.carry and cam.visible(p.x, p.y, 80):
                px, py = cam.apply(p.x, p.y)
                hw = self.L_PUP.get_width() // 2
                d.blit(self.L_PUP, (round(px / S) - hw, round(py / S) - hw), special_flags=SUB)
        vis_c = [(x, y, col) for x, y, col in self.crystals if cam.visible(x, y, 120)]
        vis_f = [(x, y) for x, y in self.fungi if cam.visible(x, y, 80)]
        if len(vis_f) > 28:                                        # en pantalla basta con los más cercanos
            vis_f = sorted(vis_f, key=lambda p: (p[0] - b.x) ** 2 + (p[1] - b.y) ** 2)[:28]
        vis_a = [(x, y) for x, y in self.algae if cam.visible(x, y, 40)]
        for x, y, col in vis_c:
            sx, sy = cam.apply(x, y)
            hw = self.L_CRY.get_width() // 2
            d.blit(self.L_CRY, (round(sx / S) - hw, round(sy / S) - hw), special_flags=SUB)
        for x, y in vis_f:
            sx, sy = cam.apply(x, y)
            hw = self.L_FUN.get_width() // 2
            d.blit(self.L_FUN, (round(sx / S) - hw, round(sy / S) - hw), special_flags=SUB)
        for x, y in vis_a:
            sx, sy = cam.apply(x, y)
            hw = self.L_ALG.get_width() // 2
            d.blit(self.L_ALG, (round(sx / S) - hw, round(sy / S) - hw), special_flags=SUB)
        # brillos tintados: se suman al color de la capa de oscuridad, así se ven de lejos
        hw = self.aura.get_width() // 2
        d.blit(self.aura, (round(bx / S) - hw, round(by / S) - hw), special_flags=ADD)
        if near_nest:
            ng = (self.dawn_glows if dawn else self.nest_glows)[int(2.5 + 2.5 * math.sin(t * 2.2))]
            hw = ng.get_width() // 2
            d.blit(ng, (round(nx / S) - hw, round(ny / S) - hw), special_flags=ADD)
        for x, y, col in vis_c:
            sx, sy = cam.apply(x, y)
            gl = self.glow[col]
            hw = gl.get_width() // 2
            d.blit(gl, (round(sx / S) - hw, round(sy / S) - hw), special_flags=ADD)
        for x, y in vis_f:
            sx, sy = cam.apply(x, y)
            hw = self.fun_glow.get_width() // 2
            d.blit(self.fun_glow, (round(sx / S) - hw, round(sy / S) - hw), special_flags=ADD)
        for x, y in vis_a:
            sx, sy = cam.apply(x, y)
            hw = self.alg_glow.get_width() // 2
            d.blit(self.alg_glow, (round(sx / S) - hw, round(sy / S) - hw), special_flags=ADD)
        sky = getattr(g.cave, 'skylight', None)                    # luz que entra por la grieta del techo
        if sky and cam.visible(*sky, 260):
            if not hasattr(self, '_sky'):
                col = {'fungi': (70, 100, 220), 'lake': (150, 90, 230), 'mine': (255, 150, 70)}[self.theme]
                self._sky = (radial(170 // S, 230, 1.3, K, 1), glow_rgb(170 // S, col, .55))
            sub, add = self._sky
            sx, sy = cam.apply(sky[0], sky[1] + 110)
            hw = sub.get_width() // 2
            d.blit(sub, (round(sx / S) - hw, round(sy / S) - hw), special_flags=SUB)
            d.blit(add, (round(sx / S) - hw, round(sy / S) - hw), special_flags=ADD)
        d.blit(self.vig, (0, 0))                                   # viñeta
        pygame.transform.scale(d, (W, H), self.up)                 # una sola ampliación
        c.blit(self.up, (0, 0))

    # ------------------------------------------------------------ efectos directos sobre el lienzo
    def draw_shield(self, c, g, t):
        """Burbuja del escudo alrededor del murciélago (parpadea al agotarse)."""
        b = g.bat
        if b.shield_t <= 0:
            return
        if b.shield_t < 1.2 and int(t * 12) % 2:
            return
        x, y = g.camera.apply(b.x, b.y)
        r = SHIELD_R + int(2 * math.sin(t * 10))
        ring(c, x, y, r - 3, (110, 200, 255), .55, 2)
        ring(c, x, y, r, (170, 230, 255), 1.0, 3)
        pygame.draw.arc(c, (255, 255, 255), (x - r + 4, y - r + 4, 2 * r - 8, 2 * r - 8), .6 + t * 2, 1.5 + t * 2, 3)

    def draw_trail(self, c, g):
        """Estela tenue que deja el murciélago al volar rápido."""
        for x, y, life in g.bat.trail:
            sx, sy = g.camera.apply(x, y)
            f = life / .35
            pygame.draw.circle(c, (int(120 * f), int(105 * f), int(190 * f)), (int(sx), int(sy)), 2 + int(3 * f))
