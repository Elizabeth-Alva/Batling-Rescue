"""Pantallas superpuestas del nivel: pausa, derrota (GAME OVER) y nivel superado."""
import pygame

import scores
import ui
from scenes.results import draw_game_over, draw_level_clear
from settings import W, H


_VEIL = None


def _touch(g):
    t = getattr(g.game, 'touch', None)
    return t is not None and t.active


def _menu_btn(screen, g):
    r = g.MENU_BTN
    pygame.draw.rect(screen, (40, 26, 70), r, border_radius=14)
    pygame.draw.rect(screen, (200, 160, 255), r, 2, border_radius=14)
    ui.text(screen, ui.F_S, 'Menú principal', r.centerx, r.centery, (240, 232, 255), True)


def draw_overlay(screen, g):
    global _VEIL
    dt = getattr(g, 'ui_dt', 1 / 60)
    if g.state == 'over':                               # GAME OVER y NIVEL SUPERADO traen su propio velo
        return draw_game_over(screen, g, dt)
    if g.state == 'clear':
        return draw_level_clear(screen, g, dt)
    if _VEIL is None:                                   # el velo se crea una sola vez
        _VEIL = pygame.Surface((W, H), pygame.SRCALPHA)
        _VEIL.fill((0, 0, 10, 195))
    screen.blit(_VEIL, (0, 0))
    cx, cfg = W // 2, g.cfg
    if g.state == 'pause':
        ui.text(screen, ui.F_L, 'PAUSA', cx, H // 2 - 70, center=True)
        ui.text(screen, ui.F_S, f'{cfg["act"]} · {cfg["name"]}', cx, H // 2 - 18, (200, 190, 230), True)
        prog = getattr(g.game, 'progress', {}) or {}
        times = f'Tiempo del nivel: {scores.fmt(g.t)}'
        if prog.get('full_run'):
            times = f'Tiempo total: {scores.fmt(prog.get("play_time", 0))}     ·     ' + times
        ui.text(screen, ui.F_XS, times + '   (el reloj está detenido)', cx, H // 2 + 12, (255, 215, 150), True)
        if _touch(g):
            ui.text(screen, ui.F_S, 'Toca la pantalla para continuar', cx, H // 2 + 50, (190, 180, 210), True)
            _menu_btn(screen, g)
        else:
            ui.text(screen, ui.F_S, 'P / Enter: continuar     M: mapa     B: brillo     Esc: menú principal',
                    cx, H // 2 + 50, (190, 180, 210), True)
