"""Escena de juego: un nivel (acto) de la historia. Orquesta cueva, Mullo, crías, enemigos, luces, HUD y momentos de historia."""
import math
import random

import pygame

import difficulty
import ui
from camera import Camera
from enemies import Enemy, Boss, pick_kind
from fauna import Defeat, DropSpider, Resting, spawn_salamanders
from events import EventBus, NoiseEvent, ImpactEvent
from lighting import Lighting, ring
from map import CaveMap
from player import Bat
from props import DryCurtain, FloatStone, HangingCan
from pups import Pup
from scenes import Scene
from scenes.overlays import draw_overlay
from settings import (W, H, NEST, NEST_R, SAFE_R, TILE, BAT_HP, SCREECH_CD, SCREECH_CD_DECIDED, SCREECH_R,
                      REVEAL_T, ECHO_FLASH_T, SHIELD_CD, BRIGHTNESS_LEVELS, IMPACT_NOISE_MIN, IMPACT_NOISE_MAX,
                      C_IMPACT, C_GREEN, C_PUP, C_GOLD)
from story import LEVELS, PUPS, pup_count, rescued_before


def _web_tile():
    s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    c = (205, 215, 215, 210)
    for a in range(0, 360, 45):
        r = math.radians(a)
        pygame.draw.line(s, c, (16, 16), (16 + math.cos(r) * 22, 16 + math.sin(r) * 22), 1)
    for rr in (5, 10, 15):
        pygame.draw.circle(s, (200, 210, 210, 150), (16, 16), rr, 1)
    return s


def _soft_blob(r, col, a):
    s = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
    for i in range(r, 0, -3):
        pygame.draw.circle(s, (*col, int(a * (1 - i / r) ** 1.5)), (r, r), i)
    return s


