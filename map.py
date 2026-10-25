"""Cueva: generación aleatoria, escenario temático por nivel, colisión, rutas, render del fondo y minimapa.

Cada noche "el agua y las raíces mueven los túneles", así que la cueva se genera al azar en cada partida.
Nivel 1: Galerías de los Hongos (hongos luminosos, telarañas, rastros de las crías).
Nivel 2: Lago Negro (agua quieta, islotes, niebla; la Sala del Eco en la isla central).
Nivel 3: Mina Vieja (vigas, rieles, vagonetas, lámparas apagadas y una corriente de aire hacia la salida).
"""
import math
import random
from collections import deque

import pygame

import decor
from settings import (TILE, MAP_W, MAP_H, WORLD_W, WORLD_H, NEST, NEST_T, NEST_R, SAFE_R, TAU, MEMORY_ALPHA)
from story import PUPS, LEVELS

T = TILE
MIN_OPEN = 1800                          # tiles abiertos mínimos para aceptar una cueva
DIRS = ((0, -1), (0, 1), (-1, 0), (1, 0))               # arriba, abajo, izquierda, derecha


def _mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


# Paleta y decoración de cada escenario
THEMES = {
    'fungi': dict(floor=(46, 66, 68), wall=(6, 12, 13), rim_hi=(120, 196, 178), rim_mid=(62, 114, 106),
                  speck=(54, 78, 80), crystals=[(90, 220, 200), (120, 255, 190)], n_crystals=35, n_fungi=330,
                  fungus=((22, 72, 60), (110, 255, 200)), mini_floor=(52, 88, 84), mini_wall=(14, 24, 24)),
    'lake': dict(floor=(44, 46, 76), wall=(6, 6, 16), rim_hi=(104, 108, 178), rim_mid=(60, 62, 112),
                 speck=(52, 54, 86), crystals=[(110, 130, 255)], n_crystals=26, n_fungi=40,
                 fungus=((20, 50, 44), (80, 200, 150)), mini_floor=(56, 56, 96), mini_wall=(14, 14, 28),
                 water=(10, 14, 36)),
    'mine': dict(floor=(68, 54, 42), wall=(12, 9, 7), rim_hi=(168, 126, 84), rim_mid=(104, 78, 52),
                 speck=(80, 64, 48), crystals=[(255, 170, 80)], n_crystals=22, n_fungi=28,
                 fungus=((40, 30, 20), (200, 150, 80)), mini_floor=(92, 72, 52), mini_wall=(26, 20, 14)),
}


