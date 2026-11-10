"""Pantallas de resultado: GAME OVER, NIVEL SUPERADO y VICTORIA.

El récord es por completar los 3 niveles (tiempo total de la historia) y se guarda solo, sin pedir nombre.
Piezas reutilizables:
  Buttons      fila de botones (teclado ← → Enter, mouse y toques)
  draw_table   tabla de mejores tiempos
  StoryResults tiempo total, récord y lugar en la tabla (pantalla de VICTORIA)
  draw_game_over / draw_level_clear   pantallas superpuestas del nivel
"""
import math
import random

import pygame

import scores
import ui
from settings import W, H, GOAL, C_GOLD, C_PUP


def run_time(g):
    """Tiempo de la partida: el total de la historia (si empezó desde el prólogo) o, si no, el del nivel."""
    prog = getattr(getattr(g, 'game', None), 'progress', None) or {}
    return prog.get('play_time', g.t) if prog.get('full_run') else g.t


def is_full_run(g):
    prog = getattr(getattr(g, 'game', None), 'progress', None) or {}
    return bool(prog.get('full_run'))


# ---------------------------------------------------------------- utilidades de dibujo
_CACHE = {}


def glow_title(s, f, txt, cx, cy, col, glow_col, t=0.0, scale=1.0):
    """Título grande con resplandor que late (las superficies se cachean)."""
    key = (id(f), txt, col, glow_col)
    if key not in _CACHE:
        _CACHE[key] = (ui.make_glow(f, txt, glow_col, blur=6, pad=40), f.render(txt, True, (10, 4, 20)),
                       f.render(txt, True, col))
    glow, shadow, word = _CACHE[key]
    if scale != 1.0:
        sz = lambda im: (max(1, int(im.get_width() * scale)), max(1, int(im.get_height() * scale)))  # noqa: E731
        glow, shadow, word = (pygame.transform.smoothscale(im, sz(im)) for im in (glow, shadow, word))
    glow.set_alpha(int(150 + 90 * (.5 + .5 * math.sin(t * 3))))
    s.blit(glow, glow.get_rect(center=(cx, cy)))
    s.blit(shadow, shadow.get_rect(center=(cx + 3, cy + 5)))
    s.blit(word, word.get_rect(center=(cx, cy)))


def card(s, rect, fill=(10, 6, 24, 215), border=(150, 120, 220), width=2, radius=16):
    key = ('card', rect[2], rect[3], fill, border, width, radius)
    im = _CACHE.get(key)
    if im is None:
        im = _CACHE[key] = pygame.Surface(rect[2:], pygame.SRCALPHA)
        pygame.draw.rect(im, fill, im.get_rect(), border_radius=radius)
        pygame.draw.rect(im, (*border, 230), im.get_rect(), width, border_radius=radius)
    s.blit(im, rect[:2])


def pill(s, txt, cx, cy, col, bg):
    w = ui.F_XS.size(txt)[0] + 28
    r = pygame.Rect(0, 0, w, 26)
    r.center = (cx, cy)
    pygame.draw.rect(s, bg, r, border_radius=13)
    pygame.draw.rect(s, col, r, 1, border_radius=13)
    ui.text(s, ui.F_XS, txt, cx, cy, col, True)


def _veil(kind):
    """Velo de pantalla completa: rojo oscuro (derrota) o violeta profundo (victoria), más oscuro en los bordes."""
    key = ('veil', kind)
    if key not in _CACHE:
        base = (24, 0, 6) if kind == 'over' else (8, 4, 26)
        small = pygame.Surface((48, 32), pygame.SRCALPHA)       # se calcula chico y se escala (suave y rápido)
        for y in range(32):
            for x in range(48):
                d = math.hypot((x - 23.5) / 24, (y - 15.5) / 16)
                small.set_at((x, y), (*base, int(min(252, 218 + 40 * d * d))))
        _CACHE[key] = pygame.transform.smoothscale(small, (W, H))
    return _CACHE[key]


