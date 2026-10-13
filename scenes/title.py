"""Portada con menú: Jugar / Instrucciones / Salir."""
import math

import pygame

import ui
from art import Cover
from scenes import Scene
from settings import IS_WEB, W, H

_LOGO = {}


def _logo_parts():
    if not _LOGO:
        big = ui.F_XL
        word = big.render('BATLING', True, (255, 255, 255))
        grad = pygame.Surface(word.get_size())
        for y in range(word.get_height()):                    # relleno degradado: lila claro -> dorado del amanecer
            f = y / word.get_height()
            col = (int(235 + 20 * f), int(225 - 40 * f), int(255 - 150 * f))
            grad.fill(col, (0, y, word.get_width(), 1))
        word = word.copy()
        word.blit(grad, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        _LOGO['word'] = word
        _LOGO['shadow'] = big.render('BATLING', True, (30, 10, 60))
        _LOGO['glow'] = ui.make_glow(big, 'BATLING', (150, 90, 255), blur=6, pad=40)
        sub = ui.F_L.render('R E S C U E', True, (255, 200, 130))
        _LOGO['sub'] = sub
        _LOGO['sub_glow'] = ui.make_glow(ui.F_L, 'R E S C U E', (255, 120, 60), blur=5, pad=30)
    return _LOGO


def draw_logo(s, t, cy=86):
    L = _logo_parts()
    pulse = .55 + .45 * math.sin(t * 2.2)
    cx = W // 2
    L['glow'].set_alpha(int(120 + 110 * pulse))
    s.blit(L['glow'], L['glow'].get_rect(center=(cx, cy)))
    s.blit(L['shadow'], L['shadow'].get_rect(center=(cx + 4, cy + 6)))
    s.blit(L['word'], L['word'].get_rect(center=(cx, cy)))
    L['sub_glow'].set_alpha(int(110 + 80 * pulse))
    s.blit(L['sub_glow'], L['sub_glow'].get_rect(center=(cx, cy + 74)))
    s.blit(L['sub'], L['sub'].get_rect(center=(cx, cy + 74)))


def draw_cover(s, t, cover, tagline=True):
    """Portada completa (también se exporta como imagen con tools/make_cover.py)."""
    cover.draw(s, t, mullo_y=372)
    draw_logo(s, t)
    if tagline:
        ui.text(s, ui.F_S, 'Una madre. Diez crías. Una sola noche.', W // 2, 196, (255, 236, 210), True)
        ui.text(s, ui.F_XS, '¿El amor puede más que el miedo?', W // 2, 220, (210, 190, 245), True)


class TitleScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.main = ['Jugar', 'Instrucciones'] + ([] if IS_WEB else ['Salir'])
        self.menu = ui.Menu(self.main, W // 2, 566, gap=236, w=220, h=44, horizontal=True)
        self.t = 0.0
        self.cover = Cover()
        self.panel = pygame.Surface((W, 92), pygame.SRCALPHA)
        for y in range(92):
            self.panel.fill((0, 0, 0, int(200 * (y / 92) ** .7)), (0, y, W, 1))

    def enter(self):
        self.game.sounds.stop()
        self.game.sounds.ambient(.3)

    def handle(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            if not IS_WEB:
                self.game.running = False
            return
        choice = self.menu.handle(ev, self.game.sounds)
        if choice == 0:
            self.game.start_story()
        elif choice == 1:
            self.game.goto('instructions')
        elif choice == 2:
            self.game.running = False

    def update(self, dt):
        self.t += dt

    def draw(self, screen):
        draw_cover(screen, self.t, self.cover)
        screen.blit(self.panel, (0, H - 92))
        self.menu.draw(screen, 1 / 60)
        ui.text(screen, ui.F_XS, '← → Elegir        Enter → Aceptar', W // 2, H - 14, (170, 155, 200), True)