class CaveMap:
    def __init__(self, level=1):
        self.level = level
        self.theme_name = LEVELS[level]['theme']
        self.theme = THEMES[self.theme_name]
        self.w, self.h = MAP_W, MAP_H
        self.g = None
        self.centers = [(NEST_T[0], NEST_T[1], 6.0)]
        for _ in range(25):
            if self._generate():
                break
        else:                              # último recurso: sala abierta
            self.g = [[1 if x in (0, self.w - 1) or y in (0, self.h - 1) else 0
                       for x in range(self.w)] for y in range(self.h)]
            self.centers = [(NEST_T[0], NEST_T[1], 6.0), (self.w / 2, self.h / 2, 8.0), (self.w - 12, self.h - 10, 8.0)]
        self.water = bytearray(self.w * self.h)
        self.web = set()                   # tiles con la cortina de telarañas (bloquean hasta que gritas)
        self.echo = self.lair = None       # Sala del Eco (nivel 2) y guarida del jefe (nivel 3)
        self.islets = []
        if self.theme_name == 'lake':
            self._make_lake()
        self.secret_mask = bytearray(self.w * self.h)      # sala secreta (cambia de lugar en cada partida)
        self.secret = None
        self.secret_found = False
        self._make_secret()
        self._index_open()
        self.flow = self._distances(NEST_T)                      # distancia (en tiles) al punto de entrega
        self.pup_spots = self._plan_pups()
        self.trail_marks, self.rails, self.carts, self.beams, self.lamps, self.cobwebs = [], [], [], [], [], []
        self.crystals = []                 # (x, y, color)
        self.fungi = []                    # (x, y) parches de hongos luminosos
        self.algae = []                    # (x, y) algas del Lago Negro
        self.secret_lights, self.dew = [], []
        self.stalactites = []              # puntas de estalactitas (de ahí caen las gotas)
        if self.theme_name == 'fungi':
            self._make_web()
        if self.theme_name in ('fungi', 'lake'):
            self._make_trails(1.0 if self.theme_name == 'fungi' else .28)
        self.current = bytearray(self.w * self.h)          # corriente de aire de la mina (zona que guía la huida)
        self.molt = None                                    # piel vieja de Xolthar en la entrada de la mina
        if self.theme_name == 'mine':
            self._make_mine()
            self._make_current()
        self._place_props()
        self.bg = self._render()
        self.explored = bytearray(self.w * self.h)
        self.visited = bytearray(self.w * self.h)           # lo que has recorrido (memoria visual)
        self.mem_version = 0                                # cambia cada vez que se recorre un tile nuevo
        self.mem = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        self.minimap = pygame.Surface((self.w * 2, self.h * 2))
        self.minimap.fill((6, 5, 9))

    # ------------------------------------------------------------ generación
    def _generate(self):
        """Cavernas amplias de borde irregular unidas por pasajes anchos (nada de laberinto)."""
        w, h = self.w, self.h
        g = [[1] * w for _ in range(h)]
        cols, rows = 5, 3
        cw, ch = (w - 6) / cols, (h - 6) / rows
        centers = [(NEST_T[0], NEST_T[1], 6.0)]
        for r in range(rows):
            for c in range(cols):
                cx, cy = 3 + cw * (c + .5) + random.uniform(-3, 3), 3 + ch * (r + .5) + random.uniform(-3, 3)
                if math.hypot(cx - NEST_T[0], cy - NEST_T[1]) < 12:
                    continue
                centers.append((cx, cy, random.uniform(6.5, 9.5)))
        for cx, cy, rad in centers:                               # cavernas con contorno ondulado
            ph = [random.uniform(0, math.tau) for _ in range(3)]
            amp = [random.uniform(.08, .2), random.uniform(.05, .14), random.uniform(.03, .08)]
            for y in range(max(2, int(cy - rad * 1.5)), min(h - 2, int(cy + rad * 1.5) + 1)):
                for x in range(max(2, int(cx - rad * 1.5)), min(w - 2, int(cx + rad * 1.5) + 1)):
                    th = math.atan2(y - cy, x - cx)
                    lim = rad * (1 + amp[0] * math.sin(2 * th + ph[0]) + amp[1] * math.sin(3 * th + ph[1])
                                 + amp[2] * math.sin(5 * th + ph[2]))
                    if math.hypot(x - cx, (y - cy) * 1.1) < lim:
                        g[y][x] = 0
        # pasajes anchos: árbol de expansión mínimo + algunos ciclos extra
        edges, linked, rest = [], {0}, set(range(1, len(centers)))
        while rest:
            i, j = min(((i, j) for i in linked for j in rest),
                       key=lambda e: math.dist(centers[e[0]][:2], centers[e[1]][:2]))
            edges.append((i, j))
            linked.add(j)
            rest.discard(j)
        for _ in range(4):
            i, j = random.sample(range(len(centers)), 2)
            if math.dist(centers[i][:2], centers[j][:2]) < 26:
                edges.append((i, j))
        for i, j in edges:
            x, y = centers[i][:2]
            tx, ty = centers[j][:2]
            wid = random.uniform(1.8, 2.6)
            for _ in range(400):
                if math.hypot(tx - x, ty - y) < 1.5:
                    break
                ang = math.atan2(ty - y, tx - x) + random.uniform(-.55, .55)
                x, y = x + math.cos(ang), y + math.sin(ang)
                for yy in range(int(y - wid) - 1, int(y + wid) + 2):
                    for xx in range(int(x - wid) - 1, int(x + wid) + 2):
                        if 2 <= xx < w - 2 and 2 <= yy < h - 2 and math.hypot(xx - x, yy - y) <= wid:
                            g[yy][xx] = 0
        # rocas sueltas dentro de las cavernas grandes (afloramientos), lejos del nido
        for cx, cy, rad in centers[1:]:
            for _ in range(random.randint(1, 3)):
                a, d = random.uniform(0, math.tau), rad * random.uniform(.25, .55)
                ox, oy, rr = cx + math.cos(a) * d, cy + math.sin(a) * d, random.uniform(1.2, 2.3)
                for y in range(int(oy - rr) - 1, int(oy + rr) + 2):
                    for x in range(int(ox - rr) - 1, int(ox + rr) + 2):
                        if 2 <= x < w - 2 and 2 <= y < h - 2 and math.hypot(x - ox, y - oy) <= rr * random.uniform(.8, 1.1):
                            g[y][x] = 1
        for y in range(h):                                        # el nido siempre despejado
            for x in range(w):
                if math.hypot(x - NEST_T[0], y - NEST_T[1]) <= 4.3 and 1 < x < w - 2 and 1 < y < h - 2:
                    g[y][x] = 0
        # rugosidad del contorno y suavizado (bordes orgánicos, sin dientes de sierra)
        for y in range(2, h - 2):
            for x in range(2, w - 2):
                if g[y][x] != g[y][x + 1] and random.random() < .22:
                    g[y][x] ^= 1
        for _ in range(2):
            ng = [row[:] for row in g]
            for y in range(1, h - 1):
                for x in range(1, w - 1):
                    n = sum(g[y + j][x + i] for j in (-1, 0, 1) for i in (-1, 0, 1))
                    ng[y][x] = 1 if n >= 5 else 0
            g = ng
        for y in range(h):
            g[y][0] = g[y][w - 1] = 1
        for x in range(w):
            g[0][x] = g[h - 1][x] = 1
        for _ in range(2):                                        # quita salientes de 1 tile (bordes más fluidos)
            for y in range(2, h - 2):
                for x in range(2, w - 2):
                    if (x, y) == NEST_T or math.hypot(x - NEST_T[0], y - NEST_T[1]) <= 4.3:
                        continue
                    same = sum(g[y + j][x + i] == g[y][x] for i, j in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                    if same <= 1:
                        g[y][x] ^= 1
        for y in range(2, h - 2):                                 # rellena islotes de roca diminutos
            for x in range(2, w - 2):
                if g[y][x] == 1:
                    comp = self._comp(g, x, y, 1, 14)
                    if comp is not None:
                        for cx, cy in comp:
                            g[cy][cx] = 0
        seen = self._flood(g, *NEST_T)                            # solo lo alcanzable desde el nido
        for y in range(h):
            for x in range(w):
                if not g[y][x] and (x, y) not in seen:
                    g[y][x] = 1
        if len(seen) < MIN_OPEN:
            return False
        self.g = g
        self.centers = centers
        return True

    @staticmethod
    def _comp(g, sx, sy, val, cap):
        """Componente de tiles == val desde (sx, sy). Devuelve None si toca el borde o supera cap."""
        seen, dq = {(sx, sy)}, deque([(sx, sy)])
        while dq:
            x, y = dq.popleft()
            if x <= 1 or y <= 1 or x >= len(g[0]) - 2 or y >= len(g) - 2:
                return None
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) not in seen and g[ny][nx] == val:
                    seen.add((nx, ny))
                    dq.append((nx, ny))
                    if len(seen) > cap:
                        return None
        return seen

    @staticmethod
    def _flood(g, sx, sy):
        seen, dq = {(sx, sy)}, deque([(sx, sy)])
        while dq:
            x, y = dq.popleft()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) not in seen and not g[ny][nx]:
                    seen.add((nx, ny))
                    dq.append((nx, ny))
        return seen


    # ------------------------------------------------------------ escenarios especiales
    def _index_open(self):
        w, h = self.w, self.h
        self.land = [(x, y) for y in range(1, h - 1) for x in range(1, w - 1)
                     if not self.g[y][x] and not self.water[y * w + x] and not self.secret_mask[y * w + x]]
        self.open = [(x, y) for x, y in self.land
                     if all(not self.g[y + j][x + i] and not self.water[(y + j) * w + x + i]
                            for j in (-1, 0, 1) for i in (-1, 0, 1))] or self.land

    def _make_secret(self):
        """Sala secreta excavada en la roca, unida a la cueva por un pasadizo de un tile de ancho.
        Los enemigos no entran: sirve para esconderse. Su lugar es distinto en cada partida."""
        w, h, g = self.w, self.h, self.g
        dist = [[-1] * w for _ in range(h)]
        dq = deque()
        for y in range(h):
            for x in range(w):
                if not g[y][x]:
                    dist[y][x] = 0
                    dq.append((x, y))
        while dq:
            x, y = dq.popleft()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < w and 0 <= ny < h and dist[ny][nx] < 0:
                    dist[ny][nx] = dist[y][x] + 1
                    dq.append((nx, ny))
        def ellipse(cx, cy):
            return {(x, y) for y in range(cy - 4, cy + 5) for x in range(cx - 5, cx + 6)
                    if ((x - cx) / 3.6) ** 2 + ((y - cy) / 2.9) ** 2 <= 1}
        cands = [(x, y) for y in range(6, h - 6) for x in range(6, w - 6)
                 if 6 <= dist[y][x] <= 10 and math.hypot(x - NEST_T[0], y - NEST_T[1]) > 16]
        random.shuffle(cands)
        room = None
        for cx, cy in cands[:400]:                          # toda la sala rodeada de roca (entrada escondida)
            r = ellipse(cx, cy)
            if all(dist[y][x] >= 3 for x, y in r):
                room = r
                break
        if not room:
            return
        path, x, y = [], cx, cy                             # pasadizo: baja por la distancia hasta la cueva
        while dist[y][x] > 0:
            x, y = min(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)), key=lambda t: dist[t[1]][t[0]])
            if dist[y][x] > 0 and (x, y) not in room:
                path.append((x, y))
        for x, y in room | set(path):
            g[y][x] = 0
            self.secret_mask[y * w + x] = 1
        mouth = path[-1] if path else (cx, cy)
        self.secret = dict(center=self._px((cx, cy)), tiles=room | set(path), room=room, path=path,
                           mouth=self._px(mouth), rx=3.6 * T, ry=2.9 * T)

    def in_secret(self, x, y):
        tx, ty = int(x // T), int(y // T)
        return 0 <= tx < self.w and 0 <= ty < self.h and bool(self.secret_mask[ty * self.w + tx])

    def _make_lake(self):
        """Salones inundados con agua quieta e islotes; la caverna más central es la Sala del Eco."""
        w = self.w
        cands = [c for c in self.centers[1:] if math.hypot(c[0] - NEST_T[0], c[1] - NEST_T[1]) > 14]
        if not cands:
            return
        mid = min(cands, key=lambda c: math.hypot(c[0] - w / 2, c[1] - self.h / 2))
        lakes = [mid] + [c for c in cands if c is not mid and random.random() < .55]
        for cx, cy, rad in lakes:
            isl = 3.0 if (cx, cy, rad) == mid else (random.uniform(1.6, 2.5) if random.random() < .65 else 0)
            ix, iy = cx + (0 if isl == 3.0 else random.uniform(-1.5, 1.5)), cy + (0 if isl == 3.0 else random.uniform(-1, 1))
            lim = rad * .74
            for y in range(int(cy - rad * 1.2), int(cy + rad * 1.2) + 1):
                for x in range(int(cx - rad * 1.2), int(cx + rad * 1.2) + 1):
                    if not (1 < x < w - 2 and 1 < y < self.h - 2) or self.g[y][x]:
                        continue
                    if math.hypot(x - cx, (y - cy) * 1.1) < lim and math.hypot(x - ix, y - iy) > isl:
                        self.water[y * w + x] = 1
            if isl:
                self.islets.append((ix * T + T / 2, iy * T + T / 2, isl))
        self.echo = (mid[0] * T + T / 2, mid[1] * T + T / 2)

    def _distances(self, start, walk=False):
        """Distancia BFS en tiles desde start (para la corriente de aire y para elegir lugares lejanos)."""
        dist = [[-1] * self.w for _ in range(self.h)]
        sx, sy = start
        dist[sy][sx] = 0
        dq = deque([start])
        blocked = self.blocked if walk else self.solid
        while dq:
            x, y = dq.popleft()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < self.w and 0 <= ny < self.h and dist[ny][nx] < 0 and not blocked(nx, ny):
                    dist[ny][nx] = dist[y][x] + 1
                    dq.append((nx, ny))
        return dist

    def _px(self, t):
        return (t[0] * T + T / 2, t[1] * T + T / 2)

    def _snap(self, p):
        """Centro del tile de tierra más cercano a p."""
        t = min(self.land, key=lambda t: math.dist(self._px(t), p))
        return self._px(t)

    def _plan_pups(self):
        """Dónde está cada cría del nivel (en el mismo orden que story.PUPS)."""
        entries = PUPS[self.level]
        spots, flow = [], self.flow
        far = [t for t in self.land if flow[t[1]][t[0]] > 22]
        pool = far or self.land

        def pick(min_d=450, prefer_far=False):
            best = None
            for _ in range(400):
                t = random.choice(pool)
                p = self._px(t)
                if all(math.dist(p, q) >= min_d for q in spots):
                    if not prefer_far:
                        return p
                    if best is None or flow[t[1]][t[0]] > flow[int(best[1] // T)][int(best[0] // T)]:
                        best = p
            return best or self._px(random.choice(pool))

        if self.level == 2 and self.echo:
            self.echo = self._snap(self.echo)
            self.islets = [(*self._snap((x, y)), r) for x, y, r in self.islets]
            out = []
            others = [i for i, (_, b) in enumerate(entries) if b != 'eco']
            spots.append(self.echo)
            res = {}
            w = self.w                                     # solo Eco está en la isla central; las demás, en tierra firme
            dry = [t for t in pool if not any(self.water[(t[1] + j) * w + t[0] + i]
                                              for j in range(-3, 4) for i in range(-3, 4)
                                              if 0 <= t[0] + i < w and 0 <= t[1] + j < self.h)]
            pool = dry or pool
            got = []
            for i in others:
                got.append(pick())
                spots.append(got[-1])
            for i, sp in zip(others, self._by_distance(got)):     # Nube, Tito y Mora en orden de distancia
                res[i] = sp
            for i, (_, b) in enumerate(entries):
                out.append(self.echo if b == 'eco' else res[i])
            return out
        if self.level == 3:
            ends = [c for c in self.centers[1:] if flow[int(c[1])][int(c[0])] > 0]
            c = max(ends, key=lambda c: flow[int(c[1])][int(c[0])]) if ends else self.centers[-1]
            lt = (int(c[0]), int(c[1]))
            if self.g[lt[1]][lt[0]]:
                lt = min(self.land, key=lambda t: math.hypot(t[0] - c[0], t[1] - c[1]))
            self.lair = self._px(lt)
            spots.append(self.lair)
            lair_d = flow[lt[1]][lt[0]]
            paco = None                                    # Paco queda antes que las gemelas: primero lo rescata a él
            for _ in range(12):
                cand = pick(700)
                ct = (int(cand[0] // T), int(cand[1] // T))
                if 0 <= flow[ct[1]][ct[0]] < lair_d * .85:
                    paco = cand
                    break
                paco = paco or cand
            return [paco, self._snap((self.lair[0] + 50, self.lair[1] + 12))]
        out = [pick() for _ in range(len(entries))]
        return self._by_distance(out)                       # Chispa es la primera que encuentra, luego Bruno y Lía

    def _by_distance(self, spots):
        """Ordena los lugares del más cercano al nido al más lejano (las crías se encuentran en ese orden)."""
        flow = self.flow
        def far(p):
            tx, ty = int(p[0] // T), int(p[1] // T)
            d = flow[ty][tx] if 0 <= ty < self.h and 0 <= tx < self.w else -1
            return d if d >= 0 else 1e6
        return sorted(spots, key=far)

    def _make_web(self):
        """Cortina de telarañas en el punto más estrecho del camino hacia la cría más lejana (nivel 1)."""
        target = self.pup_spots[2]
        path = self.path(NEST, target, walk=False) or []
        tiles = [(int(x // T), int(y // T)) for x, y in path]
        best = None
        for maxw in (7, 10, 14):                       # si no hay un paso angosto, acepta uno más ancho
            for k in range(int(len(tiles) * .45), max(int(len(tiles) * .9), int(len(tiles) * .45) + 1)):
                if k < 1 or k >= len(tiles) - 2:
                    continue
                (x0, y0), (x1, y1) = tiles[k - 1], tiles[k + 1]
                dx, dy = x1 - x0, y1 - y0
                px, py = (-dy, dx) if abs(dx) + abs(dy) else (1, 0)
                n = math.hypot(px, py) or 1
                px, py = px / n, py / n
                line = [tiles[k]]
                ok = True
                for sd in (1, -1):
                    for s in range(1, maxw):
                        tx, ty = int(round(tiles[k][0] + px * s * sd)), int(round(tiles[k][1] + py * s * sd))
                        if self.g[ty][tx]:
                            break
                        line.append((tx, ty))
                    else:
                        ok = False
                if ok and math.dist(self._px(tiles[k]), target) > 120 and (best is None or len(line) < len(best)):
                    best = line
            if best:
                break
        if best:
            ext = set(best)
            for tx, ty in best:                       # engrosa la cortina para que no queden huecos en diagonal
                for i, j in DIRS:
                    if not self.g[ty + j][tx + i] and math.dist(self._px((tx + i, ty + j)), target) > 90:
                        ext.add((tx + i, ty + j))
            self.web = {t for t in ext if all(math.dist(self._px(t), p) > 70 for p in self.pup_spots)}
        self.web_center = (sum(self._px(t)[0] for t in self.web) / len(self.web),
                           sum(self._px(t)[1] for t in self.web) / len(self.web)) if self.web else None

    def _make_trails(self, frac):
        """Rastros: piedritas movidas y rasguños. En el Acto I son de Chispa y solo llevan hasta ella."""
        web, self.web = self.web, set()                     # los rastros pasan también bajo la telaraña
        spots = self.pup_spots
        if self.level == 1:                                 # Acto I: solo los rastros de Chispa, que llevan hacia ella
            spots = [sp for (nm, _), sp in zip(PUPS[1], self.pup_spots) if nm == 'Chispa']
        paths = [self.path(NEST, spot, walk=False) or [] for spot in spots]
        self.web = web
        chispa = self.level == 1
        for path in paths:
            start = int(len(path) * (1 - frac))
            kinds = ('pebble', 'claw')                      # piedritas movidas y rasguños
            for n, k in enumerate(range(max(3, start), len(path) - 1, 2)):
                x, y = path[k]
                if chispa:                                  # en orden y a lo largo del camino: se lee como una pista
                    nx, ny = path[k + 1]
                    self.trail_marks.append((x + random.uniform(-4, 4), y + random.uniform(-4, 4), kinds[n % 2],
                                             math.atan2(ny - y, nx - x)))
                else:
                    self.trail_marks.append((x + random.uniform(-8, 8), y + random.uniform(-8, 8),
                                             random.choice(kinds), random.uniform(0, TAU)))

    @staticmethod
    def _smooth(pts, win=3):
        out = []
        for i in range(len(pts)):
            seg = pts[max(0, i - win):i + win + 1]
            out.append((sum(p[0] for p in seg) / len(seg), sum(p[1] for p in seg) / len(seg)))
        return out

    def _make_mine(self):
        """Rieles hasta la guarida, vagonetas, vigas en los pasillos y lámparas apagadas."""
        path = self.path(NEST, self.lair, walk=False) or []
        self.rails = self._smooth([NEST] + path, 3)
        if len(self.rails) > 10:
            for _ in range(4):
                i = random.randint(5, len(self.rails) - 6)
                x, y = self.rails[i]
                (ax, ay), (bx, by) = self.rails[i - 2], self.rails[i + 2]
                self.carts.append((x, y, math.atan2(by - ay, bx - ax), False))
        cx, cy = self.pup_spots[1]
        for dx in (-22, 22):                                   # dos vagonetas: una para Bolillo y otra para Pozolito
            self.carts.append((cx + dx, cy, 0.0, False))
        g = self.g
        used = []
        for x, y in self.land:
            if math.dist(self._px((x, y)), NEST) < 160 or len(self.beams) > 60:
                continue
            for horiz in (True, False):
                a = b = 0
                if horiz:
                    while a < 4 and not g[y][x - a - 1]:
                        a += 1
                    while b < 4 and not g[y][x + b + 1]:
                        b += 1
                    if g[y][x - a - 1] and g[y][x + b + 1] and 1 <= a + b <= 4 and all(
                            0 <= y + k < self.h and not g[y + k][xx] for xx in range(x - a, x + b + 1) for k in (-2, -1, 1, 2)):
                        seg = ((x - a) * T - 4, y * T + T / 2, (x + b + 1) * T + 4, y * T + T / 2)
                    else:
                        continue
                else:
                    while a < 4 and not g[y - a - 1][x]:
                        a += 1
                    while b < 4 and not g[y + b + 1][x]:
                        b += 1
                    if g[y - a - 1][x] and g[y + b + 1][x] and 1 <= a + b <= 4 and all(
                            0 <= x + k < self.w and not g[yy][x + k] for yy in range(y - a, y + b + 1) for k in (-2, -1, 1, 2)):
                        seg = (x * T + T / 2, (y - a) * T - 4, x * T + T / 2, (y + b + 1) * T + 4)
                    else:
                        continue
                c = ((seg[0] + seg[2]) / 2, (seg[1] + seg[3]) / 2)
                if all(math.dist(c, u) > 230 for u in used) and random.random() < .5:
                    used.append(c)
                    self.beams.append(seg)
                break
        for x, y in random.sample(self.land, min(len(self.land), 900)):
            if len(self.lamps) >= 45:
                break
            for side, (dx, dy) in enumerate(DIRS):
                if g[y + dy][x + dx] and random.random() < .08:
                    p = (x * T + T / 2 + dx * 12, y * T + T / 2 + dy * 12)
                    if all(math.dist(p, q[:2]) > 200 for q in self.lamps):
                        self.lamps.append((p[0], p[1], side))
                    break


    def _make_current(self):
        """La corriente de aire fresco: un pasillo a lo largo de los rieles, desde la guarida hasta la salida
        (el nido). Es la zona donde, con la 3.ª mejora, el impulso se recarga más rápido."""
        w, h = self.w, self.h
        for x, y in self.rails:
            tx, ty = int(x // T), int(y // T)
            for j in range(-2, 3):
                for i in range(-2, 3):
                    nx, ny = tx + i, ty + j
                    if 0 <= nx < w and 0 <= ny < h and i * i + j * j <= 5 and not self.g[ny][nx]:
                        self.current[ny * w + nx] = 1
        n = len(self.rails)                                    # la piel vieja: junto a los rieles, cerca de la entrada
        for k in range(min(n - 2, 7), min(n - 2, 18)):
            (ax, ay), (bx, by) = self.rails[k - 1], self.rails[k + 1]
            ang = math.atan2(by - ay, bx - ax)
            for side in (1, -1):
                x = self.rails[k][0] - math.sin(ang) * 46 * side
                y = self.rails[k][1] + math.cos(ang) * 46 * side
                if math.dist((x, y), NEST) > SAFE_R + 60 and all(not self.solid_px(x + math.cos(ang) * d, y + math.sin(ang) * d)
                                                                  for d in (-80, -40, 0, 40, 80)):
                    self.molt = (x, y, ang)
                    return

    def in_current(self, x, y):
        tx, ty = int(x // T), int(y // T)
        return 0 <= tx < self.w and 0 <= ty < self.h and bool(self.current[ty * self.w + tx])

    # ------------------------------------------------------------ consultas
    def solid(self, tx, ty):
        """Pared (o telaraña): bloquea a Mullo."""
        return tx < 0 or ty < 0 or tx >= self.w or ty >= self.h or self.g[ty][tx] or (tx, ty) in self.web

    def blocked(self, tx, ty):
        """Para los que caminan (arañas, escarabajos, cazadores): también el agua."""
        return self.solid(tx, ty) or self.water[ty * self.w + tx] or self.secret_mask[ty * self.w + tx]

    def solid_px(self, x, y):
        return self.solid(int(x // T), int(y // T))

    def is_water(self, x, y):
        tx, ty = int(x // T), int(y // T)
        return 0 <= tx < self.w and 0 <= ty < self.h and self.water[ty * self.w + tx]

    def los(self, a, b, walk=True):
        """Línea libre entre dos puntos (con un pequeño margen lateral)."""
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy)
        if d < 1:
            return True
        ux, uy = dx / d, dy / d
        steps = int(d // 10) + 1
        blk = self.blocked if walk else self.solid
        for off in (0, 9, -9):
            ox, oy = -uy * off, ux * off
            for i in range(steps + 1):
                f = min(d, i * 10)
                if blk(int((a[0] + ux * f + ox) // T), int((a[1] + uy * f + oy) // T)):
                    return False
        return True

    def _blockmap(self, walk):
        """Mapa plano de casillas bloqueadas (se recalcula solo cuando cambia la telaraña). Acelera la búsqueda."""
        key = (walk, len(self.web))
        cache = getattr(self, '_bm', None)
        if cache is None or cache[0] != key:
            w, h = self.w, self.h
            bm = bytearray(w * h)
            for y in range(h):
                row = self.g[y]
                for x in range(w):
                    i = y * w + x
                    if row[x] or (x, y) in self.web or x in (0, w - 1) or y in (0, h - 1) or \
                            (walk and (self.water[i] or self.secret_mask[i])):
                        bm[i] = 1
            self._bm = cache = (key, bm)
        return cache[1]

    def path(self, a, b, limit=7000, walk=True):
        """BFS 4-conectado entre posiciones en píxeles -> lista de centros de tile (sin el origen)."""
        w = self.w
        sx, sy = int(a[0] // T), int(a[1] // T)
        tx, ty = int(b[0] // T), int(b[1] // T)
        if not (0 <= sx < w and 0 <= sy < self.h and 0 <= tx < w and 0 <= ty < self.h):
            return None
        bm = self._blockmap(walk)
        s, t = sy * w + sx, ty * w + tx
        if bm[s] or bm[t]:
            return None
        if s == t:
            return [b]
        prev = {s: -1}
        dq, n = deque([s]), 0
        while dq and n < limit:
            cur = dq.popleft()
            n += 1
            if cur == t:
                break
            for nb in (cur + 1, cur - 1, cur + w, cur - w):
                if not bm[nb] and nb not in prev:
                    prev[nb] = cur
                    dq.append(nb)
        if t not in prev:
            return None
        out, cur = [], t
        while cur != s:
            out.append(((cur % w) * T + T / 2, (cur // w) * T + T / 2))
            cur = prev[cur]
        out.reverse()
        out[-1] = b
        return out

    def flow_dir(self, x, y):
        """Hacia dónde sopla la corriente de aire (hacia el punto de entrega) en (x, y)."""
        tx, ty = int(x // T), int(y // T)
        if not (0 <= tx < self.w and 0 <= ty < self.h):
            return 0.0, 0.0
        d0 = self.flow[ty][tx]
        if d0 <= 0:
            return 0.0, 0.0
        best, bd = (0, 0), d0
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                nx, ny = tx + i, ty + j
                if 0 <= nx < self.w and 0 <= ny < self.h and 0 <= self.flow[ny][nx] < bd:
                    best, bd = (i, j), self.flow[ny][nx]
        n = math.hypot(*best) or 1
        return best[0] / n, best[1] / n

    def clear_web(self, x, y, r):
        """El grito despeja la telaraña cercana. Devuelve cuántos tiles se rompieron."""
        hit = {t for t in self.web if math.dist(self._px(t), (x, y)) < r + T}
        if hit:
            self.web -= hit
            for tx, ty in hit:
                i = ty * self.w + tx
                if self.explored[i]:
                    self.minimap.fill(self.theme['mini_floor'], (tx * 2, ty * 2, 2, 2))
        return len(hit)

    def free_spot(self, far_from, dist, avoid=(), avoid_d=0):
        """Punto abierto (en tierra) a >= dist de far_from y >= avoid_d de los puntos de avoid."""
        best, bd = None, -1
        for _ in range(300):
            tx, ty = random.choice(self.open)
            p = (tx * T + T / 2, ty * T + T / 2)
            d = math.dist(p, far_from)
            if d >= dist and all(math.dist(p, q) >= avoid_d for q in avoid):
                return p
            if d > bd:
                best, bd = p, d
        return best

    def ring_spot(self, center, rmin, rmax):
        """Punto abierto a una distancia entre rmin y rmax de center (aparición de emboscada)."""
        for _ in range(300):
            tx, ty = random.choice(self.open)
            p = (tx * T + T / 2, ty * T + T / 2)
            if rmin <= math.dist(p, center) <= rmax:
                return p
        return self.free_spot(center, rmin)

    def near_spot(self, x, y, r):
        for _ in range(40):
            tx, ty = random.choice(self.open)
            p = (tx * T + T / 2, ty * T + T / 2)
            if math.dist(p, (x, y)) < r:
                return p
        tx, ty = random.choice(self.open)
        return (tx * T + T / 2, ty * T + T / 2)

    def resolve(self, o, rad, walk=False):
        """Saca al círculo (o.x, o.y, rad) de las paredes. Devuelve (choque, nx, ny) con la normal media."""
        hit, nx, ny = False, 0.0, 0.0
        blk = self.blocked if walk else self.solid
        for _ in range(2):
            for ty in range(int((o.y - rad) // T), int((o.y + rad) // T) + 1):
                for tx in range(int((o.x - rad) // T), int((o.x + rad) // T) + 1):
                    if not blk(tx, ty):
                        continue
                    x0, y0 = tx * T, ty * T
                    cx, cy = min(max(o.x, x0), x0 + T), min(max(o.y, y0), y0 + T)
                    dx, dy = o.x - cx, o.y - cy
                    d2 = dx * dx + dy * dy
                    if d2 >= rad * rad:
                        continue
                    if d2 == 0:                       # centro dentro del tile: salir por el lado más cercano
                        opts = ((o.x - x0, -1, 0), (x0 + T - o.x, 1, 0), (o.y - y0, 0, -1), (y0 + T - o.y, 0, 1))
                        dist, ax, ay = min(opts)
                        o.x, o.y = (x0 - rad if ax < 0 else x0 + T + rad if ax > 0 else o.x), \
                                   (y0 - rad if ay < 0 else y0 + T + rad if ay > 0 else o.y)
                        nx, ny, hit = nx + ax, ny + ay, True
                    else:
                        d = math.sqrt(d2)
                        o.x += dx / d * (rad - d)
                        o.y += dy / d * (rad - d)
                        nx, ny, hit = nx + dx / d, ny + dy / d, True
        n = math.hypot(nx, ny)
        return (hit, nx / n, ny / n) if n else (hit, 0.0, 0.0)

    # ------------------------------------------------------------ exploración / minimapa
    def mark(self, tx, ty, mem=False):
        """Marca un tile como descubierto en el minimapa; con mem=True también queda en la memoria visual."""
        if not (0 <= tx < self.w and 0 <= ty < self.h):
            return
        i = ty * self.w + tx
        if self.secret_mask[i] and not self.secret_found:     # la sala secreta no sale en el mapa hasta encontrarla
            return
        if not self.explored[i]:
            self.explored[i] = 1
            th = self.theme
            col = th['mini_wall'] if self.g[ty][tx] else ((26, 40, 96) if self.water[i] else th['mini_floor'])
            self.minimap.fill(col, (tx * 2, ty * 2, 2, 2))
        if mem and not self.visited[i]:
            self.visited[i] = 1
            self.mem_version += 1
            self.mem.set_at((tx, ty), (0, 0, 0, MEMORY_ALPHA))

    def mark_circle(self, x, y, r, mem=False):
        tr = int(r // T) + 1
        cx, cy = int(x // T), int(y // T)
        r2 = (r / T) ** 2
        for ty in range(max(0, cy - tr), min(self.h, cy + tr + 1)):
            for tx in range(max(0, cx - tr), min(self.w, cx + tr + 1)):
                if (tx - cx) ** 2 + (ty - cy) ** 2 <= r2:
                    self.mark(tx, ty, mem)

    # ------------------------------------------------------------ render
    @staticmethod
    def _band(x0, y0, side, off, th):
        """Franja dentro de un tile, a `off` px del borde `side` (0 arriba, 1 abajo, 2 izq., 3 der.)."""
        if side == 0:
            return x0, y0 + off, T, th
        if side == 1:
            return x0, y0 + T - off - th, T, th
        if side == 2:
            return x0 + off, y0, th, T
        return x0 + T - off - th, y0, th, T

    def _render(self):
        th = self.theme
        FLOOR, WALL, RIM_HI, RIM_MID, SPECK = th['floor'], th['wall'], th['rim_hi'], th['rim_mid'], th['speck']
        AO = tuple(_mix(FLOOR, WALL, k) for k in (.45, .3, .15))
        bg = pygame.Surface((WORLD_W, WORLD_H))
        bg.fill(FLOOR)
        rnd, ri = random.random, random.randint
        solid = lambda x, y: x < 0 or y < 0 or x >= self.w or y >= self.h or self.g[y][x]
        wat = self.water
        WATER = th.get('water', (0, 0, 0))
        for ty in range(self.h):
            for tx in range(self.w):
                x0, y0 = tx * T, ty * T
                if self.g[ty][tx]:
                    sh = ri(0, 3)
                    bg.fill((WALL[0] + sh, WALL[1] + sh, WALL[2] + sh), (x0, y0, T, T))
                    for _ in range(2):
                        c = ri(6, 12)
                        pygame.draw.circle(bg, (WALL[0] + c, WALL[1] + c, WALL[2] + c),
                                           (x0 + ri(2, T - 2), y0 + ri(2, T - 2)), ri(3, 8))
                elif wat[ty * self.w + tx]:
                    sh = ri(0, 2)
                    bg.fill((WATER[0] + sh, WATER[1] + sh, WATER[2] + sh), (x0, y0, T, T))
                    if rnd() < .35:                          # reflejos quietos
                        yy = y0 + ri(4, T - 4)
                        pygame.draw.line(bg, (24, 30, 64), (x0 + ri(0, 10), yy), (x0 + ri(16, T), yy), 1)
                else:
                    sh = ri(0, 3)
                    bg.fill((FLOOR[0] + sh, FLOOR[1] + sh, FLOOR[2] + sh), (x0, y0, T, T))
                    for _ in range(3):
                        c = ri(-8, 8)
                        bg.fill((SPECK[0] + c, SPECK[1] + c, SPECK[2] + c),
                                (x0 + ri(0, T - 3), y0 + ri(0, T - 3), ri(1, 3), ri(1, 3)))
        # orilla del agua, sombra junto a las paredes y borde luminoso de la roca
        for ty in range(self.h):
            for tx in range(self.w):
                x0, y0 = tx * T, ty * T
                if self.g[ty][tx]:
                    for side, (dx, dy) in enumerate(DIRS):
                        if not solid(tx + dx, ty + dy):
                            bg.fill(RIM_MID, self._band(x0, y0, side, 2, 3))
                            bg.fill(RIM_HI, self._band(x0, y0, side, 0, 2))
                elif wat[ty * self.w + tx]:
                    for side, (dx, dy) in enumerate(DIRS):
                        nx, ny = tx + dx, ty + dy
                        if not solid(nx, ny) and not wat[ny * self.w + nx]:
                            bg.fill((40, 60, 110), self._band(x0, y0, side, 0, 2))
                            bg.fill((22, 30, 66), self._band(x0, y0, side, 2, 3))
                            if rnd() < .5 and len(self.algae) < 160:
                                ax, ay = x0 + T / 2 + dx * 10 + ri(-6, 6), y0 + T / 2 + dy * 10 + ri(-6, 6)
                                decor.algae_cluster(bg, ax, ay, random)
                                if rnd() < .55:
                                    self.algae.append((ax, ay))
                else:
                    for side, (dx, dy) in enumerate(DIRS):
                        if solid(tx + dx, ty + dy):
                            for off, col in enumerate(AO):
                                bg.fill(col, self._band(x0, y0, side, off * 4, 4))
        # esquinas convexas de la roca recortadas (paredes menos "escalonadas")
        C = 10
        for ty in range(1, self.h - 1):
            for tx in range(1, self.w - 1):
                if not self.g[ty][tx]:
                    continue
                x0, y0 = tx * T, ty * T
                for sx in (-1, 1):
                    for sy in (-1, 1):
                        if solid(tx + sx, ty) or solid(tx, ty + sy) or wat[(ty + sy) * self.w + tx] or wat[ty * self.w + tx + sx]:
                            continue
                        px, py = x0 + (0 if sx < 0 else T), y0 + (0 if sy < 0 else T)
                        a, b = (px - sx * C, py), (px, py - sy * C)
                        pygame.draw.polygon(bg, FLOOR, [(px, py), a, b])
                        pygame.draw.line(bg, RIM_HI, a, b, 2)
        self._decorate(bg, th, solid)
        for x, y, kind, ang in self.trail_marks:
            if self.level == 1:
                decor.trail_mark(bg, x, y, kind, ang, 1.6)          # los rastros de Chispa: más grandes y claros
            else:
                self._trail_mark(bg, x, y, kind, ang)
        if self.theme_name == 'mine':
            self._draw_mine(bg)
        self._draw_delivery(bg)
        self._draw_skylight(bg)
        if self.secret:
            self._draw_secret(bg)
        pygame.draw.rect(bg, (10, 8, 12), (0, 0, WORLD_W, WORLD_H), 14)
        return bg

    def _decorate(self, bg, th, solid):
        """Estalactitas, cristales, hongos luminosos, telarañas y detalles del suelo."""
        rnd, ri = random.random, random.randint
        R = random.Random(random.random())
        g, w = self.g, self.w
        rim = th['rim_mid']
        dark = _mix(th['wall'], th['floor'], .45)
        nf = th['n_fungi']
        fdark, fglow = th['fungus']
        cap = _mix(fdark, fglow, .15)
        decal_p = {'fungi': .09, 'lake': .06, 'mine': .08}[self.theme_name]
        for ty in range(1, self.h - 1):                                   # detalles del suelo (debajo de todo)
            for tx in range(1, self.w - 1):
                if not g[ty][tx] and not self.water[ty * w + tx] and math.dist((tx, ty), NEST_T) >= 5 and rnd() < decal_p:
                    decor.floor_decal(bg, tx * T + ri(6, T - 6), ty * T + ri(6, T - 6), self.theme_name, R)
                if not g[ty][tx] and not self.water[ty * w + tx] and math.dist((tx, ty), NEST_T) >= 4:
                    q = rnd()                                     # señales de la sequía: no hay insectos que comer
                    if q < .07:
                        for _ in range(ri(1, 2)):
                            decor.husk(bg, tx * T + ri(6, T - 6), ty * T + ri(6, T - 6), R)
                    elif q < .1:
                        decor.dry_patch(bg, tx * T + T / 2, ty * T + T / 2, R, _mix(th['floor'], (120, 100, 70), .45))
                    # el nivel del agua bajó varias veces: franja de lodo seco con líneas de sarro y conchitas vacías
                    if self.theme_name == 'lake':
                        for i, j in DIRS:
                            if self.water[(ty + j) * w + tx + i]:
                                cx_, cy_ = tx * T + T / 2 + i * 9, ty * T + T / 2 + j * 9
                                mud = _mix(th['floor'], (120, 112, 98), .4)
                                for _ in range(5):                    # lodo reseco donde antes había agua
                                    k = R.uniform(-15, 15)
                                    px, py = cx_ + (k if j else R.uniform(-3, 3)), cy_ + (k if i else R.uniform(-3, 3))
                                    pygame.draw.ellipse(bg, mud, (px - 5, py - 3, 10, 6))
                                for _ in range(2):                    # costra pálida que dejó el agua
                                    k = R.uniform(-13, 13)
                                    px, py = cx_ - i * 6 + (k if j else 0), cy_ - j * 6 + (k if i else 0)
                                    pygame.draw.ellipse(bg, _mix(mud, (200, 200, 215), .3), (px - 3, py - 2, 6, 4))
                                if rnd() < .22:
                                    decor.shell(bg, cx_ + R.uniform(-8, 8) * (1 - abs(i)), cy_ + R.uniform(-8, 8) * (1 - abs(j)), R)
        self._dry_flats(bg, th)
        for ty in range(1, self.h - 1):
            for tx in range(1, self.w - 1):
                if g[ty][tx] or self.water[ty * w + tx] or math.dist((tx, ty), NEST_T) < 5:
                    continue
                x0, y0 = tx * T, ty * T
                if g[ty - 1][tx] and rnd() < .10:
                    sx_, sh_ = x0 + ri(7, T - 7), ri(10, 20)
                    decor.stalactite(bg, sx_, y0, sh_, dark, rim, R)
                    self.stalactites.append((sx_, y0 + sh_))
                elif g[ty + 1][tx] and rnd() < .05:
                    decor.stalactite(bg, x0 + ri(7, T - 7), y0 + T, ri(8, 14), dark, rim, R, down=False)
                elif (g[ty][tx - 1] or g[ty][tx + 1]) and rnd() < .2 and len(self.crystals) < th['n_crystals']:
                    col = random.choice(th['crystals'])
                    side = -1 if g[ty][tx - 1] else 1
                    cx, cy = x0 + (4 if side < 0 else T - 4), y0 + ri(8, T - 8)
                    decor.crystal_cluster(bg, cx, cy, col, side, R)
                    self.crystals.append((cx, cy, col))
                elif nf and rnd() < (.3 if self.theme_name == 'fungi' else .05) and len(self.fungi) < nf and any(
                        g[ty + j][tx + i] for j, i in DIRS):
                    fx, fy = x0 + ri(6, T - 6), y0 + ri(6, T - 6)
                    decor.mushroom_cluster(bg, fx, fy, cap, fglow, R, big=self.theme_name == 'fungi' and rnd() < .45)
                    self.fungi.append((fx, fy))
                # telarañas en las esquinas (pared arriba e izquierda/derecha)
                elif g[ty - 1][tx] and (g[ty][tx - 1] or g[ty][tx + 1]) and rnd() < (.5 if self.theme_name == 'fungi' else .15):
                    side = -1 if g[ty][tx - 1] else 1
                    cx, cy = x0 + (0 if side < 0 else T), y0
                    col = (190, 205, 205) if self.theme_name != 'mine' else (170, 150, 128)
                    decor.cobweb(bg, cx, cy, side, col, ri(20, 32))
                    self.cobwebs.append((cx, cy))

    def _place_props(self):
        """Dónde van los objetos interactivos: cortinas de raíces secas (pasajes), piedras flotantes (lago)
        y latas colgadas (mina)."""
        g, w = self.g, self.w
        avoid = [NEST] + list(self.pup_spots) + ([self.secret['center']] if self.secret else [])

        def free(tx, ty):
            return (0 < tx < self.w - 1 and 0 < ty < self.h - 1 and not g[ty][tx]
                    and not self.water[ty * w + tx] and not self.secret_mask[ty * w + tx])
        spans = []
        for ty in range(2, self.h - 2):                               # pasajes verticales: cortina horizontal
            tx = 1
            while tx < self.w - 1:
                if free(tx, ty) and g[ty][tx - 1]:
                    x1 = tx
                    while free(x1 + 1, ty):
                        x1 += 1
                    L = x1 - tx + 1
                    if 2 <= L <= 8 and g[ty][x1 + 1] and all(free(x, ty - 1) and free(x, ty + 1) for x in range(tx, x1 + 1)):
                        spans.append(((tx * T + 2, ty * T + 10), ((x1 + 1) * T - 2, ty * T + 10)))
                    tx = x1 + 1
                tx += 1
        # (solo cortinas horizontales: vistas desde arriba se leen como un fleco que cuelga del techo)
        random.shuffle(spans)
        self.curtains = []
        want = {'fungi': 5, 'lake': 4, 'mine': 4}[self.theme_name]
        for a, b in spans:
            m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            if len(self.curtains) >= want:
                break
            if any(math.dist(m, p) < 150 for p in avoid) or math.dist(m, NEST) < 300:
                continue
            if any(math.dist(m, ((c[0][0] + c[1][0]) / 2, (c[0][1] + c[1][1]) / 2)) < 420 for c in self.curtains):
                continue
            if self.web and any(math.dist(m, self._px(t)) < 80 for t in self.web):
                continue
            line = [(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f) for f in (0, .25, .5, .75, 1)]
            if any(math.dist(p_, q) < 40 for q in self.rails for p_ in line) or any(math.dist(m, c[:2]) < 80 for c in self.carts):
                continue
            self.curtains.append((a, b))
        self.stones = []
        if self.theme_name == 'lake':                                 # piedras flotantes en agua abierta
            inner = [(i % w, i // w) for i in range(self.w * self.h) if self.water[i]
                     and all(self.water[(i // w + j) * w + i % w + k] for j, k in DIRS)]
            random.shuffle(inner)
            for tx, ty in inner:
                if len(self.stones) >= 14:
                    break
                p = (tx * T + T / 2 + random.uniform(-6, 6), ty * T + T / 2 + random.uniform(-6, 6))
                if all(math.dist(p, q) > 140 for q in self.stones) and (not self.echo or math.dist(p, self.echo) > 100):
                    self.stones.append(p)
        self.cans = []
        if self.theme_name == 'mine':                                 # latas colgadas de brazos en la pared
            spots = []
            for ty in range(2, self.h - 2):
                for tx in range(2, self.w - 2):
                    if not free(tx, ty):
                        continue
                    for i, j in DIRS:
                        if g[ty + j][tx + i] and free(tx - i, ty - j):
                            wall = (tx * T + T / 2 + i * T / 2, ty * T + T / 2 + j * T / 2)
                            anchor = (tx * T + T / 2 - i * 4, ty * T + T / 2 - j * 4 - 10)
                            spots.append((wall, anchor))
                            break
            random.shuffle(spots)
            far = avoid + ([self.lair] if self.lair else [])
            for gap in (760, 600, 460):                              # 3 latas, bien repartidas por la mina
                for wall, anchor in spots:
                    if len(self.cans) >= 3:
                        break
                    if any(math.dist(anchor, p) < 220 for p in far) or any(math.dist(anchor, c[1]) < gap for c in self.cans):
                        continue
                    self.cans.append((wall, anchor))

    def _dry_flats(self, bg, th):
        """Charcos secos grandes y hongos marchitos: la sequía dejó la cueva sin insectos."""
        g, w = self.g, self.w
        R = random.Random(random.random())
        base = _mix(th['floor'], (150, 126, 92), .5) if self.theme_name != 'lake' else _mix(th['floor'], (130, 124, 112), .5)

        def open_area(tx, ty, r):
            return all(0 < tx + i < self.w - 1 and 0 < ty + j < self.h - 1 and not g[ty + j][tx + i]
                       and not self.water[(ty + j) * w + tx + i] and not self.secret_mask[(ty + j) * w + tx + i]
                       for j in range(-r, r + 1) for i in range(-r, r + 1))
        cand = [(tx, ty) for ty in range(2, self.h - 2) for tx in range(2, self.w - 2)
                if math.dist((tx, ty), NEST_T) > 6 and open_area(tx, ty, 1)]
        R.shuffle(cand)
        placed = []
        want = {'fungi': 9, 'lake': 6, 'mine': 8}[self.theme_name]
        for tx, ty in cand:
            if len(placed) >= want:
                break
            x, y = tx * T + T / 2, ty * T + T / 2
            if any(math.dist((x, y), p) < 230 for p in placed) or any(math.dist((x, y), p) < 50 for p in self.pup_spots):
                continue
            big = open_area(tx, ty, 2)
            decor.mud_flat(bg, x, y, R.randint(40, 58) if big else R.randint(28, 38), R.randint(24, 34) if big else R.randint(17, 23), base, R)
            placed.append((x, y))
        self.dry_flats = placed
        # hongos marchitos junto a las paredes (sin brillo, no dan luz)
        n = {'fungi': 16, 'lake': 6, 'mine': 8}[self.theme_name]
        spots = [(tx, ty) for ty in range(1, self.h - 1) for tx in range(1, self.w - 1)
                 if not g[ty][tx] and not self.water[ty * w + tx] and not self.secret_mask[ty * w + tx]
                 and math.dist((tx, ty), NEST_T) > 5 and any(g[ty + j][tx + i] for j, i in DIRS)]
        for tx, ty in R.sample(spots, min(n, len(spots))):
            decor.withered_mushroom(bg, tx * T + R.randint(8, T - 8), ty * T + R.randint(8, T - 8), R)

    @staticmethod
    def _trail_mark(bg, x, y, kind, ang):
        decor.trail_mark(bg, x, y, kind, ang)

    def _draw_mine(self, bg):
        decor.rails(bg, self.rails)
        for seg in self.beams:                                       # vigas de madera
            decor.beam(bg, *seg)
        for x, y, side in self.lamps:                                # faroles apagados
            decor.lantern(bg, x, y)
        for x, y, ang, lair in self.carts:
            draw_cart(bg, x, y, ang, 1.25 if lair else 1.0)
        if self.molt:                                                # la piel vieja de Xolthar (quieta, pálida y vacía)
            from art import draw_molt
            x, y, ang = self.molt
            draw_molt(bg, x, y, ang, 170, 150)

    def _draw_secret(self, bg):
        """Decoración de la sala secreta y la cortina que tapa su entrada."""
        sc = self.secret
        cx, cy = sc['center']
        R = random.Random(random.random())
        th = self.theme_name
        pygame.draw.ellipse(bg, _mix(self.theme['floor'], (255, 255, 255), .06),
                            (cx - sc['rx'] * .8, cy - sc['ry'] * .75, sc['rx'] * 1.6, sc['ry'] * 1.5))
        ring = [(cx + math.cos(a) * sc['rx'] * .78, cy + math.sin(a) * sc['ry'] * .72) for a in
                [k * math.tau / 14 + R.uniform(-.1, .1) for k in range(14)]]
        if th == 'fungi':                                      # sala de telarañas
            web = (205, 215, 215)
            for x, y in ring:                                   # telarañas por todas las paredes
                side = -1 if x < cx else 1
                decor.cobweb(bg, int(x), int(y - 10), side, web, R.randint(26, 40))
            for _ in range(5):                                  # telarañas tendidas en el suelo
                a, r = R.uniform(0, math.tau), R.uniform(.15, .55)
                x, y = cx + math.cos(a) * sc['rx'] * r, cy + math.sin(a) * sc['ry'] * r
                rr = R.randint(14, 22)
                for k in range(8):
                    aa = k * math.tau / 8
                    pygame.draw.aaline(bg, (150, 165, 165), (x, y), (x + math.cos(aa) * rr, y + math.sin(aa) * rr))
                for q in (.35, .7, 1.0):
                    pygame.draw.circle(bg, (130, 145, 145), (int(x), int(y)), int(rr * q), 1)
            for _ in range(9):                                  # saquitos de huevos (bolitas blancas)
                a, r = R.uniform(0, math.tau), R.uniform(.55, .85)
                x, y = cx + math.cos(a) * sc['rx'] * r, cy + math.sin(a) * sc['ry'] * r
                pygame.draw.circle(bg, (60, 66, 66), (int(x + 2), int(y + 3)), 5)
                pygame.draw.circle(bg, (225, 228, 220), (int(x), int(y)), 5)
                pygame.draw.circle(bg, (255, 255, 250), (int(x - 2), int(y - 2)), 2)
            for x, y in ring[::3]:                              # un par de hongos para que se vea
                decor.mushroom_cluster(bg, x, y, (40, 120, 110), (150, 255, 220), R)
                self.fungi.append((x, y))
        elif th == 'lake':                                     # gruta de hierro natural (roca gris con vetas metálicas)
            def iron_rock(x, y, r):
                """Roca de mineral de hierro: gris oscuro, facetas y brillo metálico plateado."""
                pts = [(x + math.cos(a) * r * R.uniform(.75, 1.1), y + math.sin(a) * r * R.uniform(.7, 1.0))
                       for a in [k * math.tau / 7 + R.uniform(-.2, .2) for k in range(7)]]
                pygame.draw.polygon(bg, (10, 10, 14), [(px + 2, py + 3) for px, py in pts])         # sombra
                pygame.draw.polygon(bg, (58, 60, 68), pts)
                pygame.draw.polygon(bg, (84, 88, 100), [pts[4], pts[5], pts[6], pts[0], (x, y)])    # cara iluminada
                pygame.draw.polygon(bg, (120, 126, 142), [pts[5], pts[6], (x - r * .1, y - r * .2)])
                pygame.draw.lines(bg, (150, 156, 172), True, pts, 1)
                for _ in range(2):                                  # puntitos de metal que brillan
                    bg.fill((225, 230, 240), (int(x + R.uniform(-r, r) * .5), int(y + R.uniform(-r, r) * .5), 2, 1))
            for k in range(22):                                 # rocas grandes contra las paredes
                a = k * math.tau / 22 + R.uniform(-.08, .08)
                iron_rock(cx + math.cos(a) * sc['rx'] * .86, cy + math.sin(a) * sc['ry'] * .82, R.randint(9, 14))
            for _ in range(14):                                 # piedras sueltas en el suelo
                a, r = R.uniform(0, math.tau), R.uniform(.35, .7)
                iron_rock(cx + math.cos(a) * sc['rx'] * r, cy + math.sin(a) * sc['ry'] * r, R.randint(4, 7))
            for k in range(4):                                  # vetas plateadas en el suelo
                pts = [(cx - sc['rx'] * .7, cy + R.uniform(-40, 40))]
                for _ in range(5):
                    pts.append((pts[-1][0] + sc['rx'] * .28, pts[-1][1] + R.uniform(-10, 10)))
                pygame.draw.lines(bg, (40, 42, 50), False, pts, 4)
                pygame.draw.lines(bg, (170, 176, 192), False, pts, 1)
            for _ in range(8):                                  # poquito óxido café (no rojo)
                x, y = cx + R.uniform(-.6, .6) * sc['rx'], cy + R.uniform(-.55, .55) * sc['ry']
                pygame.draw.ellipse(bg, (92, 70, 52), (x, y, R.randint(8, 14), R.randint(4, 8)))
            pygame.draw.ellipse(bg, (16, 20, 34), (cx - 32, cy - 13, 64, 26))                  # charquito oscuro que refleja
            pygame.draw.ellipse(bg, (110, 120, 150), (cx - 32, cy - 13, 64, 26), 2)
            pygame.draw.line(bg, (170, 180, 210), (cx - 14, cy - 5), (cx + 6, cy - 5), 1)
            for x, y in ring[::3]:
                self.crystals.append((x, y, (170, 190, 230)))   # brillo frío, metálico
        else:                                                  # sala de herramientas de los mineros
            for x, y in ring[::3]:
                self.crystals.append((x, y, (255, 190, 110)))
            def pick(x, y, ang, sc_=1.0):                       # pico de minero
                ca, sa = math.cos(ang), math.sin(ang)
                hx, hy = x + ca * 26 * sc_, y + sa * 26 * sc_
                pygame.draw.line(bg, (12, 8, 4), (x + 2, y + 3), (hx + 2, hy + 3), 5)
                pygame.draw.line(bg, (122, 84, 48), (x, y), (hx, hy), 4)
                head = [(hx - sa * 14 * sc_, hy + ca * 14 * sc_), (hx + ca * 3, hy + sa * 3), (hx + sa * 14 * sc_, hy - ca * 14 * sc_)]
                pygame.draw.lines(bg, (90, 92, 100), False, head, 5)
                pygame.draw.lines(bg, (190, 195, 205), False, head, 1)
            def shovel(x, y, ang):
                ca, sa = math.cos(ang), math.sin(ang)
                ex, ey = x + ca * 30, y + sa * 30
                pygame.draw.line(bg, (122, 84, 48), (x, y), (ex, ey), 3)
                blade = [(ex - sa * 7, ey + ca * 7), (ex + ca * 14 - sa * 5, ey + sa * 14 + ca * 5),
                         (ex + ca * 16, ey + sa * 16), (ex + ca * 14 + sa * 5, ey + sa * 14 - ca * 5), (ex + sa * 7, ey - ca * 7)]
                pygame.draw.polygon(bg, (110, 112, 120), blade)
                pygame.draw.polygon(bg, (180, 182, 190), blade, 1)
            def helmet(x, y):
                pygame.draw.circle(bg, (12, 8, 4), (int(x + 2), int(y + 3)), 11)
                pygame.draw.circle(bg, (200, 160, 40), (int(x), int(y)), 11)
                pygame.draw.circle(bg, (240, 210, 90), (int(x - 3), int(y - 3)), 4)
                pygame.draw.circle(bg, (60, 60, 60), (int(x), int(y - 8)), 4)
                pygame.draw.circle(bg, (255, 240, 180), (int(x), int(y - 8)), 2)
            def crate(x, y):
                pygame.draw.rect(bg, (12, 8, 4), (x + 3, y + 4, 30, 24))
                pygame.draw.rect(bg, (100, 68, 38), (x, y, 30, 24))
                pygame.draw.rect(bg, (146, 104, 62), (x, y, 30, 24), 2)
                pygame.draw.line(bg, (146, 104, 62), (x, y), (x + 30, y + 24), 2)
                pygame.draw.line(bg, (146, 104, 62), (x + 30, y), (x, y + 24), 2)
            def barrel(x, y):
                pygame.draw.circle(bg, (12, 8, 4), (int(x + 2), int(y + 3)), 12)
                pygame.draw.circle(bg, (110, 72, 40), (int(x), int(y)), 12)
                pygame.draw.circle(bg, (80, 80, 86), (int(x), int(y)), 12, 2)
                pygame.draw.circle(bg, (80, 80, 86), (int(x), int(y)), 7, 1)
            rack_y = cy - sc['ry'] * .62                         # estante de herramientas en la pared de arriba
            pygame.draw.line(bg, (90, 60, 34), (cx - 70, rack_y), (cx + 70, rack_y), 6)
            for k in range(4):
                pick(cx - 60 + k * 36, rack_y + 2, math.pi / 2 + R.uniform(-.15, .15), .8)
            pick(cx - 40, cy + 30, -.6)
            pick(cx + 54, cy - 4, 2.4)
            shovel(cx + 10, cy + 34, -.3)
            shovel(cx - 70, cy - 10, .9)
            helmet(cx + 30, cy + 22)
            helmet(cx - 16, cy - 8)
            crate(cx - 90, cy + 8)
            crate(cx + 62, cy + 18)
            barrel(cx + 88, cy - 20)
            barrel(cx - 84, cy - 30)
            decor.lantern(bg, cx, cy - 26)
            draw_cart(bg, cx + 4, cy + 4, .2, .9)
        for tx, ty in sc['path']:                              # la entrada está disimulada
            x0, y0 = tx * T, ty * T
            if th == 'fungi':                                  # raíces colgantes
                for k in range(6):
                    x = x0 + 3 + k * 5 + R.uniform(-1, 1)
                    pygame.draw.line(bg, (70, 56, 34), (x, y0), (x + R.uniform(-3, 3), y0 + T), 2)
                    pygame.draw.circle(bg, (60, 120, 70), (int(x), int(y0 + R.uniform(4, T - 4))), 2)
            elif th == 'lake':                                 # cortina de agua que gotea
                for k in range(7):
                    x = x0 + 2 + k * 4
                    pygame.draw.line(bg, (60, 90, 150), (x, y0), (x, y0 + T), 1)
                    pygame.draw.circle(bg, (140, 190, 240), (int(x), int(y0 + R.uniform(2, T - 2))), 1)
            else:                                              # tablas sueltas
                pygame.draw.line(bg, (96, 66, 40), (x0 + 2, y0 + 6), (x0 + T - 2, y0 + T - 10), 5)
                pygame.draw.line(bg, (110, 76, 46), (x0 + 2, y0 + T - 6), (x0 + T - 2, y0 + 8), 5)

    SKY = {'fungi': ((10, 18, 60), (30, 50, 130)), 'lake': ((40, 24, 80), (120, 70, 170)),
           'mine': ((120, 60, 50), (255, 160, 80))}

    def _draw_skylight(self, bg):
        """Una grieta en el techo por la que se ve un poquito el cielo de afuera (solo de referencia).
        Azul oscuro en el Acto I, violeta en el II y naranja del amanecer en el III."""
        cands = [(tx, ty) for tx, ty in self.land
                 if 2 <= ty <= 14 and self.g[ty - 1][tx] and self.g[ty - 2][tx] and not self.g[ty][tx - 1] and not self.g[ty][tx + 1]
                 and math.dist(self._px((tx, ty)), NEST) > 700 and not self.secret_mask[ty * self.w + tx]]
        if not cands:
            self.skylight = None
            return
        tx, ty = min(cands, key=lambda t: (t[1], random.random()))
        x, y = tx * T + T / 2, ty * T                          # borde de la roca
        self.skylight = (x, y + 6)
        top, bot = self.SKY[self.theme_name]
        R0 = random.Random(random.random())
        # grieta irregular en el techo de roca, vista desde arriba (zigzag alargado, nada redondo)
        L, ang = R0.uniform(80, 110), R0.uniform(-.25, .25)
        n = 9
        center = [(x + (k / (n - 1) - .5) * L * math.cos(ang) + R0.uniform(-3, 3),
                   y - 16 + (k / (n - 1) - .5) * L * math.sin(ang) + R0.uniform(-4, 4)) for k in range(n)]
        widths = [0] + [R0.uniform(3, 10) * math.sin(math.pi * k / (n - 1)) ** .6 for k in range(1, n - 1)] + [0]
        nx, ny = -math.sin(ang), math.cos(ang)
        upper = [(cx_ - nx * w_ * R0.uniform(.6, 1.1), cy_ - ny * w_ * R0.uniform(.6, 1.1)) for (cx_, cy_), w_ in zip(center, widths)]
        lower = [(cx_ + nx * w_ * R0.uniform(.6, 1.1), cy_ + ny * w_ * R0.uniform(.6, 1.1)) for (cx_, cy_), w_ in zip(center, widths)]
        poly = upper + lower[::-1]
        minx, miny = min(p[0] for p in poly) - 4, min(p[1] for p in poly) - 4
        sw, sh = int(max(p[0] for p in poly) - minx + 8), int(max(p[1] for p in poly) - miny + 8)
        sky = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for yy in range(sh):                                   # degradado del cielo de afuera
            sky.fill((*_mix(top, bot, yy / max(1, sh - 1)), 255), (0, yy, sw, 1))
        if self.theme_name != 'mine':
            for _ in range(6):
                sky.fill((235, 235, 255, 255), (R0.randint(0, sw - 1), R0.randint(0, sh - 1), 1, 1))
        mask = pygame.Surface((sw, sh), pygame.SRCALPHA)
        pygame.draw.polygon(mask, (255, 255, 255, 255), [(px - minx, py - miny) for px, py in poly])
        sky.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        pygame.draw.polygon(bg, (4, 4, 6), [(px + 2, py + 3) for px, py in poly])      # sombra del borde
        bg.blit(sky, (minx, miny))
        for k in range(2):                                     # grietas finitas que se ramifican
            i = R0.randint(2, n - 3)
            sx_, sy_ = center[i]
            pts = [(sx_, sy_)]
            for _ in range(3):
                sx_, sy_ = sx_ + R0.uniform(-10, 10), sy_ + R0.uniform(-9, -2)
                pts.append((sx_, sy_))
            pygame.draw.lines(bg, _mix(top, bot, .5), False, pts, 1)
        pygame.draw.lines(bg, _mix(self.theme['wall'], (0, 0, 0), .5), False, upper, 2)  # labio de roca
        pygame.draw.lines(bg, self.theme['rim_hi'], False, lower, 2)                    # borde iluminado
        self.skylight = (x, y + 2)
        R = random.Random(random.random())                      # bajo la grieta: tierra seca y hojas muertas
        decor.dry_patch(bg, x, y + 70, R, _mix(self.theme['floor'], (130, 110, 80), .5))
        for _ in range(6):
            lx, ly = x + R.uniform(-30, 30), y + 60 + R.uniform(-12, 22)
            pygame.draw.ellipse(bg, R.choice(((120, 96, 56), (100, 80, 50), (140, 110, 60))), (lx, ly, 7, 4))
        for k in range(4):                                      # raicitas secas que cuelgan de la grieta
            px, py = center[2 + k]
            pygame.draw.line(bg, (90, 70, 46), (px, py), (px + R.uniform(-4, 4), py + R.uniform(8, 16)), 1)

    def _light_pool(self, bg, col, r):
        """Charco de luz que baja de la entrada de la cueva (color según la hora: azul, violeta, naranja)."""
        pool = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for k in range(r, 0, -3):
            pygame.draw.circle(pool, (*col, int(70 * (1 - k / r) ** 1.4)), (r, r), k)
        bg.blit(pool, (NEST[0] - r, NEST[1] - r))

    def _rock_slab(self, bg, cx, cy, r, base, R):
        """Repisa de roca con volumen: sombra, cara iluminada arriba y borde claro."""
        pts = [(cx + math.cos(a) * r * R.uniform(.85, 1.08), cy + math.sin(a) * r * R.uniform(.8, 1.0))
               for a in [k * TAU / 11 + R.uniform(-.12, .12) for k in range(11)]]
        pygame.draw.polygon(bg, (6, 6, 10), [(x + 5, y + 8) for x, y in pts])
        pygame.draw.polygon(bg, _mix(base, (0, 0, 0), .35), pts)
        inner = [(cx + (x - cx) * .9, cy + (y - cy) * .86 - 4) for x, y in pts]
        pygame.draw.polygon(bg, base, inner)
        pygame.draw.lines(bg, _mix(base, (255, 255, 255), .35), True, inner, 2)
        for _ in range(10):                                    # grietas
            a = R.uniform(0, TAU)
            x, y = cx + math.cos(a) * r * .5, cy + math.sin(a) * r * .4
            pygame.draw.line(bg, _mix(base, (0, 0, 0), .3), (x, y), (x + R.uniform(-10, 10), y + R.uniform(-6, 6)), 1)

    def _draw_delivery(self, bg):
        """Lugar donde Mullo deja a sus crías: un sitio seguro y bonito en cada escenario."""
        from art import draw_nest
        R = random.Random(random.random())
        if self.theme_name == 'fungi':                         # el nido de siempre, bajo la luz azul de la madrugada
            for k in range(18):                                 # anillo de musgo y piedritas alrededor
                a = k * TAU / 18 + R.uniform(-.1, .1)
                x, y = NEST[0] + math.cos(a) * (NEST_R + 14), NEST[1] + math.sin(a) * (NEST_R + 14)
                for _ in range(3):
                    pygame.draw.circle(bg, R.choice(((52, 96, 70), (60, 112, 78), (46, 86, 64))),
                                       (int(x + R.uniform(-5, 5)), int(y + R.uniform(-4, 4))), R.randint(3, 5))
                if k % 3 == 0:
                    decor.pebble(bg, x, y, R.uniform(3, 5), (90, 104, 104), R)
            draw_nest(bg, NEST[0], NEST[1], NEST_R + 4, NEST_R + 4, seed=11)
            for k in range(6):                                  # marcas de garras que bajan del nido
                self._trail_mark(bg, NEST[0] + 66 + k * 18, NEST[1] + 36 + k * 14, 'claw', .7)
        elif self.theme_name == 'lake':                        # repisa de roca con musgo y un nidito, luz violeta
            self._rock_slab(bg, NEST[0], NEST[1] + 4, NEST_R + 14, (84, 86, 124), R)
            for _ in range(16):                                 # cojines de musgo
                a, r = R.uniform(0, TAU), R.uniform(.55, .9)
                x, y = NEST[0] + math.cos(a) * NEST_R * r, NEST[1] + math.sin(a) * NEST_R * r
                for _ in range(4):
                    pygame.draw.circle(bg, R.choice(((56, 104, 78), (66, 120, 88), (48, 90, 70))),
                                       (int(x + R.uniform(-6, 6)), int(y + R.uniform(-4, 4))), R.randint(3, 6))
            draw_nest(bg, NEST[0], NEST[1], 36, 34, seed=12)
            for k in range(5):                                  # gotitas brillantes en la orilla
                a = k * TAU / 5 + .4
                pygame.draw.circle(bg, (190, 200, 255), (int(NEST[0] + math.cos(a) * (NEST_R + 10)),
                                                         int(NEST[1] + math.sin(a) * (NEST_R + 6))), 2)
        else:                                                  # tiro de mina hacia la superficie: entra el amanecer
            for k, col in enumerate(((70, 52, 36), (110, 82, 54), (160, 120, 80), (215, 170, 110))):
                pygame.draw.circle(bg, col, NEST, int(NEST_R * (1 - k * .2)))
            s = NEST_R + 8
            for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):  # postes del marco
                px, py = NEST[0] + dx * s, NEST[1] + dy * s
                pygame.draw.rect(bg, (12, 8, 4), (px - 7, py - 5, 16, 16))
                pygame.draw.rect(bg, (120, 82, 48), (px - 8, py - 8, 16, 16))
                pygame.draw.rect(bg, (160, 116, 70), (px - 8, py - 8, 16, 16), 2)
            for a, b in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
                decor.beam(bg, NEST[0] + a[0] * s, NEST[1] + a[1] * s, NEST[0] + b[0] * s, NEST[1] + b[1] * s)
            lx = NEST[0] + s - 18                               # escalera que sube hacia la luz
            for x in (lx - 7, lx + 7):
                pygame.draw.line(bg, (110, 76, 44), (x, NEST[1] - s + 6), (x, NEST[1] + s - 6), 3)
            for y in range(int(NEST[1] - s + 12), int(NEST[1] + s - 6), 10):
                pygame.draw.line(bg, (140, 100, 60), (lx - 7, y), (lx + 7, y), 2)
            draw_nest(bg, NEST[0] - 6, NEST[1] + 2, 34, 32, seed=13)   # nidito de paja bajo la luz


def draw_cart(s, x, y, ang, sc=1.0):
    """Vagoneta oxidada vista desde arriba."""
    decor.cart(s, x, y, ang, sc)