def _sky_rays(col, seed, length=300, levels=6):
    """Haces de luz suaves que entran por la grieta del techo: varios rayos de distinto ancho e intensidad,
    un poco inclinados, que se desvanecen al bajar. Devuelve versiones con distinta intensidad (para que titilen)."""
    rnd = random.Random(seed)
    w, h = 360, length
    s = pygame.Surface((w, h))
    tilt = rnd.uniform(-.25, .25)                          # la luz entra un poco de lado
    for _ in range(16):
        x0 = w / 2 + rnd.uniform(-22, 22)                   # cada haz sale de un punto distinto de la grieta
        spread = rnd.uniform(.05, .16)
        ang = math.pi / 2 + tilt + rnd.uniform(-.28, .28)
        L = h * rnd.uniform(.6, 1.0)
        k = rnd.uniform(.35, 1.0)
        top_w = rnd.uniform(2, 7)
        pts = [(x0 - top_w, 0), (x0 + top_w, 0),
               (x0 + math.cos(ang - spread) * L, math.sin(ang - spread) * L),
               (x0 + math.cos(ang + spread) * L, math.sin(ang + spread) * L)]
        pts = [pts[0], pts[1], pts[3], pts[2]] if pts[3][0] > pts[2][0] else pts
        pygame.draw.polygon(s, tuple(min(255, int(c * k * .75)) for c in col), pts, 0)
    fade = pygame.Surface((w, h))                           # se apaga al alejarse de la grieta
    for y in range(h):
        f = (1 - y / h) ** 1.6
        fade.fill((int(255 * f), int(255 * f), int(255 * f)), (0, y, w, 1))
    s.blit(fade, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    sm = pygame.transform.smoothscale(s, (w // 5, h // 5))  # bordes suaves, nada de líneas rectas
    s = pygame.transform.smoothscale(sm, (w, h))
    out = []
    for lv in range(levels):
        v = s.copy()
        m = int(255 * (.65 + .35 * lv / (levels - 1)))
        v.fill((m, m, m), special_flags=pygame.BLEND_RGB_MULT)
        out.append(v)
    return out


def _dawn_rays(r=230, col=(36, 22, 8)):
    """Rayos de luz que bajan desde la entrada de la cueva (se suman con BLEND_ADD).
    El color cambia con la noche: azul oscuro (acto I), violeta (acto II), naranja del amanecer (acto III)."""
    s = pygame.Surface((2 * r, 2 * r))
    for k in range(9):
        a = math.tau * k / 9
        pts = [(r, r), (r + math.cos(a - .09) * r, r + math.sin(a - .09) * r), (r + math.cos(a + .09) * r, r + math.sin(a + .09) * r)]
        pygame.draw.polygon(s, col, pts)
    sm = pygame.transform.smoothscale(s, (r // 4, r // 4))
    return pygame.transform.smoothscale(sm, (2 * r, 2 * r))


PUP_SC = .6                  # tamaño de las crías en el suelo (un poco más grandes para que se note su carácter)


class PlayScene(Scene):
    def __init__(self, game, level=1):
        super().__init__(game)
        self.level = level
        self.cfg = LEVELS[level]
        self.sounds = game.sounds
        self.bus = EventBus()
        self.bus.subscribe(NoiseEvent, self.on_noise)
        self.bus.subscribe(ImpactEvent, self.on_impact)
        self.cave = CaveMap(level)
        cv = self.cave
        self.light = Lighting(cv.crystals, cv.fungi, self.cfg['theme'], cv.algae)
        self.canvas = pygame.Surface((W, H))
        self.state = 'play'
        self.bat = Bat()
        self.camera = Camera(self.bat.x, self.bat.y)
        self.pups = [Pup(x, y, name, beh) for (name, beh), (x, y) in zip(PUPS[level], cv.pup_spots)]
        self.enemies, self.rings = [], []
        self.rescued = rescued_before(level)
        self.rescued_here, self.goal_here = 0, pup_count(level)
        self.diff = difficulty.params(level, 0)
        prog = getattr(game, 'progress', {})
        self.cd_max = SCREECH_CD_DECIDED if prog.get('decided') else SCREECH_CD
        self.cd = self.shake = self.t = 0.0
        self.spawn_t = 3.0
        self.drip = 1.0
        self.drops = []                                       # gotas que caen de las estalactitas
        self.echo_t, self.echo_origin, self.reveal_t = 0.0, (0, 0), 0.0
        self.toast, self.toast_t = '', 0.0
        self.done_moments = set()
        self.spot_cd = 0.0
        self.boss_roar_t = 0.0
        self.lose_reason = ''
        self.clear_t = 0.0
        self.big_map = False
        self.heart_t = 0.0
        self.escape = False
        self.night_strip = ui.make_night_strip()
        self.web_img = _web_tile()
        self.sounds.listener = lambda: (self.bat.x, self.bat.y)
        cv.mark_circle(*NEST, TILE * 7)
        # ambientación del escenario
        self.air = []                                         # corriente de aire (mina)
        self.mist = []                                        # niebla baja (lago)
        if self.cfg['theme'] == 'lake':
            water = [(i % cv.w, i // cv.w) for i in range(cv.w * cv.h) if cv.water[i]]
            blobs = [_soft_blob(r, (150, 160, 210), 34) for r in (90, 120, 150)]
            for _ in range(min(26, len(water) // 12)):
                tx, ty = random.choice(water)
                self.mist.append([tx * TILE + 16, ty * TILE + 16, random.choice(blobs), random.uniform(-10, 10), random.uniform(0, 6)])
        rc = {'fungi': (40, 64, 170), 'lake': (110, 60, 170), 'mine': (210, 120, 50)}[self.cfg['theme']]
        self.rays = [_sky_rays(rc, 1), _sky_rays(rc, 2)]      # dos juegos de haces que se alternan suave
        self.sky_dust = []                                    # polvo que flota en la luz (no hay insectos: sequía)
        self.salamanders = spawn_salamanders(cv) if self.cfg['theme'] == 'lake' else []   # salamandras de cueva
        self.defeated = []                                    # enemigos vencidos (animación amable)
        sc = cv.secret                                        # sala secreta: escondite y medio corazón
        self.secret_heart = sc['center'] if sc else None
        self.sparkles = []
        self.fireflies = []                                   # (sin luciérnagas)
        self.tiny_spiders = []                                # (sin arañitas: la sala del Acto I solo tiene telarañas)
        self.wake_t = None                                    # animación del despertar del Gran Ciempiés
        self.wake_done = False
        self.resting = []                                     # crías ya a salvo en el punto de entrega
        # objetos interactivos
        self.curtains = [DryCurtain(a, b_, self.cfg['theme']) for a, b_ in cv.curtains]   # cortinas de raíces secas
        self.stones = [FloatStone(x, y) for x, y in cv.stones]                           # piedras flotantes (lago)
        self.cans = [HangingCan(wl, an) for wl, an in cv.cans]                            # latas colgadas (mina)
        # población inicial
        n0 = {1: 4, 2: 6, 3: 7}[level]
        for _ in range(n0):
            self.spawn_enemy(NEST, 800)
        self.drop_spider = None                               # susto amable del inicio (solo en el nivel 1)
        self.scare_done = level != 1
        self.boss = None
        if level == 3 and cv.lair:
            self.boss = Boss(cv.lair[0] - 60, cv.lair[1] + 20)
            self.enemies.append(self.boss)

    def enter(self):
        self.sounds.stop()
        self.sounds.ambient(.55, 'amb_' + self.cfg['theme'])          # ambiente sonoro de cada escenario

    # ------------------------------------------------------------ utilidades
    def spawn_enemy(self, ref, dist, ambush=False):
        """Aparece lejos o, en emboscada, a 600-1100 px del jugador (ya va tras el ruido)."""
        kind = pick_kind(self.cfg['enemies'], self.enemies)
        cv = self.cave
        if kind == 'spider' and (cv.cobwebs or cv.web) and not ambush:      # las arañas viven cerca de sus telarañas
            homes = list(cv.cobwebs)
            if getattr(cv, 'web_center', None):
                homes += [cv.web_center] * 6
            home = random.choice(homes)
            x, y = cv.near_spot(*home, 260)
            if math.dist((x, y), NEST) < 600 or math.dist((x, y), (self.bat.x, self.bat.y)) < 420:
                x, y = cv.free_spot(ref, dist)
                home = (x, y)
        else:
            x, y = cv.ring_spot(ref, 600, 1100) if ambush else cv.free_spot(ref, dist)
            home = (x, y)
        if math.dist((x, y), NEST) < SAFE_R + 120 or (self.cave.lair and math.dist((x, y), self.cave.lair) < 320):
            return
        e = Enemy(x, y, kind, home)
        if ambush:
            e.state, e.target = 'inv', ref
        self.enemies.append(e)

    def moment(self, key):
        """Momentos de la historia a mitad del nivel: se viven en tiempo real, sin texto ni pausa
        (las cinemáticas de fin de acto los cuentan con palabras)."""
        if key in self.done_moments:
            return
        self.done_moments.add(key)
        b = self.bat
        if key == 'whisper':                                  # elemento plantado: el susurro sube desde abajo
            self.sounds.play('whisper', base=.6)
        elif key == 'echo_room':                              # punto medio: su propia voz; la culpa se vuelve decisión
            self.sounds.play('whisper', base=1.0)
            self.sounds.play('story', base=.6)
            self.cd_max = SCREECH_CD_DECIDED
            self.cd = 0
            if hasattr(self.game, 'progress'):
                self.game.progress['decided'] = True
            for k in range(3):
                self.rings.append([b.x, b.y, -k * 60, 420, (200, 180, 255)])
        elif key == 'low_point':                              # un respiro: los cercanos pierden el rastro
            self.sounds.play('story', base=.5)
            for e in self.enemies:
                if e.kind != 'boss' and math.dist((e.x, e.y), (b.x, b.y)) < 420:
                    e.state, e.target, e.path, e.stun = 'patrol', None, [], 1.5

    def hidden_by_curtain(self, p, q):
        """Una cortina de raíces cerrada entre el bicho y Mullo no deja que la vea."""
        return any(c.blocks_view(p, q) for c in self.curtains)

    def spotted(self, e):
        """Un enemigo acaba de ver a Mullo: aviso corto (no se repite en ráfaga)."""
        if self.spot_cd <= 0:
            self.spot_cd = 1.0
            self.sounds.play('spotted', base=.9)
            self.rings.append([e.x, e.y, 0, 60, (255, 90, 70)])

    def shield(self):
        b = self.bat
        if b.try_shield(SHIELD_CD):
            self.sounds.play('shield_on')

    def dash(self, mv):
        mx, my = pygame.mouse.get_pos()
        if self.bat.try_dash(mv, self.camera.to_world(mx, my)):
            self.sounds.play('dash')

    def screech(self):
        """Grito sónico: aturde y daña a los cercanos, despeja telarañas y marca a las crías en el minimapa."""
        if self.cd > 0:
            return
        b = self.bat
        self.cd, self.shake = self.cd_max, .15
        self.sounds.play('screech')
        self.echo_t, self.echo_origin, self.reveal_t = ECHO_FLASH_T, (b.x, b.y), REVEAL_T
        self.cave.mark_circle(b.x, b.y, SCREECH_R * 2.4)           # ecolocación: dibuja el entorno en el mapa
        for p in self.pups:
            p.revealed = REVEAL_T
        for e in self.enemies:
            if math.dist((e.x, e.y), (b.x, b.y)) < SCREECH_R + e.rad:
                e.hit_by_screech(b.x, b.y)
                if e.hp <= 0:
                    self.sounds.play('die', (e.x, e.y))
                    self.defeated.append(Defeat(e, b.x, b.y))
        self.enemies = [e for e in self.enemies if e.hp > 0]
        if self.cave.web and self.cave.clear_web(b.x, b.y, SCREECH_R):
            self.sounds.play('web')
        for can in self.cans:                                 # el grito hace sonar las latas cercanas
            if math.dist(can.pos, (b.x, b.y)) < SCREECH_R * 1.4:
                can.strike(b.x, b.y, 1.2)
        for cu in self.curtains:                              # y sacude las cortinas
            if math.dist(cu.mid_pt, (b.x, b.y)) < SCREECH_R + cu.half:
                for st in cu.strands:
                    d = math.dist((st['ax'], st['ay']), (b.x, b.y)) or 1
                    st['vx'] += (st['ax'] - b.x) / d * 160
                    st['vy'] += (st['ay'] - b.y) / d * 120
        self.bus.emit(NoiseEvent(b.x, b.y, 170, (150, 220, 255), 'screech'))    # gritar también hace ruido
        self.rings.append([b.x, b.y, 0, SCREECH_R * 1.2, (170, 230, 255)])

    def lose(self, reason):
        self.state, self.lose_reason = 'over', reason
        self.sounds.stop()
        self.sounds.play('lose')
        if hasattr(self.game, 'progress'):
            self.game.progress['retries'] = self.game.progress.get('retries', 0) + 1

    # ------------------------------------------------------------ eventos del bus
    def on_noise(self, e):
        self.rings.append([e.x, e.y, 0, e.radius, e.color])
        for en in self.enemies:
            en.hear(e.x, e.y, e.radius, self.diff.hear_mult)

    def on_impact(self, e):
        k = min(1.0, e.speed / 350)
        self.sounds.play('impact', base=.4 + .6 * k)
        if e.speed > 200:
            self.shake = max(self.shake, .06 + .1 * k)
        r = IMPACT_NOISE_MIN + (IMPACT_NOISE_MAX - IMPACT_NOISE_MIN) * k
        self.bus.emit(NoiseEvent(e.x, e.y, r, C_IMPACT, 'impact'))          # el golpe atrae criaturas

    # ------------------------------------------------------------ entrada
    def _mv(self):
        K = pygame
        ks = K.key.get_pressed()
        return (int(ks[K.K_d] or ks[K.K_RIGHT]) - int(ks[K.K_a] or ks[K.K_LEFT]),
                int(ks[K.K_s] or ks[K.K_DOWN]) - int(ks[K.K_w] or ks[K.K_UP]))

    def handle(self, ev):
        g, K = self.game, pygame
        if ev.type == K.KEYDOWN:
            k = ev.key
            if k == K.K_ESCAPE:
                if self.state == 'play':
                    self.state = 'pause'
                else:
                    g.goto('title')
            elif k == K.K_b and self.state in ('play', 'pause'):
                g.brightness = (g.brightness + 1) % len(BRIGHTNESS_LEVELS)
                self.toast, self.toast_t = f'Brillo: {BRIGHTNESS_LEVELS[g.brightness][0]}', 2.0
                self.sounds.play('menu_move')
            elif k == K.K_m and self.state in ('play', 'pause'):
                self.big_map = not self.big_map
                self.sounds.play('menu_move')
            elif self.state == 'play':
                if k == K.K_SPACE:
                    self.screech()
                elif k in (K.K_LSHIFT, K.K_RSHIFT):
                    self.dash(self._mv())
                elif k == K.K_e:
                    self.shield()
                elif k == K.K_p:
                    self.state = 'pause'
            elif self.state == 'pause' and k in (K.K_p, K.K_RETURN):
                self.state = 'play'
            elif self.state == 'over' and k in (K.K_r, K.K_RETURN, K.K_SPACE):
                g.retry_level(self.level)
            elif self.state == 'clear' and self.clear_t > 1.2 and k in (K.K_RETURN, K.K_SPACE):
                g.advance()
        elif ev.type == K.MOUSEBUTTONDOWN and self.state == 'play':
            if ev.button == 1:
                self.screech()
            elif ev.button == 3:
                self.shield()

    # ------------------------------------------------------------ lógica
    WAKE_T = 2.6

    def _update_wake(self, dt):
        """Animación del despertar: la cámara va al gigante, la cueva tiembla, abre los ojos y ruge."""
        self.wake_t += dt
        t, bo, b = self.wake_t, self.boss, self.bat
        k = min(1, t / .5) if t < 1.9 else max(0, 1 - (t - 1.9) / .6)
        k = k * k * (3 - 2 * k)
        tx, ty = b.x + (bo.x - b.x) * k, b.y + (bo.y - b.y) * k
        self.camera.follow(tx, ty, 1, snap=True)
        bo.anim += dt * (1 + 6 * min(1, t))
        if t > 1.1:                                           # se desenrosca y levanta la cabeza hacia Mullo
            ang = math.atan2(b.y - bo.y, b.x - bo.x)
            bo.face += ((ang - bo.face + math.pi) % math.tau - math.pi) * min(1, dt * 4)
            q = min(1, dt * 2.5)
            bo.segs = [(sx + (bo.x - math.cos(ang) * bo.gap * i - sx) * q, sy + (bo.y - math.sin(ang) * bo.gap * i - sy) * q)
                       for i, (sx, sy) in enumerate(bo.segs)]
        self.shake = max(self.shake, .35 if t > .5 else .15)
        if t > .3 and random.random() < dt * 30:              # caen piedritas del techo
            self.sparkles.append([bo.x + random.uniform(-220, 220), bo.y + random.uniform(-200, 120), 0, 'rock', 0.0])
        if t > 1.0 and not getattr(self, '_roared', False):
            self._roared = True
            self.sounds.play('roar', base=1.0)
            for k2 in range(4):
                self.rings.append([bo.x, bo.y, -k2 * 70, 520, (255, 70, 50)])
        for r in self.rings:
            r[2] += dt * 320
        self.rings = [r for r in self.rings if r[2] < r[3]]
        self._update_sparkles(dt)
        if t >= self.WAKE_T:
            self.state, self.wake_t = 'play', None
            bo.waking = .25

    def _update_sparkles(self, dt):
        for s in self.sparkles:
            s[4] += dt
            if s[3] == 'rock':
                s[2] += 420 * dt                              # cae (en pantalla, eje y)
            else:
                s[0] += math.cos(s[2]) * 60 * dt
                s[1] += math.sin(s[2]) * 60 * dt - 20 * dt
        self.sparkles = [s for s in self.sparkles if s[4] < (.7 if s[3] == 'rock' else 1.2)]

    def _secret(self, dt):
        """Sala secreta: al entrar por primera vez se ilumina en el mapa; el medio corazón se recoge al tocarlo."""
        cv, b = self.cave, self.bat
        if not cv.secret:
            return
        for f in self.fireflies:
            f[2] += dt
        cxs, cys = cv.secret['center']
        for sp in self.tiny_spiders:                          # caminan, se paran y se apartan de Mullo
            sp[3] += dt
            sp[4] = max(0, sp[4] - dt)
            if math.dist((sp[0], sp[1]), (b.x, b.y)) < 50:
                sp[2], sp[4] = math.atan2(sp[1] - b.y, sp[0] - b.x), .6
            elif random.random() < dt * .8:
                sp[2] += random.uniform(-1.5, 1.5)
            moving = sp[4] > 0 or (sp[3] % 3) < 1.6
            if moving:
                sp_ = 70 if sp[4] > 0 else 22
                nx, ny = sp[0] + math.cos(sp[2]) * sp_ * dt, sp[1] + math.sin(sp[2]) * sp_ * dt
                if ((nx - cxs) / (cv.secret['rx'] * .75)) ** 2 + ((ny - cys) / (cv.secret['ry'] * .7)) ** 2 < 1:
                    sp[0], sp[1] = nx, ny
                else:
                    sp[2] += math.pi * .8
        if cv.in_secret(b.x, b.y) and not cv.secret_found:
            cv.secret_found = True
            for tx, ty in cv.secret['tiles']:
                cv.mark(tx, ty)
            self.sounds.play('secret', base=.9)
            for k in range(26):
                self.sparkles.append([b.x, b.y, k * math.tau / 26, 'star', 0.0])
        h = self.secret_heart
        if h and b.hp < BAT_HP and math.dist(h, (b.x, b.y)) < 24:
            b.hp = min(BAT_HP, b.hp + 1)                      # un corazón entero
            self.secret_heart = None
            self.sounds.play('heart', base=1.0)
            for k in range(16):
                self.sparkles.append([h[0], h[1], k * math.tau / 16, 'heart', 0.0])

    def update(self, dt):
        if self.state == 'wake':
            return self._update_wake(dt)
        if self.state == 'clear':
            self.clear_t += dt
            self.t += 0
            if self.clear_t > 4.5:
                self.game.advance()
            return
        if self.state != 'play':
            return
        mv = self._mv()
        mx, my = pygame.mouse.get_pos()
        self.t += dt
        if hasattr(self.game, 'progress'):
            self.game.progress['play_time'] = self.game.progress.get('play_time', 0) + dt
        b, cv = self.bat, self.cave
        b.update(dt, mv, self.camera.to_world(mx, my), cv, self.bus)
        self.camera.follow(b.x, b.y, dt, vx=b.vx, vy=b.vy)
        self.cd, self.shake = max(0, self.cd - dt), max(0, self.shake - dt)
        self.echo_t, self.reveal_t = max(0, self.echo_t - dt), max(0, self.reveal_t - dt)
        self.toast_t, self.spot_cd = max(0, self.toast_t - dt), max(0, self.spot_cd - dt)
        cv.mark_circle(b.x, b.y, TILE * 6, mem=True)
        if b.shield_t > 0 and b.shield_t <= dt:
            self.sounds.play('shield_off')
        if self.t > self.cfg['duration']:                    # se acabó la noche para este tramo
            return self.lose('dawn')
        self._pups(dt)
        self._friendly_scare(dt)
        self._secret(dt)
        self._update_sparkles(dt)
        if self.state != 'play':
            return
        self._enemies(dt)
        if self.state != 'play':
            return
        self._story_triggers()
        self._ambience(dt)
        for r in self.rings:
            r[2] += dt * 320
        self.rings = [r for r in self.rings if r[2] < r[3]]

    def _pups(self, dt):
        b = self.bat
        for p in self.pups:
            p.update(dt, self)
            if p is b.carry:
                p.x, p.y = b.x, b.y + 14
            elif not b.carry and math.dist((p.x, p.y), (b.x, b.y)) < (36 if p.count > 1 else 26):
                b.carry = p
                self.sounds.play('pickup')
                p.hop = .35                                 # brinca a los brazos de su madre
                if p.behavior == 'gemelas' and self.boss and self.boss.wake():
                    self.escape = True                       # clímax: el gigante despierta, empieza la huida
                    if not self.wake_done:
                        self.wake_done = True
                        self.state, self.wake_t = 'wake', 0.0
                        self.boss.waking = 9.0               # se queda en su sitio durante la animación
                        self.sounds.play('quake', base=1.0)
                    self.boss_roar_t = 3.0
        if b.carry and math.dist((b.x, b.y), NEST) < NEST_R:
            p = b.carry
            self.pups.remove(p)
            for k in range(p.count):
                self.resting.append(Resting(len(self.resting), self.goal_here, p.looks[k % len(p.looks)]))
            b.carry = None
            self.rescued += p.count
            self.rescued_here += p.count
            b.hp = min(BAT_HP, b.hp + 1)
            self.rings.append([NEST[0], NEST[1], 0, 140, C_GREEN])
            self.sounds.play('deliver')
            self.diff = difficulty.params(self.level, self.rescued_here)
            if self.rescued_here >= self.goal_here:
                self.state, self.clear_t = 'clear', 0.0
                self.sounds.stop()
                self.sounds.play('win')
                if hasattr(self.game, 'progress'):
                    self.game.progress['rescued'] = self.rescued
                return
            if self.level == 1 and self.rescued_here == 2:
                self.moment('whisper')                       # elemento plantado

    def _enemies(self, dt):
        b = self.bat
        dmin = 1e9
        for e in self.enemies:
            e.update(dt, self)
            if e.kind != 'boss' and e.stun <= 0 and any(c.near(e.x, e.y, 6) for c in self.curtains):
                e.x -= e.vx * dt * .55                       # las raíces secas los frenan
                e.y -= e.vy * dt * .55
            d = math.dist((e.x, e.y), (b.x, b.y)) or 1
            if e.state == 'chase':
                dmin = min(dmin, d)
            if d < 12 + e.rad and e.stun <= 0 and e.state != 'sleep':
                if b.shield_t > 0:                           # el escudo repele y aturde
                    e.stun = 1.2 * e.spec['stun'] + .3
                    k = 340 * max(.3, e.spec['push'])
                    e.vx, e.vy = (e.x - b.x) / d * k, (e.y - b.y) / d * k
                    if e.kind == 'boss':
                        b.knockback((b.x - e.x) / d, (b.y - e.y) / d, 380)
                    self.sounds.play('shield_hit')
                    self.shake = max(self.shake, .12)
                    self.rings.append([b.x, b.y, 0, 90, (170, 230, 255)])
                elif b.inv <= 0:
                    b.hp, b.inv, self.shake = b.hp - e.spec['dmg'], 1.3, .4
                    b.knockback((b.x - e.x) / d, (b.y - e.y) / d, 320 if e.kind != 'boss' else 460)
                    self.sounds.play('hit')
                    if b.carry:
                        b.carry.t = 0
                    if b.hp <= 0:
                        return self.lose('lives')
                    if b.hp == 1 and self.level == 2:
                        self.moment('low_point')
        if self.boss and self.boss.state == 'chase' and getattr(self.boss, 'waking', 0) <= 0:
            self.boss_roar_t -= dt                            # el gigante ruge mientras te persigue
            if self.boss_roar_t <= 0:
                self.boss_roar_t = random.uniform(4, 6)
                self.sounds.play('roar', (self.boss.x, self.boss.y), 1.0)
                self.shake = max(self.shake, .25)
        if (self.boss and b.carry and b.carry.behavior == 'gemelas' and self.boss.state in ('return', 'sleep')
                and not self.cave.in_secret(b.x, b.y)):          # sale del escondite: el gigante la vuelve a seguir
            self.boss.wake()
        bo = self.boss                                         # música de persecución durante la huida
        chasing = bo is not None and bo.state == 'chase' and bo.waking <= .3
        if chasing and self.sounds.music_name != 'chase':
            self.sounds.music('chase', .55)
        elif not chasing and self.sounds.music_name == 'chase':
            self.sounds.stop_music()
        # latido de peligro: más rápido y fuerte cuanto más cerca está quien te persigue
        self.heart_t -= dt
        if dmin < 480 and self.heart_t <= 0:
            k = dmin / 480
            self.heart_t = .42 + .8 * k
            self.sounds.play('heartbeat', base=.35 + .55 * (1 - k))
        self.spawn_t -= dt
        if self.spawn_t <= 0:
            self.spawn_t = self.diff.spawn_interval * random.uniform(.8, 1.2)
            if sum(1 for e in self.enemies if e.kind != 'boss') < self.diff.max_enemies:
                self.spawn_enemy((b.x, b.y), 650, random.random() < .35)

    def _story_triggers(self):
        b, cv = self.bat, self.cave
        if self.level == 1 and cv.web and getattr(cv, 'web_center', None) and math.dist((b.x, b.y), cv.web_center) < 230:
            self.moment('web')
        elif self.level == 2 and cv.echo and math.dist((b.x, b.y), cv.echo) < 170:
            self.moment('echo_room')
        elif self.level == 3 and cv.lair and math.dist((b.x, b.y), cv.lair) < 340:
            self.moment('climax')

    def _ambience(self, dt):
        b, cv = self.bat, self.cave
        sky = cv.skylight                                      # polvo flotando en los haces de luz
        if sky:
            if len(self.sky_dust) < 26:
                self.sky_dust.append([sky[0] + random.uniform(-40, 40), sky[1] + random.uniform(0, 30), random.uniform(0, 6)])
            for d in self.sky_dust:
                d[0] += math.sin(d[2] + self.t) * 6 * dt
                d[1] += 12 * dt
                d[2] += dt
            self.sky_dust = [d for d in self.sky_dust if d[1] < sky[1] + 260]
        self.defeated = [d for d in self.defeated if d.update(dt)]
        for r in self.resting:
            r.update(dt)
        threats = [e for e in self.enemies if e.kind != 'boss' and e.state != 'sleep']
        for sa in self.salamanders:
            sa.update(dt, cv, b, [e for e in threats if math.dist((e.x, e.y), (sa.x, sa.y)) < 260], self.stones)
        self._props(dt)
        self.drip -= dt                                       # goteras: caen de las estalactitas cercanas
        if self.drip <= 0:
            self.drip = random.uniform(.5, 1.4) if self.cfg['theme'] == 'lake' else random.uniform(.8, 2.2)
            near = [p_ for p_ in cv.stalactites if math.dist(p_, (b.x, b.y)) < 650]
            if near:
                x, y = random.choice(near)
                self.drops.append([x, y, 0.0, random.uniform(28, 46)])
        for d in self.drops:
            d[2] += dt
            if d[2] >= .35 and len(d) == 4:                   # toca el suelo: se oye y salpica
                d.append(True)
                self.sounds.play('drip', (d[0], d[1] + d[3]), .9)
                for sa in self.salamanders:                   # una gota que cae cerca también las asusta
                    if math.dist((sa.x, sa.y), (d[0], d[1] + d[3])) < 60:
                        sa.scare(d[0], d[1] + d[3])
        self.drops = [d for d in self.drops if d[2] < .9]
        for m in self.mist:
            m[0] += m[3] * dt
            m[4] += dt
        if self.cfg['theme'] == 'mine':                       # corriente de aire fresco hacia la salida
            cam = self.camera
            want = 90 if self.escape else 55
            for _ in range(3):
                if len(self.air) >= want:
                    break
                x, y = cam.x + random.uniform(0, W), cam.y + random.uniform(0, H)
                if not cv.solid_px(x, y):
                    self.air.append([x, y, random.uniform(1.2, 2.4)])
            sp = 120 if self.escape else 75
            for a in self.air:
                fx, fy = cv.flow_dir(a[0], a[1])
                a[0] += fx * sp * dt
                a[1] += fy * sp * dt
                a[2] -= dt
            self.air = [a for a in self.air if a[2] > 0 and cam.visible(a[0], a[1], 40)]

    def _friendly_scare(self, dt):
        """Al poco de salir del nido, una arañita baja de golpe frente a Mullo, se asusta ella sola y se va."""
        b, cv = self.bat, self.cave
        if not self.scare_done and self.t > 2.5 and math.dist((b.x, b.y), NEST) > 190:
            sp = math.hypot(b.vx, b.vy)
            if sp > 40:
                ux, uy = b.vx / sp, b.vy / sp
                for dist in (95, 80, 65):
                    x, y = b.x + ux * dist, b.y + uy * dist
                    if not cv.solid_px(x, y) and not cv.is_water(x, y) and not cv.solid_px(x, y - 30) \
                            and cv.los((b.x, b.y), (x, y)):
                        self.drop_spider = DropSpider(x, y)
                        self.scare_done = True
                        break
        ds = self.drop_spider
        if ds:
            for snd in ds.update(dt):
                self.sounds.play(snd, (ds.x, ds.y), 1.0)
            if ds.done:
                self.drop_spider = None

    def _props(self, dt):
        """Cortinas de raíces, piedras flotantes y latas colgadas."""
        b, cam = self.bat, self.camera
        movers = [(b.x, b.y, b.vx, b.vy, 1.0)]
        movers += [(e.x, e.y, e.vx, e.vy, .8) for e in self.enemies if e.kind != 'boss' and cam.visible(e.x, e.y, 300)]
        for cu in self.curtains:
            if cam.visible(*cu.mid_pt, 400) and cu.update(dt, movers):
                self.sounds.play('rustle', cu.mid_pt, .8)
        riders = [sa for sa in self.salamanders if sa.visible]          # cualquier salamandra que pase encima la hunde
        for st in self.stones:
            if st.update(dt, riders):
                self.sounds.play('plop', (st.x, st.y), .8)
        for sa in self.salamanders:                           # la salamandra se hunde junto con su piedra
            under = [st.sink for st in self.stones if math.dist((st.x, st.y), (sa.x, sa.y)) < st.r + 4]
            sa.sub = max(under) if under else max(0.0, sa.sub - dt * 2.5)
        for can in self.cans:
            if math.dist(can.pos, (b.x, b.y)) < 22 and math.hypot(b.vx, b.vy) > 30:
                can.strike(b.x, b.y, min(1.4, .6 + math.hypot(b.vx, b.vy) / 300))
            if can.update(dt):                                # "clanc": los bichos van a ver qué pasó
                x, y = can.pos
                self.sounds.play('clang', (x, y), 1.0)
                self.bus.emit(NoiseEvent(x, y, can.NOISE_R, (255, 220, 140), 'can'))

    # ------------------------------------------------------------ dibujo
    def draw(self, screen):
        c, b, cam, cv = self.canvas, self.bat, self.camera, self.cave
        ix, iy = int(cam.x), int(cam.y)
        c.blit(cv.bg, (0, 0), (ix, iy, W, H))
        if cv.web:                                           # cortina de telarañas
            for tx, ty in cv.web:
                x, y = tx * TILE, ty * TILE
                if cam.visible(x, y, 40):
                    c.blit(self.web_img, cam.apply(x, y))
        if b.over_water or self.cfg['theme'] == 'lake':      # ondas en el agua bajo Mullo
            if b.over_water:
                for k in range(2):
                    p = ((self.t * .8 + k * .5) % 1)
                    sx, sy = cam.apply(b.x, b.y + 10)
                    ring(c, sx, sy, 8 + 30 * p, (90, 120, 200), .5 * (1 - p), 1)
        for st in self.stones:
            if cam.visible(st.x, st.y, 60):
                st.draw(c, cam)
        for sa in self.salamanders:
            if cam.visible(sa.x, sa.y, 60):
                sa.draw(c, *cam.apply(sa.x, sa.y), cam)
        if cam.visible(*NEST, 80):
            for r in self.resting:
                r.draw(c, cam)
        for p in self.pups:
            if p is not b.carry and cam.visible(p.x, p.y):
                self._draw_pup(c, p)
        for d in self.defeated:
            d.draw(c, cam)
        for e in self.enemies:
            if cam.visible(e.x, e.y, 200 if e.kind == 'boss' else 60):
                ui.draw_enemy(c, *cam.apply(e.x, e.y), e, cam)
        for cu in self.curtains:
            if cam.visible(*cu.mid_pt, cu.half + 60):
                cu.draw(c, cam, self.t)
        if self.drop_spider:                                  # susto amable
            self.drop_spider.draw(c, cam)
        for can in self.cans:
            if cam.visible(*can.anchor, 60):
                can.draw(c, cam, self.t)
        bx, by = cam.apply(b.x, b.y)
        if b.carry:
            p = b.carry
            for k in range(p.count):
                ui.draw_pup(c, bx + (k * 12 - 6 if p.count > 1 else 0), by + 16, self.t * 12 + k, 0.0, .5,
                            p.looks[k % len(p.looks)], self.t)
        if b.inv <= 0 or int(self.t * 12) % 2:
            ui.draw_bat_tilted(c, bx, by, b.flap, b.tilt)
        self.light.apply(c, self, self.t)
        self._draw_after_light(c)
        self._draw_secret_fx(c)
        for d in self.defeated:
            d.draw_fx(c, cam)
        for x, y, r, mr, col in self.rings:
            sx, sy = cam.apply(x, y)
            ring(c, sx, sy, r, col, .7 * (1 - r / mr), 2)
        self.light.draw_shield(c, self, self.t)
        self.light.draw_trail(c, self)
        ui.draw_hud(c, self)
        if self.toast_t > 0:                                  # solo confirma el cambio de brillo (tecla B)
            ui.text(c, ui.F_S, self.toast, W // 2, 92, (220, 215, 235), True)
        if self.big_map:
            ui.draw_minimap(c, self, big=True)
        amp = 3 * min(1, self.shake / .3)
        ox, oy = (random.randint(-round(amp), round(amp)), random.randint(-round(amp), round(amp))) if amp >= .5 else (0, 0)
        screen.fill((0, 0, 0))
        screen.blit(c, (ox, oy))
        if self.state == 'wake':
            self._draw_wake(screen)
        elif self.state != 'play':
            draw_overlay(screen, self)

    def _draw_secret_fx(self, c):
        """Luciérnagas de la sala secreta, el medio corazón flotando y destellos."""
        cam, t = self.camera, self.t + (self.wake_t or 0)
        sc = self.cave.secret
        if sc and cam.visible(*sc['center'], 220):
            col = {'fungi': (200, 255, 140), 'lake': (200, 215, 240), 'mine': (255, 210, 130)}[self.cfg['theme']]
            for x, y, a, ph, scared in self.tiny_spiders:     # arañitas (chiquitas y amigables)
                sx, sy = cam.apply(x, y)
                walk = (ph % 3) < 1.6 or scared > 0
                for k in range(8):
                    la = a + math.pi / 2 * (1 if k < 4 else -1) + ((k % 4) - 1.5) * .5 + (math.sin(ph * 18 + k) * .25 if walk else 0)
                    pygame.draw.line(c, (70, 60, 80), (sx, sy), (sx + math.cos(la) * 6, sy + math.sin(la) * 6), 1)
                pygame.draw.circle(c, (120, 100, 140), (int(sx - math.cos(a) * 2), int(sy - math.sin(a) * 2)), 3)
                pygame.draw.circle(c, (150, 130, 170), (int(sx + math.cos(a) * 2), int(sy + math.sin(a) * 2)), 2)
                for sd in (-1, 1):
                    ex, ey = sx + math.cos(a) * 3 - math.sin(a) * sd, sy + math.sin(a) * 3 + math.cos(a) * sd
                    c.fill((255, 255, 255), (int(ex), int(ey), 1, 1))
            for fx, fy, ph in self.fireflies:
                x = fx + math.sin(ph * .7) * 30
                y = fy + math.cos(ph * .9) * 18
                k = .5 + .5 * math.sin(ph * 3)
                sx, sy = cam.apply(x, y)
                pygame.draw.circle(c, tuple(int(v * (.3 + .4 * k)) for v in col), (int(sx), int(sy)), 3)
                pygame.draw.circle(c, col, (int(sx), int(sy)), 1)
            if self.secret_heart:
                hx, hy = cam.apply(self.secret_heart[0], self.secret_heart[1] + math.sin(t * 3) * 4)
                r = 16 + 3 * math.sin(t * 4)
                pygame.draw.circle(c, (90, 30, 50), (int(hx), int(hy + 4)), int(r))
                pygame.draw.circle(c, (255, 140, 180), (int(hx), int(hy + 4)), int(r), 1)
                ui.heart(c, int(hx), int(hy), (90, 40, 60))
                ui.heart(c, int(hx), int(hy), (255, 80, 120))
        for x, y, a, kind, life in self.sparkles:
            if kind == 'rock':
                sx, sy = cam.apply(x, y - 200 + a)
                g = int(150 * (1 - life / .7))
                pygame.draw.circle(c, (g, int(g * .85), int(g * .7)), (int(sx), int(sy)), 3)
                continue
            sx, sy = cam.apply(x, y)
            f = 1 - life / 1.2
            if kind == 'heart':
                ui.star(c, sx, sy, 3 + 2 * f, (255, int(120 + 100 * f), 170))
            else:
                ui.star(c, sx, sy, 2 + 3 * f, (255, 240, int(120 + 100 * f)))

    def _draw_wake(self, screen):
        """Encima de la escena: franjas de cine, viñeta roja que late y los ojos que se encienden."""
        t = self.wake_t or 0
        k = min(1, t / .4) if t < self.WAKE_T - .4 else max(0, (self.WAKE_T - t) / .4)
        bh = int(70 * k)
        screen.fill((0, 0, 0), (0, 0, W, bh))
        screen.fill((0, 0, 0), (0, H - bh, W, bh))
        pulse = .5 + .5 * math.sin(t * 9)
        v = getattr(self, '_wake_veil', None)
        if v is None:
            v = self._wake_veil = pygame.Surface((W, H), pygame.SRCALPHA)
            for i in range(0, 120, 4):
                pygame.draw.rect(v, (160, 0, 0, int(120 * (1 - i / 120) ** 2)), (i, i, W - 2 * i, H - 2 * i), 4)
        v.set_alpha(int(255 * k * (.5 + .5 * pulse)))
        screen.blit(v, (0, 0))
        if t > .8:                                           # los ojos del gigante se encienden
            bo = self.boss
            ex, ey = self.camera.apply(bo.x, bo.y)
            g = min(1, (t - .8) / .4)
            rr = int(30 + 60 * g * (1 - max(0, t - 1.6)))
            if rr > 0:
                glow = pygame.Surface((rr * 2, rr * 2))
                for i in range(rr, 0, -3):
                    q = (1 - i / rr) ** 1.5
                    pygame.draw.circle(glow, (int(180 * q * g), int(20 * q * g), int(10 * q * g)), (rr, rr), i)
                screen.blit(glow, (ex - rr, ey - rr), special_flags=pygame.BLEND_RGB_ADD)

    def _draw_pup(self, c, p):
        cam = self.camera
        sx, sy = cam.apply(p.x, p.y + math.sin(self.t * 3 + p.x) * 1.5 - p.lift())
        if p.lift() > 0:                                      # sombrita en el suelo durante el brinco
            pygame.draw.ellipse(c, (0, 0, 0), (sx - 7, sy + p.lift() + 6, 14, 4))
        if p.count > 1:
            ox = p.x - p.home[0]                               # cada gemela en su vagoneta
            cry = p.ping > 0
            ui.draw_pup(c, sx - 22 - ox, sy - 4 + math.sin(self.t * 5) * 1.5, p.flap, p.sway(self.t), PUP_SC, p.looks[0], self.t, cry)
            ui.draw_pup(c, sx + 22 - ox, sy - 3 + math.sin(self.t * 5 + 2) * 1.5, p.flap + 1.3, -p.sway(self.t + 1), PUP_SC,
                        p.looks[-1], self.t + 1, cry)
        else:
            ui.draw_pup(c, sx, sy, p.flap, p.sway(self.t), PUP_SC, p.looks[0], self.t, p.ping > 0)

    def _draw_after_light(self, c):
        """Lo que debe verse aun en la oscuridad: ojos, nombres, niebla, corriente de aire y luz del amanecer."""
        b, cam = self.bat, self.camera
        for x, y, img, vx, ph in self.mist:                  # niebla baja del lago
            if cam.visible(x, y, 160):
                sx, sy = cam.apply(x + math.sin(ph * .3) * 30, y)
                c.blit(img, (sx - img.get_width() // 2, sy - img.get_height() // 2))
        sky = self.cave.skylight                             # rayos que entran por la grieta del techo (referencia del cielo)
        if sky and cam.visible(sky[0], sky[1] + 150, 300):
            sx, sy = cam.apply(*sky)
            for n, layer in enumerate(self.rays):            # titilan despacio, como luz que pasa entre ramas
                k = .5 + .5 * math.sin(self.t * (.7 + .4 * n) + n * 2)
                img = layer[min(len(layer) - 1, int(k * len(layer)))]
                c.blit(img, (sx - img.get_width() // 2, sy - 4), special_flags=pygame.BLEND_RGB_ADD)
            dcol = {'fungi': (150, 170, 230), 'lake': (190, 160, 230), 'mine': (255, 210, 150)}[self.cfg['theme']]
            for x, y, ph in self.sky_dust:
                px, py = cam.apply(x, y)
                f = max(0, 1 - (y - sky[1]) / 280) * (.5 + .5 * math.sin(ph * 2))
                c.fill(tuple(int(v * f) for v in dcol), (int(px), int(py), 2, 2))
        for a in self.air:
            fx, fy = self.cave.flow_dir(a[0], a[1])
            sx, sy = cam.apply(a[0], a[1])
            k = min(1, a[2]) * (1 if self.escape else .65)
            col = (int(150 * k), int(170 * k), int(190 * k))
            pygame.draw.line(c, col, (sx, sy), (sx - fx * 12, sy - fy * 12), 1)
        reach = max(300, BRIGHTNESS_LEVELS[self.game.brightness][2] * 1.3)
        for e in self.enemies:                                # ojos visibles en la oscuridad
            if not cam.visible(e.x, e.y, 80):
                continue
            d = math.dist((e.x, e.y), (b.x, b.y))
            if d < reach * (1.8 if e.kind == 'boss' else 1) or (self.echo_t > 0 and d < SCREECH_R * 2.4):
                if e.state == 'sleep':
                    continue
                col = (120, 120, 60) if e.stun > 0 else ((255, 40, 40) if e.state == 'chase' else (200, 90, 40))
                ex, ey = cam.apply(e.x, e.y)
                sz = e.spec['size']
                fx, fy = math.cos(e.face), math.sin(e.face)
                off = 6 * sz if e.kind != 'boss' else 12
                for sd in (-1, 1):
                    px, py = ex + fx * off - fy * sd * 3.5 * sz, ey + fy * off + fx * sd * 3.5 * sz
                    pygame.draw.circle(c, col, (int(px), int(py)), 2 if e.kind != 'boss' else 5)
        for x, y, t, fall, *hit in self.drops:                # gotas y salpicaduras
            if not cam.visible(x, y, 40):
                continue
            if t < .35:
                sx, sy = cam.apply(x, y + fall * (t / .35) ** 2)
                pygame.draw.line(c, (150, 190, 230), (sx, sy - 3), (sx, sy + 1), 2)
            else:
                q = (t - .35) / .55
                sx, sy = cam.apply(x, y + fall)
                g = int(170 * (1 - q))
                pygame.draw.ellipse(c, (int(g * .7), int(g * .9), g), (sx - 3 - 9 * q, sy - 1 - 3 * q, 6 + 18 * q, 2 + 6 * q), 1)
                if q < .4:
                    for sd in (-1, 1):
                        c.fill((150, 190, 230), (int(sx + sd * (2 + 10 * q)), int(sy - 6 * q + 12 * q * q), 1, 1))
        for sa in self.salamanders:                           # ojitos que reflejan un poco de luz
            if sa.visible and sa.sub < .5 and cam.visible(sa.x, sa.y, 20):
                hx, hy = cam.apply(sa.x + math.cos(sa.ang) * 9, sa.y + math.sin(sa.ang) * 9)
                pygame.draw.circle(c, (110, 90, 70), (int(hx), int(hy)), 3)
        for can in self.cans:
            if can.ring > 0 and cam.visible(*can.anchor, 60):
                can.draw_fx(c, cam)
        if self.drop_spider:
            self.drop_spider.draw_fx(c, cam)
        if cam.visible(*NEST, 80):
            for r in self.resting:
                r.draw_fx(c, cam)
        for p in self.pups:                                   # detalles de cada cría (zzz, ondas de eco)
            if p is not b.carry and cam.visible(p.x, p.y):
                sx, sy = cam.apply(p.x, p.y)
                for k, nm in enumerate(p.looks):
                    ui.pup_extras(c, sx + ((k * 44 - 22) - (p.x - p.home[0]) if p.count > 1 else 0), sy, ui.PUP_LOOKS.get(nm, {}), self.t + k)
        for p in self.pups:                                   # nombres de las crías cercanas
            if p is b.carry or not cam.visible(p.x, p.y):
                continue
            d = math.dist((p.x, p.y), (b.x, b.y))
            if d < 230 and p.found:
                sx, sy = cam.apply(p.x, p.y)
                ui.text(c, ui.F_XS, p.name, sx, sy - 24, C_PUP, True)
            if p.ping > 1.8 and d < 900:                     # chillido visible
                sx, sy = cam.apply(p.x, p.y)
                ring(c, sx, sy, 10 + (2.2 - p.ping) * 120, C_PUP, .8, 2)
        if b.carry:                                           # destino de entrega
            if cam.visible(*NEST, 40):
                sx, sy = cam.apply(*NEST)
                ring(c, sx, sy, NEST_R + 6 + 4 * math.sin(self.t * 5), C_GOLD, .9, 2)
