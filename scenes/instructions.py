"""Pantalla de instrucciones."""
import math

import pygame

import ui
from scenes import Scene
from settings import W, H, GOAL, C_PURPLE, C_GREEN, C_SONAR, C_IMPACT

ENTRIES = [
    ('bat', 'Volar y rescatar', 'WASD / Flechas: volar',
     'Lleva a las crías hasta el nido (círculo marrón). Sigue sus chillidos y las flechas rosadas del borde.'),
    ('screech', 'Grito sónico', 'Espacio o clic izquierdo',
     'Aturde y daña a los enemigos cercanos, pero también hace ruido. Tiene enfriamiento.'),
    ('shield', 'ESCUDO', 'E, Shift o clic derecho',
     'Durante 5 segundos no recibes daño y repeles a quien te toque. Luego hay que esperar para reusarlo.'),
    ('sonar', 'SONAR', 'Q o clic central',
     'Una onda ilumina TODA la cueva y el minimapa. A cambio, los enemigos cercanos te ven por completo.'),
    ('wall', 'Cuidado con los choques', 'Vuela despacio junto a las paredes',
     'Chocar contra la roca hace ruido y atrae a las criaturas hacia ese punto.'),
    ('spider', 'El peligro crece', f'Rescata {GOAL} crías',
     'Los enemigos aparecen sin parar, y con cada rescate son más rápidos. ¡Llegan depredadores enormes!'),
]


def icon(s, kind, cx, cy, t):
    if kind == 'bat':
        ui.draw_bat(s, cx, cy + 2, t * 9, .8)
    elif kind == 'shield':
        r = 26 + int(2 * math.sin(t * 8))
        pygame.draw.circle(s, (40, 80, 110), (cx, cy), r)
        pygame.draw.circle(s, (170, 230, 255), (cx, cy), r, 3)
        ui.draw_bat(s, cx, cy + 1, t * 9, .45)
    elif kind in ('screech', 'sonar'):
        col = (150, 220, 255) if kind == 'screech' else C_SONAR
        for k in range(3):
            p = ((t * (1.2 if kind == 'screech' else .8) + k / 3) % 1)
            pygame.draw.circle(s, tuple(min(255, int(c * (1 - p) + 20)) for c in col), (cx, cy), int(6 + 26 * p), 2)
        ui.draw_bat(s, cx, cy + 1, t * 9, .3)
    elif kind == 'wall':
        pygame.draw.rect(s, (40, 34, 46), (cx + 6, cy - 26, 20, 52))
        pygame.draw.line(s, (100, 86, 110), (cx + 6, cy - 26), (cx + 6, cy + 26), 3)
        p = (t * 1.5) % 1
        pygame.draw.circle(s, tuple(min(255, int(c * (1 - p) + 20)) for c in C_IMPACT), (cx + 4, cy), int(4 + 24 * p), 2)
        ui.draw_bat(s, cx - 16, cy, t * 9, .4)
    else:
        ui.draw_scorpion(s, cx + 4, cy, t, math.pi * .9 + .15 * math.sin(t * 2), .95)


class InstructionsScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        self.panel = pygame.Surface((W - 80, H - 40), pygame.SRCALPHA)       # se crea una sola vez
        pygame.draw.rect(self.panel, (6, 4, 16, 205), self.panel.get_rect(), border_radius=18)
        pygame.draw.rect(self.panel, (110, 80, 170, 220), self.panel.get_rect(), 2, border_radius=18)

    def handle(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE, pygame.K_BACKSPACE):
            self.game.sounds.play('menu_select')
            self.game.goto('title')
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.game.sounds.play('menu_select')
            self.game.goto('title')

    def update(self, dt):
        self.t += dt
        self.game.backdrop.update(dt)

    def draw(self, screen):
        self.game.backdrop.draw(screen)
        screen.blit(self.panel, (40, 20))
        ui.text(screen, ui.F_L, 'INSTRUCCIONES', W // 2, 62, C_PURPLE, True)
        y = 108
        for kind, head, keys, desc in ENTRIES:
            icon(screen, kind, 100, y + 28, self.t)
            ui.text(screen, ui.F_M, head, 160, y - 2, (240, 232, 255))
            ui.text(screen, ui.F_S, keys, 160 + ui.F_M.size(head)[0] + 18, y + 4, C_GREEN)
            ui.text(screen, ui.F_XS, desc, 160, y + 34, (190, 180, 210))
            y += 80
        ui.text(screen, ui.F_XS, 'P: pausa   ·   B: brillo de la cueva   ·   Esc: volver al menú', W // 2, H - 38, (150, 135, 180), True)
        ui.text(screen, ui.F_S, 'Pulsa Esc o Enter para volver', W // 2, H - 60, (255, 255, 255), True)
