"""Fondo de la portada hecho con el mismo motor del juego: la cueva real de Las Galerías de los Hongos
(roca, hongos luminosos, cristales e iluminación del nivel 1), el nido con las diez crías y Mullo volando.

La cueva se genera una sola vez con una semilla fija (siempre se ve igual) y se guarda en el juego.
"""
import math
import random
from types import SimpleNamespace

import pygame

import ui
from camera import Camera
from fauna import Resting
from lighting import Lighting
from map import CaveMap
from settings import W, H, NEST, TILE
from story import PUPS

SEED = 7
NAMES = [n.strip() for lv in (1, 2, 3) for name, _ in PUPS[lv] for n in name.split(' y ')]


class TitleCave:
    def __init__(self, seed=SEED):
        state = random.getstate()
        random.seed(seed)
        try:
            self.cave = cv = CaveMap(1)
            self.resting = [Resting(i, len(NAMES), nm) for i, nm in enumerate(NAMES)]
        finally:
            random.setstate(state)
        for r in self.resting:
            r.arrive = 0.0
        self.camera = Camera(*NEST)
        self.camera.x, self.camera.y = self._best_view()
        cam = self.camera
        cv.mark_circle(cam.x + W / 2, cam.y + H / 2, max(W, H), mem=True)     # la cueva se ve tenue, como ya recorrida
        self.light = Lighting(cv.crystals, cv.fungi, 'fungi', cv.algae)
        self.view = cv.bg.subsurface((int(cam.x), int(cam.y), W, H)).copy()   # roca y hongos del juego (fijo)
        self.path = self._flight_path()
        self.t = 0.0
        self.bat = SimpleNamespace(x=NEST[0], y=NEST[1], carry=None)
        self.g = SimpleNamespace(camera=cam, bat=self.bat, pups=[], cave=cv, echo_t=0.0,
                                 game=SimpleNamespace(brightness=2))

    # ------------------------------------------------------------ preparación
    def _best_view(self):
        """Encuadre con el nido a la izquierda y la mayor cantidad de hongos a la vista."""
        cv, best, bs = self.cave, (0, 0), -1
        max_x, max_y = cv.w * TILE - W, cv.h * TILE - H
        for x in range(0, min(max_x, 400) + 1, 20):
            for y in range(0, min(max_y, 300) + 1, 20):
                nx, ny = NEST[0] - x, NEST[1] - y
                if not (90 < nx < 300 and 200 < ny < 470):
                    continue
                score = sum(1 for fx, fy in cv.fungi if x + 30 < fx < x + W - 30 and y + 30 < fy < y + H - 30)
                if score > bs:
                    best, bs = (x, y), score
        return best

    LOGO_BOX = pygame.Rect(270, 30, 420, 370)                 # dónde va el logo (Mullo no vuela detrás)

    def _flight_path(self):
        """Vuelta suave alrededor del nido, por donde no hay roca y fuera del logo y del menú."""
        cv, cam = self.cave, self.camera
        for rx, ry in ((120, 95), (105, 85), (90, 75), (75, 62), (60, 50)):
            pts = [self._loop(a, rx, ry) for a in [k * math.tau / 48 for k in range(48)]]
            if not any(cv.solid_px(x, y) or self.LOGO_BOX.collidepoint(x - cam.x, y - cam.y) or y - cam.y > 520
                       or x - cam.x < 20 for x, y in pts):
                return rx, ry
        return 55, 45

    @staticmethod
    def _loop(a, rx, ry):
        return NEST[0] + math.cos(a) * rx, NEST[1] + 20 + math.sin(a) * ry

    # ------------------------------------------------------------ cada cuadro
    def mullo_at(self, t):
        rx, ry = self.path
        x, y = self._loop(t * .7, rx, ry)
        return x, y + math.sin(t * 2.3) * 5

    def update(self, dt):
        self.t += dt
        for r in self.resting:
            r.update(dt)

    def draw(self, s, t=None):
        t = self.t if t is None else t
        cam, b = self.camera, self.bat
        s.blit(self.view, (0, 0))
        for r in self.resting:
            r.draw(s, cam)
        x0, y0 = self.mullo_at(t - .05)
        b.x, b.y = self.mullo_at(t)
        tilt = max(-.45, min(.45, (b.x - x0) * .06))
        sx, sy = cam.apply(b.x, b.y)
        ui.draw_bat_tilted(s, sx, sy, t * 13, tilt)
        self.light.apply(s, self.g, t)
        for r in self.resting:
            r.draw_fx(s, cam)
