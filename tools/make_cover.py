#!/usr/bin/env python3
"""Exporta el material promocional dibujado por código: portada, banner para itch.io e icono.

Uso:  python tools/make_cover.py            (deja los PNG en assets/promo/)
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pygame  # noqa: E402


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    import ui
    from art import Cover, bat_sil, glow
    from scenes.title import draw_cover
    from settings import W, H
    ui.init_fonts()
    out = os.path.join(ROOT, 'assets', 'promo')
    os.makedirs(out, exist_ok=True)
    s = pygame.Surface((W, H))
    draw_cover(s, 2.35, Cover())
    ui.text(s, ui.F_S, 'Acción y rescate en 2D  ·  3 actos, una sola noche  ·  E10+', W // 2, H - 52, (235, 220, 255), True)
    ui.text(s, ui.F_XS, 'Python 3 + Pygame  ·  Equipo 10IDS2', W // 2, H - 26, (170, 155, 200), True)
    pygame.image.save(s, os.path.join(out, 'portada.png'))
    # banner de itch.io (630 x 500): recorte centrado de la portada
    k = 500 / H
    big = pygame.transform.smoothscale(s, (int(W * k), 500))
    banner = big.subsurface(((big.get_width() - 630) // 2, 0, 630, 500))
    pygame.image.save(banner, os.path.join(out, 'banner_itch.png'))
    # icono (256 x 256): Mullo sobre un círculo de luz
    ic = pygame.Surface((256, 256))
    ic.fill((14, 10, 34))
    ic.blit(glow(128, (150, 90, 255), .9), (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    bat_sil(ic, 128, 140, 1.2, 2.0, (6, 4, 12), (210, 170, 255), (255, 214, 110))
    pygame.image.save(ic, os.path.join(out, 'icono.png'))
    print(f'Listo: {out}')


if __name__ == '__main__':
    main()