def _rays():
    """Abanico de rayos dorados que gira detrás del título de victoria."""
    if 'rays' not in _CACHE:
        R = 520
        s = pygame.Surface((2 * R, 2 * R), pygame.SRCALPHA)
        for i in range(16):
            a0 = i * math.tau / 16
            pts = [(R, R), (R + math.cos(a0) * R, R + math.sin(a0) * R),
                   (R + math.cos(a0 + .12) * R, R + math.sin(a0 + .12) * R)]
            pygame.draw.polygon(s, (255, 200, 110, 20), pts)
        _CACHE['rays'] = s
    return _CACHE['rays']


def ease_out_back(k):
    k = max(0.0, min(1.0, k))
    c = 1.7
    return 1 + (c + 1) * (k - 1) ** 3 + c * (k - 1) ** 2


# ---------------------------------------------------------------- partículas
class Particles:
    """Polvo que cae (derrota) o confeti/estrellitas (victoria)."""

    def __init__(self, kind, n=60):
        self.kind, self.p = kind, []
        rnd = random.Random(7)
        for _ in range(n):
            self.p.append(self._new(rnd, rnd.uniform(0, H)))

    def _new(self, rnd, y=-10.0):
        if self.kind == 'over':
            return [rnd.uniform(0, W), y, rnd.uniform(-8, 8), rnd.uniform(18, 45), rnd.uniform(1, 2.5),
                    (120 + rnd.randint(0, 40), 70, 80), rnd.uniform(0, 6)]
        col = random.choice([C_GOLD, C_PUP, (190, 150, 255), (160, 255, 190), (255, 255, 255)])
        return [rnd.uniform(0, W), y, rnd.uniform(-30, 30), rnd.uniform(50, 110), rnd.uniform(2, 4), col,
                rnd.uniform(0, 6)]

    def update(self, dt):
        for q in self.p:
            q[0] += (q[2] + math.sin(q[6] + q[1] * .02) * 20) * dt
            q[1] += q[3] * dt
            q[6] += dt * 3
            if q[1] > H + 10:
                q[:] = self._new(random)

    def draw(self, s):
        for x, y, _, _, r, col, ph in self.p:
            if self.kind == 'over':
                pygame.draw.circle(s, col, (int(x), int(y)), int(r))
            else:                                              # confeti que gira
                w = max(1, int(r * 2 * abs(math.cos(ph))))
                pygame.draw.rect(s, col, (int(x) - w // 2, int(y) - int(r), w, int(r * 2)))


# ---------------------------------------------------------------- botones
class Buttons:
    """Fila de botones centrada. handle() devuelve el índice elegido o None."""

    def __init__(self, labels, cy, w=210, h=50, gap=24, cx=W // 2):
        self.labels, self.sel, self.t = labels, 0, 0.0
        total = len(labels) * w + (len(labels) - 1) * gap
        x0 = cx - total // 2
        self.rects = [pygame.Rect(x0 + i * (w + gap), cy - h // 2, w, h) for i in range(len(labels))]

    def handle(self, ev, sounds=None):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_LEFT, pygame.K_a) and len(self.labels) > 1:
                self.sel = (self.sel - 1) % len(self.labels)
                sounds and sounds.play('menu_move')
            elif ev.key in (pygame.K_RIGHT, pygame.K_d) and len(self.labels) > 1:
                self.sel = (self.sel + 1) % len(self.labels)
                sounds and sounds.play('menu_move')
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                sounds and sounds.play('menu_select')
                return self.sel
        elif ev.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self.rects):
                if r.collidepoint(ev.pos) and i != self.sel:
                    self.sel = i
                    sounds and sounds.play('menu_move')
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            return self.click(ev.pos, sounds)
        return None

    def click(self, pos, sounds=None):
        for i, r in enumerate(self.rects):
            if r.collidepoint(pos):
                self.sel = i
                sounds and sounds.play('menu_select')
                return i
        return None

    def draw(self, s, dt, accent=(200, 160, 255), fill=(110, 70, 190)):
        self.t += dt
        pulse = .5 + .5 * math.sin(self.t * 5)
        for i, (label, r) in enumerate(zip(self.labels, self.rects)):
            on = i == self.sel
            box = pygame.Surface(r.size, pygame.SRCALPHA)
            if on:
                pygame.draw.rect(box, (*fill, 170 + int(50 * pulse)), box.get_rect(), border_radius=14)
                pygame.draw.rect(box, (*accent, 255), box.get_rect(), 2, border_radius=14)
            else:
                pygame.draw.rect(box, (20, 14, 34, 190), box.get_rect(), border_radius=14)
                pygame.draw.rect(box, (90, 74, 120, 220), box.get_rect(), 1, border_radius=14)
            s.blit(box, r.move(0, -2 if on else 0))
            ui.text(s, ui.F_S, label, r.centerx, r.centery - (2 if on else 0),
                    (255, 255, 255) if on else (175, 160, 200), True)


# ---------------------------------------------------------------- tabla de récords
def draw_table(s, rect, title, rows, highlight=None, t=0.0, row_h=28):
    """Tabla de mejores tiempos: lugar, tiempo y fecha. highlight: fila que parpadea (la marca recién hecha)."""
    x, y, w, h = rect
    card(s, rect, (8, 5, 20, 205), (120, 100, 175), 1, 14)
    ui.text(s, ui.F_XS, title, x + w // 2, y + 20, (200, 185, 235), True)
    pygame.draw.line(s, (90, 75, 130), (x + 18, y + 36), (x + w - 18, y + 36), 1)
    medals = [(255, 210, 90), (205, 210, 225), (220, 150, 90)]
    for i in range(scores.TOP_N):
        ry = y + 52 + i * row_h
        r = rows[i] if i < len(rows) else None
        hl = i == highlight
        if hl:
            k = .5 + .5 * math.sin(t * 6)
            pygame.draw.rect(s, (int(70 + 40 * k), int(50 + 20 * k), 30), (x + 10, ry - row_h // 2 + 1, w - 20, row_h - 2),
                             border_radius=8)
        col = medals[i] if i < 3 else (180, 170, 205)
        filled = r is not None and i < 3
        pygame.draw.circle(s, col, (x + 32, ry), 10, 0 if filled else 1)
        ui.text(s, ui.F_XS, str(i + 1), x + 32, ry, (30, 20, 10) if filled else col, True)
        if r:
            nc = (255, 240, 200) if hl else (235, 228, 250)
            ui.text(s, ui.F_S, scores.fmt(r['time']), x + 54, ry - 11, nc)
            d = str(r.get('date', ''))
            ui.text(s, ui.F_XS, d, x + w - 22 - ui.F_XS.size(d)[0], ry - 8, (255, 225, 170) if hl else (160, 150, 190))
        else:
            ui.text(s, ui.F_XS, '— — —', x + 54, ry - 8, (100, 90, 125))


# ---------------------------------------------------------------- resultado de la historia completa
class StoryResults:
    """Al terminar los 3 niveles: guarda el tiempo total (sin pedir nombre) y muestra el lugar y la tabla."""

    def __init__(self, t, sounds=None, button='Ver créditos  »'):
        self.time, self.sounds = t, sounds
        self.prev_best = scores.best()
        self.new_record = self.prev_best is None or t < self.prev_best
        self.place = scores.add(t)                                 # lugar en la tabla (None si no entró)
        self.age = 0.0
        self.buttons = Buttons([button], 572, w=240)
        self._sfx = False

    def handle(self, ev):
        """True cuando el jugador quiere continuar."""
        return self.age >= .8 and self.buttons.handle(ev, self.sounds) is not None

    def click(self, pos):
        return self.age >= .8 and self.buttons.click(pos, self.sounds) is not None

    def update(self, dt):
        self.age += dt
        if self.new_record and not self._sfx and self.age > .9:     # suena cuando aparece «¡NUEVO RÉCORD!»
            self._sfx = True
            if self.sounds:
                self.sounds.play('deliver')

    def draw(self, s, dt, y0=206, extra=None):
        t = self.age
        lx, rx = 60, 490
        card(s, (lx, y0, 380, 128), (14, 8, 30, 220), (255, 205, 120), 2, 18)
        ui.text(s, ui.F_XS, 'TIEMPO TOTAL · 3 NIVELES', lx + 190, y0 + 20, (230, 200, 150), True)
        shown = self.time * min(1.0, t / .9)                        # el número "corre" hasta el tiempo final
        glow_title(s, ui.F_L, scores.fmt(shown), lx + 190, y0 + 66, (255, 240, 210), (255, 160, 60), t)
        if self.new_record and t > .9:
            if int(t * 3) % 2 or t > 3:
                pill(s, '¡NUEVO RÉCORD!', lx + 190, y0 + 108, (40, 20, 0), C_GOLD)
        elif self.prev_best is not None:
            ui.text(s, ui.F_XS, f'Récord: {scores.fmt(self.prev_best)}   (+{scores.fmt(self.time - self.prev_best)})',
                    lx + 190, y0 + 106, (200, 185, 225), True)
        if extra:
            extra(s, lx + 190, y0 + 152)
        if t > .9:
            if self.place is not None:
                ui.text(s, ui.F_M, f'¡Quedaste en el lugar #{self.place + 1}!', lx + 190, y0 + 210, C_GOLD, True)
            else:
                ui.text(s, ui.F_S, f'No entraste al TOP {scores.TOP_N}… ¡a la próxima!', lx + 190, y0 + 210,
                        (200, 185, 225), True)
        draw_table(s, (rx, y0, 410, 52 + scores.TOP_N * 28), 'MEJORES TIEMPOS · HISTORIA COMPLETA', scores.top(),
                   self.place, t)
        if t > .8:
            self.buttons.draw(s, dt)


# ---------------------------------------------------------------- pantallas del nivel
_FX = {}


def _fx(g, kind):
    """Partículas propias de cada escena/estado."""
    key = (id(g), kind)
    if key not in _FX:
        _FX.clear()
        _FX[key] = Particles(kind, 70 if kind == 'over' else 90)
    return _FX[key]


def hint(s, txt, y=H - 18):
    ui.text(s, ui.F_XS, txt, W // 2, y, (170, 155, 200), True)


DAWN_T = 7.0                                                    # segundos de la escena «la colonia se va sin Mullo»
DAWN_LINES = ['Mullo tardó demasiado y la noche se acabó.',
              'Antes del amanecer, la colonia parte hacia su nuevo refugio.',
              'La Abuela Canela es la última en salir... y se va sin Mullo.']


def dawn_scene_on(g):
    """¿Se está mostrando la escena de la colonia yéndose? (solo cuando se acabó el tiempo)"""
    return g.lose_reason == 'dawn' and g.over_t < DAWN_T


def _draw_left_behind(s, g):
    """Se acabó el tiempo: la colonia se va sin Mullo (propuesta: «con ella o sin ella»). Cualquier tecla la salta."""
    shot = getattr(g, '_left_shot', None)
    if shot is None:
        from art import make_shot
        shot = g._left_shot = make_shot('left_behind')
    t = g.over_t
    shot.draw(s, t, DAWN_T)
    bars = _CACHE.get('bars')
    if bars is None:
        bars = _CACHE['bars'] = pygame.Surface((W, 74))
        bars.fill((0, 0, 0))
    s.blit(bars, (0, 0))
    s.blit(bars, (0, H - 74))
    ui.text(s, ui.F_XS, 'SE ACABÓ LA NOCHE', W // 2, 37, (255, 200, 150), True)
    shown = int((t - .5) * 40)                                  # el texto se escribe solo
    y = H - 160
    for ln in DAWN_LINES:
        part = ln[:max(0, shown)]
        shown -= len(ln)
        if part:
            ui.text(s, ui.F_S, part, W // 2, y, (250, 240, 235), True)
        y += 28
    if t < .6:                                                  # entra desde negro
        v = _CACHE.get('black')
        if v is None:
            v = _CACHE['black'] = pygame.Surface((W, H))
        v.set_alpha(int(255 * (1 - t / .6)))
        s.blit(v, (0, 0))
    elif t > DAWN_T - .6:                                       # y se funde a negro antes del GAME OVER
        v = _CACHE.get('black') or pygame.Surface((W, H))
        _CACHE['black'] = v
        v.set_alpha(int(255 * min(1, (t - (DAWN_T - .6)) / .6)))
        s.blit(v, (0, 0))
    if t > 1.5:
        ui.text(s, ui.F_XS, 'Cualquier tecla: continuar', W - 120, H - 37, (170, 155, 200), True)


def draw_game_over(s, g, dt):
    """Pantalla de derrota: GAME OVER, motivo, estadísticas del intento y botones.
    Si se acabó el tiempo, antes se ve cómo la colonia se va sin Mullo."""
    if dawn_scene_on(g):
        return _draw_left_behind(s, g)
    t = g.over_t - (DAWN_T if g.lose_reason == 'dawn' else 0)
    s.blit(_veil('over'), (0, 0))
    fx = _fx(g, 'over')
    fx.update(dt)
    fx.draw(s)
    cx = W // 2
    k = ease_out_back(t / .7)
    glow_title(s, ui.F_XL, 'GAME OVER', cx, int(-60 + 190 * k), (255, 225, 225), (230, 30, 50), t, .6 + .4 * k)
    if t > .4:
        reason = 'SE ACABÓ LA NOCHE · LA COLONIA SE FUE' if g.lose_reason == 'dawn' else 'TE QUEDASTE SIN VIDAS'
        pill(s, reason, cx, 208, (255, 200, 200), (60, 10, 20))
    # Mullo, triste y envuelta en sus alas
    bob = math.sin(t * 2) * 4
    ui.draw_mullo(s, cx, 268 + bob, 1.0 + .1 * math.sin(t * 2), 1.8, fold=.95, mood='closed')
    for i in range(2):                                          # lagrimitas
        p = (t * .8 + i * .5) % 1
        pygame.draw.circle(s, (140, 190, 255), (int(cx + (-9 if i else 9)), int(268 + bob + 4 + p * 26)), 2)
    # estadísticas del intento
    cw, ch = 600, 96
    x0, y0 = cx - cw // 2, 322
    card(s, (x0, y0, cw, ch), (16, 4, 10, 220), (200, 80, 100), 2, 16)
    best = getattr(g, 'best_time', None)
    cols = [('TIEMPO TOTAL' if is_full_run(g) else 'TIEMPO', scores.fmt(run_time(g)), (255, 230, 230)),
            ('CRÍAS DEL NIVEL', f'{g.rescued_here}/{g.goal_here}', C_PUP),
            ('RÉCORD · 3 NIVELES', scores.fmt(best) if best is not None else '—', C_GOLD)]
    for i, (lab, val, col) in enumerate(cols):
        ccx = x0 + cw * (i + .5) / 3
        ui.text(s, ui.F_XS, lab, ccx, y0 + 26, (210, 160, 170), True)
        ui.text(s, ui.F_M, val, ccx, y0 + 62, col, True)
        if i:
            pygame.draw.line(s, (110, 50, 70), (x0 + cw * i / 3, y0 + 16), (x0 + cw * i / 3, y0 + ch - 16), 1)
    sub = f'{g.cfg["act"]} · {g.cfg["name"]}'
    if is_full_run(g):
        sub += '    ·    el reloj sigue contando al reintentar'
    ui.text(s, ui.F_XS, sub, cx, y0 + ch + 22, (200, 170, 190), True)
    if t > .6:
        g.over_buttons.draw(s, dt, (255, 150, 160), (150, 40, 60))
        touch = getattr(getattr(g, 'game', None), 'touch', None)
        if not (touch is not None and touch.active):
            hint(s, '← → elegir    ·    Enter aceptar    ·    R reintentar    ·    Esc menú principal')


def draw_level_clear(s, g, dt):
    """Pantalla de nivel superado: título con rayos, tiempo del nivel, tiempo total y avance hacia el récord."""
    t = g.clear_t
    s.blit(_veil('clear'), (0, 0))
    rays = pygame.transform.rotate(_rays(), (t * 12) % 360)
    s.blit(rays, rays.get_rect(center=(W // 2, 120)))
    fx = _fx(g, 'clear')
    fx.update(dt)
    fx.draw(s)
    cx, cfg = W // 2, g.cfg
    ui.text(s, ui.F_S, f'{cfg["act"].upper()} · {cfg["name"].upper()}', cx, 56, C_GOLD, True)
    k = ease_out_back(t / .6)
    glow_title(s, ui.F_L, '¡NIVEL SUPERADO!', cx, 118, (255, 245, 220), (255, 170, 60), t, max(.05, k))
    for i in range(g.goal_here):                                # crías de este nivel, a salvo
        ui.pup_icon(s, cx - (g.goal_here - 1) * 13 + i * 26, 172, 'safe', t + i)
    ui.draw_mullo(s, cx - 160, 166 + math.sin(t * 4) * 5, t * 10, .8, mood='happy')
    ui.draw_mullo(s, cx + 160, 166 + math.sin(t * 4 + 1) * 5, t * 10 + 1, .8, mood='happy')
    # tiempos
    full = is_full_run(g)
    best = getattr(g, 'best_time', None)
    cw, ch = 680, 124
    x0, y0 = cx - cw // 2, 212
    card(s, (x0, y0, cw, ch), (14, 8, 30, 220), (255, 205, 120), 2, 18)
    cols = [('TIEMPO DEL NIVEL', scores.fmt(g.t), (240, 232, 255))]
    if full:
        cols.append(('TIEMPO TOTAL', scores.fmt(run_time(g) * min(1.0, t / .9)), (255, 240, 210)))
    cols.append(('RÉCORD · 3 NIVELES', scores.fmt(best) if best is not None else '—', C_GOLD))
    n = len(cols)
    for i, (lab, val, col) in enumerate(cols):
        ccx = x0 + cw * (i + .5) / n
        ui.text(s, ui.F_XS, lab, ccx, y0 + 30, (230, 200, 150), True)
        if lab == 'TIEMPO TOTAL':
            glow_title(s, ui.F_L, val, ccx, y0 + 76, col, (255, 160, 60), t, .8)
        else:
            ui.text(s, ui.F_M, val, ccx, y0 + 76, col, True)
        if i:
            pygame.draw.line(s, (120, 95, 70), (x0 + cw * i / n, y0 + 18), (x0 + cw * i / n, y0 + ch - 18), 1)
    # avance: los 3 niveles
    py = 392
    for lv in (1, 2, 3):
        x = cx + (lv - 2) * 150
        done = lv <= g.level
        if lv < 3:
            pygame.draw.line(s, C_GOLD if lv < g.level else (80, 70, 110), (x + 22, py), (x + 128, py), 3)
        pygame.draw.circle(s, C_GOLD if done else (30, 24, 50), (x, py), 20)
        pygame.draw.circle(s, (255, 240, 200) if done else (110, 95, 150), (x, py), 20, 2)
        ui.text(s, ui.F_S, str(lv), x, py, (40, 20, 0) if done else (170, 155, 200), True)
        ui.text(s, ui.F_XS, f'Nivel {lv}', x, py + 34, (240, 225, 200) if done else (150, 140, 175), True)
    left = 3 - g.level
    if not full:
        msg, col = 'El récord solo cuenta jugando los 3 niveles desde «Jugar».', (200, 185, 225)
    elif left:
        msg, col = f'Te falta{"n" if left > 1 else ""} {left} nivel{"es" if left > 1 else ""} para tu tiempo final. ¡El reloj sigue!', C_PUP
    else:
        msg, col = '¡Completaste los 3 niveles! Tu tiempo final se guarda al terminar la historia.', C_PUP
    ui.text(s, ui.F_S, msg, cx, 468, col, True)
    if t > .8:
        g.clear_buttons.draw(s, dt)
    touch = getattr(getattr(g, 'game', None), 'touch', None)
    if not (touch is not None and touch.active):
        hint(s, 'Enter: continuar la historia    ·    Esc: menú principal', H - 14)
