"""Ambiente de cada acto (propuesta 3.4: «en cada acto baja a un lugar peor»).

  Acto I  · Galerías de los Hongos: esporas que brillan y suben despacio desde los hongos luminosos.
  Acto III· Mina Vieja: polvo que flota en la luz de Mullo y tierrita que cae de las vigas viejas
            (los faroles de la mina están apagados: es una mina abandonada).
  (El Acto II ya tiene su niebla baja sobre el Lago Negro.)

Pensado para no cargar el rendimiento: un número fijo de partículas que se reciclan (nunca se crean listas nuevas
por cuadro), solo alrededor de la cámara, sprites pequeños hechos una vez, y la mitad de partículas en el navegador.
"""
import math
import random

import pygame

from settings import IS_WEB, W, H

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
    def update(self, dt, cam, bat, shake=0.0):
        if not self.p:
            return
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
