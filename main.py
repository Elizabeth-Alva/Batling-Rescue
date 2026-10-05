#!/usr/bin/env python3
"""BATLING RESCUE: Rescate en la cueva
Escritorio:  pip install pygame  y  python main.py
Navegador:   se compila con pygbag (ver tools/build_web.py y LEEME.txt).
Todo (gráficos y sonidos) se genera por código; no necesita archivos externos."""
import asyncio

import pygame

from sound import init_mixer


async def main():
    init_mixer()                      # antes de pygame.init()
    pygame.init()
    from game import Game
    await Game().run()
    pygame.quit()


asyncio.run(main())                   # sin "if __name__": pygbag necesita esta llamada en el nivel superior
