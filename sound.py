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

    # --- historia ---
    # latido de peligro: dos golpes graves
    def beat(t, p):
        e = lambda x: math.sin(TAU * 52 * x) * math.exp(-x * 22) if x >= 0 else 0
        return e(t) + .75 * e(t - .16)
    S['heartbeat'] = mk(.55, beat, .9)
    # susurro de madre deformado por el eco: ruido con sílabas ("ya-vuel-vo, qué-den-se quie-tas")
    syl = [(.0, .12), (.16, .3), (.34, .46), (.62, .74), (.78, .9), (.94, 1.04), (1.12, 1.3)]
    wn = [0.0]

    def whisper(t, p):
        wn[0] += .35 * (random.uniform(-1, 1) - wn[0])
        a = 0.0
        for s0, s1 in syl:
            for rep, g in ((0, 1.0), (.22, .45), (.44, .2)):       # el eco repite la frase más débil
                x = t - rep
                if s0 <= x <= s1:
                    a += g * math.sin(math.pi * (x - s0) / (s1 - s0))
        return wn[0] * a * (.6 + .4 * math.sin(TAU * 180 * t))
    S['whisper'] = mk(1.8, whisper, .55)
    # voz verdadera de Mullo: llamada melódica y clara
    S['call'] = mk(1.1, lambda t, p: (math.sin(TAU * (1500 + 900 * math.sin(TAU * 3 * t)) * t) * .6
                                      + .3 * math.sin(TAU * 3000 * t)) * math.sin(math.pi * p) ** .5
                   * (.5 + .5 * math.sin(TAU * 4 * t) ** 2), .4)
    S['dash'] = mk(.25, lambda t, p: random.uniform(-1, 1) * math.sin(math.pi * p) * (1 - p) * 1.4, .4)
    S['web'] = mk(.35, lambda t, p: (random.uniform(-1, 1) if random.random() < .3 else 0) * (1 - p), .55)
    S['story'] = mk(1.4, lambda t, p: (math.sin(TAU * 220 * t) + .6 * math.sin(TAU * 277 * t) + .45 * math.sin(TAU * 330 * t))
                    * min(1, p * 8) * (1 - p) ** 1.3, .32)

    ny = [0.0]

    def amb(t, p):
        ny[0] += .03 * (random.uniform(-1, 1) - ny[0])
        return .5 * math.sin(TAU * 55 * t) + .3 * math.sin(TAU * 82 * t + 1) + ny[0] * 1.6 * (.6 + .4 * math.sin(TAU * t / 6))
    S['amb'] = mk(6.0, amb, .5)
    S.update(build_ambients())
    S['chase'] = build_chase()
    # sala secreta: arpegio brillante;  medio corazón: dos notas dulces
    S['secret'] = mk(1.0, lambda t, p: sum(math.sin(TAU * f * t) * (1 if t > i * .12 else 0) * math.exp(-(t - i * .12) * 4)
                                          for i, f in enumerate((784, 988, 1175, 1568)) if t > i * .12) * .5, .4)
    S['heart'] = mk(.45, lambda t, p: math.sin(TAU * (880 if t < .15 else 1320) * t) * (1 - p) ** 1.2, .4)
    # el gigante despierta: estruendo grave que crece
    S['quake'] = mk(1.6, lambda t, p: (math.sin(TAU * 38 * t) + .6 * math.sin(TAU * 57 * t) + random.uniform(-1, 1) * .7)
                    * min(1, p * 3) * (1 - p) ** .6, .7)
    # "te vieron": dos notas cortas y agudas, fáciles de reconocer
    S['spotted'] = mk(.24, lambda t, p: (math.sin(TAU * (1046 if t < .1 else 1568) * t) * (1 - ((t % .1) / .1)) ** 1.5
                                         if t < .2 else 0.0), .42)
    # objetos interactivos: raíces secas que crujen, piedra que se hunde ("plop"), lata que suena ("clanc")
    rn = [0.0]

    def rustle(t, p):
        rn[0] += .6 * (random.uniform(-1, 1) - rn[0])
        crack = random.uniform(-1, 1) if random.random() < .08 else 0
        return (rn[0] * .7 + crack * .8) * math.sin(math.pi * p) ** .8 * (.6 + .4 * math.sin(TAU * 9 * t))
    S['rustle'] = mk(.45, rustle, .35)
    S['plop'] = mk(.3, lambda t, p: math.sin(TAU * (900 - 650 * min(1, p * 2.5)) * t) * math.exp(-p * 7)
                   + random.uniform(-1, 1) * .15 * math.exp(-p * 12), .4)

    def clang(t, p):
        partials = ((523, 1.0), (1236, .6), (1873, .45), (2741, .3), (3500, .2))
        return sum(a * math.sin(TAU * f * t + f) for f, a in partials) * math.exp(-p * 4.5) * .45 \
            + random.uniform(-1, 1) * math.exp(-t * 60) * .6
    S['clang'] = [mk(.7, clang, .42), mk(.7, lambda t, p: clang(t * 1.12, p), .42)]
    # susto amable: la arañita cae colgada de su hilo ("boing") y se asusta ella sola ("¡iik!")
    S['boing'] = mk(.55, lambda t, p: math.sin(TAU * (190 + 70 * math.sin(TAU * 11 * t) * (1 - p)) * t) * (1 - p) ** 1.5, .45)
    S['eek'] = mk(.22, chirp(1700, 3400, .22, env=lambda p: math.sin(math.pi * p) ** .5, vib=120), .3)
    S['zip'] = mk(.35, chirp(500, 2600, .35, env=lambda p: (1 - p) ** .6, noise=.15), .25)
    return S


