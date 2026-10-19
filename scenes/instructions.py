"""Pantalla de instrucciones."""
import math

import pygame

import ui
from scenes import Scene
from settings import W, H, C_PURPLE, C_GREEN, C_GOLD, C_PUP

ENTRIES = [
    ('bat', 'Volar y rescatar', 'WASD / Flechas',
     'Eres Mullo. Lleva a cada cría al nido (brillo dorado, arriba): ahí nadie entra y recuperas una vida.'),
    ('screech', 'Grito sónico', 'Espacio o clic izq.',
     'Aturde a los bichos, rompe telarañas y MARCA A LAS CRÍAS EN EL MINIMAPA. Pero hace ruido.'),
    ('dash', 'Impulso', 'Shift',
     'Un empujón veloz para escapar o cruzar tramos abiertos. También se recarga.'),
    ('shield', 'Escudo', 'E o clic derecho',
     '5 segundos sin recibir daño; repele a quien te toque. Luego hay que esperar.'),
    ('map', 'Minimapa', 'Siempre visible · M amplía',
     'Es la memoria de Mullo: lo explorado, el nido y las crías que marcó tu último grito.'),
    ('enemies', 'Arañas, escarabajos y cazadores', 'Oyen los chillidos',
     'No son malvados: tienen hambre. Chocar con la roca hace ruido. Ningún bicho cruza el agua.'),
    ('dawn', 'Antes del amanecer', '3 actos · 10 crías',
     'Cada nivel tiene su reloj. Antes del amanecer la colonia se va, con Mullo o sin ella.'),
]


def icon(s, kind, cx, cy, t):
    if kind == 'bat':
        ui.draw_mullo(s, cx, cy + 2, t * 9, .8)
    elif kind == 'shield':
        r = 24 + int(2 * math.sin(t * 8))
        pygame.draw.circle(s, (40, 80, 110), (cx, cy), r)
        pygame.draw.circle(s, (170, 230, 255), (cx, cy), r, 3)
        ui.draw_bat(s, cx, cy + 1, t * 9, .45)
    elif kind == 'screech':
        for k in range(3):
            p = ((t * 1.2 + k / 3) % 1)
            pygame.draw.circle(s, tuple(min(255, int(c * (1 - p) + 20)) for c in (150, 220, 255)), (cx, cy), int(6 + 26 * p), 2)
        ui.draw_bat(s, cx, cy + 1, t * 9, .3)
    elif kind == 'dash':
        for k in range(4):
            pygame.draw.line(s, (255, 200, 120), (cx - 30 + k * 4, cy - 6 + k * 4), (cx - 8 + k * 4, cy - 6 + k * 4), 2)
        ui.draw_bat(s, cx + 10 + 4 * math.sin(t * 6), cy, t * 14, .45)
    elif kind == 'map':
        pygame.draw.rect(s, (10, 8, 20), (cx - 28, cy - 20, 56, 40), border_radius=4)
        pygame.draw.rect(s, (110, 95, 140), (cx - 28, cy - 20, 56, 40), 1, border_radius=4)
        pygame.draw.circle(s, C_GOLD, (cx - 16, cy - 10), 3)
        pygame.draw.circle(s, (255, 235, 120), (cx + 2, cy + 4), 2)
        if int(t * 3) % 2:
            pygame.draw.circle(s, C_PUP, (cx + 18, cy + 10), 3)
    elif kind == 'enemies':
        ui.draw_spider(s, cx - 18, cy, t, .6, 0)
        ui.draw_beetle(s, cx + 18, cy, t, -1.6, .7)
    else:
        for i in range(30):
            f = i / 29
            pygame.draw.line(s, (int(20 + 235 * f), int(30 + 120 * f), int(90 - 20 * f)), (cx - 28 + i * 2, cy - 14), (cx - 28 + i * 2, cy + 14), 2)
        ui.draw_bat(s, cx, cy, t * 9, .35, (10, 6, 14), (14, 8, 18), (60, 40, 70))


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
        y = 100
        for kind, head, keys, desc in ENTRIES:
            icon(screen, kind, 100, y + 22, self.t)
            ui.text(screen, ui.F_S, head, 160, y, (240, 232, 255))
            ui.text(screen, ui.F_XS, keys, 160 + ui.F_S.size(head)[0] + 16, y + 3, C_GREEN)
            ui.text(screen, ui.F_XS, desc, 160, y + 26, (190, 180, 210))
            y += 66
        if getattr(self.game, 'touch', None) and self.game.touch.active:
            ui.text(screen, ui.F_XS, 'En el teléfono: joystick a la izquierda · GRITO, IMPULSO y ESCUDO a la derecha · Toca para volver',
                    W // 2, H - 36, (200, 190, 225), True)
        else:
            ui.text(screen, ui.F_XS, 'P / Esc: pausa   ·   B: brillo de la cueva   ·   Pulsa Esc o Enter para volver', W // 2, H - 36, (200, 190, 225), True)
