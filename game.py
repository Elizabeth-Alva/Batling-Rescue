"""Bucle principal y gestor de escenas con fundido entre ellas."""
import pygame

import ui
from settings import W, H, FPS, TITLE, DEFAULT_BRIGHTNESS
from sound import SoundManager


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        ui.init_fonts()
        self.sounds = SoundManager()
        self.backdrop = ui.Backdrop()
        self.running = True
        self.brightness = DEFAULT_BRIGHTNESS         # nivel de brillo (tecla B), se conserva entre partidas
        self.pending = None
        self.fade, self.fade_dir = 255.0, -1        # 255 = negro total
        self.veil = pygame.Surface((W, H))
        self.scene = self._make('title')
        self.scene.enter()

    def _make(self, name):
        from scenes.title import TitleScene
        from scenes.instructions import InstructionsScene
        from scenes.play import PlayScene
        if name == 'play':                           # generar la cueva tarda un instante
            self.screen.fill((0, 0, 0))
            ui.text(self.screen, ui.F_M, 'Generando la cueva...', W // 2, H // 2, (170, 150, 210), True)
            pygame.display.flip()
        return {'title': TitleScene, 'instructions': InstructionsScene, 'play': PlayScene}[name](self)

    def goto(self, name):
        if self.pending is None:
            self.pending, self.fade_dir = name, 1

    def _fade_step(self, dt):
        if self.fade_dir == 0:
            return
        self.fade = min(255, max(0, self.fade + self.fade_dir * dt * 1100))
        if self.fade_dir > 0 and self.fade >= 255:
            self.scene = self._make(self.pending)
            self.scene.enter()
            self.pending, self.fade_dir = None, -1
        elif self.fade_dir < 0 and self.fade <= 0:
            self.fade_dir = 0

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000, .05)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                elif self.pending is None:
                    self.scene.handle(ev)
            self.scene.update(dt)
            self._fade_step(dt)
            self.scene.draw(self.screen)
            if self.fade > 0:
                self.veil.set_alpha(int(self.fade))
                self.screen.blit(self.veil, (0, 0))
            pygame.display.flip()
