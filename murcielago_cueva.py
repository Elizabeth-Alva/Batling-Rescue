#!/usr/bin/env python3
"""MURCIÉLAGO: Rescate en la cueva
Requisitos: pip install pygame
Todo (gráficos y sonidos) se genera por código; no necesita archivos externos."""
import math, random
from array import array
import pygame

SR = 22050
pygame.mixer.pre_init(SR, -16, 1, 512)
pygame.init()
W, H = 960, 640
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Murciélago: Rescate en la cueva")
clock = pygame.time.Clock()
F_S = pygame.font.SysFont("arial", 18, bold=True)
F_M = pygame.font.SysFont("arial", 28, bold=True)
F_L = pygame.font.SysFont("arial", 54, bold=True)
TAU = math.tau
GOAL = 10                      # crías a rescatar para ganar
NEST, NEST_R = (90, 90), 55
game = None


# ---------------------------------------------------------------- SONIDO
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
    ny = [0.0]

    def amb(t, p):
        ny[0] += .03 * (random.uniform(-1, 1) - ny[0])
        return .5 * math.sin(TAU * 55 * t) + .3 * math.sin(TAU * 82 * t + 1) + ny[0] * 1.6 * (.6 + .4 * math.sin(TAU * t / 6))
    S['amb'] = mk(6.0, amb, .5)
    return S


def play(snd, pos=None, base=1.0):
    if isinstance(snd, list):
        snd = random.choice(snd)
    v = base
    if pos and game:
        v *= max(.12, 1 - math.dist(pos, (game.bat.x, game.bat.y)) / 650)
    ch = snd.play()
    if ch:
        ch.set_volume(v)


# ---------------------------------------------------------------- LUCES / CUEVA
def radial(r, peak=255):
    s = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
    for i in range(r, 0, -2):
        pygame.draw.circle(s, (255, 255, 255, int(peak * (1 - i / r) ** 1.3)), (r, r), i)
    return s


CONE_R = 280


