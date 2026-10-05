"""Escena de juego: orquesta cueva, jugador, crías, enemigos, luces y HUD."""
import math
import random

import pygame

import difficulty
import ui
from camera import Camera
from enemies import Enemy, pick_kind, BIG
from events import EventBus, NoiseEvent, ImpactEvent, SonarEvent
from lighting import Lighting, ring
from map import CaveMap
from player import Bat
from pups import Pup
from scenes import Scene
from scenes.overlays import draw_overlay
from settings import (W, H, GOAL, NEST, NEST_R, TILE, BAT_HP, SCREECH_CD, SCREECH_R, SHIELD_CD, BRIGHTNESS_LEVELS, SONAR_MAX_R,
                      IMPACT_NOISE_MIN, IMPACT_NOISE_MAX, C_SONAR, C_IMPACT, C_GREEN, C_PUP)


class PlayScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.sounds = game.sounds
        self.bus = EventBus()
        self.bus.subscribe(NoiseEvent, self.on_noise)
        self.bus.subscribe(ImpactEvent, self.on_impact)
        self.bus.subscribe(SonarEvent, self.on_sonar)
        self.cave = CaveMap()
        self.light = Lighting(self.cave.crystals, self.cave.fungi)
        self.canvas = pygame.Surface((W, H))
        self.state = 'play'
        self.bat = Bat()
        self.camera = Camera(self.bat.x, self.bat.y)
        self.pups, self.enemies, self.rings, self.texts = [], [], [], []
        self.rescued = 0
        self.diff = difficulty.params(0)
        self.cd = self.shake = self.spawn_t = self.t = self.danger_flash = 0.0
        self.drip = 3.0
        self.toast, self.toast_t = '', 0.0
        self.sonar_done = True
        self.sounds.listener = lambda: (self.bat.x, self.bat.y)
        self.refill()
        for _ in range(5):                                   # población inicial repartida por la cueva
            self.spawn_enemy(NEST, 800)

    def enter(self):
        self.sounds.stop()
        self.sounds.ambient(.5)

    # ------------------------------------------------------------ utilidades
    def refill(self):
        while len(self.pups) < min(3, GOAL - self.rescued):
            spot = self.cave.free_spot(NEST, 700, [(p.x, p.y) for p in self.pups], 450)
            self.pups.append(Pup(*spot))

    def spawn_enemy(self, ref, dist, ambush=False):
        """Aparece fuera de pantalla: en cualquier punto lejano o, en emboscada, a 600-1100 px del jugador."""
        x, y = self.cave.ring_spot(ref, 600, 1100) if ambush else self.cave.free_spot(ref, dist)
        e = Enemy(x, y, pick_kind(self.diff, self.enemies))
        if ambush:                                           # los de emboscada ya vienen tras el ruido
            e.state, e.target = 'inv', ref
        self.enemies.append(e)
        if e.kind in BIG:
            self.sounds.play('roar', (x, y), .9)

    def say(self, x, y, t, col=(255, 230, 240)):
        self.texts.append([x, y, t, col, 2.0])

    def shield(self):
        b = self.bat
        if b.try_shield(SHIELD_CD):
            self.sounds.play('shield_on')
            self.say(b.x, b.y - 34, '¡Escudo!', (170, 235, 255))

    def screech(self):
        if self.cd > 0:
            return
        b = self.bat
        self.cd, self.shake = SCREECH_CD, .15
        self.sounds.play('screech')
        for e in self.enemies:
            d = math.dist((e.x, e.y), (b.x, b.y)) or 1
            if d < SCREECH_R:
                e.hp -= 1
                e.stun = 1.8 * e.spec['stun']
                e.vx, e.vy = (e.x - b.x) / d * 260, (e.y - b.y) / d * 260
                if e.hp <= 0:
                    self.sounds.play('die', (e.x, e.y))
                    self.say(e.x, e.y - 15, '¡Fuera!', (255, 120, 120))
        self.enemies = [e for e in self.enemies if e.hp > 0]
        self.bus.emit(NoiseEvent(b.x, b.y, 170, (150, 220, 255), 'screech'))    # gritar también hace ruido

    def end(self, state, snd):
        self.state = state
        self.sounds.stop()
        self.sounds.play(snd)

    # ------------------------------------------------------------ eventos del bus
    def on_noise(self, e):
        self.rings.append([e.x, e.y, 0, e.radius, e.color])
        for en in self.enemies:
            en.hear(e.x, e.y, e.radius, self.diff.hear_mult)

    def on_impact(self, e):
        k = min(1.0, e.speed / 350)
        self.sounds.play('impact', base=.4 + .6 * k)
        if e.speed > 200:                                    # solo los choques fuertes sacuden la pantalla
            self.shake = max(self.shake, .06 + .1 * k)
        r = IMPACT_NOISE_MIN + (IMPACT_NOISE_MAX - IMPACT_NOISE_MIN) * k
        self.bus.emit(NoiseEvent(e.x, e.y, r, C_IMPACT, 'impact'))          # el golpe atrae criaturas

    def on_sonar(self, e):
        self.sounds.play('sonar')
        self.sounds.play('alarm', base=.5)
        self.sonar_done = False
        self.say(e.x, e.y - 30, '¡Sonar! Estás expuesto', C_SONAR)

    # ------------------------------------------------------------ entrada
    def handle(self, ev):
        g, K = self.game, pygame
        if ev.type == K.KEYDOWN:
            k = ev.key
            if k == K.K_ESCAPE:
                g.goto('title')
            elif k == K.K_b and self.state in ('play', 'pause'):      # cambia el brillo de la cueva
                g.brightness = (g.brightness + 1) % len(BRIGHTNESS_LEVELS)
                self.toast, self.toast_t = f'Brillo: {BRIGHTNESS_LEVELS[g.brightness][0]}', 2.0
                self.sounds.play('menu_move')
            elif self.state == 'play':
                if k == K.K_SPACE:
                    self.screech()
                elif k == K.K_q:
                    self.bat.try_sonar(self.diff.sonar_cd, self.bus)
                elif k in (K.K_e, K.K_LSHIFT, K.K_RSHIFT):
                    self.shield()
                elif k == K.K_p:
                    self.state = 'pause'
            elif self.state == 'pause' and k == K.K_p:
                self.state = 'play'
            elif self.state in ('over', 'win') and k == K.K_r:
                g.goto('play')
        elif ev.type == K.MOUSEBUTTONDOWN and self.state == 'play':
            if ev.button == 1:
                self.screech()
            elif ev.button == 3:
                self.shield()
            elif ev.button == 2:
                self.bat.try_sonar(self.diff.sonar_cd, self.bus)

    # ------------------------------------------------------------ lógica
    def update(self, dt):
        if self.state != 'play':
            return
        K = pygame
        ks = K.key.get_pressed()
        mv = (int(ks[K.K_d] or ks[K.K_RIGHT]) - int(ks[K.K_a] or ks[K.K_LEFT]),
              int(ks[K.K_s] or ks[K.K_DOWN]) - int(ks[K.K_w] or ks[K.K_UP]))
        mx, my = K.mouse.get_pos()
        self.t += dt
        b = self.bat
        b.update(dt, mv, self.camera.to_world(mx, my), self.cave, self.bus)
        self.camera.follow(b.x, b.y, dt, vx=b.vx, vy=b.vy)
        self.cd, self.shake = max(0, self.cd - dt), max(0, self.shake - dt)
        self.danger_flash = max(0, self.danger_flash - dt)
        self.toast_t = max(0, self.toast_t - dt)
        self.cave.mark_circle(b.x, b.y, TILE * 6, mem=True)
        rad = b.sonar_radius
        if rad is not None and not self.sonar_done:
            self.cave.mark_circle(*b.sonar_origin, rad)
            self.sonar_done = rad >= SONAR_MAX_R
        if self.bat.shield_t > 0 and self.bat.shield_t <= dt:
            self.sounds.play('shield_off')
        for p in self.pups:
            p.update(dt, self)
            if p is b.carry:
                p.x, p.y = b.x, b.y + 14
            elif not b.carry and math.dist((p.x, p.y), (b.x, b.y)) < 26:
                b.carry = p
                self.sounds.play('pickup')
                self.say(p.x, p.y - 20, '¡Llévala al nido!')
        if b.carry and math.dist((b.x, b.y), NEST) < NEST_R:
            self.pups.remove(b.carry)
            b.carry, self.rescued = None, self.rescued + 1
            b.hp = min(BAT_HP, b.hp + 1)
            self.say(NEST[0], NEST[1] - 60, f'¡Cría a salvo! {self.rescued}/{GOAL}', C_GREEN)
            if self.rescued >= GOAL:
                return self.end('win', 'win')
            self.diff = difficulty.params(self.rescued)          # la dificultad sube con cada rescate
            self.danger_flash = 2.5
            self.sounds.play('deliver')
            self.sounds.play('levelup', base=.7)
            self.say(NEST[0], NEST[1] - 85, f'¡Peligro {self.diff.level}!', (255, 200, 120))
            self.refill()
        for e in self.enemies:
            e.update(dt, self)
            d = math.dist((e.x, e.y), (b.x, b.y)) or 1
            if d < 12 + e.rad and e.stun <= 0:
                if b.shield_t > 0:                           # el escudo repele y aturde
                    e.stun = 1.2 * e.spec['stun'] + .3
                    e.vx, e.vy = (e.x - b.x) / d * 340, (e.y - b.y) / d * 340
                    self.sounds.play('shield_hit')
                    self.shake = max(self.shake, .12)
                    self.rings.append([b.x, b.y, 0, 90, (170, 230, 255)])
                elif b.inv <= 0:
                    b.hp, b.inv, self.shake = b.hp - e.spec['dmg'], 1.3, .4
                    b.knockback((b.x - e.x) / d, (b.y - e.y) / d, 320)
                    self.sounds.play('hit')
                    if b.carry:
                        b.carry.t = 0
                    if b.hp <= 0:
                        return self.end('over', 'lose')
        self.spawn_t -= dt                                   # aparición continua, no solo cerca de las crías
        if self.spawn_t <= 0:
            self.spawn_t = self.diff.spawn_interval * random.uniform(.8, 1.2)
            if len(self.enemies) < self.diff.max_enemies:
                ambush = random.random() < .4
                self.spawn_enemy((b.x, b.y), 650, ambush)
        self.drip -= dt
        if self.drip <= 0:
            self.sounds.play('drip', (b.x + random.randint(-600, 600), b.y + random.randint(-600, 600)), .6)
            self.drip = random.uniform(3, 8)
        for r in self.rings:
            r[2] += dt * 320
        self.rings = [r for r in self.rings if r[2] < r[3]]
        for t in self.texts:
            t[1] -= 18 * dt
            t[4] -= dt
        self.texts = [t for t in self.texts if t[4] > 0]

    # ------------------------------------------------------------ dibujo
    def draw(self, screen):
        c, b, cam = self.canvas, self.bat, self.camera
        ix, iy = int(cam.x), int(cam.y)
        c.blit(self.cave.bg, (0, 0), (ix, iy, W, H))
        for p in self.pups:
            if p is not b.carry and cam.visible(p.x, p.y):
                sx, sy = cam.apply(p.x, p.y + math.sin(self.t * 3 + p.x) * 1.5)
                ui.draw_pup(c, sx, sy, self.t)
        for e in self.enemies:
            if cam.visible(e.x, e.y):
                ui.draw_enemy(c, *cam.apply(e.x, e.y), e)
        bx, by = cam.apply(b.x, b.y)
        if b.inv <= 0 or int(self.t * 12) % 2:
            ui.draw_bat_tilted(c, bx, by, b.flap, b.tilt)
        if b.carry:
            ui.draw_bat(c, bx, by + 16, self.t * 12, .5, (120, 70, 100), (150, 95, 125))
        self.light.apply(c, self, self.t)
        srad, sk = b.sonar_radius, b.sonar_strength
        for e in self.enemies:                       # ojos visibles en la oscuridad
            if not cam.visible(e.x, e.y):
                continue
            d = math.dist((e.x, e.y), (b.x, b.y))
            reach = max(300, BRIGHTNESS_LEVELS[self.game.brightness][2] * 1.3) * (1.6 if e.kind in BIG else 1)
            seen = d < reach or (srad and sk > .15 and math.dist((e.x, e.y), b.sonar_origin) < srad)
            if seen:
                col = (120, 120, 60) if e.stun > 0 else ((255, 40, 40) if e.state == 'chase' else (200, 90, 40))
                ex, ey = cam.apply(e.x, e.y)
                for sd in (-4, 4):
                    pygame.draw.circle(c, col, (int(ex + sd * e.spec['size']), int(ey - 3)), 2 + int(e.spec['size'] > 1.5))
        for x, y, r, mr, col in self.rings:                  # anillos de ruido (sin capa alfa de pantalla completa)
            sx, sy = cam.apply(x, y)
            ring(c, sx, sy, r, col, .7 * (1 - r / mr), 2)
        self.light.draw_sonar_ring(c, self)
        self.light.draw_shield(c, self, self.t)
        self.light.draw_trail(c, self)
        for x, y, t, col, life in self.texts:
            sx, sy = cam.apply(x, y)
            ui.text(c, ui.F_S, t, sx, sy, col, True)
        ui.draw_hud(c, self)
        if self.toast_t > 0:
            ui.text(c, ui.F_S, self.toast, (W - 220) // 2, H - 52, (255, 255, 255), True)
        amp = 3 * min(1, self.shake / .3)                    # sacudida suave que decae (máx. 3 px)
        ox, oy = (random.randint(-round(amp), round(amp)), random.randint(-round(amp), round(amp))) if amp >= .5 else (0, 0)
        screen.fill((0, 0, 0))
        screen.blit(c, (ox, oy))
        if self.state != 'play':
            draw_overlay(screen, self.state, self.rescued, self.t)
