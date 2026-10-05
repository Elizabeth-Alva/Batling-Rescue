"""Pantalla de título con menú: Jugar / Instrucciones / Salir."""
import math

import pygame

import ui
from scenes import Scene
from settings import W, H


class TitleScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.menu = ui.Menu(['Jugar', 'Instrucciones', 'Salir'], W // 2, 350)
        self.t = 0.0
        self.glow = ui.make_glow(ui.F_XL, 'BATLING RESCUE', (150, 90, 255), blur=6, pad=40)
        self.title = ui.F_XL.render('BATLING RESCUE', True, (232, 218, 255))
        self.shadow = ui.F_XL.render('BATLING RESCUE', True, (40, 20, 80))

    def enter(self):
        self.game.sounds.ambient(.3)

    def handle(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.game.running = False
            return
        choice = self.menu.handle(ev, self.game.sounds)
        if choice == 0:
            self.game.goto('play')
        elif choice == 1:
            self.game.goto('instructions')
        elif choice == 2:
            self.game.running = False

    def update(self, dt):
        self.t += dt
        self.game.backdrop.update(dt)

    def draw(self, screen):
        self.game.backdrop.draw(screen)
        cx, cy = W // 2, 150
        pulse = .55 + .45 * math.sin(self.t * 2.2)
        self.glow.set_alpha(int(120 + 120 * pulse))
        screen.blit(self.glow, self.glow.get_rect(center=(cx, cy)))
        screen.blit(self.shadow, self.shadow.get_rect(center=(cx + 4, cy + 5)))
        screen.blit(self.title, self.title.get_rect(center=(cx, cy)))
        ui.text(screen, ui.F_M, 'Rescate en la cueva', cx, 222, (210, 190, 245), True)
        ui.text(screen, ui.F_XS, 'Un murciélago, una cueva sin luz y crías que esperan en la oscuridad',
                cx, 254, (140, 125, 170), True)
        self.menu.draw(screen, 1 / 60)
        ui.text(screen, ui.F_XS, '↑ ↓ / ratón: elegir        Enter / clic: aceptar', cx, H - 28, (130, 118, 160), True)
