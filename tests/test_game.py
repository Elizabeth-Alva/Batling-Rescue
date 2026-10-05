"""Pruebas headless: python -m unittest discover -s tests"""
import math
import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402
from sound import init_mixer  # noqa: E402

init_mixer()
pygame.init()

import difficulty  # noqa: E402
from events import EventBus, NoiseEvent, ImpactEvent  # noqa: E402
from settings import (NEST, NEST_T, GOAL, SONAR_EXPOSE_T, TILE, W, H, BAT_SPEED, MEMORY_ALPHA,  # noqa: E402
                      BRIGHTNESS_LEVELS, DEFAULT_BRIGHTNESS)
from map import CaveMap  # noqa: E402
from game import Game  # noqa: E402
from scenes.play import PlayScene  # noqa: E402
from enemies import Enemy  # noqa: E402
from player import Bat  # noqa: E402
from camera import Camera  # noqa: E402


class OpenCave:
    """Cueva sin paredes (para probar el movimiento aislado)."""
    def resolve(self, o, rad):
        return False, 0.0, 0.0


class WallCave:
    """Pared vertical infinita en x = wall_x (el murciélago queda a su izquierda)."""
    def __init__(self, wall_x):
        self.wall_x = wall_x

    def resolve(self, o, rad):
        if o.x + rad > self.wall_x:
            o.x = self.wall_x - rad
            return True, -1.0, 0.0
        return False, 0.0, 0.0


class Dummy:
    pass


class GameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = Game()
        cls.scene = PlayScene(cls.game)

    def test_map_connected(self):
        cave = self.scene.cave
        seen = CaveMap._flood(cave.g, *NEST_T)
        floor = {(x, y) for y in range(cave.h) for x in range(cave.w) if not cave.g[y][x]}
        self.assertEqual(seen, floor)
        self.assertGreater(len(floor), 1500)

    def test_pups_reachable(self):
        cave = self.scene.cave
        for p in self.scene.pups:
            self.assertIsNotNone(cave.path(NEST, (p.x, p.y)))

    def test_difficulty_monotonic(self):
        prev = difficulty.params(0)
        for r in range(1, GOAL + 1):
            cur = difficulty.params(r)
            self.assertGreaterEqual(cur.chase_speed, prev.chase_speed)
            self.assertGreaterEqual(cur.max_enemies, prev.max_enemies)
            self.assertLessEqual(cur.spawn_interval, prev.spawn_interval)
            self.assertGreaterEqual(cur.sonar_cd, prev.sonar_cd)
            prev = cur

    def test_impact_generates_noise_only_when_fast(self):
        s = PlayScene(self.game)
        noises = []
        s.bus.subscribe(NoiseEvent, lambda e: noises.append(e))
        b, cave = s.bat, s.cave
        # buscar una pared a la derecha del murciélago
        tx = int(b.x // TILE)
        ty = int(b.y // TILE)
        while not cave.solid(tx, ty):
            tx += 1
            if tx >= cave.w:
                self.skipTest("sin pared a la vista")
        b.x, b.y = tx * TILE - 13, ty * TILE + TILE / 2
        b.vx, b.vy = 200, 0
        b.update(1 / 60, (1, 0), (b.x + 10, b.y), cave, s.bus)
        self.assertTrue(any(n.source == 'impact' for n in noises))
        noises.clear()
        b.impact_cd = 0
        b.x, b.y = tx * TILE - 13, ty * TILE + TILE / 2
        b.vx, b.vy = 20, 0
        b.update(1 / 60, (1, 0), (b.x + 10, b.y), cave, s.bus)
        self.assertFalse(any(n.source == 'impact' for n in noises))

    def test_sonar_exposes_and_attracts(self):
        s = PlayScene(self.game)
        s.enemies = []
        b = s.bat
        e = Enemy(b.x + 300, b.y)           # fuera del radio normal de detección
        s.enemies.append(e)
        self.assertTrue(b.try_sonar(s.diff.sonar_cd, s.bus))
        self.assertAlmostEqual(b.exposed, SONAR_EXPOSE_T)
        self.assertFalse(b.try_sonar(s.diff.sonar_cd, s.bus))   # en enfriamiento
        s.cave.resolve(e, e.rad)
        e.update(1 / 60, s)
        self.assertEqual(e.state, 'chase')

    def test_noise_attracts_enemy(self):
        s = PlayScene(self.game)
        e = Enemy(*NEST)
        e.state = 'patrol'
        s.enemies = [e]
        s.bus.emit(NoiseEvent(NEST[0] + 100, NEST[1], 200, (255, 255, 255), 'impact'))
        self.assertEqual(e.state, 'inv')
        far = Enemy(NEST[0] + 2000, NEST[1])
        far.hear(NEST[0], NEST[1], 200, 1.0)
        self.assertEqual(far.state, 'patrol')

    def test_no_flashlight(self):
        s = PlayScene(self.game)
        self.assertFalse(hasattr(s, 'flash'))

    def test_shield_blocks_damage_and_repels(self):
        s = PlayScene(self.game)
        b = s.bat
        e = Enemy(b.x + 5, b.y, 'predator')
        s.enemies = [e]
        s.spawn_t = 999
        self.assertTrue(b.try_shield(15))
        self.assertFalse(b.try_shield(15))
        hp = b.hp
        s.update(1 / 60)
        self.assertEqual(b.hp, hp)
        self.assertGreater(e.stun, 0)
        # sin escudo el depredador hace daño
        b.shield_t = 0
        e.stun = 0
        e.x, e.y = b.x + 5, b.y
        s.update(1 / 60)
        self.assertEqual(b.hp, hp - 1)

    def test_shield_lasts_five_seconds(self):
        s = PlayScene(self.game)
        s.bat.try_shield(15)
        for _ in range(int(4.9 * 60)):
            s.bat.update(1 / 60, (0, 0), (0, 0), s.cave, s.bus)
        self.assertGreater(s.bat.shield_t, 0)
        for _ in range(12):
            s.bat.update(1 / 60, (0, 0), (0, 0), s.cave, s.bus)
        self.assertEqual(s.bat.shield_t, 0)

    def test_predators_only_when_difficulty_rises(self):
        from enemies import pick_kind, BIG
        low = difficulty.params(1)
        self.assertTrue(all(pick_kind(low) not in BIG for _ in range(300)))
        hi = difficulty.params(8)
        kinds = [pick_kind(hi) for _ in range(400)]
        self.assertTrue(any(k in BIG for k in kinds))
        self.assertIn('behemoth', kinds)
        # respeta el tope de grandes simultáneos
        crowd = [Enemy(0, 0, 'predator') for _ in range(hi.max_predators)]
        self.assertTrue(all(pick_kind(hi, crowd) not in BIG for _ in range(300)))

    def test_continuous_spawning(self):
        s = PlayScene(self.game)
        n0 = len(s.enemies)
        s.enemies = s.enemies[:2]
        s.spawn_t = 0
        s.update(1 / 60)
        self.assertEqual(len(s.enemies), 3)

    # ------------------------------------------------------------ movilidad
    def test_bat_accelerates_fast(self):
        b = Bat()
        b.x = b.y = 500
        for _ in range(9):                                   # 0.15 s
            b.update(1 / 60, (1, 0), (0, 0), OpenCave(), EventBus())
        self.assertGreaterEqual(b.vx, .9 * BAT_SPEED)

    def test_bat_stops_fast(self):
        b = Bat()
        b.x = b.y = 500
        for _ in range(30):
            b.update(1 / 60, (1, 0), (0, 0), OpenCave(), EventBus())
        for _ in range(12):                                  # 0.2 s soltando las teclas
            b.update(1 / 60, (0, 0), (0, 0), OpenCave(), EventBus())
        self.assertLess(math.hypot(b.vx, b.vy), 5)

    def test_bat_turns_around_quickly(self):
        b = Bat()
        b.x = b.y = 500
        for _ in range(30):
            b.update(1 / 60, (1, 0), (0, 0), OpenCave(), EventBus())
        for _ in range(15):                                  # 0.25 s en sentido contrario
            b.update(1 / 60, (-1, 0), (0, 0), OpenCave(), EventBus())
        self.assertLess(b.vx, -.5 * BAT_SPEED)

    def test_bat_slides_along_wall_without_sticking(self):
        b, bus = Bat(), EventBus()
        wall = WallCave(100)
        b.x, b.y = 60, 0
        for _ in range(60):                                  # 1 s empujando en diagonal contra la pared
            b.update(1 / 60, (1, 1), (0, 0), wall, bus)
        self.assertLessEqual(b.x, 100 - 12 + .01)            # no la atraviesa
        self.assertGreaterEqual(b.vy, .85 * BAT_SPEED)       # sigue a velocidad casi completa por la pared
        self.assertGreater(b.y, 150)

    def test_hard_hit_is_one_impact_and_light_scrape_is_silent(self):
        b, bus, hits = Bat(), EventBus(), []
        bus.subscribe(ImpactEvent, hits.append)
        wall = WallCave(100)
        b.x, b.y = 60, 0
        for _ in range(90):
            b.update(1 / 60, (1, .2), (0, 0), wall, bus)
        self.assertEqual(len(hits), 1)                       # un choque, no una ráfaga

    def test_physics_independent_of_frame_rate(self):
        def run(fps):
            b = Bat()
            b.x = b.y = 500
            for _ in range(fps // 2):
                b.update(1 / fps, (1, 0), (0, 0), OpenCave(), EventBus())
            return b.x
        self.assertAlmostEqual(run(30), run(120), delta=4)

    def test_knockback_not_cancelled_by_input(self):
        b = Bat()
        b.x = b.y = 500
        b.knockback(1, 0, 320)
        for _ in range(6):
            b.update(1 / 60, (-1, 0), (0, 0), OpenCave(), EventBus())
        self.assertGreater(b.x, 500 + 8)                     # el empujón sigue ganando un instante
        for _ in range(60):
            b.update(1 / 60, (0, 0), (0, 0), OpenCave(), EventBus())
        self.assertLess(math.hypot(b.kx, b.ky), 1)           # y decae solo

    def test_camera_keeps_up_at_full_speed(self):
        b, cam = Bat(), None
        b.x, b.y = 1200, 1000
        cam = Camera(b.x, b.y)
        for _ in range(120):
            b.update(1 / 60, (1, 0), (0, 0), OpenCave(), EventBus())
            cam.follow(b.x, b.y, 1 / 60, vx=b.vx, vy=b.vy)
        self.assertLess(abs(b.x - (cam.x + W / 2)), 15)      # sin retraso apreciable
        stop = b.x
        for _ in range(120):                                 # quieto: la cámara se centra sin oscilar
            b.update(1 / 60, (0, 0), (0, 0), OpenCave(), EventBus())
            cam.follow(b.x, b.y, 1 / 60, vx=b.vx, vy=b.vy)
        self.assertLess(abs(b.x - (cam.x + W / 2)), 1.5)
        self.assertGreater(stop, 1200)

    def test_shake_is_small_and_soft(self):
        s = PlayScene(self.game)
        s.shake = .4
        screen = pygame.display.get_surface()
        s.state = 'play'
        s.draw(screen)                                       # no debe lanzar y la amplitud máx. es 3 px
        self.assertLessEqual(3 * min(1, s.shake / .3), 3)

    # ------------------------------------------------------------ visibilidad
    def _lum(self, surf, cx, cy, r0, r1):
        tot = n = 0
        for a in range(0, 360, 10):
            for r in range(r0, r1, 10):
                x, y = int(cx + math.cos(math.radians(a)) * r), int(cy + math.sin(math.radians(a)) * r)
                if 0 <= x < W and 0 <= y < H:
                    c = surf.get_at((x, y))
                    tot += (c.r + c.g + c.b) / 3
                    n += 1
        return tot / n

    def test_floor_and_wall_contrast(self):
        cave = self.scene.cave
        fl = wl = nf = nw = 0
        for ty in range(2, cave.h - 2, 2):
            for tx in range(2, cave.w - 2, 2):
                c = cave.bg.get_at((tx * TILE + 16, ty * TILE + 16))
                v = (c.r + c.g + c.b) / 3
                if cave.g[ty][tx]:
                    wl, nw = wl + v, nw + 1
                else:
                    fl, nf = fl + v, nf + 1
        self.assertGreater(fl / nf, 3 * wl / nw)             # suelo claramente más claro que la roca

    def test_landmarks_exist(self):
        cave = self.scene.cave
        self.assertGreaterEqual(len(cave.crystals), 40)
        self.assertGreaterEqual(len(cave.fungi), 20)

    def test_brightness_levels_and_readable_light(self):
        s = PlayScene(self.game)
        s.spawn_t = 999
        s.enemies, s.pups = [], []
        b, cave = s.bat, s.cave
        for tx, ty in cave.open:                             # un hueco amplio y despejado
            if math.dist((tx * TILE, ty * TILE), NEST) > 450 and all(
                    not cave.solid(tx + i, ty + j) for i in range(-4, 5) for j in range(-4, 5)):
                b.x, b.y = tx * TILE + 16, ty * TILE + 16
                break
        else:
            self.skipTest("sin hueco amplio")
        s.camera.follow(b.x, b.y, 1, snap=True)
        screen = pygame.display.get_surface()
        vals = []
        for lv in range(3):
            self.game.brightness = lv
            s.draw(screen)
            cx, cy = s.camera.apply(b.x, b.y)
            vals.append(self._lum(s.canvas, cx, cy, 60, 130))      # dentro del hueco despejado (±4 tiles)
        self.game.brightness = DEFAULT_BRIGHTNESS
        # (cerca del nido o de cristales la luz puede saturar y dos niveles empatar, por eso <=)
        self.assertLessEqual(vals[0], vals[1])
        self.assertLessEqual(vals[1], vals[2])
        self.assertLess(vals[0], vals[2])
        self.assertGreater(vals[DEFAULT_BRIGHTNESS], 50)     # a 60-130 px del murciélago se distingue bien el suelo

    def test_visited_tiles_are_remembered(self):
        s = PlayScene(self.game)
        s.cave.mark_circle(s.bat.x, s.bat.y, TILE * 3, mem=True)
        tx, ty = int(s.bat.x // TILE), int(s.bat.y // TILE)
        self.assertEqual(s.cave.mem.get_at((tx, ty)).a, MEMORY_ALPHA)
        s.cave.mark_circle(s.bat.x + 900, s.bat.y, TILE * 3)             # solo minimapa (p. ej. sonar)
        self.assertEqual(s.cave.mem.get_at((int((s.bat.x + 900) // TILE), ty)).a, 0)

    def test_brightness_key_cycles(self):
        s = PlayScene(self.game)
        start = self.game.brightness
        ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b)
        s.handle(ev)
        self.assertEqual(self.game.brightness, (start + 1) % len(BRIGHTNESS_LEVELS))
        self.assertGreater(s.toast_t, 0)
        for _ in range(len(BRIGHTNESS_LEVELS) - 1):
            s.handle(ev)
        self.assertEqual(self.game.brightness, start)

    def test_run_frames(self):
        s = PlayScene(self.game)
        s.bat.try_sonar(s.diff.sonar_cd, s.bus)
        screen = pygame.display.get_surface()
        for _ in range(180):
            s.update(1 / 60)
            s.draw(screen)
        self.assertEqual(s.state, 'play')


if __name__ == "__main__":
    unittest.main()