def make_cone():
    m = pygame.Surface((2 * CONE_R, 2 * CONE_R), pygame.SRCALPHA)
    for half, a in ((.46, 110), (.34, 190), (.22, 255)):
        pts = [(CONE_R, CONE_R)] + [(CONE_R + CONE_R * math.cos(-half + 2 * half * k / 16),
                                     CONE_R + CONE_R * math.sin(-half + 2 * half * k / 16)) for k in range(17)]
        pygame.draw.polygon(m, (255, 255, 255, a), pts)
    m.blit(radial(CONE_R), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return m


def gen_cave():
    rocks, tries = [], 0
    while len(rocks) < 13 and tries < 600:
        tries += 1
        r, = random.randint(28, 62),
        x, y = random.randint(r, W - r), random.randint(r, H - r)
        if math.dist((x, y), NEST) < r + 130:
            continue
        if all(math.dist((x, y), (a, b)) > r + c + 60 for a, b, c in rocks):
            rocks.append((x, y, r))
    bg = pygame.Surface((W, H))
    bg.fill((30, 24, 28))
    for _ in range(2500):
        c = random.randint(22, 44)
        bg.set_at((random.randrange(W), random.randrange(H)), (c, c - 5, c - 2))
    for x, y, r in rocks:
        pts = [(x + math.cos(a) * r * random.uniform(.85, 1.12), y + math.sin(a) * r * random.uniform(.85, 1.12))
               for a in [TAU * k / 14 for k in range(14)]]
        pygame.draw.polygon(bg, (14, 12, 16), pts)
        pygame.draw.polygon(bg, (58, 48, 54), pts, 3)
        pygame.draw.circle(bg, (40, 33, 38), (int(x - r * .2), int(y - r * .2)), int(r * .45))
    pygame.draw.rect(bg, (10, 8, 12), (0, 0, W, H), 14)
    pygame.draw.rect(bg, (60, 50, 56), (0, 0, W, H), 3)
    pygame.draw.circle(bg, (60, 45, 38), NEST, NEST_R)
    pygame.draw.circle(bg, (90, 70, 55), NEST, NEST_R, 4)
    return rocks, bg


def collide(o, rad):
    for x, y, r in game.rocks:
        dx, dy = o.x - x, o.y - y
        d, m = math.hypot(dx, dy) or .01, r * .92 + rad
        if d < m:
            o.x, o.y = x + dx / d * m, y + dy / d * m
    o.x = min(max(o.x, 16 + rad), W - 16 - rad)
    o.y = min(max(o.y, 16 + rad), H - 16 - rad)


# ---------------------------------------------------------------- DIBUJO
def draw_bat(s, x, y, flap, sc=1.0, col=(40, 30, 60), body=(55, 42, 80)):
    w = math.sin(flap)
    for sd in (-1, 1):
        pts = [(x + sd * 6 * sc, y - 2 * sc), (x + sd * 30 * sc, y - 14 * sc - w * 12 * sc),
               (x + sd * 40 * sc, y + 4 * sc - w * 16 * sc), (x + sd * 28 * sc, y + 6 * sc - w * 4 * sc),
               (x + sd * 20 * sc, y + 14 * sc - w * 2 * sc), (x + sd * 10 * sc, y + 8 * sc)]
        pygame.draw.polygon(s, col, pts)
        pygame.draw.polygon(s, (95, 75, 130), pts, max(1, int(2 * sc)))
    pygame.draw.ellipse(s, body, (x - 8 * sc, y - 12 * sc, 16 * sc, 26 * sc))
    for sd in (-1, 1):
        pygame.draw.polygon(s, body, [(x + sd * 3 * sc, y - 10 * sc), (x + sd * 9 * sc, y - 22 * sc), (x + sd * 10 * sc, y - 8 * sc)])
        pygame.draw.circle(s, (255, 220, 90), (int(x + sd * 3.5 * sc), int(y - 6 * sc)), max(1, int(2 * sc)))


def draw_spider(s, e):
    x, y = e.x, e.y
    for k in range(8):
        a = TAU * k / 8 + math.sin(e.anim * 8 + k) * .25
        pygame.draw.lines(s, (8, 6, 10), False, [(x, y), (x + math.cos(a) * 14, y + math.sin(a) * 14 - 4),
                                                   (x + math.cos(a) * 24, y + math.sin(a) * 24)], 3)
    pygame.draw.circle(s, (22, 16, 24), (int(x), int(y)), 13)
    pygame.draw.circle(s, (60, 40, 60), (int(x), int(y)), 13, 2)


def heart(s, x, y, col):
    pygame.draw.circle(s, col, (x - 5, y), 6)
    pygame.draw.circle(s, col, (x + 5, y), 6)
    pygame.draw.polygon(s, col, [(x - 11, y + 2), (x + 11, y + 2), (x, y + 15)])


def text(s, f, t, x, y, col=(235, 225, 245), center=False):
    im = f.render(t, True, col)
    s.blit(im, im.get_rect(center=(x, y)) if center else (x, y))


# ---------------------------------------------------------------- ENTIDADES
class Bat:
    def __init__(s):
        s.x, s.y = NEST[0] + 70, NEST[1] + 40
        s.vx = s.vy = s.aim = s.flap = s.inv = 0
        s.hp, s.carry = 5, None


class Pup:
    def __init__(s, x, y):
        s.x, s.y, s.t = x, y, random.uniform(.5, 2.5)

    def update(s, dt, g):
        s.t -= dt
        if s.t <= 0:
            carried = g.bat.carry is s
            s.t = max(1.3, 3.8 - .22 * g.rescued) * random.uniform(.8, 1.2) * (.7 if carried else 1)
            g.make_noise(s.x, s.y, (300 + 14 * g.rescued) * (.8 if carried else 1), (255, 150, 210))
            play(g.snd['squeak'], (s.x, s.y), .9)


class Enemy:
    def __init__(s, x, y):
        s.x, s.y, s.hp, s.state, s.target = x, y, 2, 'patrol', None
        s.wait = s.stun = s.lose = s.vx = s.vy = 0
        s.anim = random.random() * 9

    def update(s, dt, g):
        b = g.bat
        d = math.dist((s.x, s.y), (b.x, b.y))
        s.anim += dt
        if s.stun > 0:
            s.stun -= dt
            s.vx *= .9
            s.vy *= .9
            s.x += s.vx * dt
            s.y += s.vy * dt
            collide(s, 12)
            return
        dif, lit = g.rescued, False
        if g.flash and d < 270:       # la luz atrae a las arañas
            ang = math.atan2(s.y - b.y, s.x - b.x)
            lit = abs((ang - b.aim + math.pi) % TAU - math.pi) < .46
        if (d < 120 + 5 * dif or lit) and s.state != 'chase':
            s.state, s.lose = 'chase', 0
            play(g.snd['growl'], (s.x, s.y), .8)
        sp = 0
        if s.state == 'chase':
            s.target, sp = (b.x, b.y), 95 + 9 * dif
            s.lose = s.lose + dt if d > 300 else 0
            if s.lose > 2.5:
                s.state, s.target = 'patrol', None
        elif s.state == 'inv':
            sp = 70 + 4 * dif
            if math.dist((s.x, s.y), s.target) < 14:
                s.wait, sp = s.wait + dt, 0
                if s.wait > 1.8:
                    s.state, s.target = 'patrol', None
        else:
            sp, s.wait = 42, s.wait + dt
            if not s.target or math.dist((s.x, s.y), s.target) < 14 or s.wait > 5:
                s.target, s.wait = (random.randint(40, W - 40), random.randint(40, H - 40)), 0
        if s.target and sp:
            dx, dy = s.target[0] - s.x, s.target[1] - s.y
            n = math.hypot(dx, dy) or 1
            s.vx, s.vy = dx / n * sp, dy / n * sp
            s.x += s.vx * dt
            s.y += s.vy * dt
        collide(s, 12)


# ---------------------------------------------------------------- JUEGO
class Game:
    def __init__(s):
        s.snd = build_sounds()
        s.cone = make_cone()
        s.L_BAT, s.L_NEST, s.L_PUP = radial(90), radial(120), radial(40, 255)
        s.L_PUP.fill((255, 255, 255, 110), special_flags=pygame.BLEND_RGBA_MULT)
        s.canvas = pygame.Surface((W, H))
        s.dark = pygame.Surface((W, H), pygame.SRCALPHA)
        s.fx = pygame.Surface((W, H), pygame.SRCALPHA)
        s.state = 'menu'
        s.reset()

    def reset(s):
        s.rocks, s.bg = gen_cave()
        s.bat, s.pups, s.enemies, s.rings, s.texts = Bat(), [], [], [], []
        s.rescued, s.flash, s.battery, s.locked = 0, False, 100, False
        s.cd = s.shake = s.spawn_t = s.t = 0
        s.drip = 3
        s.refill()
        for _ in range(2):
            s.spawn_enemy(NEST, 320)

    def start(s):
        pygame.mixer.stop()
        s.reset()
        s.state = 'play'
        ch = s.snd['amb'].play(-1)
        if ch:
            ch.set_volume(.5)

    def free_spot(s, far_from, dist):
        for _ in range(200):
            x, y = random.randint(40, W - 40), random.randint(40, H - 40)
            if math.dist((x, y), far_from) > dist and all(math.dist((x, y), (a, b)) > c + 28 for a, b, c in s.rocks) \
                    and all(math.dist((x, y), (p.x, p.y)) > 90 for p in s.pups):
                return x, y
        return W - 80, H - 80

    def refill(s):
        while len(s.pups) < min(3, GOAL - s.rescued):
            s.pups.append(Pup(*s.free_spot(NEST, 350)))

    def spawn_enemy(s, ref, dist):
        s.enemies.append(Enemy(*s.free_spot(ref, dist)))

    def make_noise(s, x, y, r, col):
        s.rings.append([x, y, 0, r, col])
        for e in s.enemies:
            if e.state != 'chase' and e.stun <= 0 and math.dist((e.x, e.y), (x, y)) < r:
                e.state, e.target, e.wait = 'inv', (x, y), 0

    def say(s, x, y, t, col=(255, 230, 240)):
        s.texts.append([x, y, t, col, 2.0])

    def toggle_flash(s):
        if s.flash:
            s.flash = False
        elif not s.locked and s.battery > 0:
            s.flash = True
        play(s.snd['click'])

    def screech(s):
        if s.cd > 0:
            return
        b = s.bat
        s.cd, s.shake = 1.1, .15
        s.rings.append([b.x, b.y, 0, 150, (150, 220, 255)])
        play(s.snd['screech'])
        for e in s.enemies:
            d = math.dist((e.x, e.y), (b.x, b.y)) or 1
            if d < 150:
                e.hp -= 1
                e.stun = 1.8
                e.vx, e.vy = (e.x - b.x) / d * 260, (e.y - b.y) / d * 260
                if e.hp <= 0:
                    play(s.snd['die'], (e.x, e.y))
                    s.say(e.x, e.y - 15, '¡Fuera!', (255, 120, 120))
        s.enemies = [e for e in s.enemies if e.hp > 0]
        s.make_noise(b.x, b.y, 170, (150, 220, 255))    # gritar también hace ruido

    def end(s, state, snd):
        s.state = state
        pygame.mixer.stop()
        play(s.snd[snd])

    def update(s, dt, mv, aim):
        if s.state != 'play':
            return
        s.t += dt
        b, dif = s.bat, s.rescued
        n = math.hypot(*mv)
        sp = 215 * (.8 if b.carry else 1)
        k = min(1, dt * 7)
        b.vx += ((mv[0] / n * sp if n else 0) - b.vx) * k
        b.vy += ((mv[1] / n * sp if n else 0) - b.vy) * k
        b.x += b.vx * dt
        b.y += b.vy * dt
        collide(b, 12)
        b.aim = math.atan2(aim[1] - b.y, aim[0] - b.x)
        b.flap += dt * (14 + math.hypot(b.vx, b.vy) / 20)
        b.inv, s.cd, s.shake = max(0, b.inv - dt), max(0, s.cd - dt), max(0, s.shake - dt)
        if s.flash:
            s.battery -= 16 * dt
            if s.battery <= 0:
                s.battery, s.flash, s.locked = 0, False, True
        else:
            s.battery = min(100, s.battery + 9 * dt)
            if s.locked and s.battery >= 25:
                s.locked = False
        for p in s.pups:
            p.update(dt, s)
            if p is b.carry:
                p.x, p.y = b.x, b.y + 14
            elif not b.carry and math.dist((p.x, p.y), (b.x, b.y)) < 26:
                b.carry = p
                play(s.snd['pickup'])
                s.say(p.x, p.y - 20, '¡Llévala al nido!')
        if b.carry and math.dist((b.x, b.y), NEST) < NEST_R:
            s.pups.remove(b.carry)
            b.carry, s.rescued = None, s.rescued + 1
            b.hp, s.battery = min(5, b.hp + 1), min(100, s.battery + 30)
            s.say(NEST[0], NEST[1] - 60, f'¡Cría a salvo! {s.rescued}/{GOAL}', (160, 255, 190))
            if s.rescued >= GOAL:
                return s.end('win', 'win')
            play(s.snd['deliver'])
            s.refill()
        for e in s.enemies:
            e.update(dt, s)
            d = math.dist((e.x, e.y), (b.x, b.y)) or 1
            if d < 24 and e.stun <= 0 and b.inv <= 0:
                b.hp, b.inv, s.shake = b.hp - 1, 1.3, .4
                b.vx, b.vy = (b.x - e.x) / d * 320, (b.y - e.y) / d * 320
                play(s.snd['hit'])
                if b.carry:
                    b.carry.t = 0
                if b.hp <= 0:
                    return s.end('over', 'lose')
        if len(s.enemies) < min(8, 2 + (dif + 1) // 2):
            s.spawn_t -= dt
            if s.spawn_t <= 0:
                s.spawn_enemy((b.x, b.y), 350)
                s.spawn_t = max(2, 6 - .4 * dif)
        s.drip -= dt
        if s.drip <= 0:
            play(s.snd['drip'], (random.randint(0, W), random.randint(0, H)), .6)
            s.drip = random.uniform(3, 8)
        for r in s.rings:
            r[2] += dt * 320
        s.rings = [r for r in s.rings if r[2] < r[3]]
        for t in s.texts:
            t[1] -= 18 * dt
            t[4] -= dt
        s.texts = [t for t in s.texts if t[4] > 0]

    def draw(s):
        c, b = s.canvas, s.bat
        c.blit(s.bg, (0, 0))
        for p in s.pups:
            if p is not b.carry:
                draw_bat(c, p.x, p.y + math.sin(s.t * 3 + p.x) * 1.5, s.t * 9, .55, (120, 70, 100), (150, 95, 125))
        for e in s.enemies:
            draw_spider(c, e)
        if b.inv <= 0 or int(s.t * 12) % 2:
            draw_bat(c, b.x, b.y, b.flap, 1.0)
        if b.carry:
            draw_bat(c, b.x, b.y + 16, s.t * 12, .5, (120, 70, 100), (150, 95, 125))
        d = s.dark
        d.fill((0, 0, 8, 246))
        sub = pygame.BLEND_RGBA_SUB
        d.blit(s.L_BAT, (b.x - 90, b.y - 90), special_flags=sub)
        d.blit(s.L_NEST, (NEST[0] - 120, NEST[1] - 120), special_flags=sub)
        for p in s.pups:
            if p is not b.carry:
                d.blit(s.L_PUP, (p.x - 40, p.y - 40), special_flags=sub)
        if s.flash:
            rot = pygame.transform.rotate(s.cone, -math.degrees(b.aim))
            d.blit(rot, rot.get_rect(center=(b.x, b.y)), special_flags=sub)
        c.blit(d, (0, 0))
        for e in s.enemies:                       # ojos visibles en la oscuridad
            if math.dist((e.x, e.y), (b.x, b.y)) < 300:
                col = (120, 120, 60) if e.stun > 0 else ((255, 40, 40) if e.state == 'chase' else (200, 90, 40))
                for sd in (-4, 4):
                    pygame.draw.circle(c, col, (int(e.x + sd), int(e.y - 3)), 2)
        fx = s.fx
        fx.fill((0, 0, 0, 0))
        for x, y, r, mr, col in s.rings:
            pygame.draw.circle(fx, (*col, int(130 * (1 - r / mr))), (int(x), int(y)), int(r), 2)
        c.blit(fx, (0, 0))
        for x, y, t, col, life in s.texts:
            text(c, F_S, t, x, y, col, True)
        s.hud(c)
        ox, oy = (random.randint(-5, 5), random.randint(-5, 5)) if s.shake > 0 else (0, 0)
        screen.fill((0, 0, 0))
        screen.blit(c, (ox, oy))
        if s.state != 'play':
            s.overlay()
        pygame.display.flip()

    def hud(s, c):
        for i in range(5):
            heart(c, 28 + i * 30, 24, (220, 50, 80) if i < s.bat.hp else (60, 30, 40))
        text(c, F_S, 'LUZ', 14, 48)
        pygame.draw.rect(c, (40, 40, 40), (52, 50, 110, 12))
        pygame.draw.rect(c, (255, 80, 60) if s.locked else (250, 220, 90), (52, 50, 1.1 * s.battery, 12))
        text(c, F_S, 'GRITO', 14, 68)
        pygame.draw.rect(c, (40, 40, 40), (62, 70, 100, 12))
        pygame.draw.rect(c, (120, 210, 255), (62, 70, 100 * (1 - s.cd / 1.1), 12))
        text(c, F_M, f'Crías: {s.rescued}/{GOAL}', W - 20 - F_M.size(f'Crías: {s.rescued}/{GOAL}')[0], 12)
        danger = f'Peligro: {s.rescued + 1}'
        text(c, F_S, danger, W - 20 - F_S.size(danger)[0], 48, (255, 150, 120))
        if s.t < 9:
            text(c, F_S, 'Sigue los chillidos rosados. Sin luz te ven menos... pero tampoco ves.', W // 2, H - 24, (200, 190, 215), True)

    def overlay(s):
        v = pygame.Surface((W, H), pygame.SRCALPHA)
        v.fill((0, 0, 10, 205))
        screen.blit(v, (0, 0))
        cx = W // 2
        if s.state == 'menu':
            text(screen, F_L, 'MURCIÉLAGO', cx, 100, (190, 150, 255), True)
            text(screen, F_M, 'Rescate en la cueva', cx, 150, (230, 220, 245), True)
            lines = ['Las crías se perdieron en la cueva oscura. Llévalas al nido (círculo marrón).',
                     'Sus chillidos atraen a las arañas... y tu grito y tu linterna también.', '',
                     'WASD / Flechas: volar        Ratón: apuntar la linterna',
                     'F o clic derecho: linterna (se gasta la batería, y atrae arañas)',
                     'ESPACIO o clic izquierdo: grito sónico (aturde y daña, con enfriamiento)',
                     'P: pausa        ESC: salir', '',
                     f'Rescata {GOAL} crías. Cada rescate sube el peligro: más arañas, más rápidas.']
            for i, l in enumerate(lines):
                text(screen, F_S, l, cx, 215 + i * 28, center=True)
            text(screen, F_M, 'Pulsa ENTER para empezar', cx, 535, (160, 255, 190), True)
        elif s.state == 'pause':
            text(screen, F_L, 'PAUSA', cx, H // 2, center=True)
        elif s.state == 'over':
            text(screen, F_L, 'LA CUEVA TE VENCIÓ', cx, 250, (255, 110, 110), True)
            text(screen, F_M, f'Crías rescatadas: {s.rescued}/{GOAL}', cx, 320, center=True)
            text(screen, F_M, 'R para reintentar', cx, 380, (160, 255, 190), True)
        else:
            text(screen, F_L, '¡TODAS A SALVO!', cx, 250, (160, 255, 190), True)
            text(screen, F_M, 'Las crías vuelven a casa gracias a ti.', cx, 320, center=True)
            text(screen, F_M, 'R para jugar de nuevo', cx, 380, (190, 150, 255), True)


def main():
    global game
    game = Game()
    K = pygame
    while True:
        dt = min(clock.tick(60) / 1000, .05)
        for ev in pygame.event.get():
            if ev.type == K.QUIT:
                return
            if ev.type == K.KEYDOWN:
                k, st = ev.key, game.state
                if k == K.K_ESCAPE:
                    return
                if st == 'menu' and k in (K.K_RETURN, K.K_SPACE):
                    game.start()
                elif st in ('over', 'win') and k == K.K_r:
                    game.start()
                elif st == 'play':
                    if k == K.K_f:
                        game.toggle_flash()
                    elif k == K.K_SPACE:
                        game.screech()
                    elif k == K.K_p:
                        game.state = 'pause'
                elif st == 'pause' and k == K.K_p:
                    game.state = 'play'
            if ev.type == K.MOUSEBUTTONDOWN and game.state == 'play':
                if ev.button == 1:
                    game.screech()
                elif ev.button == 3:
                    game.toggle_flash()
        ks = pygame.key.get_pressed()
        mv = (int(ks[K.K_d] or ks[K.K_RIGHT]) - int(ks[K.K_a] or ks[K.K_LEFT]),
              int(ks[K.K_s] or ks[K.K_DOWN]) - int(ks[K.K_w] or ks[K.K_UP]))
        game.update(dt, mv, pygame.mouse.get_pos())
        game.draw()


if __name__ == "__main__":
    main()
