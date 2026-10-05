"""Iluminación: penumbra azulada legible, luz propia amplia, memoria de lo recorrido, balizas y sonar.

Todo el cálculo de luz se hace en un mapa de 1/2 de resolución (SW x SH) y se amplía una sola vez:
la luz es suave, así que no se nota, y evita varias mezclas de pantalla completa por frame
(muy caras en el navegador con WebAssembly).
"""
import math

import pygame

from settings import (W, H, TILE, NEST, SONAR_MAX_R, SHIELD_R, C_SONAR, BRIGHTNESS_LEVELS, AMBIENT_RGB)

S = 2                                  # factor de reducción del mapa de luz
SW, SH = W // S, H // S
SUB = pygame.BLEND_RGBA_SUB
ADD = pygame.BLEND_RGB_ADD
K = (0, 0, 0)
TINT = (30, 70, 150)                   # color de la zona revelada por el sonar


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
    def __init__(self, crystals, fungi=()):
        self.crystals, self.fungi = crystals, list(fungi)
        self.small = pygame.Surface((SW, SH), pygame.SRCALPHA)
        self.up = pygame.Surface((W, H), pygame.SRCALPHA)
        # luces que se RESTAN de la oscuridad (solo opacidad)
        self.bat_lights = {lv[2]: radial(lv[2] // S, 255, .8, K, 1) for lv in BRIGHTNESS_LEVELS}
        self.L_NEST = radial(210 // S, 255, 1.0, K, 1)
        self.L_PUP = faded(radial(60 // S, 255, 1.0, K, 1), 150)
        self.L_CRY = faded(radial(70 // S, 255, 1.0, K, 1), 110)
        self.L_FUN = faded(radial(36 // S, 255, 1.0, K, 1), 110)
        # brillos de color que se SUMAN (balizas visibles de lejos)
        self.glow = {col: glow_rgb(70 // S, col, 1.0) for col in {c[2] for c in crystals}}
        self.fun_glow = glow_rgb(36 // S, (70, 230, 170), .9)
        self.nest_glows = [glow_rgb(210 // S, (255, 170, 90), .45 + .2 * k / 5) for k in range(6)]
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
        d = self.small
        d.fill((*AMBIENT_RGB, ambient))
        k, rad = b.sonar_strength, b.sonar_radius
        if k > 0 and rad:                      # el sonar aclara y tiñe de azul todo lo que alcanza la onda
            ox, oy = cam.apply(*b.sonar_origin)
            for dr, frac in ((0, .30), (40, .55), (90, .78), (150, .9)):          # borde suave de la onda
                if rad - dr > 0:
                    a = int(ambient * (1 - frac * k))
                    mix = frac * k
                    col = tuple(int(AMBIENT_RGB[i] * (1 - mix) + TINT[i] * mix) for i in range(3))
                    pygame.draw.circle(d, (*col, a), (int(ox / S), int(oy / S)), int((rad - dr) / S))
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
        near_nest = cam.visible(*NEST, 260)
        if near_nest:
            hw = self.L_NEST.get_width() // 2
            d.blit(self.L_NEST, (round(nx / S) - hw, round(ny / S) - hw), special_flags=SUB)
        for p in g.pups:
            if p is not b.carry and cam.visible(p.x, p.y, 80):
                px, py = cam.apply(p.x, p.y)
                hw = self.L_PUP.get_width() // 2
                d.blit(self.L_PUP, (round(px / S) - hw, round(py / S) - hw), special_flags=SUB)
        vis_c = [(x, y, col) for x, y, col in self.crystals if cam.visible(x, y, 80)]
        vis_f = [(x, y) for x, y in self.fungi if cam.visible(x, y, 50)]
        for x, y, col in vis_c:
            sx, sy = cam.apply(x, y)
            hw = self.L_CRY.get_width() // 2
            d.blit(self.L_CRY, (round(sx / S) - hw, round(sy / S) - hw), special_flags=SUB)
        for x, y in vis_f:
            sx, sy = cam.apply(x, y)
            hw = self.L_FUN.get_width() // 2
            d.blit(self.L_FUN, (round(sx / S) - hw, round(sy / S) - hw), special_flags=SUB)
        # brillos tintados: se suman al color de la capa de oscuridad, así se ven de lejos
        hw = self.aura.get_width() // 2
        d.blit(self.aura, (round(bx / S) - hw, round(by / S) - hw), special_flags=ADD)
        if near_nest:
            ng = self.nest_glows[int(2.5 + 2.5 * math.sin(t * 2.2))]
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

    def draw_sonar_ring(self, c, g):
        b = g.bat
        rad = b.sonar_radius
        if rad is not None and b.sonar_t is not None and rad < SONAR_MAX_R:
            ox, oy = g.camera.apply(*b.sonar_origin)
            ring(c, ox, oy, rad, C_SONAR, .75, 5)
            ring(c, ox, oy, max(1, rad - 14), C_SONAR, .35, 3)