def build_chase():
    """Música de persecución (huida de la mina): bajo insistente, arpegio tenso, bombo y platillo. 150 bpm, bucle de 6.4 s."""
    beat = .4
    bass = [55, 55, 65.41, 55, 73.42, 55, 65.41, 49.0] * 2           # dos compases de corcheas
    arp = [220, 261.6, 329.6, 261.6, 220, 246.9, 311.1, 246.9]
    total = 16 * beat

    def f(t, p):
        e = t % (beat / 2)
        i = int(t / (beat / 2)) % 16
        k = i // 8
        v = .55 * (1 if math.sin(TAU * bass[i] * (1 + .06 * k) * t) > 0 else -1) * math.exp(-e * 6) * .6
        ai = int(t / (beat / 4)) % 8
        ae = t % (beat / 4)
        v += .22 * math.sin(TAU * arp[ai] * (1.335 if k else 1) * t) * math.exp(-ae * 22)
        b = t % beat                                                   # bombo en cada tiempo
        v += .8 * math.sin(TAU * (110 - 70 * min(1, b * 12)) * b) * math.exp(-b * 16)
        if (t + beat / 2) % beat < .05:                                # platillo a contratiempo
            v += random.uniform(-1, 1) * .25 * (1 - ((t + beat / 2) % beat) / .05)
        return v * min(1.0, t / .01, (total - t) / .01)
    return mk(total, f, .42)


LOOP = 8.0                    # duración de los ambientes (frecuencias enteras: el bucle no "salta")


def _loop_env(t):
    return min(1.0, t / .03, (LOOP - t) / .03)


