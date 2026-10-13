"""Pantallas superpuestas del nivel: pausa, derrota y nivel completado."""
import pygame

import ui
from settings import W, H, GOAL, C_GREEN, C_RED, C_PURPLE, C_GOLD, C_PUP


_VEIL = None


def draw_overlay(screen, g):
    global _VEIL
    if _VEIL is None:                                   # el velo se crea una sola vez
        _VEIL = pygame.Surface((W, H), pygame.SRCALPHA)
        _VEIL.fill((0, 0, 10, 195))
    screen.blit(_VEIL, (0, 0))
    cx, state, cfg = W // 2, g.state, g.cfg
    if state == 'pause':
        ui.text(screen, ui.F_L, 'PAUSA', cx, H // 2 - 70, center=True)
        ui.text(screen, ui.F_S, f'{cfg["act"]} · {cfg["name"]}', cx, H // 2 - 18, (200, 190, 230), True)
        ui.text(screen, ui.F_S, 'P / Enter: continuar     M: mapa     B: brillo     Esc: menú principal',
                cx, H // 2 + 30, (190, 180, 210), True)
    elif state == 'over':
        if g.lose_reason == 'dawn':
            ui.text(screen, ui.F_L, 'LA NOCHE SE ACABA', cx, 220, C_GOLD, True)
            ui.text(screen, ui.F_S, 'La colonia se prepara para partir y los chillidos se apagan en lo profundo.',
                    cx, 290, (220, 210, 235), True)
        else:
            ui.text(screen, ui.F_L, 'MULLO NO PUEDE MÁS', cx, 220, C_RED, True)
            ui.text(screen, ui.F_S, 'Agotada, se refugia en lo alto. Pero sus crías siguen allá abajo.',
                    cx, 290, (220, 210, 235), True)
        ui.text(screen, ui.F_M, f'Crías a salvo: {g.rescued}/{GOAL}', cx, 340, C_PUP, True)
        ui.text(screen, ui.F_M, 'R / Enter: intentar de nuevo este nivel', cx, 400, C_GREEN, True)
        ui.text(screen, ui.F_S, 'Esc: menú principal', cx, 445, (190, 180, 210), True)
    elif state == 'clear':
        k = min(1, g.clear_t / .6)
        ui.text(screen, ui.F_S, f'{cfg["act"].upper()} · COMPLETADO', cx, 210, C_GOLD, True)
        ui.text(screen, ui.F_L, cfg['name'], cx, 260, (240, 232, 255), True)
        ui.text(screen, ui.F_M, f'Crías a salvo: {g.rescued}/{GOAL}', cx, 330, C_PUP, True)
        ui.text(screen, ui.F_S, f'Tiempo: {int(g.t // 60)}:{int(g.t % 60):02d}', cx, 370, (210, 200, 230), True)
        for i in range(GOAL):
            ui.pup_icon(screen, cx - 9 * 22 // 2 + i * 22 - 11 + 11, 410, 'safe' if i < g.rescued else 'lost', g.clear_t + i)
        if k >= 1 and g.clear_t > 1.2:
            ui.text(screen, ui.F_S, 'Enter: continuar la historia', cx, 460, C_PURPLE, True)
