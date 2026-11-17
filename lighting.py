"""Iluminación: penumbra con el color de cada escenario, luz propia, memoria de lo recorrido, balizas y ecolocación.

Todo el cálculo de luz se hace en un mapa de 1/2 de resolución (SW x SH) y se amplía una sola vez:
la luz es suave, así que no se nota, y evita varias mezclas de pantalla completa por frame
(muy caras en el navegador con WebAssembly).
"""
import math

import pygame

from settings import (IS_WEB, W, H, VIEW_W, VIEW_H, TILE, NEST, SHIELD_R, BRIGHTNESS_LEVELS, SCREECH_R, ECHO_FLASH_T)

S = 2                                  # factor de reducción del mapa de luz
SW, SH = W // S, H // S
SUB = pygame.BLEND_RGBA_SUB
BAKE_STATIC = IS_WEB or bool(__import__('os').environ.get('BATLING_BAKE'))   # luces fijas pre-sumadas
ADD = pygame.BLEND_RGB_ADD
K = (0, 0, 0)
# penumbra de cada escenario: (color, cambio de opacidad, color del brillo del punto de entrega)
# Cada nivel está más oscuro que el anterior (se baja más y más en la cueva); para compensar, la luz de Mullo
# se achica un poco y los objetos que brillan (cristales, hongos, algas) alumbran más y se ven de más lejos.
AMBIENT = {
    'fungi': ((4, 20, 22), -18, (255, 170, 90)),      # verde azulado: luz tenue y segura
    'lake': ((3, 5, 22), 36, (150, 170, 255)),         # índigo casi negro
    'mine': ((12, 7, 3), 56, (255, 160, 80)),          # marrón y ámbar oscuro, casi sin luz
}
BAT_SCALE = {'fungi': 1.0, 'lake': .9, 'mine': .82}      # radio de la luz propia de Mullo
OBJ_SCALE = {'fungi': 1.0, 'lake': 1.2, 'mine': 1.5}     # cuánto alumbran los objetos que brillan
FUNGUS_GLOW = {'fungi': (70, 230, 170), 'lake': (70, 210, 160), 'mine': (255, 170, 70)}   # en la mina: madera podrida que brilla


MOUTH_STEPS = 12
_MOUTH = ((0.0, (36, 56, 170)), (.36, (70, 66, 190)), (.8, (170, 84, 190)), (1.0, (255, 130, 160)))


def mouth_color(f):
    """Color de la luz de afuera según la noche (0 = medianoche, 1 = 05:30): azul, violeta y rosado al final."""
    for (f0, c0), (f1, c1) in zip(_MOUTH, _MOUTH[1:]):
        if f <= f1:
            k = (f - f0) / (f1 - f0)
            return tuple(int(a + (b - a) * k) for a, b in zip(c0, c1))
    return _MOUTH[-1][1]


DIM_LEVELS = (.18, .38, .58, .8, 1.0)


def dim_rgb(surf, k):
    """Copia de un brillo (para sumar) con el color atenuado."""
    t = surf.copy()
    v = int(255 * k)
    t.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
    return t


def radial(r, peak=255, exp=1.3, rgb=(255, 255, 255), step=2):
    """Disco de luz: opaco en el centro y cayendo suavemente hasta 0 en el borde.
    Para restar de la oscuridad se usa rgb=(0, 0, 0): BLEND_RGBA_SUB resta también el color,
    y así solo cambia la opacidad sin desteñir el tinte ambiente."""
    s = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
    for i in range(r, 0, -step):
        pygame.draw.circle(s, (*rgb, int(peak * (1 - i / r) ** exp)), (r, r), i)
    return s


def faded(surf, alpha):
    t = surf.copy()
    t.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    return t


