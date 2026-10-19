"""Cinemáticas entre niveles: cielo que cambia de color, la silueta de Mullo y 2-3 líneas de contexto.

Espacio / Enter / clic: completar el texto o pasar a la siguiente toma.   Esc: saltar la escena.
"""
import math

import pygame

import ui
from art import make_shot
from scenes import Scene
from settings import W, H, GOAL, C_GOLD, C_PUP, C_PURPLE
from story import CUTSCENES, VOICE, SHOT_SFX

CPS = 42                 # letras por segundo del texto
BAR = 74                 # alto de las franjas de cine


class CutsceneScene(Scene):
    def __init__(self, game, key='apertura'):
        super().__init__(game)
        self.key = key
        self.data = CUTSCENES[key]
        self.i = 0
        self.shots = {}
        self.canvas = pygame.Surface((W, H))
        self.prev = None                          # última imagen de la toma anterior (fundido cruzado)
        self._start()

    def _start(self):
        self.t = 0.0
        name, lines = self.data['shots'][self.i][:2]
        if name not in self.shots:
            self.shots[name] = make_shot(name)
        self.shot = self.shots[name]
        self.lines = lines
        self.voice_col = (246, 196, 140) if VOICE.get(name) == 'canela' else (214, 196, 255)
        self._quoted = set()                      # líneas que siguen una cita abierta en la línea anterior
        open_ = False
        for ln in lines:
            if open_:
                self._quoted.add(ln)
            open_ = (open_ or '«' in ln) and '»' not in ln
        self.total = sum(len(ln) for ln in lines)
        self.dur = max(6.0, self.total / CPS + 4.0)

    def _in_quote(self, ln):
        return ln in self._quoted

    def enter(self):
        self.game.sounds.stop()
        theme = {'n1_intro': 'fungi', 'n1_fin': 'fungi', 'n2_intro': 'lake', 'n2_fin': 'lake',
                 'n3_intro': 'mine'}.get(self.key)
        self.game.sounds.ambient(.3, 'amb_' + theme if theme else 'amb')
        self.game.sounds.play('story', base=.7)
        self._cue()

    def _cue(self):
        """Sonido de la toma: la voz de la Abuela, el susurro de la cueva, la voz verdadera..."""
        sfx = SHOT_SFX.get(self.data['shots'][self.i][0])
        if sfx:
            self.game.sounds.play(sfx[0], base=sfx[1])

    def _next(self):
        if self.i + 1 >= len(self.data['shots']):
            self.game.advance()
            return
        if self.prev is None:
            self.prev = pygame.Surface((W, H))
        self.shot.draw(self.prev, self.t, max(self.dur, self.t))   # la toma anterior se desvanece sobre la nueva
        self.prev_from_black = False
        self.i += 1
        self._start()
        self._cue()

    def handle(self, ev):
        K = pygame
        if ev.type == K.KEYDOWN and ev.key == K.K_ESCAPE:
            self.game.advance()
            return
        go = (ev.type == K.KEYDOWN and ev.key in (K.K_SPACE, K.K_RETURN, K.K_KP_ENTER)) or \
             (ev.type == K.MOUSEBUTTONDOWN and ev.button == 1)
        if not go:
            return
        if self.t * CPS < self.total:
            self.t = self.total / CPS + .01          # completa el texto
        else:
            self.game.sounds.play('menu_select')
            self._next()

    def update(self, dt):
        self.t += dt                         # la historia solo avanza con Espacio / Enter / clic

    def draw(self, screen):
        c = self.canvas
        self.shot.draw(c, self.t, max(self.dur, self.t))      # la animación se detiene suave al final de la toma
        if self.prev is not None and self.t < .9:            # fundido cruzado entre tomas (más suave que a negro)
            q = self.t / .9
            self.prev.set_alpha(int(255 * (1 - q * q * (3 - 2 * q))))
            c.blit(self.prev, (0, 0))
        k = min(1, self.t / .8)                    # las franjas entran suavemente
        bh = int(BAR * (.6 + .4 * k))
        c.fill((0, 0, 0), (0, 0, W, bh))
        c.fill((0, 0, 0), (0, H - bh - 30, W, bh + 30))
        ui.text(c, ui.F_XS, self.data['label'].upper(), 24, 20, C_GOLD)
        ui.text(c, ui.F_XS, f'{self.i + 1}/{len(self.data["shots"])}', W - 50, 20, (130, 120, 160))
        shown = int(self.t * CPS)
        y = H - bh - 30 + (22 if len(self.lines) < 3 else 16)
        for ln in self.lines:
            part = ln[:max(0, shown)]
            shown -= len(ln)
            if part:
                quote = '«' in ln or '»' in ln or self._in_quote(ln)
                col = (self.voice_col if quote else (242, 236, 252))
                f = ui.F_M if len(self.lines) < 3 and max(ui.F_M.size(x)[0] for x in self.lines) < W - 50 else ui.F_S
                ui.text(c, f, part, W // 2, y, col, True)
            y += 36 if len(self.lines) < 3 else 27
        if self.t * CPS >= self.total:                       # espera a que el jugador termine de leer
            k = .78 + .22 * math.sin(self.t * 4)
            hint = 'Toca para continuar  »' if getattr(self.game, 'touch', None) and self.game.touch.active else 'Espacio para continuar  »'
            ui.text(c, ui.F_S, hint, W - 140, H - 16, tuple(int(v * k) for v in (255, 220, 150)), True)
        # fundido de entrada desde negro (solo la primera toma de la escena)
        if self.prev is None and self.t < .5:
            v = pygame.Surface((W, H))
            v.set_alpha(int(255 * (1 - self.t / .5)))
            c.blit(v, (0, 0))
        screen.blit(c, (0, 0))


class EndScene(Scene):
    """Pantalla final: FIN, resumen de la noche y créditos del equipo."""

    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        from art import Departure
        self.shot = Departure()
        self.canvas = pygame.Surface((W, H))
        self.veil = pygame.Surface((W, H), pygame.SRCALPHA)
        self.veil.fill((0, 0, 0, 190))

    def enter(self):
        self.game.sounds.stop()
        self.game.sounds.play('win')
        self.game.sounds.ambient(.2)

    def handle(self, ev):
        if self.t > 1.5 and ((ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE))
                             or (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1)):
            self.game.sounds.play('menu_select')
            self.game.goto('title')

    def update(self, dt):
        self.t += dt

    def draw(self, screen):
        c = self.canvas
        self.shot.draw(c, self.t + 20, 30)
        c.blit(self.veil, (0, 0))
        p = self.game.progress
        cx = W // 2
        ui.text(c, ui.F_XL, 'FIN', cx, 86, (255, 236, 200), True)
        ui.text(c, ui.F_M, '¿El amor puede más que el miedo?', cx, 148, C_GOLD, True)
        ui.text(c, ui.F_S, f'Las {GOAL} crías están a salvo y la colonia parte completa.', cx, 184, (245, 238, 250), True)
        tt = p.get('play_time', 0)
        ui.text(c, ui.F_XS, f'Tiempo de juego: {int(tt // 60)}:{int(tt % 60):02d}    ·    Reintentos: {p.get("retries", 0)}',
                cx, 212, C_PUP, True)
        for i in range(GOAL):
            ui.pup_icon(c, cx - 99 + i * 22, 242, 'safe', self.t + i)
        # créditos: nombre y materia, profesor, equipo y grupo (cada uno en su bloque)
        blocks = [('Videojuego · Materia', ['BATling Rescue  ·  Creación de videojuegos']),
                  ('Profesor', ['Mtro. Jesús Barrón Vidales']),
                  ('Equipo', ['Alva Bustamante Elizabeth  ·  Gael Rodrigo Cervantes Rios',
                              'Francisco Feliciano Carlos  ·  Galavis Ricardo Hugo Enrique']),
                  ('Grupo', ['10IDS2'])]
        y = 284
        for label, lines in blocks:
            ui.text(c, ui.F_XS, label.upper(), cx, y, (170, 155, 200), True)
            y += 20
            for ln in lines:
                ui.text(c, ui.F_S, ln, cx, y, (240, 232, 250), True)
                y += 24
            y += 14
        if self.t > 1.5 and int(self.t * 2) % 2:
            ui.text(c, ui.F_S, 'Enter: volver al menú', cx, H - 40, C_PURPLE, True)
        screen.blit(c, (0, 0))
