"""Pantallas superpuestas: pausa, derrota y victoria."""
import pygame

import ui
from settings import W, H, GOAL, C_GREEN, C_RED, C_PURPLE


def draw_overlay(screen, state, rescued, t):
    v = pygame.Surface((W, H), pygame.SRCALPHA)
    v.fill((0, 0, 10, 195))
    screen.blit(v, (0, 0))
    cx = W // 2
    if state == 'pause':
        ui.text(screen, ui.F_L, 'PAUSA', cx, H // 2 - 20, center=True)
        ui.text(screen, ui.F_S, 'P: continuar        B: brillo        Esc: menú principal', cx, H // 2 + 30, (190, 180, 210), True)
    elif state == 'over':
        ui.text(screen, ui.F_L, 'LA CUEVA TE VENCIÓ', cx, 240, C_RED, True)
        ui.text(screen, ui.F_M, f'Crías rescatadas: {rescued}/{GOAL}', cx, 315, center=True)
        ui.text(screen, ui.F_M, 'R para reintentar', cx, 380, C_GREEN, True)
        ui.text(screen, ui.F_S, 'Esc: menú principal', cx, 425, (190, 180, 210), True)
    elif state == 'win':
        ui.text(screen, ui.F_L, '¡TODAS A SALVO!', cx, 240, C_GREEN, True)
        ui.text(screen, ui.F_M, 'Las crías vuelven a casa gracias a ti.', cx, 315, center=True)
        ui.text(screen, ui.F_S, f'Tiempo: {int(t // 60)}:{int(t % 60):02d}', cx, 355, (210, 200, 230), True)
        ui.text(screen, ui.F_M, 'R para jugar de nuevo', cx, 405, C_PURPLE, True)
        ui.text(screen, ui.F_S, 'Esc: menú principal', cx, 450, (190, 180, 210), True)