def build_ambients():
    """Un ambiente sonoro distinto para cada escenario."""
    A = {}
    rnd = random.Random(21)
    # Galerías de los Hongos: colchón cálido, aire suave y destellos como esporas que brillan
    chimes = [(rnd.uniform(.2, LOOP - 1.2), rnd.choice((880, 988, 1175, 1319, 1480))) for _ in range(7)]
    n1 = [0.0]

    def fungi(t, p):
        n1[0] += .02 * (random.uniform(-1, 1) - n1[0])
        v = (.26 * math.sin(TAU * 110 * t) * (.6 + .4 * math.sin(TAU * t / 8))
             + .18 * math.sin(TAU * 165 * t) * (.6 + .4 * math.sin(TAU * t / 4 + 1))
             + .1 * math.sin(TAU * 220 * t) + n1[0] * 1.2)
        for t0, f in chimes:
            x = t - t0
            if 0 <= x < 1.2:
                v += .22 * math.sin(TAU * f * x) * math.exp(-x * 3.5)
        return v * _loop_env(t)
    A['amb_fungi'] = mk(LOOP, fungi, .45)
    # Lago Negro: zumbido grave, agua que golpea suave y gotas con eco
    drips = [rnd.uniform(.2, LOOP - .8) for _ in range(6)]
    n2 = [0.0]

    def lake(t, p):
        n2[0] += .012 * (random.uniform(-1, 1) - n2[0])
        v = (.34 * math.sin(TAU * 55 * t) + .22 * math.sin(TAU * 73 * t) * (.5 + .5 * math.sin(TAU * t / 8))
             + n2[0] * 3.2 * (.55 + .45 * math.sin(TAU * t / 2)) ** 2)
        for t0 in drips:
            for d, g in ((0, .5), (.27, .22), (.52, .1)):
                x = t - t0 - d
                if 0 <= x < .25:
                    v += g * math.sin(TAU * (1500 - 900 * min(1, x * 10)) * x) * math.exp(-x * 14)
        return v * _loop_env(t)
    A['amb_lake'] = mk(LOOP, lake, .5)
    # Mina Vieja: viento que silba por los túneles, crujidos de madera y metal lejano
    creaks = [rnd.uniform(.3, LOOP - 1) for _ in range(3)]
    clanks = [rnd.uniform(.3, LOOP - 1) for _ in range(2)]
    n3 = [0.0]

    def mine(t, p):
        n3[0] += .05 * (random.uniform(-1, 1) - n3[0])
        gust = .5 + .5 * math.sin(TAU * t / 8 + 2)
        v = (n3[0] * 1.8 * gust + .07 * math.sin(TAU * 420 * t + 3 * math.sin(TAU * t / 4)) * gust
             + .22 * math.sin(TAU * 41 * t))
        for t0 in creaks:
            x = t - t0
            if 0 <= x < .7:
                v += .3 * (math.sin(TAU * (75 - 30 * x) * x) + random.uniform(-.5, .5)) * math.sin(math.pi * x / .7) \
                     * (.6 + .4 * math.sin(TAU * 31 * x))
        for t0 in clanks:
            x = t - t0
            if 0 <= x < .6:
                v += .14 * (math.sin(TAU * 620 * x) + .6 * math.sin(TAU * 1470 * x)) * math.exp(-x * 8)
        return v * _loop_env(t)
    A['amb_mine'] = mk(LOOP, mine, .5)
    return A


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
        self.amb_ch, self.amb_name = None, None
        self.music_ch, self.music_name = None, None
        pygame.mixer.set_num_channels(16)
        pygame.mixer.set_reserved(1)                 # el canal 0 queda para la música

    def play(self, name, pos=None, base=1.0):
        snd = self.S.get(name)
        if snd is None:
            return
        if isinstance(snd, list):
            snd = random.choice(snd)
        v = base
        if pos and self.listener:
            lx, ly = self.listener()
            v *= max(.12, 1 - math.dist(pos, (lx, ly)) / 650)
        ch = snd.play()
        if ch:
            ch.set_volume(min(1.0, v))

    def ambient(self, vol, name='amb'):
        """Ambiente en bucle; si cambia de escenario, cambia el sonido de fondo."""
        name = name if name in self.S else 'amb'
        if self.amb_ch and self.amb_ch.get_busy() and self.amb_name == name:
            self.amb_ch.set_volume(vol)
            return
        if self.amb_ch:
            self.amb_ch.stop()
        self.amb_name = name
        self.amb_ch = self.S[name].play(-1)
        if self.amb_ch:
            self.amb_ch.set_volume(vol)

    def music(self, name, vol=.55):
        """Música en su propio canal (no la corta el resto de los sonidos)."""
        if self.music_name == name and self.music_ch and self.music_ch.get_busy():
            return
        self.music_name = name
        self.music_ch = pygame.mixer.Channel(0)
        self.music_ch.play(self.S[name], loops=-1, fade_ms=600)
        self.music_ch.set_volume(vol)

    def stop_music(self, fade=900):
        if self.music_ch and self.music_name:
            self.music_ch.fadeout(fade)
        self.music_name = None

    def stop(self):
        pygame.mixer.stop()
        self.amb_ch = None
        self.music_name = None
