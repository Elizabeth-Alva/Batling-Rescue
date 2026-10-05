"""Síntesis de sonidos por código y gestor con atenuación por distancia."""
import math
import os
import random
import re
from array import array

import pygame

from settings import IS_WEB, TAU

SR = 22050


def init_mixer():
    """Debe llamarse antes de pygame.init()."""
    pygame.mixer.pre_init(SR, -16, 1, 512)


def mk(dur, f, vol=0.6):
    n = int(SR * dur)
    a = array('h', (int(max(-1, min(1, f(i / SR, i / n))) * vol * 32767) for i in range(n)))
    return pygame.mixer.Sound(buffer=a.tobytes())


def chirp(f0, f1, dur, env=lambda p: math.sin(math.pi * p), noise=0.0, vib=0.0):
    k = (f1 - f0) / dur
    return lambda t, p: (math.sin(TAU * (f0 * t + .5 * k * t * t) + vib * math.sin(TAU * 30 * t) / 30 * TAU)
                         + noise * random.uniform(-1, 1)) * env(p)


def build_sounds():
    S, notes = {}, [523, 659, 784, 1047, 1319]
    S['squeak'] = [mk(.16, chirp(2600 + d, 4300 + d, .16, vib=60), .35) for d in (0, 400, -300)]
    S['screech'] = mk(.4, chirp(7000, 1800, .4, env=lambda p: (1 - p) ** .7, noise=.25, vib=80), .55)
    S['hit'] = mk(.3, lambda t, p: (math.sin(TAU * 110 * t * (1 - p * .5)) + random.uniform(-1, 1) * .6) * (1 - p) ** 2, .7)
    S['pickup'] = mk(.22, lambda t, p: math.sin(TAU * (500 + 500 * p) * t) * math.sin(math.pi * p), .4)
    S['deliver'] = mk(.7, lambda t, p: math.sin(TAU * notes[min(3, int(t / .15))] * t) * (1 - (t % .15) / .15 * .6) * (1 - p * .4), .45)
    S['win'] = mk(1.0, lambda t, p: math.sin(TAU * notes[min(4, int(t / .2))] * t) * (1 - (t % .2) / .2 * .5) * (1 - p * .3), .5)
    S['growl'] = mk(.6, lambda t, p: (math.sin(TAU * 68 * t) + .5 * math.sin(TAU * 101 * t) + random.uniform(-1, 1) * .4)
                    * (.6 + .4 * math.sin(TAU * 22 * t)) * math.sin(math.pi * p), .6)

    def drip(t, p):
        e = lambda x: math.sin(TAU * (1300 - 800 * min(1, x * 10)) * x) * math.exp(-x * 16) if x >= 0 else 0
        return e(t) + .35 * e(t - .2)
    S['drip'] = mk(.5, drip, .3)
    S['click'] = mk(.04, lambda t, p: random.uniform(-1, 1) * (1 - p), .4)
    S['die'] = mk(.35, chirp(900, 120, .35, env=lambda p: 1 - p, noise=.3), .5)
    S['lose'] = mk(1.3, chirp(400, 50, 1.3, env=lambda p: (1 - p) ** 1.5, noise=.15), .6)

    # --- nuevos ---
    # choque contra la pared: golpe grave con crujido de roca (dos variantes)
    S['impact'] = [mk(.26, lambda t, p, f=f: (math.sin(TAU * f * t * (1 - p * .45)) + random.uniform(-1, 1) * .55)
                      * (1 - p) ** 2.3, .75) for f in (70, 95)]
    # sonar: barrido ascendente con eco
    S['sonar'] = mk(1.0, lambda t, p: (math.sin(TAU * (900 * t + 1350 * t * t / 1.0))
                                         + .45 * math.sin(TAU * (900 * (t - .18) + 1350 * (t - .18) ** 2) if t > .18 else 0))
                    * min(1, p * 25) * (1 - p) ** .8, .5)
    S['alarm'] = mk(.5, lambda t, p: math.sin(TAU * (880 if int(t / .12) % 2 == 0 else 660) * t) * (1 - p * .5), .3)
    S['levelup'] = mk(.8, chirp(220, 90, .8, env=lambda p: math.sin(math.pi * p) ** .7, noise=.08), .55)
    S['menu_move'] = mk(.06, lambda t, p: math.sin(TAU * 660 * t) * (1 - p), .25)
    S['menu_select'] = mk(.2, lambda t, p: math.sin(TAU * (660 if t < .08 else 990) * t) * (1 - p * .7), .35)

    # escudo
    S['shield_on'] = mk(.45, chirp(300, 1400, .45, env=lambda p: math.sin(math.pi * p) ** .6), .4)
    S['shield_off'] = mk(.4, chirp(1100, 200, .4, env=lambda p: (1 - p) ** 1.2), .35)
    S['shield_hit'] = mk(.22, lambda t, p: (math.sin(TAU * 1500 * t) + .6 * math.sin(TAU * 2250 * t)) * math.exp(-p * 7), .45)
    # rugido de depredador
    S['roar'] = mk(1.0, lambda t, p: (math.sin(TAU * (60 + 25 * math.sin(TAU * 5 * t)) * t) + .7 * math.sin(TAU * 95 * t)
                                      + random.uniform(-1, 1) * .5) * math.sin(math.pi * p) ** .6, .7)

    ny = [0.0]

    def amb(t, p):
        ny[0] += .03 * (random.uniform(-1, 1) - ny[0])
        return .5 * math.sin(TAU * 55 * t) + .3 * math.sin(TAU * 82 * t + 1) + ny[0] * 1.6 * (.6 + .4 * math.sin(TAU * t / 6))
    S['amb'] = mk(6.0, amb, .5)
    return S


SOUND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sounds')


def load_sounds(folder=SOUND_DIR):
    """Carga los .ogg precalculados (tools/export_sounds.py). nombre_0.ogg, nombre_1.ogg... forman una lista."""
    S = {}
    for fn in sorted(os.listdir(folder)):
        stem, ext = os.path.splitext(fn)
        if ext != '.ogg':
            continue
        snd = pygame.mixer.Sound(os.path.join(folder, fn))
        m = re.match(r'^(.*)_(\d+)$', stem)
        if m:
            S.setdefault(m.group(1), []).append(snd)
        else:
            S[stem] = snd
    return S


def get_sounds():
    """En el navegador (o si existe la carpeta sounds/ y BATLING_SOUND_FILES=1) usa los archivos; si no, sintetiza."""
    if (IS_WEB or os.environ.get('BATLING_SOUND_FILES')) and os.path.isdir(SOUND_DIR):
        S = load_sounds()
        if 'amb' in S:
            return S
    return build_sounds()


class SoundManager:
    """Reproduce sonidos con volumen según la distancia al 'oyente' (el murciélago)."""

    def __init__(self):
        self.S = get_sounds()
        self.listener = None            # callable -> (x, y) o None
        self.amb_ch = None

    def play(self, name, pos=None, base=1.0):
        snd = self.S[name]
        if isinstance(snd, list):
            snd = random.choice(snd)
        v = base
        if pos and self.listener:
            lx, ly = self.listener()
            v *= max(.12, 1 - math.dist(pos, (lx, ly)) / 650)
        ch = snd.play()
        if ch:
            ch.set_volume(min(1.0, v))

    def ambient(self, vol):
        if self.amb_ch and self.amb_ch.get_busy():
            self.amb_ch.set_volume(vol)
            return
        self.amb_ch = self.S['amb'].play(-1)
        if self.amb_ch:
            self.amb_ch.set_volume(vol)

    def stop(self):
        pygame.mixer.stop()
        self.amb_ch = None
