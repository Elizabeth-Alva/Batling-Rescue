#!/usr/bin/env python3
"""Exporta los sonidos sintetizados a .ogg (pygbag no admite .wav y sintetizar en el navegador es lento).

Uso:  python tools/export_sounds.py [carpeta_destino]     (por defecto ./sounds)
Requiere:  pip install pygame soundfile numpy
Las listas de variantes se guardan como nombre_0.ogg, nombre_1.ogg...
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pygame  # noqa: E402
import soundfile as sf  # noqa: E402

from sound import SR, build_sounds, init_mixer  # noqa: E402


def export(dest):
    init_mixer()
    pygame.init()
    os.makedirs(dest, exist_ok=True)
    count = 0
    for name, snd in build_sounds().items():
        variants = snd if isinstance(snd, list) else [snd]
        for i, s in enumerate(variants):
            fn = f"{name}_{i}.ogg" if isinstance(snd, list) else f"{name}.ogg"
            data = np.frombuffer(s.get_raw(), dtype=np.int16)
            sf.write(os.path.join(dest, fn), data, SR, format="OGG", subtype="VORBIS")
            count += 1
    return count


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "sounds"
    print(f"{export(out)} sonidos exportados a {out}")
