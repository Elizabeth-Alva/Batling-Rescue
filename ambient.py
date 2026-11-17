"""Ambiente de cada acto (propuesta 3.4: «en cada acto baja a un lugar peor»).

  Acto I  · Galerías de los Hongos: esporas que brillan y suben despacio desde los hongos luminosos.
  Acto III· Mina Vieja: polvo que flota en la luz de Mullo y tierrita que cae de las vigas viejas
            (los faroles de la mina están apagados: es una mina abandonada).
  Acto II · Lago Negro: jirones de niebla muy tenues que se arrastran sobre el agua (LakeWisps), la humedad
            que frena a Mullo; se abren a su alrededor para no taparle nada.

Detalles que reaccionan a Mullo (no cambian la historia ni las reglas, solo dan qué mirar):
  · FungusPuffs   — los hongos sueltan una nubecita de esporas brillantes cuando Mullo los roza.
  · WebSway       — las telarañas de las esquinas se mecen cuando Mullo pasa cerca.
  · CrystalGlints — los cristales destellan cuando les llega la luz de Mullo.
  · ShellGlints   — el caparazón «azul petróleo con brillo metálico» de los escarabajos destella con su luz.
  · WaterWake     — estela de ondas cuando Mullo vuela sobre el agua, y su reflejo oscuro (con los ojos ámbar).
  · MulloFx       — respira agitada tras un impulso o una persecución y se sacude el polvo si choca varias veces.
  · CoalBits      — trocitos de carbón que saltan cuando una vagoneta frena o choca.
  · WetWings      — sobre el agua «el aire húmedo frena a Mullo» (propuesta 3.5) y se nota: gotitas en sus alas
                    que gotean al lago y vaho alrededor de ella (sin niebla en la pantalla).
  · MoltSway      — la piel vieja de Xolthar se mece con la corriente de aire de la mina.
  · BurrowFx      — Xolthar rompe el piso: agujeros que quedan, grietas de aviso, retumbo bajo tierra y piedras.
  (El polvo de la mina además se aparta girando con el aire de las alas de Mullo.)

Pensado para no cargar el rendimiento: un número fijo de partículas que se reciclan (nunca se crean listas nuevas
por cuadro), solo alrededor de la cámara, sprites pequeños hechos una vez, y la mitad de partículas en el navegador.
"""
import math
import random

import pygame

from settings import IS_WEB, VIEW_W as W, VIEW_H as H, TILE      # (lo que se ve del mundo)
from lighting import FUNGUS_GLOW

import decor
import ui

_SPRITES = {}


def _glow(r, col):
    """Puntito con halo (se suma a la imagen: brilla en la oscuridad)."""
    key = (r, col)
    g = _SPRITES.get(key)
    if g is None:
        g = _SPRITES[key] = pygame.Surface((2 * r, 2 * r))
        for i in range(r, 0, -1):
            k = (1 - i / r) ** 2.2
            pygame.draw.circle(g, tuple(int(c * k) for c in col), (r, r), i)
    return g


