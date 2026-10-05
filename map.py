"""Cueva: generación por autómata celular, colisión, rutas, render del fondo y minimapa."""
import math
import random
from collections import deque

import pygame

from settings import (TILE, MAP_W, MAP_H, WORLD_W, WORLD_H, NEST, NEST_T, NEST_R, TAU, MEMORY_ALPHA)

T = TILE
MIN_OPEN = 1800                          # tiles abiertos mínimos para aceptar una cueva
CRYSTAL_COLORS = [(90, 170, 255), (180, 110, 255), (100, 255, 200)]
DIRS = ((0, -1), (0, 1), (-1, 0), (1, 0))               # arriba, abajo, izquierda, derecha
FLOOR, WALL = (66, 58, 78), (9, 8, 12)                   # suelo claro y pared muy oscura: mucho contraste
RIM_HI, RIM_MID = (150, 134, 178), (92, 80, 114)          # borde luminoso de la roca
AO = ((44, 38, 52), (52, 45, 61), (59, 51, 69))          # oclusión ambiental en el suelo junto a la pared


class CaveMap:
    def __init__(self):
        self.w, self.h = MAP_W, MAP_H
        self.g = None
        for _ in range(25):
            if self._generate():
                break
        else:                              # último recurso: sala abierta con pilares
            self.g = [[1 if x in (0, self.w - 1) or y in (0, self.h - 1) else 0
                       for x in range(self.w)] for y in range(self.h)]
        self.open = [(x, y) for y in range(1, self.h - 1) for x in range(1, self.w - 1)
                     if all(not self.g[y + j][x + i] for j in (-1, 0, 1) for i in (-1, 0, 1))]
        self.crystals = []                 # (x, y, color)
        self.fungi = []                    # (x, y) parches de hongos luminosos
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

    # ------------------------------------------------------------ consultas
    def solid(self, tx, ty):
        return tx < 0 or ty < 0 or tx >= self.w or ty >= self.h or self.g[ty][tx]

    def solid_px(self, x, y):
        return self.solid(int(x // T), int(y // T))

    def los(self, a, b):
        """Línea de visión libre entre dos puntos (con un pequeño margen lateral)."""
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy)
        if d < 1:
            return True
        ux, uy = dx / d, dy / d
        steps = int(d // 10) + 1
        for off in (0, 9, -9):
            ox, oy = -uy * off, ux * off
            for i in range(steps + 1):
                f = min(d, i * 10)
                if self.solid_px(a[0] + ux * f + ox, a[1] + uy * f + oy):
                    return False
        return True

    def path(self, a, b, limit=7000):
        """BFS 4-conectado entre posiciones en píxeles -> lista de centros de tile (sin el origen)."""
        s = (int(a[0] // T), int(a[1] // T))
        t = (int(b[0] // T), int(b[1] // T))
        if self.solid(*s) or self.solid(*t):
            return None
        if s == t:
            return [b]
        prev, dq, n = {s: None}, deque([s]), 0
        while dq and n < limit:
            cur = dq.popleft()
            n += 1
            if cur == t:
                break
            x, y = cur
            for nb in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if nb not in prev and not self.solid(*nb):
                    prev[nb] = cur
                    dq.append(nb)
        if t not in prev:
            return None
        out, cur = [], t
        while cur != s:
            out.append((cur[0] * T + T / 2, cur[1] * T + T / 2))
            cur = prev[cur]
        out.reverse()
        out[-1] = b
        return out

    def free_spot(self, far_from, dist, avoid=(), avoid_d=0):
        """Punto abierto a >= dist de far_from y >= avoid_d de los puntos de avoid."""
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

    def resolve(self, o, rad):
        """Saca al círculo (o.x, o.y, rad) de las paredes. Devuelve (choque, nx, ny) con la normal media."""
        hit, nx, ny = False, 0.0, 0.0
        for _ in range(2):
            for ty in range(int((o.y - rad) // T), int((o.y + rad) // T) + 1):
                for tx in range(int((o.x - rad) // T), int((o.x + rad) // T) + 1):
                    if not self.solid(tx, ty):
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
        if not self.explored[i]:
            self.explored[i] = 1
            col = (70, 56, 84) if not self.g[ty][tx] else (24, 20, 30)
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
        bg = pygame.Surface((WORLD_W, WORLD_H))
        bg.fill(FLOOR)
        rnd = random.random
        solid = self.solid
        for ty in range(self.h):
            for tx in range(self.w):
                x0, y0 = tx * T, ty * T
                if self.g[ty][tx]:
                    sh = random.randint(0, 3)
                    bg.fill((WALL[0] + sh, WALL[1] + sh, WALL[2] + sh), (x0, y0, T, T))
                    for _ in range(2):
                        c = random.randint(12, 19)
                        pygame.draw.circle(bg, (c, c - 2, c + 3), (x0 + random.randint(2, T - 2), y0 + random.randint(2, T - 2)),
                                           random.randint(3, 8))
                else:
                    sh = random.randint(0, 3)
                    bg.fill((FLOOR[0] + sh, FLOOR[1] + sh, FLOOR[2] + sh), (x0, y0, T, T))
                    for _ in range(3):
                        c = random.randint(56, 76)
                        bg.fill((c, c - 6, c + 6), (x0 + random.randint(0, T - 3), y0 + random.randint(0, T - 3),
                                                    random.randint(1, 3), random.randint(1, 3)))
        # sombra suave en el suelo junto a las paredes y borde luminoso de la roca (siluetas legibles)
        for ty in range(self.h):
            for tx in range(self.w):
                x0, y0 = tx * T, ty * T
                if self.g[ty][tx]:
                    for side, (dx, dy) in enumerate(DIRS):
                        if not solid(tx + dx, ty + dy):
                            bg.fill(RIM_MID, self._band(x0, y0, side, 2, 3))
                            bg.fill(RIM_HI, self._band(x0, y0, side, 0, 2))
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
                        if solid(tx + sx, ty) or solid(tx, ty + sy):
                            continue
                        px, py = x0 + (0 if sx < 0 else T), y0 + (0 if sy < 0 else T)
                        a, b = (px - sx * C, py), (px, py - sy * C)
                        pygame.draw.polygon(bg, FLOOR, [(px, py), a, b])
                        pygame.draw.line(bg, RIM_HI, a, b, 2)
        # estalagmitas, cristales y hongos luminosos pegados a las paredes
        for ty in range(1, self.h - 1):
            for tx in range(1, self.w - 1):
                if self.g[ty][tx] or math.dist((tx, ty), NEST_T) < 5:
                    continue
                x0, y0 = tx * T, ty * T
                if self.g[ty - 1][tx] and rnd() < .10:
                    bx = x0 + random.randint(6, T - 6)
                    hgt = random.randint(8, 18)
                    pts = [(bx - 5, y0), (bx + 5, y0), (bx, y0 + hgt)]       # estalactita colgando
                    pygame.draw.polygon(bg, (34, 28, 38), pts)
                    pygame.draw.polygon(bg, (92, 80, 104), pts, 1)
                elif self.g[ty + 1][tx] and rnd() < .06:
                    bx = x0 + random.randint(6, T - 6)
                    hgt = random.randint(8, 16)
                    pts = [(bx - 5, y0 + T), (bx + 5, y0 + T), (bx, y0 + T - hgt)]
                    pygame.draw.polygon(bg, (34, 28, 38), pts)
                    pygame.draw.polygon(bg, (92, 80, 104), pts, 1)
                elif (self.g[ty][tx - 1] or self.g[ty][tx + 1]) and rnd() < .2 and len(self.crystals) < 100:
                    col = random.choice(CRYSTAL_COLORS)
                    cx, cy = x0 + (4 if self.g[ty][tx - 1] else T - 4), y0 + random.randint(8, T - 8)
                    pts = [(cx, cy - 9), (cx + 5, cy), (cx, cy + 9), (cx - 5, cy)]
                    pygame.draw.polygon(bg, tuple(int(c * .55) for c in col), pts)
                    pygame.draw.polygon(bg, col, pts, 1)
                    self.crystals.append((cx, cy, col))
                elif rnd() < .1 and len(self.fungi) < 200 and any(
                        self.g[ty + j][tx + i] for j, i in DIRS):
                    fx, fy = x0 + random.randint(6, T - 6), y0 + random.randint(6, T - 6)
                    for _ in range(4):                               # parche de hongos
                        ox, oy = random.randint(-6, 6), random.randint(-5, 5)
                        pygame.draw.circle(bg, (24, 70, 58), (fx + ox, fy + oy), 3)
                        pygame.draw.circle(bg, (90, 235, 180), (fx + ox, fy + oy - 1), 1)
                    self.fungi.append((fx, fy))
        # nido
        pygame.draw.circle(bg, (60, 45, 38), NEST, NEST_R)
        pygame.draw.circle(bg, (90, 70, 55), NEST, NEST_R, 4)
        for k in range(14):
            a = TAU * k / 14 + random.uniform(-.2, .2)
            r0, r1 = NEST_R * random.uniform(.2, .6), NEST_R * random.uniform(.6, .95)
            pygame.draw.line(bg, (105, 80, 58), (NEST[0] + math.cos(a) * r0, NEST[1] + math.sin(a) * r0),
                             (NEST[0] + math.cos(a + .5) * r1, NEST[1] + math.sin(a + .5) * r1), 2)
        # marco de la cueva
        pygame.draw.rect(bg, (10, 8, 12), (0, 0, WORLD_W, WORLD_H), 14)
        return bg
