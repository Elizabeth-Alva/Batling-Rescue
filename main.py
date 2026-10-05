#!/usr/bin/env python3
"""BATLING RESCUE: Rescate en la cueva
Requisitos: pip install pygame
Todo (gráficos y sonidos) se genera por código; no necesita archivos externos."""
import pygame

from sound import init_mixer


def main():
    init_mixer()                      # antes de pygame.init()
    pygame.init()
    from game import Game
    Game().run()
    pygame.quit()


if __name__ == "__main__":
    main()
