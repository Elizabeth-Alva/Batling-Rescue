"""Pantalla de récords del menú: los mejores tiempos por completar los 3 niveles (historia completa)."""
import pygame

import scores
import ui
from scenes import Scene
from scenes.results import draw_table, glow_title, hint
from settings import W, H


class RecordsScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        self.panel = pygame.Surface((W - 80, H - 40), pygame.SRCALPHA)
        pygame.draw.rect(self.panel, (6, 4, 16, 205), self.panel.get_rect(), border_radius=18)
        pygame.draw.rect(self.panel, (110, 80, 170, 220), self.panel.get_rect(), 2, border_radius=18)

    def enter(self):
        self.game.sounds.stop(keep_song=True)
        self.game.sounds.menu_music()                                   # sigue el Can-Can del menú

    def handle(self, ev):
        if (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE, pygame.K_BACKSPACE)) \
                or (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1):
            self.game.sounds.play('menu_select')
            self.game.goto('title')

    def update(self, dt):
        self.t += dt
        self.game.backdrop.update(dt)

    def draw(self, screen):
        self.game.backdrop.draw(screen)
        screen.blit(self.panel, (40, 20))
        glow_title(screen, ui.F_L, 'RÉCORDS DE TIEMPO', W // 2, 66, (255, 236, 200), (255, 150, 60), self.t)
        ui.text(screen, ui.F_XS, 'Tiempo por completar los 3 niveles. Menos tiempo = mejor lugar.',
                W // 2, 108, (200, 185, 230), True)
        ui.text(screen, ui.F_XS, 'El reloj se detiene en pausa y en las cinemáticas; los reintentos sí cuentan.',
                W // 2, 128, (170, 160, 200), True)
        w = 460
        draw_table(screen, (W // 2 - w // 2, 150, w, 52 + scores.TOP_N * 36), 'HISTORIA COMPLETA · 3 NIVELES',
                   scores.top(), None, self.t, 36)
        touch = getattr(self.game, 'touch', None)
        hint(screen, 'Toca para volver' if touch is not None and touch.active else 'Esc o Enter: volver al menú', H - 30)
