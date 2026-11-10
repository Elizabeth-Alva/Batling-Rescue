"""Fondo de la portada hecho con el mismo motor del juego: la cueva real de cada nivel (roca, hongos, cristales,
agua o vías e iluminación del nivel), el nido con las diez crías y Mullo volando.

TitleCave      una cueva (nivel 1, 2 o 3) generada con una semilla fija: siempre se ve igual.
TitleBackdrop  las tres cuevas; cambia de una a otra con un fundido (al ritmo del Can-Can del menú).
Las cuevas se generan una sola vez (al cargar el juego) y se guardan en el juego.
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
from story import PUPS, LEVELS

SEED = 7
NAMES = [n.strip() for lv in (1, 2, 3) for name, _ in PUPS[lv] for n in name.split(' y ')]


class TitleCave:
    def __init__(self, seed=SEED, level=1):
        self.level = level
        state = random.getstate()
        random.seed(seed)
        try:
            self.cave = cv = CaveMap(level)
            self.resting = [Resting(i, len(NAMES), nm, sc=.55) for i, nm in enumerate(NAMES)]   # las 10 juntas: más chiquitas
        finally:
            random.setstate(state)
        for r in self.resting:
            r.arrive = 0.0
        self.camera = Camera(*NEST)
        self.camera.x, self.camera.y = self._best_view()
        cam = self.camera
        cv.mark_circle(cam.x + W / 2, cam.y + H / 2, max(W, H), mem=True)     # la cueva se ve tenue, como ya recorrida
        self.light = Lighting(cv.crystals, cv.fungi, LEVELS[level]['theme'], cv.algae)
        self.view = cv.bg.subsurface((int(cam.x), int(cam.y), W, H)).copy()   # roca y hongos del juego (fijo)
        cv.bg = None                                          # el mapa completo ya no hace falta (ahorra memoria)
        self.path = self._flight_path()
        self.t = 0.0
        self.bat = SimpleNamespace(x=NEST[0], y=NEST[1], carry=None)
        self.g = SimpleNamespace(camera=cam, bat=self.bat, pups=[], cave=cv, echo_t=0.0,
                                 game=SimpleNamespace(brightness=2))

    # ------------------------------------------------------------ preparación
    def _best_view(self):
        """Encuadre con el nido a la izquierda y la mayor cantidad de luces (hongos, cristales, algas) a la vista."""
        cv, best, bs = self.cave, (0, 0), -1
        max_x, max_y = cv.w * TILE - W, cv.h * TILE - H
        for x in range(0, min(max_x, 400) + 1, 20):
            for y in range(0, min(max_y, 300) + 1, 20):
                nx, ny = NEST[0] - x, NEST[1] - y
                if not (90 < nx < 300 and 200 < ny < 470):
                    continue
                lights = list(cv.fungi) + [(c[0], c[1]) for c in cv.crystals] + [(a[0], a[1]) for a in cv.algae]
                score = sum(1 for fx, fy in lights if x + 30 < fx < x + W - 30 and y + 30 < fy < y + H - 30)
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
        self.light.apply(s, self.g, t)                       # (la luz de Mullo ya la sigue: b.x, b.y)
        for r in self.resting:
            r.draw_fx(s, cam)
        ui.draw_bat_tilted(s, sx, sy, t * 13, tilt)           # Mullo al final: vuela POR ENCIMA de sus crías


class TitleBackdrop:
    """Las cuevas de los 3 niveles para la portada. set_level() cambia de cueva con un fundido suave."""
    FADE = 1.4

    def __init__(self, seed=SEED):
        self.caves = {lv: TitleCave(seed, lv) for lv in (1, 2, 3)}
        self.level, self.prev, self.fade, self.t = 1, None, 0.0, 0.0
        self._tmp = pygame.Surface((W, H))

    def set_level(self, lv, instant=False):
        if lv == self.level:
            return
        self.prev, self.level = self.level, lv
        self.fade = 0.0 if instant else self.FADE

    def update(self, dt):
        self.t += dt
        self.fade = max(0.0, self.fade - dt)
        for c in self.caves.values():
            c.update(dt)

    def draw(self, s, t=None):
        t = self.t if t is None else t
        self.caves[self.level].draw(s, t)
        if self.fade > 0 and self.prev is not None:          # la cueva anterior se desvanece encima
            self.caves[self.prev].draw(self._tmp, t)
            k = self.fade / self.FADE
            self._tmp.set_alpha(int(255 * k * k * (3 - 2 * k)))
            s.blit(self._tmp, (0, 0))
