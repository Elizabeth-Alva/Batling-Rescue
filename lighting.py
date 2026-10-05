"""Iluminación: penumbra azulada legible, luz propia amplia, memoria de lo recorrido, balizas y sonar."""
import math

import pygame

from settings import (W, H, TILE, NEST, SONAR_MAX_R, SHIELD_R, C_SONAR, BRIGHTNESS_LEVELS, AMBIENT_RGB)

SUB = pygame.BLEND_RGBA_SUB


def radial(r, peak=255, exp=1.3, rgb=(255, 255, 255)):
    """Disco de luz: opaco en el centro y cayendo suavemente hasta 0 en el borde.
    Para restar de la oscuridad se usa rgb=(0, 0, 0): BLEND_RGBA_SUB resta también el color,
    y así solo cambia la opacidad sin desteñir el tinte ambiente."""
    s = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
    for i in range(r, 0, -2):
        pygame.draw.circle(s, (*rgb, int(peak * (1 - i / r) ** exp)), (r, r), i)
    return s


def tinted(surf, col):
    t = surf.copy()
    t.fill((*col, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return t


def faded(surf, alpha):
    t = surf.copy()
    t.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    return t


K = (0, 0, 0)


def make_vignette():
    sm = pygame.Surface((48, 32), pygame.SRCALPHA)
    for y in range(32):
        for x in range(48):
            d = math.hypot((x - 23.5) / 24, (y - 15.5) / 16)
            sm.set_at((x, y), (0, 0, 0, int(max(0, min(1, (d - .6) / .6)) ** 1.4 * 150)))
    return pygame.transform.smoothscale(sm, (W, H))


class Lighting:
    def __init__(self, crystals, fungi=()):
        self.crystals, self.fungi = crystals, list(fungi)
        # luz del murciélago, una por nivel de brillo (suave: exponente < 1)
        self.bat_lights = {lv[2]: radial(lv[2], 255, .8, K) for lv in BRIGHTNESS_LEVELS}
        self.bat_aura = tinted(radial(70, 70, 1.0), (150, 160, 255))
        self.L_NEST = radial(210, 255, 1.0, K)
        self.nest_glow = tinted(radial(210, 110, 1.0), (255, 170, 90))
        self.L_PUP = faded(radial(60, 255, 1.0, K), 150)
        self.L_CRY = faded(radial(70, 255, 1.0, K), 150)
        self.L_FUN = faded(radial(36, 255, 1.0, K), 130)
        self.glow = {c: tinted(radial(70, 150, 1.0), c) for c in {c[2] for c in crystals}}
        self.fun_glow = tinted(radial(36, 120, 1.0), (70, 230, 170))
        self.dark = pygame.Surface((W, H), pygame.SRCALPHA)
        self.reveal = pygame.Surface((W, H), pygame.SRCALPHA)
        self.tint = pygame.Surface((W, H))
        self.vig = make_vignette()

    def _memory(self, d, cam, cave):
        """Aclara tenuemente los tiles ya recorridos, para orientarte por dónde pasaste."""
        tx0, ty0 = int(cam.x) // TILE, int(cam.y) // TILE
        rect = pygame.Rect(tx0, ty0, W // TILE + 2, H // TILE + 2).clip(pygame.Rect(0, 0, cave.w, cave.h))
        if rect.w <= 0 or rect.h <= 0:
            return
        big = pygame.transform.smoothscale(cave.mem.subsurface(rect), (rect.w * TILE, rect.h * TILE))
        d.blit(big, (rect.x * TILE - int(cam.x), rect.y * TILE - int(cam.y)), special_flags=SUB)

    def apply(self, c, g, t):
        """Oscurece el lienzo c y añade los brillos de color. g es la escena de juego."""
        cam, b = g.camera, g.bat
        _, ambient, radius = BRIGHTNESS_LEVELS[g.game.brightness]
        d = self.dark
        d.fill((*AMBIENT_RGB, ambient))
        self._memory(d, cam, g.cave)
        flick = 1 + .03 * math.sin(t * 9) * math.sin(t * 3.1)
        r = int(radius * flick)
        lb = self.bat_lights[radius]
        if r != radius:
            lb = pygame.transform.scale(lb, (2 * r, 2 * r))
        bx, by = cam.apply(b.x, b.y)
        d.blit(lb, (bx - r, by - r), special_flags=SUB)
        nx, ny = cam.apply(*NEST)
        if cam.visible(*NEST, 260):
            d.blit(self.L_NEST, (nx - 210, ny - 210), special_flags=SUB)
        for p in g.pups:
            if p is not b.carry and cam.visible(p.x, p.y, 80):
                px, py = cam.apply(p.x, p.y)
                d.blit(self.L_PUP, (px - 60, py - 60), special_flags=SUB)
        for x, y, col in self.crystals:
            if cam.visible(x, y, 80):
                sx, sy = cam.apply(x, y)
                d.blit(self.L_CRY, (sx - 70, sy - 70), special_flags=SUB)
        for x, y in self.fungi:
            if cam.visible(x, y, 50):
                sx, sy = cam.apply(x, y)
                d.blit(self.L_FUN, (sx - 36, sy - 36), special_flags=SUB)
        k = b.sonar_strength
        rad = b.sonar_radius
        if k > 0 and rad:
            ox, oy = cam.apply(*b.sonar_origin)
            rv = self.reveal
            rv.fill((0, 0, 0, 0))
            for dr, a in ((0, 70), (40, 130), (90, 190), (150, 215)):   # borde suave de la onda
                if rad - dr > 0:
                    pygame.draw.circle(rv, (0, 0, 0, int(a * k)), (int(ox), int(oy)), int(rad - dr))
            d.blit(rv, (0, 0), special_flags=SUB)
            tn = self.tint
            tn.fill((0, 0, 0))
            pygame.draw.circle(tn, (int(10 * k), int(26 * k), int(48 * k)), (int(ox), int(oy)), int(min(rad, SONAR_MAX_R)))
            c.blit(tn, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        c.blit(d, (0, 0))
        # brillos tintados encima de la oscuridad (las balizas se ven de lejos)
        c.blit(self.bat_aura, (bx - 70, by - 70))
        if cam.visible(*NEST, 260):
            self.nest_glow.set_alpha(int(190 + 65 * math.sin(t * 2.2)))
            c.blit(self.nest_glow, (nx - 210, ny - 210))
        for x, y, col in self.crystals:
            if cam.visible(x, y, 80):
                sx, sy = cam.apply(x, y)
                c.blit(self.glow[col], (sx - 70, sy - 70))
        for x, y in self.fungi:
            if cam.visible(x, y, 50):
                sx, sy = cam.apply(x, y)
                c.blit(self.fun_glow, (sx - 36, sy - 36))

    def finish(self, c):
        c.blit(self.vig, (0, 0))

    def draw_shield(self, fx, g, t):
        """Burbuja del escudo alrededor del murciélago (parpadea al agotarse)."""
        b = g.bat
        if b.shield_t <= 0:
            return
        if b.shield_t < 1.2 and int(t * 12) % 2:
            return
        x, y = g.camera.apply(b.x, b.y)
        r = SHIELD_R + int(2 * math.sin(t * 10))
        pygame.draw.circle(fx, (110, 200, 255, 55), (int(x), int(y)), r)
        pygame.draw.circle(fx, (170, 230, 255, 230), (int(x), int(y)), r, 3)
        pygame.draw.arc(fx, (255, 255, 255, 200), (x - r + 4, y - r + 4, 2 * r - 8, 2 * r - 8), .6 + t * 2, 1.5 + t * 2, 3)

    def draw_trail(self, fx, g):
        """Estela tenue que deja el murciélago al volar rápido."""
        for x, y, life in g.bat.trail:
            sx, sy = g.camera.apply(x, y)
            pygame.draw.circle(fx, (170, 150, 255, int(150 * life / .35)), (int(sx), int(sy)), 2 + int(3 * life / .35))

    def draw_sonar_ring(self, fx, g):
        b = g.bat
        rad = b.sonar_radius
        if rad is not None and b.sonar_t is not None and rad < SONAR_MAX_R:
            ox, oy = g.camera.apply(*b.sonar_origin)
            pygame.draw.circle(fx, (*C_SONAR, 190), (int(ox), int(oy)), int(rad), 5)
            pygame.draw.circle(fx, (*C_SONAR, 90), (int(ox), int(oy)), int(max(1, rad - 14)), 3)