class ActAmbience:
    SPORES = 30                 # Acto I
    DUST = 22                   # Acto III: polvo en la luz
    GRIT = 14                   # Acto III: tierrita que cae de las vigas

    def __init__(self, theme, cave):
        self.theme, self.cave = theme, cave
        k = .5 if IS_WEB else 1.0
        self.p = []                                         # [x, y, vx, vy, edad, vida, fase, tipo]
        if theme == 'fungi':
            self.p = [self._dead('spore') for _ in range(int(self.SPORES * k))]
        elif theme == 'mine':
            self.p = [self._dead('dust') for _ in range(int(self.DUST * k))] + \
                     [self._dead('grit') for _ in range(int(self.GRIT * k))]
        self.spore_img = [[_glow(r, tuple(int(v * f) for v in col)) for f in (.35, .65, 1.0)]
                          for r, col in ((6, (150, 255, 210)), (5, (190, 255, 170)))]
        self.grit_t = 0.0

    @staticmethod
    def _dead(kind):
        return [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, random.uniform(0, 6.3), kind]   # edad >= vida: se recicla

    # ------------------------------------------------------------------ reciclar
    def _respawn(self, q, cam, bat):
        kind = q[7]
        x0, y0 = cam.x - 60, cam.y - 60
        if kind == 'spore':                                # nace en un hongo cercano (si hay alguno a la vista)
            fungi = self.cave.fungi
            spot = None
            for _ in range(5):
                if not fungi:
                    break
                f = fungi[random.randrange(len(fungi))]
                if cam.visible(f[0], f[1], 40):
                    spot = f
                    break
            if spot is None:
                spot = (x0 + random.uniform(0, W + 120), y0 + random.uniform(0, H + 120))
            q[0], q[1] = spot[0] + random.uniform(-10, 10), spot[1] + random.uniform(-6, 6)
            q[2], q[3] = random.uniform(-6, 6), random.uniform(-16, -7)
            q[5] = random.uniform(4.0, 7.5)
        elif kind == 'dust':                               # flota cerca de Mullo (se ve en su luz)
            a, r = random.uniform(0, 6.3), random.uniform(20, 230)
            q[0], q[1] = bat.x + math.cos(a) * r, bat.y + math.sin(a) * r
            q[2], q[3] = random.uniform(-7, 7), random.uniform(-4, 6)
            q[5] = random.uniform(3.0, 6.0)
        else:                                              # 'grit': cae de una viga visible
            beams = [b for b in self.cave.beams if cam.visible((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, 30)]
            if not beams:
                q[4], q[5] = 0.0, random.uniform(.6, 1.6)  # nada que soltar: espera un rato
                q[0] = q[1] = -9999
                return
            b = random.choice(beams)
            f = random.random()
            q[0], q[1] = b[0] + (b[2] - b[0]) * f, b[1] + (b[3] - b[1]) * f
            q[2], q[3] = random.uniform(-4, 4), random.uniform(20, 40)
            q[5] = random.uniform(.7, 1.3)
        q[4] = 0.0

    # ------------------------------------------------------------------ cada cuadro
    SWIRL_R = 70
    SWIRL_R2 = SWIRL_R * SWIRL_R

    def update(self, dt, cam, bat, shake=0.0):
        if not self.p:
            return
        sp = math.hypot(bat.vx, bat.vy)
        wing = min(1.5, sp / 160) if sp > 30 else 0.0
        for q in self.p:
            q[4] += dt
            if q[4] >= q[5] or not cam.visible(q[0], q[1], 140):
                if q[7] == 'grit' and q[4] < q[5] and q[0] == -9999:
                    continue                                # esperando una viga a la vista
                self._respawn(q, cam, bat)
                continue
            q[6] += dt
            if q[7] == 'spore':
                q[0] += (q[2] + math.sin(q[6] * 1.3) * 7) * dt
                q[1] += q[3] * dt
            elif q[7] == 'dust':
                if wing:                                    # el aire de las alas de Mullo lo aparta girando
                    dx, dy = q[0] - bat.x, q[1] - bat.y
                    d2 = dx * dx + dy * dy
                    if 16 < d2 < self.SWIRL_R2:
                        d = math.sqrt(d2)
                        k = (1 - d / self.SWIRL_R) * wing * dt
                        q[2] += (dx / d * 90 - dy / d * 70) * k     # hacia afuera y de lado (remolino)
                        q[3] += (dy / d * 90 + dx / d * 70) * k
                q[2] *= 1 - min(1.0, 1.6 * dt)               # y se va calmando
                q[3] *= 1 - min(1.0, 1.6 * dt)
                q[0] += (q[2] + math.sin(q[6]) * 3) * dt
                q[1] += (q[3] + math.cos(q[6] * .8) * 2) * dt
            else:
                q[3] += 260 * dt                           # cae
                q[0] += q[2] * dt
                q[1] += q[3] * dt
        if shake > .15 and self.theme == 'mine':           # cuando la mina retumba cae más tierra
            for q in self.p:
                if q[7] == 'grit' and q[0] == -9999:
                    q[4] = q[5]

    def draw(self, c, cam, bat, reach):
        """Se dibuja después de la oscuridad: las esporas brillan solas; el polvo y la tierra solo se ven en la luz."""
        for x, y, vx, vy, age, life, ph, kind in self.p:
            if x == -9999:
                continue
            fade = min(1.0, age / .6, (life - age) / .8)
            if fade <= 0:
                continue
            sx, sy = x - cam.x, y - cam.y
            if kind == 'spore':                            # brillo que late (3 intensidades ya hechas)
                k = fade * (.65 + .35 * math.sin(ph * 3))
                lv = min(2, int(k * 3))
                if k > .1:
                    img = self.spore_img[int(ph * 7) % 2][lv]
                    c.blit(img, (sx - img.get_width() // 2, sy - img.get_height() // 2), special_flags=pygame.BLEND_RGB_ADD)
                continue
            d = math.hypot(x - bat.x, y - bat.y)
            lit = max(0.0, 1 - d / reach)
            if lit <= 0:
                continue
            if kind == 'dust':
                g = int(150 * lit * fade * (.6 + .4 * math.sin(ph * 2)))
                if g > 6:
                    c.fill((g, int(g * .86), int(g * .66)), (int(sx), int(sy), 2, 2))
            else:
                g = int(130 * lit * fade)
                if g > 6:
                    pygame.draw.line(c, (g, int(g * .8), int(g * .6)), (sx, sy - 2), (sx, sy + 1), 2)


# ====================================================================== hongos que sueltan esporas al rozarlos
class FungusPuffs:
    """Cuando Mullo roza un hongo luminoso sale una nubecita de esporas que brillan y se apagan.
    Los hongos se buscan en una rejilla (solo las celdas alrededor de Mullo) y las esporas salen de un
    grupo fijo que se recicla: no se crean listas ni superficies durante el juego."""
    CELL = 128
    TOUCH = 26                                     # px: qué tan cerca hay que pasar
    REST = 2.5                                     # s: el mismo hongo no vuelve a soltar esporas enseguida

    def __init__(self, fungi, theme):
        self.fungi = list(fungi)
        self.grid = {}
        for i, (x, y) in enumerate(self.fungi):
            self.grid.setdefault((int(x) // self.CELL, int(y) // self.CELL), []).append(i)
        self.ready = [0.0] * len(self.fungi)
        self.t = 0.0
        n = 14 if IS_WEB else 30
        self.p = [[0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0] for _ in range(n)]    # x, y, vx, vy, edad, vida, fase
        col = FUNGUS_GLOW.get(theme, (70, 230, 170))
        self.img = [_glow(5, tuple(int(v * f) for v in col)) for f in (.3, .6, 1.0)]
        self.per = 3 if IS_WEB else 6               # esporas por roce

    def update(self, dt, bat):
        self.t += dt
        for q in self.p:
            if q[4] < q[5]:
                q[4] += dt
                q[6] += dt
                q[2] *= 1 - min(1.0, 2.6 * dt)       # frenan rápido y luego flotan
                q[3] = q[3] * (1 - min(1.0, 2.6 * dt)) - 9 * dt
                q[0] += (q[2] + math.sin(q[6] * 2.3) * 5) * dt
                q[1] += q[3] * dt
        if not self.fungi or math.hypot(bat.vx, bat.vy) < 35:
            return
        cx, cy = int(bat.x) // self.CELL, int(bat.y) // self.CELL
        for gx in (cx - 1, cx, cx + 1):
            for gy in (cy - 1, cy, cy + 1):
                for i in self.grid.get((gx, gy), ()):
                    if self.ready[i] > self.t:
                        continue
                    fx, fy = self.fungi[i]
                    if abs(fx - bat.x) < self.TOUCH and abs(fy - bat.y) < self.TOUCH:
                        self.ready[i] = self.t + self.REST
                        self._burst(fx, fy, bat)

    def burst_at(self, x, y):
        """Esporas sin que Mullo lo roce (p. ej. le cayó una gota encima)."""
        self._burst(x, y, None)

    def near(self, x, y, r):
        """Hongo más cercano a (x, y) dentro de r, o None."""
        best, bd = None, r * r
        for gx in (int(x) // self.CELL - 1, int(x) // self.CELL, int(x) // self.CELL + 1):
            for gy in (int(y) // self.CELL - 1, int(y) // self.CELL, int(y) // self.CELL + 1):
                for i in self.grid.get((gx, gy), ()):
                    fx, fy = self.fungi[i]
                    d = (fx - x) ** 2 + (fy - y) ** 2
                    if d < bd:
                        best, bd = (fx, fy), d
        return best

    def _burst(self, x, y, bat):
        n = self.per
        for q in self.p:
            if n <= 0:
                break
            if q[4] >= q[5]:
                a = random.uniform(0, 6.3)
                sp = random.uniform(25, 60)
                q[0], q[1] = x + random.uniform(-5, 5), y + random.uniform(-6, 2)
                q[2] = math.cos(a) * sp + (bat.vx * .15 if bat else 0)
                q[3] = math.sin(a) * sp * .7 - 18 + (bat.vy * .15 if bat else 0)
                q[4], q[5], q[6] = 0.0, random.uniform(1.1, 2.0), random.uniform(0, 6.3)
                n -= 1

    def draw(self, c, cam):
        for x, y, vx, vy, age, life, ph in self.p:
            if age >= life:
                continue
            k = min(1.0, age / .12) * (1 - age / life) * (.7 + .3 * math.sin(ph * 6))
            if k < .08:
                continue
            img = self.img[min(2, int(k * 3))]
            c.blit(img, (x - cam.x - 5, y - cam.y - 5), special_flags=pygame.BLEND_RGB_ADD)


# ====================================================================== telarañas que se mecen
class WebSway:
    """Las telarañas de las esquinas se mecen cuando Mullo pasa cerca (y se calman solas). Es solo ambiente:
    no hace daño ni ruido para los bichos.
    El fondo ya trae la telaraña quieta: solo se vuelve a pintar mientras se mueve (tapando la quieta con el
    pedacito de fondo limpio que se guardó al generar la cueva). Los cuadros de animación se hacen la primera vez
    que se mueve cada telaraña."""
    FRAMES = 4

    def __init__(self, webs):
        self.webs = [w for w in webs if w.get('clean') is not None]
        for w in self.webs:
            w['agit'], w['frames'] = 0.0, None
        self.t = 0.0

    def update(self, dt, bat):
        self.t += dt
        fast = math.hypot(bat.vx, bat.vy) > 40
        for w in self.webs:
            if w['agit'] > 0:
                w['agit'] = max(0.0, w['agit'] - dt / 1.4)
            reach = w['r'] + 34
            if fast and abs(w['x'] - bat.x) < reach and abs(w['y'] - bat.y) < reach:
                w['agit'] = 1.0

    def _frames(self, w):
        if w['frames'] is None:
            w['frames'] = [decor.cobweb_surface(w['side'], w['col'], w['r'], amp, i * math.tau / self.FRAMES)[0]
                           for amp in (2.0, 4.5) for i in range(self.FRAMES)]
        return w['frames']

    def draw(self, c, cam):
        for w in self.webs:
            if w['agit'] <= .12 or not cam.visible(w['x'], w['y'], w['r'] + 10):
                continue
            rect = w['rect']
            c.blit(w['clean'], (rect.x - int(cam.x), rect.y - int(cam.y)))   # tapa la telaraña quieta del fondo
            fr = self._frames(w)
            i = int(self.t * 9 + w['x']) % self.FRAMES + (self.FRAMES if w['agit'] > .5 else 0)
            r = w['r']
            c.blit(fr[i], (w['x'] - r - 2 - int(cam.x), w['y'] - r - 2 - int(cam.y)))


# ====================================================================== cristales que destellan con la luz de Mullo
def _star(r, col):
    """Destello en cruz con un centro brillante (sobre negro, para sumarlo a la imagen)."""
    s = pygame.Surface((2 * r + 1, 2 * r + 1))
    for i in range(r, 0, -1):
        k = (1 - i / r) ** 1.6
        cc = tuple(min(255, int(v * k)) for v in col)
        pygame.draw.line(s, cc, (r - i, r), (r + i, r))
        pygame.draw.line(s, cc, (r, r - i), (r, r + i))
    for i in range(r // 2, 0, -1):                       # diagonales más cortas
        k = (1 - i / (r / 2)) ** 1.6 * .55
        cc = tuple(min(255, int(v * k)) for v in col)
        pygame.draw.line(s, cc, (r - i, r - i), (r + i, r + i))
        pygame.draw.line(s, cc, (r - i, r + i), (r + i, r - i))
    core = _glow(3, tuple(min(255, int(v * .9 + 40)) for v in col))
    s.blit(core, (r - 3, r - 3), special_flags=pygame.BLEND_RGB_ADD)
    return s


class CrystalGlints:
    """Los cristales de las paredes destellan cuando les llega la luz de Mullo: más cerca, más brillo.
    Cada uno titila a su ritmo. Destellos hechos una vez por color (3 intensidades); solo se revisan los cristales a la vista."""
    R = 9

    def __init__(self, crystals):
        self.crystals = [(x, y, col, (x * .131 + y * .071) % 6.3) for x, y, col in crystals]
        self.img = {}
        for col in {c[2] for c in self.crystals}:
            light = tuple(min(255, int(v * .7 + 90)) for v in col)
            self.img[col] = [_star(self.R, tuple(int(v * f) for v in light)) for f in (.35, .65, 1.0)]

    def draw(self, c, cam, bat, reach, t):
        R = self.R
        for x, y, col, ph in self.crystals:
            if not cam.visible(x, y, 20):
                continue
            d = math.hypot(x - bat.x, y - bat.y)
            if d >= reach:
                continue
            tw = .5 + .5 * math.sin(t * 2.4 + ph)
            k = (1 - d / reach) ** .8 * (.3 + .7 * tw * tw * tw)
            if k < .12:
                continue
            img = self.img[col][min(2, int(k * 3))]
            c.blit(img, (x - cam.x - R + math.cos(ph) * 3, y - cam.y - R + math.sin(ph) * 3), special_flags=pygame.BLEND_RGB_ADD)


class ShellGlints:
    """El caparazón de los escarabajos (propuesta 5.3: «azul petróleo con brillo metálico») destella con la luz de
    Mullo: un reflejo que corre sobre el caparazón al moverse y una chispa en su punto más alto. Solo se revisan los
    escarabajos a la vista y dentro de su luz; los brillos se hacen una vez (3 intensidades)."""

    def __init__(self):
        col = (150, 235, 250)
        self.dot = [_glow(4, tuple(int(v * f) for v in col)) for f in (.3, .6, 1.0)]
        self.star = [_star(7, tuple(int(v * f) for v in col)) for f in (.35, .65, 1.0)]

    def draw(self, c, cam, bat, enemies, reach, t):
        for e in enemies:
            if e.kind != 'beetle' or not cam.visible(e.x, e.y, 30):
                continue
            d = math.hypot(e.x - bat.x, e.y - bat.y)
            if d >= reach:
                continue
            k = (1 - d / reach) ** .7
            ph = (t * .45 + (e.x * .013 + e.y * .007)) % 1.0     # el reflejo recorre el caparazón de atrás hacia adelante
            sheen = k * math.sin(math.pi * ph) * (1.0 if e.stun <= 0 else .5)
            if sheen < .1:
                continue
            P = ui._rot(e.x - cam.x, e.y - cam.y, e.face, e.spec['size'])
            along = -13 + 24 * ph
            lv = min(2, int(sheen * 3))
            for sd in (-1, 1):                                # una franja de luz en cada ala del caparazón
                for j, off in enumerate((3, 6.5, 9.5)):
                    x, y = P(along - j * 1.5, sd * off)
                    c.blit(self.dot[max(0, lv - (j == 2))], (x - 4, y - 4), special_flags=pygame.BLEND_RGB_ADD)
            if sheen > .55:                                  # chispa cuando el reflejo pasa por lo más alto
                x, y = P(along, -6)
                img = self.star[min(2, int((sheen - .55) / .45 * 3))]
                c.blit(img, (x - 7, y - 7), special_flags=pygame.BLEND_RGB_ADD)


# ====================================================================== agua: estela y reflejo de Mullo
REFLECT = dict(col=(12, 14, 36), body=(16, 18, 46), edge=(44, 48, 104), eye=(130, 96, 36),
               bones=(24, 26, 60), ear_in=(20, 20, 52), slim=.72)


class WaterWake:
    """El agua se agita con Mullo:
      · Al volar encima deja una estela en forma de V (ondas que se abren hacia los lados detrás de ella) y,
        de vez en cuando, salpica gotitas.
      · Si se queda quieta encima, el aire de sus alas sigue moviendo el agua: un anillo suave debajo de ella
        y dos hoyuelos bajo las puntas de las alas, al ritmo del aleteo.
    También se ve su reflejo oscuro debajo, con los ojos ámbar apagados.
    Grupos fijos de ondas y gotitas (se reciclan) y una sola capa reutilizada para el reflejo."""
    # tipos de onda: 0 estela (se abre de lado), 1 anillo bajo Mullo quieta, 2 hoyuelo de ala
    LIFE = (1.1, 1.9, .7)
    SIZE = (24, 58, 15)

    def __init__(self):
        n = 14 if IS_WEB else 30
        self.rings = [[0.0, 0.0, 1.0, 1.0, 0, 0.0, 0.0] for _ in range(n)]    # x, y, edad, vida, tipo, vx, vy
        self.drops = [[0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0] for _ in range(8 if IS_WEB else 16)]   # x y z vx vy edad vida
        self.timer = self.hover_t = self.splash_t = 0.0
        self.last_flap = 0.0
        self.layer = pygame.Surface((130, 100), pygame.SRCALPHA)

    def _ring(self, x, y, kind, vx=0.0, vy=0.0, cave=None):
        if cave is not None and not cave.is_water(x, y):
            return
        for r in self.rings:
            if r[2] >= r[3]:
                r[:] = [x, y, 0.0, self.LIFE[kind] * random.uniform(.9, 1.1), kind, vx, vy]
                return

    def drip(self, x, y):
        """Una gota que cae desde las alas de Mullo al agua (hace su anillito al caer)."""
        for q in self.drops:
            if q[5] >= q[6]:
                q[:] = [x, y, 9.0, random.uniform(-6, 6), 0.0, 0.0, 2.0]
                return

    def update(self, dt, bat, cave=None):
        for r in self.rings:
            if r[2] < r[3]:
                r[2] += dt
                r[0] += r[5] * dt                              # la estela se abre hacia los lados
                r[1] += r[6] * dt
                r[5] *= 1 - min(1.0, 1.5 * dt)
                r[6] *= 1 - min(1.0, 1.5 * dt)
        for q in self.drops:
            if q[5] < q[6]:
                q[5] += dt
                q[4] -= 300 * dt
                q[2] += q[4] * dt
                q[0] += q[3] * dt
                if q[2] <= 0:                                  # cae al agua: hace su propio anillito
                    q[5] = q[6]
                    self._ring(q[0], q[1], 2, cave=cave)
        if not bat.over_water:
            self.timer = self.hover_t = 0.0
            return
        sp = math.hypot(bat.vx, bat.vy)
        if sp > 40:                                            # volando: estela en V detrás de ella
            self.timer -= dt
            if self.timer <= 0:
                self.timer = .09
                ux, uy = bat.vx / sp, bat.vy / sp
                bx, by = bat.x - ux * 12, bat.y + 8 - uy * 8
                side = 55 + sp * .12                            # qué tan rápido se abre la V
                self._ring(bx - uy * 4, by + ux * 4, 0, -uy * side, ux * side, cave)
                self._ring(bx + uy * 4, by - ux * 4, 0, uy * side, -ux * side, cave)
            self.splash_t -= dt
            if self.splash_t <= 0:                             # salpica gotitas de vez en cuando
                self.splash_t = random.uniform(.25, .5)
                for q in self.drops:
                    if q[5] >= q[6]:
                        a = math.atan2(-bat.vy, -bat.vx) + random.uniform(-.9, .9)
                        v = random.uniform(30, 60)
                        q[:] = [bat.x, bat.y + 8, 2.0, math.cos(a) * v, random.uniform(50, 90), 0.0, 2.0]
                        q[1] += math.sin(a) * 4
                        break
        else:                                                  # quieta encima: el aire de las alas mueve el agua
            self.hover_t -= dt
            if self.hover_t <= 0:
                self.hover_t = .5
                self._ring(bat.x, bat.y + 10, 1, cave=cave)
            down = math.sin(bat.flap)                          # cada aletazo hacia abajo hace dos hoyuelos
            if self.last_flap > .6 >= down:
                ca, sa = math.cos(bat.tilt), math.sin(bat.tilt)
                for sd in (-1, 1):
                    self._ring(bat.x + ca * sd * 38, bat.y + 8 + sa * sd * 38, 2, cave=cave)
            self.last_flap = down

    def draw(self, c, cam):
        ox, oy = cam.x, cam.y
        for x, y, age, life, kind, vx, vy in self.rings:
            if age >= life:
                continue
            p = age / life
            g = (1 - p) ** 1.2
            rx = 4 + self.SIZE[kind] * (p ** .7)
            sx, sy = x - ox, y - oy
            rect = (sx - rx, sy - rx * .6, 2 * rx, 1.2 * rx)
            pygame.draw.ellipse(c, (int(80 * g), int(118 * g), int(205 * g)), rect, 1)
            if kind != 2 and rx > 9:                           # brillo del borde de la onda
                hi = (int(150 * g), int(180 * g), int(240 * g))
                pygame.draw.arc(c, hi, rect, math.pi * 1.15, math.pi * 1.85, 1)
        for x, y, z, vx, vy, age, life in self.drops:
            if age >= life:
                continue
            sx, sy = int(x - ox), int(y - oy - z)
            c.fill((150, 190, 240), (sx, sy, 2, 2))

    def draw_reflection(self, c, cam, bat, cave, t):
        """Reflejo de Mullo en el agua: oscuro, de cabeza (se ve hacia abajo) y con un vaivén suave del agua.
        Solo se pinta sobre los tiles de agua (no sobre la orilla ni los islotes)."""
        if not bat.over_water:
            return
        L = self.layer
        L.fill((0, 0, 0, 0))
        ui.draw_bat(L, 65, 50, bat.flap, .92, **REFLECT)
        img = pygame.transform.flip(L, False, True)
        wx = bat.x - 65 + math.sin(t * 3.1) * 1.5           # esquina del reflejo en el mundo
        wy = bat.y - 50 + 22
        T = TILE
        ox, oy = int(cam.x), int(cam.y)
        for ty in range(int(wy) // T, int(wy + 100) // T + 1):
            for tx in range(int(wx) // T, int(wx + 130) // T + 1):
                if not cave.is_water(tx * T + 1, ty * T + 1):
                    continue
                area = pygame.Rect(tx * T - int(wx), ty * T - int(wy), T, T)
                c.blit(img, (tx * T - ox, ty * T - oy), area)


# ====================================================================== Mullo: respira agitada y se sacuda el polvo
class MulloFx:
    """Detalles de Mullo que no cambian cómo se juega:
      · Después de un impulso o de escapar de una persecución respira agitada: su cuerpo sube y baja rápido y
        suelta vaporcitos frente al hocico.
      · Si choca varias veces seguidas, se sacude (un meneo rápido) y suelta una nubecita de polvo de su pelaje."""
    PANT_DASH, PANT_CHASE = 1.6, 2.2
    HITS, HIT_WINDOW = 3, 3.0

    def __init__(self):
        self.pant = 0.0
        self.shake = 0.0
        self.hits = []
        self.pending = -1.0                              # pequeña pausa antes de sacudirse
        self.t = 0.0
        self.puff_t = 0.0
        self.p = [[0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0] for _ in range(10 if IS_WEB else 20)]   # x, y, vx, vy, edad, vida, tipo

    def panting(self, secs):
        self.pant = max(self.pant, secs)

    def impact(self):
        self.hits = [h for h in self.hits if self.t - h < self.HIT_WINDOW] + [self.t]
        if len(self.hits) >= self.HITS and self.shake <= 0 and self.pending < 0:
            self.pending, self.hits = .18, []

    def _spawn(self, x, y, vx, vy, life, kind):
        for q in self.p:
            if q[4] >= q[5]:
                q[:] = [x, y, vx, vy, 0.0, life, kind]
                return

    def update(self, dt, bat):
        self.t += dt
        for q in self.p:
            if q[4] < q[5]:
                q[4] += dt
                q[0] += q[2] * dt
                q[1] += q[3] * dt
                q[2] *= 1 - min(1.0, 3 * dt)
                q[3] *= 1 - min(1.0, 3 * dt)
        if self.pending >= 0:
            self.pending -= dt
            if self.pending < 0:
                self.shake = .5
                for i in range(7 if IS_WEB else 12):          # polvo que sale de su pelaje
                    a = i * math.tau / 12 + random.uniform(-.3, .3)
                    sp = random.uniform(40, 80)
                    self._spawn(bat.x + math.cos(a) * 8, bat.y + math.sin(a) * 6, math.cos(a) * sp, math.sin(a) * sp,
                                random.uniform(.5, .8), 1)
        self.shake = max(0.0, self.shake - dt)
        if self.pant > 0:
            self.pant = max(0.0, self.pant - dt)
            self.puff_t -= dt
            if self.puff_t <= 0:                              # vaporcito frente al hocico (la cabeza va arriba)
                self.puff_t = .28
                hx = bat.x + math.sin(bat.tilt) * 11
                hy = bat.y - math.cos(bat.tilt) * 11
                self._spawn(hx, hy, random.uniform(-6, 6) + bat.vx * .3, -22 + bat.vy * .3, .5, 0)

    def pose(self, t):
        """(escala, inclinación extra) para dibujar a Mullo."""
        sc, tilt = 1.0, 0.0
        if self.pant > 0:
            k = min(1.0, self.pant / .6)
            sc += .035 * k * math.sin(t * 21)
        if self.shake > 0:
            k = self.shake / .5
            tilt += .38 * k * math.sin(t * 46)
        return sc, tilt

    def draw(self, c, cam):
        for x, y, vx, vy, age, life, kind in self.p:
            if age >= life:
                continue
            f = 1 - age / life
            sx, sy = int(x - cam.x), int(y - cam.y)
            if kind == 0:                                    # vaporcito
                g = int(150 * f)
                pygame.draw.circle(c, (g, g, int(g * 1.1)), (sx, sy), 2 + int(3 * (1 - f)), 1)
            else:                                            # polvo café
                g = int(160 * f)
                pygame.draw.circle(c, (g, int(g * .8), int(g * .6)), (sx, sy), 1 + int(2 * f))


# ====================================================================== trocitos de carbón de las vagonetas
class CoalBits:
    """Cuando una vagoneta frena de golpe (tope del riel o choca con Xolthar) se le caen pedacitos de carbón que
    rebotan en el suelo y se quedan un rato. Vistos desde arriba: la altura se dibuja como un salto con su sombrita."""

    def __init__(self):
        self.p = [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 2] for _ in range(14 if IS_WEB else 28)]  # x y z vx vy vz edad vida tamaño

    def spill(self, x, y, ang, v):
        n = 5 if IS_WEB else 8
        fx, fy = math.cos(ang) * (1 if v >= 0 else -1), math.sin(ang) * (1 if v >= 0 else -1)
        for q in self.p:
            if n <= 0:
                break
            if q[6] >= q[7]:
                a = math.atan2(fy, fx) + random.uniform(-1.1, 1.1)
                sp = random.uniform(40, 110)
                q[:] = [x + fx * 14, y + fy * 14, 2.0, math.cos(a) * sp, math.sin(a) * sp, random.uniform(70, 140),
                        0.0, random.uniform(2.5, 4.0), random.choice((2, 2, 3))]
                n -= 1

    def update(self, dt, cave):
        for q in self.p:
            if q[6] >= q[7]:
                continue
            q[6] += dt
            if q[2] > 0 or q[5] > 0:                          # en el aire: cae y rebota
                q[5] -= 420 * dt
                q[2] += q[5] * dt
                nx, ny = q[0] + q[3] * dt, q[1] + q[4] * dt
                if cave.solid_px(nx, ny):
                    q[3] = q[4] = 0.0
                else:
                    q[0], q[1] = nx, ny
                if q[2] <= 0:
                    q[2] = 0.0
                    q[5] = -q[5] * .38 if abs(q[5]) > 40 else 0.0
                    q[3] *= .55
                    q[4] *= .55

    def draw(self, c, cam):
        for x, y, z, vx, vy, vz, age, life, r in self.p:
            if age >= life or not cam.visible(x, y, 10):
                continue
            f = min(1.0, (life - age) / .6)
            sx, sy = int(x - cam.x), int(y - cam.y)
            if z > 1:
                pygame.draw.circle(c, (6, 5, 4), (sx, sy), r)                # sombrita en el suelo
            g = int(26 * f)
            pygame.draw.circle(c, (g, g, int(g * 1.1)), (sx, sy - int(z)), r)
            hi = int(95 * f)
            c.fill((hi, hi, int(hi * 1.1)), (sx - 1, sy - int(z) - 1, 1, 1))  # brillito del carbón


# ====================================================================== la piel vieja de Xolthar se mece
class MoltSway:
    """La muda de Xolthar en la entrada de la mina se mece con la corriente de aire (más cuando la mina retumba
    o durante la huida). El fondo trae la piel quieta; aquí solo se repinta cuando está a la vista, tapándola con
    el pedacito de fondo limpio. Los cuadros se hacen una vez, al cargar el nivel."""
    FRAMES = 8

    def __init__(self, cave):
        self.ok = bool(cave.molt and cave.molt_clean)
        if not self.ok:
            return
        from art import molt_surface
        self.x, self.y, ang = cave.molt
        self.rect, self.clean = cave.molt_clean
        self.frames = [molt_surface(ang, 170, 150, sway=amp, phase=i * math.tau / self.FRAMES)
                       for amp in (3.0, 6.5) for i in range(self.FRAMES)]

    def draw(self, c, cam, t, strong=False):
        if not self.ok or not cam.visible(self.x, self.y, 120):
            return
        c.blit(self.clean, (self.rect.x - int(cam.x), self.rect.y - int(cam.y)))
        i = int(t * (7 if strong else 3.5)) % self.FRAMES + (self.FRAMES if strong else 0)
        img = self.frames[i]
        c.blit(img, img.get_rect(center=(int(self.x - cam.x), int(self.y - cam.y))))


# ====================================================================== aire húmedo sobre el lago
class WetWings:
    """Sobre el Lago Negro el aire húmedo frena a Mullo (propuesta 3.5). Para que el jugador lo entienda (y no
    piense que es un error) la humedad se ve en ella:
      · Gotitas que se le juntan en las alas y brillan con su luz; al salir del agua se secan poco a poco.
      · De las puntas de las alas gotea al lago (cada gota hace su anillito).
      · Vaho: puntitos de humedad que flotan pegados a ella y se quedan atrás al volar (no es niebla: solo
        alrededor de Mullo, nada tapa la pantalla).
    Grupos fijos (se reciclan); todo se dibuja solo cerca de Mullo."""
    # gotitas sobre las alas, en coordenadas de Mullo (x a los lados, y hacia la cola; la cabeza va arriba)
    BEADS = ((-30, -6), (-22, -2), (-14, 4), (-36, 2), (30, -6), (22, -2), (14, 4), (36, 2), (-8, 8), (8, 8))

    def __init__(self):
        self.k = 0.0                                     # 0 seca · 1 empapada
        self.drip_t = 0.0
        n = 10 if IS_WEB else 18
        self.mist = [[0.0, 0.0, random.uniform(0, 6.3), random.uniform(18, 46), random.uniform(.6, 1.4)] for _ in range(n)]

    def update(self, dt, bat, wake=None):
        target = 1.0 if bat.over_water else 0.0
        rate = 2.5 if target > self.k else .55          # se moja rápido y se seca despacio
        self.k += (target - self.k) * min(1.0, dt * rate)
        if self.k < .02:
            return
        for m in self.mist:                              # el vaho flota alrededor y se queda atrás al volar
            m[2] += dt * m[4]
            ax = bat.x + math.cos(m[2]) * m[3]
            ay = bat.y + math.sin(m[2] * 1.3) * m[3] * .7
            lag = min(1.0, dt * 3)
            if m[0] == 0.0 and m[1] == 0.0:
                m[0], m[1] = ax, ay
            m[0] += (ax - m[0]) * lag
            m[1] += (ay - m[1]) * lag - 4 * dt
        if bat.over_water and wake is not None:
            self.drip_t -= dt
            if self.drip_t <= 0:
                self.drip_t = random.uniform(.3, .6)
                sd = random.choice((-1, 1))
                ca, sa = math.cos(bat.tilt), math.sin(bat.tilt)
                wx, wy = sd * random.uniform(24, 38), random.uniform(0, 6)
                wake.drip(bat.x + wx * ca - wy * sa, bat.y + wx * sa + wy * ca)

    def draw(self, c, cam, bat, t):
        k = self.k
        if k < .03:
            return
        ox, oy = cam.x, cam.y
        for x, y, ph, r, sp in self.mist:                # vaho: puntitos tenues que flotan
            a = k * (.45 + .3 * math.sin(t * 2 + ph * 3))
            g = int(190 * a)
            if g > 6:
                c.fill((int(g * .75), int(g * .88), g), (int(x - ox), int(y - oy), 2, 2))
        ca, sa = math.cos(bat.tilt), math.sin(bat.tilt)
        flap = math.sin(bat.flap)
        bx, by = bat.x - ox, bat.y - oy
        n = int(len(self.BEADS) * min(1.0, k * 1.3))     # mientras más mojada, más gotitas
        for i, (lx, ly) in enumerate(self.BEADS[:n]):
            ly2 = ly - flap * abs(lx) * .25               # suben y bajan con el aleteo
            x, y = bx + lx * ca - ly2 * sa, by + lx * sa + ly2 * ca
            shine = .6 + .4 * math.sin(t * 5 + i * 1.7)
            g = min(255, int(270 * k * shine))
            c.fill((int(g * .55), int(g * .8), g), (int(x) - 1, int(y), 3, 2))
            c.fill((int(g * .55), int(g * .8), g), (int(x), int(y) - 1, 1, 4))
            if shine > .85:                               # destello de la gota
                c.fill((g, g, g), (int(x), int(y), 1, 1))


# ====================================================================== jirones de niebla sobre el lago
def _wisp(w, h, rnd, peak=38):
    """Jirón alargado y suave: varias nubecitas alargadas sumadas (en chiquito) y ampliadas con suavizado,
    así los bordes quedan difusos y sin cortes."""
    sw, sh = max(12, w // 6), max(6, h // 6)
    blobs = [(rnd.uniform(.15, .85) * sw, rnd.uniform(.3, .7) * sh, rnd.uniform(.08, .22) * sw, rnd.uniform(.14, .32) * sh,
              rnd.uniform(.35, .9)) for _ in range(9)]                    # nubecitas de distinto tamaño: borde irregular
    small = pygame.Surface((sw, sh), pygame.SRCALPHA)
    for py in range(sh):
        for px in range(sw):
            v = sum(k * math.exp(-(((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2)) for cx, cy, rx, ry, k in blobs)
            v *= .75 + .25 * math.sin(px * .9 + py * 2.1)                    # un poco deshilachado
            edge = min(1.0, px / (sw * .15), (sw - 1 - px) / (sw * .15), py / (sh * .3), (sh - 1 - py) / (sh * .3))
            small.set_at((px, py), (170, 182, 225, int(min(1.0, v) * peak * max(0.0, edge))))
    return pygame.transform.smoothscale(small, (w, h))


class LakeWisps:
    """Niebla del Lago Negro (la humedad que frena a Mullo), en dos capas:
      · Jirones largos que se arrastran despacio sobre el agua.
      · Neblina baja pegada al agua en las orillas, donde se junta más la humedad: se mece en su lugar.
    Se nota, pero deja ver: es translúcida y se abre alrededor de Mullo para no taparle las crías ni los bichos.
    Sprites hechos una vez al cargar; los jirones que llegan a la orilla reaparecen en otra parte del lago lejos
    de la vista. Solo se dibuja lo que está en pantalla."""
    OPEN_R = 120                                          # alrededor de Mullo la niebla se abre
    STRENGTH = 1.0                                        # qué tanto se nota toda la niebla (1 = normal)

    def __init__(self, cave):
        self.cave = cave
        self.water = [i for i in range(cave.w * cave.h) if cave.water[i]]
        self.items, self.banks = [], []
        if not self.water:
            return
        rnd = random.Random(11)
        self.imgs = [_wisp(rnd.randint(240, 380), rnd.randint(46, 70), rnd, 58) for _ in range(5)]
        self.bank_imgs = [_wisp(rnd.randint(130, 190), rnd.randint(54, 80), rnd, 72) for _ in range(4)]
        n = min(14 if IS_WEB else 32, len(self.water) // 9)
        for _ in range(n):
            x, y = self._spot()
            self.items.append([x, y, random.choice((-1, 1)) * random.uniform(6, 13), random.randrange(len(self.imgs)),
                               random.uniform(0, 6.3), 1.0])          # x, y, velocidad, sprite, fase, aparición
        # orillas: tiles de agua que tocan tierra (ahí la niebla se junta más)
        w, T = cave.w, TILE
        shore = [i for i in self.water if not all(cave.water[i + d] for d in (1, -1, w, -w))]
        random.shuffle(shore)
        taken = []
        for i in shore:
            x, y = (i % w) * T + T / 2, (i // w) * T + T / 2
            if all(abs(x - a) > 110 or abs(y - b) > 60 for a, b in taken):
                taken.append((x, y))
                self.banks.append([x, y, random.randrange(len(self.bank_imgs)), random.uniform(0, 6.3)])
            if len(self.banks) >= (16 if IS_WEB else 40):
                break

    def _spot(self, cam=None):
        T = TILE
        for _ in range(30):
            i = self.water[random.randrange(len(self.water))]
            x, y = (i % self.cave.w) * T + T / 2, (i // self.cave.w) * T + T / 2
            if cam is None or not cam.visible(x, y, 260):
                return x, y
        return x, y

    def update(self, dt, cam):
        for w in self.items:
            w[0] += w[2] * dt
            w[4] += dt
            w[5] = min(1.0, w[5] + dt / 3)                # aparece despacio (sin saltos)
            if not self.cave.is_water(w[0], w[1]):        # llegó a la orilla: reaparece en otra parte del lago
                w[0], w[1] = self._spot(cam)
                w[5] = 0.0
        for bk in self.banks:
            bk[3] += dt

    def _open(self, x, y, bat):
        d = math.hypot(x - bat.x, (y - bat.y) * 1.6)
        return .22 + .78 * min(1.0, max(0.0, (d - 40) / self.OPEN_R))

    def draw(self, c, cam, bat):
        ox, oy, st = cam.x, cam.y, self.STRENGTH
        for x, y, idx, ph in self.banks:                  # neblina baja de las orillas (se mece en su lugar)
            img = self.bank_imgs[idx]
            hw, hh = img.get_width() // 2, img.get_height() // 2
            if not cam.visible(x, y, hw):
                continue
            a = int(255 * st * (.6 + .4 * math.sin(ph * .6)) * self._open(x, y, bat))
            if a < 12:
                continue
            img.set_alpha(min(255, a))
            c.blit(img, (int(x - ox + math.sin(ph * .35) * 14) - hw, int(y - oy) - hh))
        for x, y, vx, idx, ph, fade in self.items:        # jirones que se arrastran sobre el agua
            img = self.imgs[idx]
            hw, hh = img.get_width() // 2, img.get_height() // 2
            if not cam.visible(x, y, hw):
                continue
            a = int(255 * st * fade * (.6 + .4 * math.sin(ph * .5)) * self._open(x, y, bat))
            if a < 12:
                continue
            img.set_alpha(min(255, a))
            c.blit(img, (int(x - ox) - hw, int(y - oy + math.sin(ph * .7) * 6) - hh))


# ====================================================================== Xolthar rompe el piso
class BurrowFx:
    """Lo que se ve cuando Xolthar rompe el piso:
      · Agujeros que se quedan en el suelo (por donde entró y por donde salió), con escombro alrededor.
      · Bajo tierra: montoncitos de tierra que se levantan a su paso (se ve hacia dónde va).
      · Aviso (1 s): el piso se abomba y tiembla, las grietas crecen brillando rojo y sale polvo y piedritas.
      · Al salir: estallido de piedras, nube de polvo que se abre y una onda en el suelo; el agujero es más grande.
    Grupos fijos (se reciclan); los agujeros tienen tope."""
    MAX_HOLES = 8

    def __init__(self):
        self.holes = []                                  # [x, y, edad, semilla, tamaño]
        self.cracks = None                               # [x, y, edad, rayos]
        self.wave = None                                 # onda de polvo en el suelo al salir [x, y, edad]
        n = 40 if IS_WEB else 96
        self.p = [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0, 0.0] for _ in range(n)]  # x y z vx vy vz edad vida tipo tamaño
        self.trail_t = self.warn_t = 0.0
        self.puff = [_dust_puff(r) for r in (10, 16, 24)]

    def _spawn(self, x, y, z, vx, vy, vz, life, kind, size=0.0):
        for q in self.p:
            if q[6] >= q[7]:
                q[:] = [x, y, z, vx, vy, vz, 0.0, life, kind, size]
                return

    def hole(self, x, y, size=1.0):
        self.holes.append([x, y, 0.0, random.randrange(1000), size])
        if len(self.holes) > self.MAX_HOLES:
            self.holes.pop(0)

    def burst(self, x, y, n=14, big=False):
        n = n if not IS_WEB else n // 2
        for i in range(n):                               # piedras que saltan
            a = i * math.tau / n + random.uniform(-.2, .2)
            sp = random.uniform(90, 240 if big else 170)
            self._spawn(x, y, 4.0, math.cos(a) * sp, math.sin(a) * sp * .8, random.uniform(160, 320 if big else 230),
                        random.uniform(.9, 1.5), 1, random.uniform(3, 7) if big else 4)
        if big:                                          # nube de polvo que se abre
            for i in range(12 if not IS_WEB else 6):
                a = i * math.tau / 12 + random.uniform(-.25, .25)
                sp = random.uniform(60, 120)
                self._spawn(x, y, 0.0, math.cos(a) * sp, math.sin(a) * sp * .7, 0.0, random.uniform(.9, 1.4), 2,
                            random.uniform(.6, 1.0))
            self.wave = [x, y, 0.0]

    def warn(self, x, y):
        rays = []
        for i in range(9):                               # grietas que salen del centro en zigzag
            a = i * math.tau / 9 + random.uniform(-.25, .25)
            pts, r = [(0.0, 0.0)], 0.0
            for _ in range(6):
                r += random.uniform(11, 17)
                a += random.uniform(-.4, .4)
                pts.append((math.cos(a) * r, math.sin(a) * r * .8))
            rays.append(pts)
        self.cracks = [x, y, 0.0, rays]
        self.warn_t = 0.0

    def trail(self, dt, x, y, cave):
        self.trail_t -= dt
        if self.trail_t > 0:
            return
        self.trail_t = .07
        if cave.solid_px(x, y) or cave.is_water(x, y):
            return
        for _ in range(2):                               # tierra que se levanta encima de donde va
            self._spawn(x + random.uniform(-14, 14), y + random.uniform(-10, 10), 0.0, random.uniform(-15, 15),
                        random.uniform(-10, 10), random.uniform(50, 90), random.uniform(.5, .8), 0)

    def update(self, dt, warning=False):
        for h in self.holes:
            h[2] += dt
        if self.cracks:
            self.cracks[2] += dt
            if warning:                                  # mientras avisa: sale polvo y brincan piedritas
                self.warn_t -= dt
                if self.warn_t <= 0:
                    self.warn_t = .05
                    x, y, age = self.cracks[0], self.cracks[1], self.cracks[2]
                    a, r = random.uniform(0, math.tau), random.uniform(5, 30 + 50 * min(1.0, age))
                    self._spawn(x + math.cos(a) * r, y + math.sin(a) * r * .8, 0.0, random.uniform(-12, 12),
                                random.uniform(-14, -4), 0.0, random.uniform(.6, 1.0), 2, random.uniform(.3, .55))
                    if random.random() < .5:
                        self._spawn(x + math.cos(a) * r * .6, y + math.sin(a) * r * .5, 1.0, random.uniform(-25, 25),
                                    random.uniform(-20, 20), random.uniform(60, 120), .5, 1, 2.5)
            if self.cracks[2] > 2.6:
                self.cracks = None
        if self.wave:
            self.wave[2] += dt
            if self.wave[2] > .7:
                self.wave = None
        for q in self.p:
            if q[6] >= q[7]:
                continue
            q[6] += dt
            if q[8] == 2:                                # polvo: se abre, frena y sube un poco
                q[3] *= 1 - min(1.0, 2.2 * dt)
                q[4] *= 1 - min(1.0, 2.2 * dt)
                q[0] += q[3] * dt
                q[1] += q[4] * dt - 6 * dt
                continue
            q[5] -= 420 * dt
            q[2] = max(0.0, q[2] + q[5] * dt)
            q[0] += q[3] * dt
            q[1] += q[4] * dt
            if q[2] <= 0:
                q[3] *= .5
                q[4] *= .5

    def draw_floor(self, c, cam, t=0.0):
        """Agujeros, onda de polvo, bulto que tiembla y grietas (en el suelo, antes de la oscuridad)."""
        ox, oy = cam.x, cam.y
        for x, y, age, seed, size in self.holes:
            if not cam.visible(x, y, 70):
                continue
            sx, sy = int(x - ox), int(y - oy)
            rnd = random.Random(seed)
            k = size
            for _ in range(int(9 * k)):                  # escombro alrededor
                a, r = rnd.uniform(0, math.tau), rnd.uniform(30, 48) * k
                pygame.draw.circle(c, (70, 56, 42), (int(sx + math.cos(a) * r), int(sy + math.sin(a) * r * .75)),
                                   rnd.randint(2, 5))
            pygame.draw.ellipse(c, (54, 42, 32), (sx - 34 * k, sy - 24 * k, 68 * k, 48 * k))         # borde roto
            pygame.draw.ellipse(c, (10, 7, 6), (sx - 27 * k, sy - 19 * k, 54 * k, 38 * k))           # el hoyo
            pygame.draw.ellipse(c, (4, 2, 2), (sx - 18 * k, sy - 12 * k, 36 * k, 24 * k))
            pygame.draw.arc(c, (110, 90, 66), (sx - 34 * k, sy - 24 * k, 68 * k, 48 * k), math.pi * .1, math.pi * .9, 2)
        if self.wave:                                    # onda de polvo que corre por el suelo
            x, y, age = self.wave
            q = age / .7
            r = 30 + 170 * q
            g = int(150 * (1 - q))
            pygame.draw.ellipse(c, (g, int(g * .8), int(g * .6)), (x - ox - r, y - oy - r * .7, 2 * r, 1.4 * r), 4)
        if self.cracks:
            x, y, age, rays = self.cracks
            if age < 1.6:
                k = min(1.0, age / .9)
                jx = random.uniform(-1, 1) * 3 * k       # todo tiembla cada vez más
                sx, sy = x - ox + jx, y - oy
                mr = 18 + 26 * k                         # el piso se abomba
                pygame.draw.ellipse(c, (78, 62, 46), (sx - mr, sy - mr * .7, 2 * mr, 1.4 * mr))
                pygame.draw.ellipse(c, (104, 84, 62), (sx - mr * .7, sy - mr * .65, 1.4 * mr, mr * .8))
                glow = int(170 + 85 * math.sin(age * (18 + 20 * k)))
                for pts in rays:
                    m = max(2, int(len(pts) * k + .5))
                    line = [(sx + px, sy + py) for px, py in pts[:m]]
                    pygame.draw.lines(c, (16, 8, 6), False, line, 5)
                    pygame.draw.lines(c, (glow, int(40 + 50 * k), 24), False, line, 2)

    def draw_air(self, c, cam):
        """Tierra, piedras y polvo en el aire (con su sombrita)."""
        ox, oy = cam.x, cam.y
        for x, y, z, vx, vy, vz, age, life, kind, size in self.p:
            if age >= life:
                continue
            f = min(1.0, (life - age) / .3)
            sx, sy = int(x - ox), int(y - oy)
            if kind == 2:                                # nubecita de polvo que crece y se desvanece
                q = age / life
                img = self.puff[min(2, int((size + q * .8) * 2))]
                img.set_alpha(int(170 * (1 - q) * min(1.0, age / .1)))
                c.blit(img, (sx - img.get_width() // 2, sy - img.get_height() // 2))
            elif kind == 0:                              # tierrita
                g = int(120 * f)
                pygame.draw.circle(c, (g, int(g * .8), int(g * .6)), (sx, sy - int(z)), 3)
            else:                                        # piedra
                r = int(size) if size else 4
                if z > 1:
                    pygame.draw.circle(c, (8, 6, 5), (sx, sy), r)
                g = int(110 * f)
                pygame.draw.circle(c, (g, int(g * .85), int(g * .7)), (sx, sy - int(z)), r)
                c.fill((min(255, g + 50),) * 3, (sx - 1, sy - int(z) - 2, 2, 1))


def _dust_puff(r):
    """Nubecita de polvo suave (se reutiliza con distinta transparencia)."""
    s = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
    for i in range(r, 0, -1):
        a = int(200 * (1 - i / r) ** 1.4)
        pygame.draw.circle(s, (120, 98, 74, a), (r, r), i)
    return s