def glow_rgb(r, col, peak=1.0, exp=1.0):
    """Brillo de color para sumar (BLEND_RGB_ADD): el color se apaga hacia el borde, sobre negro."""
    s = pygame.Surface((2 * r, 2 * r))
    for i in range(r, 0, -1):
        k = peak * (1 - i / r) ** exp
        pygame.draw.circle(s, tuple(min(255, int(c * k)) for c in col), (r, r), i)
    return s


def make_vignette(sw=SW, sh=SH):
    sm = pygame.Surface((48, 32), pygame.SRCALPHA)
    for y in range(32):
        for x in range(48):
            d = math.hypot((x - 23.5) / 24, (y - 15.5) / 16)
            sm.set_at((x, y), (0, 0, 0, int(max(0, min(1, (d - .6) / .6)) ** 1.4 * 150)))
    return pygame.transform.smoothscale(sm, (sw, sh))


def ring(c, x, y, r, col, a, width=2):
    """Anillo tenue directo sobre el lienzo (sin capa alfa de pantalla completa): color atenuado por a (0-1)."""
    if r < 1 or a <= 0:
        return
    pygame.draw.circle(c, tuple(min(255, int(ch * a)) for ch in col), (int(x), int(y)), int(r), width)


class Lighting:
    def __init__(self, crystals, fungi=(), theme='fungi', algae=(), size=(VIEW_W, VIEW_H)):
        """size: lo que se ve del mundo (con zoom en el navegador es más chico que la pantalla)."""
        self.vw, self.vh = size
        self.crystals, self.fungi, self.algae = crystals, list(fungi), list(algae)
        self.amb_rgb, self.amb_off, nest_col = AMBIENT[theme]
        self.theme = theme
        self.small = pygame.Surface((self.vw // S, self.vh // S), pygame.SRCALPHA)
        self.up = pygame.Surface((self.vw, self.vh), pygame.SRCALPHA)
        # luces que se RESTAN de la oscuridad (solo opacidad)
        bs, o = BAT_SCALE[theme], OBJ_SCALE[theme]
        self.bat_lights = {lv[2]: radial(int(lv[2] * bs) // S, 255, .8, K, 1) for lv in BRIGHTNESS_LEVELS}
        self.L_NEST = radial(210 // S, 255, 1.0, K, 1)
        self.L_PUP = faded(radial(60 // S, 255, 1.0, K, 1), 150)
        self.L_CRY = faded(radial(int(70 * o) // S, 255, 1.0, K, 1), min(255, int(110 * o)))
        self.L_FUN = faded(radial(int(36 * o) // S, 255, 1.0, K, 1), min(255, int(110 * o)))
        # brillos de color que se SUMAN (balizas visibles de lejos)
        self.glow = {col: glow_rgb(int(70 * o) // S, col, 1.0) for col in {c[2] for c in crystals}}
        self.fun_glow = glow_rgb(int(36 * o) // S, FUNGUS_GLOW[theme], .9)
        self.L_ALG = faded(radial(int(26 * o) // S, 255, 1.0, K, 1), min(255, int(70 * o)))
        self.alg_glow = glow_rgb(int(26 * o) // S, (60, 200, 120), .55)
        # cuando Xolthar ve a Mullo las luces de la cueva bajan y vuelven a subir: versiones más tenues ya hechas
        self.dim_cry = [faded(self.L_CRY, int(255 * k)) for k in DIM_LEVELS]
        self.dim_fun = [faded(self.L_FUN, int(255 * k)) for k in DIM_LEVELS]
        self.dim_alg = [faded(self.L_ALG, int(255 * k)) for k in DIM_LEVELS]
        self.dim_glow = {col: [dim_rgb(gl, k) for k in DIM_LEVELS] for col, gl in self.glow.items()}
        self.dim_fun_glow = [dim_rgb(self.fun_glow, k) for k in DIM_LEVELS]
        self.dim_alg_glow = [dim_rgb(self.alg_glow, k) for k in DIM_LEVELS]
        # luz roja de Xolthar: ilumina las paredes y se ve venir por los túneles (no baja con las demás)
        self.L_BOSS = faded(radial(260 // S, 255, 1.1, K, 1), 175)
        self.L_BOSS_LV = [faded(self.L_BOSS, int(255 * k)) for k in (.25, .5, .75, 1.0)]
        self.boss_glows = [glow_rgb(260 // S, (255, 46, 26), .45 + .35 * k / 3) for k in range(4)]
        self.nest_glows = [glow_rgb(210 // S, nest_col, .45 + .2 * k / 5) for k in range(6)]
        self.dawn_glows = [glow_rgb(300 // S, (255, 170, 90), .55 + .25 * k / 5) for k in range(6)]
        # boca de la cueva (junto al nido): su luz pasa de azul noche a rosado conforme se acerca el amanecer
        self.mouth_glows = [glow_rgb(260 // S, mouth_color(k / (MOUTH_STEPS - 1)), .55) for k in range(MOUTH_STEPS)]
        self.L_DAWN = radial(300 // S, 255, 1.0, K, 1)
        self.L_ECHO = {}
        self._warm_echo()                                  # el destello del grito se prepara aquí (no a medio juego)
        self.aura = glow_rgb(70 // S, (150, 160, 255), .35)
        self.vig = make_vignette(self.vw // S, self.vh // S)
        self.bake = BAKE_STATIC                            # (ver _baked)
        self._bake_key, self._bake = None, None
        self._mem_key, self._mem_img = None, None          # imagen ampliada de la memoria (se recalcula solo si cambia)
        self._flick = {}                                   # luz del murciélago con distintos parpadeos (precalculadas)
        for lv in BRIGHTNESS_LEVELS:                       # se preparan todas al cargar el nivel (sin tirones al jugar)
            base = self.bat_lights[lv[2]]
            for step in range(-3, 4):
                sz = int(base.get_width() * (1 + .01 * step))
                self._flick[(lv[2], step)] = pygame.transform.scale(base, (sz, sz)) if step else base
        col = {'fungi': (70, 100, 220), 'lake': (150, 90, 230), 'mine': (255, 150, 70)}[theme]
        self._sky = (radial(170 // S, 230, 1.3, K, 1), glow_rgb(170 // S, col, .55))

    @staticmethod
    def _echo_key(k):
        r = int((SCREECH_R * 2.4 * (1 - k * .55)) / S)
        return (r // 4, int(k * 6)), k

    def _echo_surf(self, key, k):
        surf = self.L_ECHO.get(key)
        if surf is None:
            surf = self.L_ECHO[key] = faded(radial(max(4, key[0] * 4), 255, .5, K, 2), int(200 * min(1, k * 1.3)))
        return surf

    def _warm_echo(self):
        """Crea de una vez todos los tamaños del destello de ecolocación. Antes se creaban durante el primer grito
        de cada nivel y ese momento se trababa."""
        for i in range(0, 241):
            key, k = self._echo_key(i / 240)
            if k > 0:
                self._echo_surf(key, k)

    BAKE_GRID = 128                                        # cada cuánto (px del mundo) se vuelven a sumar las luces fijas

    def _baked(self, cam, li):
        """Luces fijas (cristales, hongos, algas) sumadas en dos capas que cubren la vista y un margen alrededor.
        Da exactamente el mismo resultado que pegarlas una por una (la suma y la resta son las mismas), pero
        en vez de ~2 pegados por luz en cada cuadro, son 2 en total; solo se rehacen al moverse la cámara 128 px.
        En el navegador cada pegado cuesta mucho: esto es lo que más aligera la luz."""
        g = self.BAKE_GRID
        ox = int(cam.x) // g * g - g
        oy = int(cam.y) // g * g - g
        key = (ox, oy, li)
        if key != self._bake_key:
            rw, rh = (self.vw + 3 * g) // S, (self.vh + 3 * g) // S
            if self._bake is None or self._bake[0].get_size() != (rw, rh):
                self._bake = (pygame.Surface((rw, rh), pygame.SRCALPHA), pygame.Surface((rw, rh)))
            bsub, badd = self._bake
            bsub.fill((0, 0, 0, 0))
            badd.fill((0, 0, 0))
            x0, y0, x1, y1 = ox - 130, oy - 130, ox + rw * S + 130, oy + rh * S + 130
            l_cry, l_fun, l_alg = self.dim_cry[li], self.dim_fun[li], self.dim_alg[li]
            fun_glow, alg_glow = self.dim_fun_glow[li], self.dim_alg_glow[li]
            lights = [(x, y, l_cry, self.dim_glow[col][li]) for x, y, col in self.crystals]
            lights += [(x, y, l_fun, fun_glow) for x, y in self.fungi]
            lights += [(x, y, l_alg, alg_glow) for x, y in self.algae]
            for x, y, ls, lg in lights:
                if x0 <= x <= x1 and y0 <= y <= y1:
                    px, py = round((x - ox) / S), round((y - oy) / S)
                    hw = ls.get_width() // 2
                    bsub.blit(ls, (px - hw, py - hw), special_flags=pygame.BLEND_RGBA_ADD)
                    hw = lg.get_width() // 2
                    badd.blit(lg, (px - hw, py - hw), special_flags=ADD)
            self._bake_key = key
        bsub, badd = self._bake
        return bsub, badd, round((int(cam.x) - ox) / S), round((int(cam.y) - oy) / S)

    def _memory(self, d, cam, cave):
        """Aclara tenuemente los tiles ya recorridos, para orientarte por dónde pasaste."""
        tx0, ty0 = int(cam.x) // TILE, int(cam.y) // TILE
        rect = pygame.Rect(tx0, ty0, self.vw // TILE + 2, self.vh // TILE + 2).clip(pygame.Rect(0, 0, cave.w, cave.h))
        if rect.w <= 0 or rect.h <= 0:
            return
        key = (rect.x, rect.y, rect.w, rect.h, cave.mem_version)
        if key != self._mem_key:
            tile_s = TILE // S
            self._mem_img = pygame.transform.smoothscale(cave.mem.subsurface(rect), (rect.w * tile_s, rect.h * tile_s))
            self._mem_key = key
        d.blit(self._mem_img, ((rect.x * TILE - int(cam.x)) // S, (rect.y * TILE - int(cam.y)) // S), special_flags=SUB)

    def apply(self, c, g, t):
        """Oscurece el lienzo c y añade los brillos de color. g es la escena de juego."""
        cam, b = g.camera, g.bat
        _, ambient, radius = BRIGHTNESS_LEVELS[g.game.brightness]
        dim = g.light_dim() if hasattr(g, 'light_dim') else 1.0       # Xolthar la vio: las luces bajan y suben
        li = min(len(DIM_LEVELS) - 1, max(0, int(round((dim - DIM_LEVELS[0]) / (1 - DIM_LEVELS[0]) * (len(DIM_LEVELS) - 1)))))
        ambient = max(120, min(252, ambient + self.amb_off + int((1 - dim) * 62)))
        d = self.small
        d.fill((*self.amb_rgb, ambient))
        if g.echo_t > 0:                       # ecolocación: el grito "dibuja" un momento lo que rodea a Mullo
            key, k = self._echo_key(min(1.0, g.echo_t / ECHO_FLASH_T))
            ox, oy = cam.apply(*g.echo_origin)
            surf = self._echo_surf(key, k)
            hw = surf.get_width() // 2
            d.blit(surf, (round(ox / S) - hw, round(oy / S) - hw), special_flags=SUB)
        self._memory(d, cam, g.cave)
        step = round(3 * math.sin(t * 9) * math.sin(t * 3.1))      # parpadeo suave en 7 pasos (-3..3)
        if dim < .95:                                                # su luz también se encoge un poco
            step = max(-3, step - int((1 - dim) * 5))
        lb = self._flick.get((radius, step))
        if lb is None:
            base = self.bat_lights[radius]
            sz = int(base.get_width() * (1 + .01 * step))
            lb = self._flick[(radius, step)] = pygame.transform.scale(base, (sz, sz)) if step else base
        bx, by = cam.apply(b.x, b.y)
        hw = lb.get_width() // 2
        d.blit(lb, (round(bx / S) - hw, round(by / S) - hw), special_flags=SUB)
        nx, ny = cam.apply(*NEST)
        dawn = self.theme == 'mine'
        near_nest = cam.visible(*NEST, 340 if dawn else 260)
        if near_nest:
            ln = self.L_DAWN if dawn else self.L_NEST
            hw = ln.get_width() // 2
            d.blit(ln, (round(nx / S) - hw, round(ny / S) - hw), special_flags=SUB)
        for p in g.pups:
            if p is not b.carry and cam.visible(p.x, p.y, 80):
                px, py = cam.apply(p.x, p.y)
                hw = self.L_PUP.get_width() // 2
                d.blit(self.L_PUP, (round(px / S) - hw, round(py / S) - hw), special_flags=SUB)
        if self.bake:                                              # navegador: luces fijas ya sumadas en 2 capas
            bsub, badd, box, boy = self._baked(cam, li)
            d.blit(bsub, (-box, -boy), special_flags=SUB)
            vis_c = vis_f = vis_a = ()
        else:
            badd = None
            vis_c = [(x, y, col) for x, y, col in self.crystals if cam.visible(x, y, 120)]
            vis_f = [(x, y) for x, y in self.fungi if cam.visible(x, y, 80)]
            if len(vis_f) > 28:                                    # en pantalla basta con los más cercanos
                vis_f = sorted(vis_f, key=lambda p: (p[0] - b.x) ** 2 + (p[1] - b.y) ** 2)[:28]
            vis_a = [(x, y) for x, y in self.algae if cam.visible(x, y, 40)]
        l_cry, l_fun, l_alg = self.dim_cry[li], self.dim_fun[li], self.dim_alg[li]
        for x, y, col in vis_c:
            sx, sy = cam.apply(x, y)
            hw = l_cry.get_width() // 2
            d.blit(l_cry, (round(sx / S) - hw, round(sy / S) - hw), special_flags=SUB)
        for x, y in vis_f:
            sx, sy = cam.apply(x, y)
            hw = l_fun.get_width() // 2
            d.blit(l_fun, (round(sx / S) - hw, round(sy / S) - hw), special_flags=SUB)
        for x, y in vis_a:
            sx, sy = cam.apply(x, y)
            hw = l_alg.get_width() // 2
            d.blit(l_alg, (round(sx / S) - hw, round(sy / S) - hw), special_flags=SUB)
        if dim < .97:                                                # todas las luces bajan (también la de Mullo)
            d.fill((0, 0, 0, int((1 - dim) * 150)), special_flags=pygame.BLEND_RGBA_ADD)
        bl = g.boss_light() if hasattr(g, 'boss_light') else None
        if bl:                                                       # luz roja de Xolthar (ilumina las paredes)
            bxl, byl, bk = bl
            sx, sy = cam.apply(bxl, byl)
            hw = self.L_BOSS.get_width() // 2
            lb_boss = self.L_BOSS_LV[min(3, int(bk * 3.99))]
            d.blit(lb_boss, (round(sx / S) - hw, round(sy / S) - hw), special_flags=SUB)
        # brillos tintados: se suman al color de la capa de oscuridad, así se ven de lejos
        hw = self.aura.get_width() // 2
        d.blit(self.aura, (round(bx / S) - hw, round(by / S) - hw), special_flags=ADD)
        if near_nest:
            ng = (self.dawn_glows if dawn else self.nest_glows)[int(2.5 + 2.5 * math.sin(t * 2.2))]
            hw = ng.get_width() // 2
            d.blit(ng, (round(nx / S) - hw, round(ny / S) - hw), special_flags=ADD)
            if not dawn and hasattr(g, 'night_frac'):        # (en la mina ya se ve el amanecer naranja)
                mg = self.mouth_glows[min(MOUTH_STEPS - 1, int(g.night_frac() * (MOUTH_STEPS - 1) + .5))]
                hw = mg.get_width() // 2
                mx, my = cam.apply(NEST[0] - 70, NEST[1] - 80)  # hacia la salida, arriba del nido
                d.blit(mg, (round(mx / S) - hw, round(my / S) - hw), special_flags=ADD)
        if badd is not None:
            d.blit(badd, (-box, -boy), special_flags=ADD)
        for x, y, col in vis_c:
            sx, sy = cam.apply(x, y)
            gl = self.dim_glow[col][li]
            hw = gl.get_width() // 2
            d.blit(gl, (round(sx / S) - hw, round(sy / S) - hw), special_flags=ADD)
        fun_glow, alg_glow = self.dim_fun_glow[li], self.dim_alg_glow[li]
        for x, y in vis_f:
            sx, sy = cam.apply(x, y)
            hw = fun_glow.get_width() // 2
            d.blit(fun_glow, (round(sx / S) - hw, round(sy / S) - hw), special_flags=ADD)
        for x, y in vis_a:
            sx, sy = cam.apply(x, y)
            hw = alg_glow.get_width() // 2
            d.blit(alg_glow, (round(sx / S) - hw, round(sy / S) - hw), special_flags=ADD)
        if bl:
            sx, sy = cam.apply(bxl, byl)
            gb = self.boss_glows[min(3, int(bk * 3.99))]
            hw = gb.get_width() // 2
            d.blit(gb, (round(sx / S) - hw, round(sy / S) - hw), special_flags=ADD)
        sky = getattr(g.cave, 'skylight', None)                    # luz que entra por la grieta del techo
        if sky and cam.visible(*sky, 260):
            sub, add = self._sky
            sx, sy = cam.apply(sky[0], sky[1] + 110)
            hw = sub.get_width() // 2
            d.blit(sub, (round(sx / S) - hw, round(sy / S) - hw), special_flags=SUB)
            d.blit(add, (round(sx / S) - hw, round(sy / S) - hw), special_flags=ADD)
        d.blit(self.vig, (0, 0))                                   # viñeta
        pygame.transform.scale(d, (self.vw, self.vh), self.up)                 # una sola ampliación
        c.blit(self.up, (0, 0))

    # ------------------------------------------------------------ efectos directos sobre el lienzo
    def draw_shield(self, c, g, t):
        """Burbuja del escudo alrededor del murciélago (parpadea al agotarse)."""
        b = g.bat
        if b.shield_t <= 0:
            return
        if b.shield_t < 1.2 and int(t * 12) % 2:
            return
        x, y = g.camera.apply(b.x, b.y)
        r = SHIELD_R + int(2 * math.sin(t * 10))
        ring(c, x, y, r - 3, (110, 200, 255), .55, 2)
        ring(c, x, y, r, (170, 230, 255), 1.0, 3)
        pygame.draw.arc(c, (255, 255, 255), (x - r + 4, y - r + 4, 2 * r - 8, 2 * r - 8), .6 + t * 2, 1.5 + t * 2, 3)

    def draw_trail(self, c, g):
        """Estela tenue que deja el murciélago al volar rápido."""
        for x, y, life in g.bat.trail:
            sx, sy = g.camera.apply(x, y)
            f = life / .35
            pygame.draw.circle(c, (int(120 * f), int(105 * f), int(190 * f)), (int(sx), int(sy)), 2 + int(3 * f))
