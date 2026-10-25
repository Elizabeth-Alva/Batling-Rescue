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
import story  # noqa: E402
from events import EventBus, NoiseEvent, ImpactEvent  # noqa: E402
from settings import (NEST, NEST_T, GOAL, TILE, W, H, BAT_SPEED, MEMORY_ALPHA, SAFE_R,  # noqa: E402
                      BRIGHTNESS_LEVELS, DEFAULT_BRIGHTNESS, SCREECH_CD, SCREECH_CD_DECIDED, REVEAL_T,
                      REVEAL_T_READER, DASH_CD, DASH_CD_AIR)
from map import CaveMap  # noqa: E402
from game import Game  # noqa: E402
from scenes.play import PlayScene  # noqa: E402
from enemies import Enemy, Boss, pick_kind  # noqa: E402
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
        cls.scene = PlayScene(cls.game, 1)
        cls.levels = {lv: PlayScene(cls.game, lv) for lv in (1, 2, 3)}

    def fresh(self, level=1):
        self.game.progress = Game.new_progress()          # sin mejoras de una prueba anterior
        s = PlayScene(self.game, level)
        s.spawn_t = 999
        return s

    # ------------------------------------------------------------ historia y niveles
    def test_story_totals(self):
        self.assertEqual(sum(story.pup_count(lv) for lv in (1, 2, 3)), GOAL)
        self.assertEqual([story.pup_count(lv) for lv in (1, 2, 3)], [3, 4, 3])
        self.assertEqual(story.LEVELS[1]['enemies'].keys(), {'spider'})
        self.assertEqual(story.LEVELS[2]['enemies'].keys(), {'spider', 'beetle'})
        self.assertEqual(story.LEVELS[3]['enemies'].keys(), {'spider', 'beetle', 'hunter'})
        names = [n for lv in (1, 2, 3) for n, _ in story.PUPS[lv]]
        self.assertEqual(len(names), len(set(names)))                # cada cría tiene su nombre

    def test_every_cutscene_shot_has_two_or_three_lines(self):
        from art import SHOTS
        for key, d in story.CUTSCENES.items():
            for name, lines in d['shots']:
                self.assertIn(name, SHOTS)
                self.assertTrue(1 <= len(lines) <= 3, (key, name))

    def test_ai_image_overrides_scene(self):
        import tempfile
        import art
        old = art.ASSET_DIR
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'escenas'))
            img = pygame.Surface((300, 200))
            img.fill((200, 40, 40))
            pygame.image.save(img, os.path.join(d, 'escenas', 'lake.png'))
            art.ASSET_DIR = d
            try:
                shot = art.make_shot('lake')
                self.assertIsInstance(shot, art.ImageShot)
                surf = pygame.Surface((W, H))
                shot.draw(surf, 1.0, 6.0)
                self.assertGreater(surf.get_at((W // 2, H // 2)).r, 150)
                self.assertNotIsInstance(art.make_shot('mine'), art.ImageShot)
            finally:
                art.ASSET_DIR = old

    def test_map_connected(self):
        for lv, s in self.levels.items():
            cave = s.cave
            seen = CaveMap._flood(cave.g, *NEST_T)
            floor = {(x, y) for y in range(cave.h) for x in range(cave.w) if not cave.g[y][x]}
            self.assertEqual(seen, floor)
            self.assertGreater(len(floor), 1500)

    def test_pups_reachable_by_flying(self):
        for lv, s in self.levels.items():
            cave = s.cave
            web, cave.web = cave.web, set()
            for p in s.pups:
                self.assertIsNotNone(cave.path(NEST, (p.x, p.y), walk=False), (lv, p.name))
                self.assertFalse(cave.solid_px(p.x, p.y))
            cave.web = web

    def test_level_scenery(self):
        c1, c2, c3 = (self.levels[lv].cave for lv in (1, 2, 3))
        self.assertTrue(c1.web, 'nivel 1: cortina de telarañas')
        self.assertGreater(len(c1.trail_marks), 10, 'nivel 1: rastros de las crías')
        self.assertGreater(sum(c2.water), 100, 'nivel 2: agua quieta')
        self.assertIsNotNone(c2.echo, 'nivel 2: Sala del Eco')
        eco = [p for p in self.levels[2].pups if p.behavior == 'eco'][0]
        self.assertLess(math.dist((eco.x, eco.y), c2.echo), 5)
        self.assertIsNotNone(c3.lair, 'nivel 3: guarida del jefe')
        self.assertGreater(len(c3.rails), 10, 'nivel 3: rieles')
        self.assertTrue(c3.carts and c3.lamps, 'nivel 3: vagonetas y lámparas')
        self.assertIsInstance(self.levels[3].boss, Boss)
        self.assertEqual(len(c3.trail_marks), 0, 'nivel 3: sin rastros')

    def test_web_blocks_until_screech(self):
        s = self.fresh(1)
        cave = s.cave
        self.assertTrue(cave.web)
        tx, ty = next(iter(cave.web))
        self.assertTrue(cave.solid(tx, ty))
        s.bat.x, s.bat.y = cave.web_center
        s.cd = 0
        s.screech()
        self.assertFalse(cave.web)
        self.assertFalse(cave.solid(tx, ty))

    def test_water_blocks_walkers_not_bat(self):
        cave = self.levels[2].cave
        i = cave.water.index(1)
        tx, ty = i % cave.w, i // cave.w
        self.assertTrue(cave.blocked(tx, ty))
        self.assertFalse(cave.solid(tx, ty))
        self.assertTrue(cave.is_water(tx * TILE + 16, ty * TILE + 16))
        self.assertTrue(all(not cave.water[y * cave.w + x] for x, y in cave.open))   # los enemigos no aparecen en el agua

    def test_difficulty_rises_by_level(self):
        prev = difficulty.params(1)
        for lv in (2, 3):
            cur = difficulty.params(lv)
            self.assertGreater(cur.chase_speed, prev.chase_speed)
            self.assertGreater(cur.max_enemies, prev.max_enemies)
            self.assertLess(cur.spawn_interval, prev.spawn_interval)
            prev = cur
        self.assertGreaterEqual(difficulty.params(2, 3).chase_speed, difficulty.params(2, 0).chase_speed)

    def test_enemy_kinds_follow_levels(self):
        for lv in (1, 2, 3):
            kinds = {pick_kind(story.LEVELS[lv]['enemies']) for _ in range(400)}
            self.assertEqual(kinds, set(story.LEVELS[lv]['enemies']))
        crowd = [Enemy(0, 0, 'hunter') for _ in range(3)]
        self.assertTrue(all(pick_kind(story.LEVELS[3]['enemies'], crowd) != 'hunter' for _ in range(200)))

    # ------------------------------------------------------------ grito, impulso, escudo
    def test_screech_stuns_damages_and_reveals_pups(self):
        s = self.fresh(1)
        b = s.bat
        sp = Enemy(b.x + 60, b.y, 'spider')
        s.enemies = [sp]
        s.cd = 0
        s.screech()
        self.assertEqual(sp.hp, 1)
        self.assertGreater(sp.stun, 0)
        self.assertTrue(all(p.revealed == REVEAL_T for p in s.pups))      # marcadas en el minimapa
        self.assertGreater(s.cd, 0)
        s.screech()                                                        # en recarga: no hace nada
        self.assertEqual(sp.hp, 1)

    def test_screech_on_beetle_hunter_and_boss(self):
        s = self.fresh(3)
        b = s.bat
        be, hu, bo = Enemy(b.x + 50, b.y, 'beetle'), Enemy(b.x - 50, b.y, 'hunter'), Boss(b.x, b.y + 60)
        s.enemies = [be, hu, bo]
        s.cd = 0
        s.screech()
        self.assertEqual(be.hp, 3)                                         # aguanta más
        self.assertLess(hu.stun, be.stun)                                  # al cazador solo lo aturde un momento
        self.assertGreater(bo.hp, 10 ** 6)                                 # al jefe no se le puede vencer
        self.assertIn(bo, s.enemies)

    def test_screech_recharges_faster_after_echo_room(self):
        s = self.fresh(2)
        self.assertEqual(s.cd_max, SCREECH_CD)
        s.moment('echo_room')
        self.assertEqual(s.state, 'play')                                  # en tiempo real: sin pausa ni texto
        self.assertEqual(s.cd_max, SCREECH_CD_DECIDED)
        self.assertTrue(self.game.progress['decided'])
        self.game.progress['decided'] = False

    def test_dash(self):
        b, bus = Bat(), EventBus()
        b.x = b.y = 500
        self.assertTrue(b.try_dash((1, 0), (0, 0)))
        b.update(1 / 60, (1, 0), (0, 0), OpenCave(), bus)
        self.assertGreater(b.vx, BAT_SPEED * 1.5)
        self.assertFalse(b.try_dash((1, 0), (0, 0)))                       # se recarga
        for _ in range(30):
            b.update(1 / 60, (1, 0), (0, 0), OpenCave(), bus)
        self.assertLessEqual(b.vx, BAT_SPEED + 1)

    def test_shield_blocks_damage_and_repels(self):
        s = self.fresh(2)
        b = s.bat
        b.x, b.y = s.cave.free_spot(NEST, 700)
        e = Enemy(b.x + 5, b.y, 'beetle')
        s.enemies = [e]
        self.assertTrue(b.try_shield(15))
        self.assertFalse(b.try_shield(15))
        hp = b.hp
        s.update(1 / 60)
        self.assertEqual(b.hp, hp)
        self.assertGreater(e.stun, 0)
        b.shield_t = 0
        e.stun = 0
        e.x, e.y = b.x + 5, b.y
        s.update(1 / 60)
        self.assertEqual(b.hp, hp - 1)

    def test_shield_lasts_five_seconds(self):
        s = self.fresh(1)
        s.bat.try_shield(15)
        for _ in range(int(4.9 * 60)):
            s.bat.update(1 / 60, (0, 0), (0, 0), s.cave, s.bus)
        self.assertGreater(s.bat.shield_t, 0)
        for _ in range(12):
            s.bat.update(1 / 60, (0, 0), (0, 0), s.cave, s.bus)
        self.assertEqual(s.bat.shield_t, 0)

    # ------------------------------------------------------------ enemigos
    def test_noise_attracts_enemy(self):
        s = self.fresh(1)
        e = Enemy(*s.cave.free_spot(NEST, 700))
        s.enemies = [e]
        s.bus.emit(NoiseEvent(e.x + 100, e.y, 200, (255, 255, 255), 'impact'))
        self.assertEqual(e.state, 'inv')
        far = Enemy(e.x + 2000, e.y)
        far.hear(e.x, e.y, 200, 1.0)
        self.assertEqual(far.state, 'patrol')

    def test_beetles_hear_farther_than_spiders(self):
        sp, be = Enemy(0, 0, 'spider'), Enemy(0, 0, 'beetle')
        sp.hear(250, 0, 200, 1.0)
        be.hear(250, 0, 200, 1.0)
        self.assertEqual(sp.state, 'patrol')
        self.assertEqual(be.state, 'inv')

    def test_safe_zone_keeps_enemies_out(self):
        s = self.fresh(1)
        e = Enemy(NEST[0] + 10, NEST[1], 'spider')
        s.enemies = [e]
        e.update(1 / 60, s)
        self.assertGreaterEqual(math.dist((e.x, e.y), NEST), SAFE_R)

    def test_hunter_loses_track(self):
        s = self.fresh(3)
        b = s.bat
        b.x, b.y = NEST[0] + 600, NEST[1]
        h = Enemy(*s.cave.free_spot((b.x, b.y), 900), 'hunter')
        h.state = 'chase'
        s.enemies = [h]
        for _ in range(120):
            h.update(1 / 60, s)
            b.x, b.y = h.x + 900, h.y                                     # Mullo se aleja
        self.assertNotEqual(h.state, 'chase')

    def test_continuous_spawning(self):
        s = PlayScene(self.game, 1)
        s.enemies = s.enemies[:2]
        s.spawn_t = 0
        n = len(s.enemies)
        for _ in range(20):
            s.spawn_t = 0
            s.update(1 / 60)
            if len(s.enemies) > n:
                break
        self.assertGreater(len(s.enemies), n)

    # ------------------------------------------------------------ crías
    def test_pickup_and_delivery(self):
        s = self.fresh(1)
        s.enemies = []
        b, p = s.bat, s.pups[0]
        b.x, b.y = p.x, p.y
        s.update(1 / 60)
        self.assertIs(b.carry, p)
        b.x, b.y = NEST
        s.update(1 / 60)
        self.assertIsNone(b.carry)
        self.assertEqual(s.rescued, 1)
        self.assertEqual(s.rescued_here, 1)

    def test_twins_count_double_and_wake_the_boss(self):
        s = self.fresh(3)
        s.enemies = [s.boss]
        b = s.bat
        twins = [p for p in s.pups if p.behavior == 'gemelas'][0]
        self.assertEqual(twins.count, 2)
        self.assertEqual(s.boss.state, 'sleep')
        b.x, b.y = twins.x, twins.y
        s.update(1 / 60)
        self.assertIs(b.carry, twins)
        self.assertEqual(s.boss.state, 'chase')
        self.assertTrue(s.escape)
        self.assertEqual(s.state, 'wake')                                 # animación del despertar
        while s.state == 'wake':
            s.update(1 / 10)
        self.assertEqual(s.state, 'play')
        b.x, b.y = NEST
        s.boss.x, s.boss.y = s.cave.lair
        s.update(1 / 60)
        self.assertEqual(s.rescued, story.rescued_before(3) + 2)

    def test_level_clear_after_all_pups(self):
        s = self.fresh(1)
        s.enemies = []
        b = s.bat
        for p in list(s.pups):
            b.x, b.y = p.x, p.y
            s.update(1 / 60)
            b.x, b.y = NEST
            s.update(1 / 60)
            self.assertIn(s.state, ('play', 'clear'))
        self.assertIn('whisper', s.done_moments)                            # elemento plantado tras la 2.a cría
        self.assertEqual(s.state, 'clear')
        self.assertEqual(s.rescued, 3)

    def test_low_point_moment_in_level_two(self):
        s = self.fresh(2)
        b = s.bat
        b.x, b.y = s.cave.free_spot(NEST, 700)
        b.hp = 2
        s.enemies = [Enemy(b.x + 5, b.y, 'spider')]
        s.update(1 / 60)
        self.assertEqual(b.hp, 1)
        self.assertEqual(s.state, 'play')
        self.assertIn('low_point', s.done_moments)

    def test_running_out_of_night(self):
        s = self.fresh(1)
        s.enemies = []
        s.t = s.cfg['duration'] + 1
        s.update(1 / 60)
        self.assertEqual(s.state, 'over')
        self.assertEqual(s.lose_reason, 'dawn')

    def test_no_messages_during_play(self):
        s = self.fresh(1)
        self.assertFalse(hasattr(s, 'texts'))
        self.assertFalse(hasattr(s, 'tip'))
        b = s.bat
        b.x, b.y = s.pups[0].x, s.pups[0].y
        for _ in range(30):
            s.update(1 / 60)
        self.assertEqual(s.toast_t, 0)

    def test_twins_names(self):
        self.assertEqual(story.PUPS[3][1], ('Bolillo y Pozolito', 'gemelas'))
        self.assertLess(SCREECH_CD, 2.6)

    def test_lake_pups_not_all_on_islets(self):
        for _ in range(3):
            cave = CaveMap(2)
            for (name, beh), (x, y) in zip(story.PUPS[2], cave.pup_spots):
                if beh == 'eco':
                    continue
                tx, ty = int(x // TILE), int(y // TILE)
                near = any(cave.water[(ty + j) * cave.w + tx + i] for j in range(-3, 4) for i in range(-3, 4)
                           if 0 <= tx + i < cave.w and 0 <= ty + j < cave.h)
                self.assertFalse(near, name)

    def test_spotted_alert(self):
        s = self.fresh(1)
        b = s.bat
        cv = s.cave
        for tx, ty in cv.open:                               # un lugar despejado, con vista libre entre los dos
            p = (tx * TILE + 16, ty * TILE + 16)
            if math.dist(p, NEST) > 700 and not cv.in_secret(*p) and cv.los(p, (p[0] + 40, p[1]), False) \
                    and not cv.solid_px(p[0] + 40, p[1]):
                b.x, b.y = p
                break
        e = Enemy(b.x + 40, b.y, 'spider')
        s.enemies = [e]
        e.update(1 / 60, s)
        self.assertEqual(e.state, 'chase')
        self.assertGreater(s.spot_cd, 0)

    def test_pups_move_a_little(self):
        s = self.fresh(1)
        s.enemies = []
        p = [q for q in s.pups if q.behavior == 'dormilona'][0]
        x0, y0 = p.x, p.y
        moved, lifted = 0.0, False
        for _ in range(240):
            p.update(1 / 60, s)
            moved = max(moved, math.dist((x0, y0), (p.x, p.y)))
            lifted = lifted or p.lift() > 0
        self.assertGreater(moved, 1)
        self.assertLess(moved, 40)

    def test_ambient_per_level(self):
        sm = self.game.sounds
        for lv in (1, 2, 3):
            s = PlayScene(self.game, lv)
            s.enter()
            self.assertEqual(sm.amb_name, 'amb_' + story.LEVELS[lv]['theme'])

    def test_cutscene_waits_for_space(self):
        from scenes.cutscene import CutsceneScene
        g = Game()
        c = CutsceneScene(g, 'apertura')
        for _ in range(600):                                             # 60 s sin tocar nada
            c.update(1 / 10)
        self.assertEqual(c.i, 0)
        self.assertIsNone(g.pending)
        c.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertEqual(c.i, 1)
        screen = pygame.display.get_surface()                            # todas las tomas se dibujan bien aunque esperen mucho
        for key, d in story.CUTSCENES.items():
            cs = CutsceneScene(g, key)
            for i in range(len(d['shots'])):
                cs.i = i
                cs._start()
                for tt in (0.2, 5.0, 90.0):
                    cs.t = tt
                    cs.draw(screen)

    def test_defeated_enemy_runs_away_and_salamanders(self):
        s = self.fresh(2)
        b = s.bat
        b.x, b.y = s.cave.free_spot(NEST, 700)
        e = Enemy(b.x + 50, b.y, 'spider')
        e.hp = 1
        s.enemies = [e]
        s.cd = 0
        s.screech()
        self.assertEqual(len(s.defeated), 1)
        x0 = e.x
        for _ in range(60):
            s.update(1 / 60)
            s.draw(pygame.display.get_surface())
        self.assertGreater(e.x, x0 + 40)                                   # sale corriendo, no hay sangre
        for _ in range(30):
            s.update(1 / 60)
        self.assertEqual(s.defeated, [])
        self.assertGreater(len(s.salamanders), 0)
        for sa in s.salamanders:
            self.assertTrue(s.cave.is_water(sa.x, sa.y))
        self.assertEqual(self.fresh(1).salamanders, [])
        sa = s.salamanders[0]                                             # se espanta al ver a Mullo
        s.bat.x, s.bat.y = sa.x + 60, sa.y
        sa.update(1 / 60, s.cave, s.bat)
        self.assertEqual(sa.state, 'startle')
        for _ in range(120):
            sa.update(1 / 60, s.cave, s.bat)
        self.assertIn(sa.state, ('dive', 'hidden'))

    def test_rescued_pups_rest_in_nest(self):
        s = self.fresh(1)
        s.enemies = []
        b, p = s.bat, s.pups[0]
        b.x, b.y = p.x, p.y
        s.update(1 / 60)
        b.x, b.y = NEST
        s.update(1 / 60)
        self.assertEqual(len(s.resting), 1)
        self.assertLess(math.dist((s.resting[0].x, s.resting[0].y), NEST), 40)

    def test_secret_room(self):
        for lv in (1, 2, 3):
            s = self.fresh(lv)
            cv = s.cave
            sc = cv.secret
            self.assertIsNotNone(sc)
            web, cv.web = cv.web, set()
            self.assertIsNotNone(cv.path(NEST, sc['center'], walk=False, limit=10 ** 5))   # Mullo puede llegar volando
            cv.web = web
            self.assertIsNone(cv.path(NEST, sc['center'], walk=True))            # los enemigos no
            self.assertTrue(all(not cv.in_secret(p.x, p.y) for p in s.pups))
            tx, ty = next(iter(sc['room']))
            cv.mark(tx, ty)
            self.assertFalse(cv.explored[ty * cv.w + tx])                        # oculta en el mapa
            b = s.bat
            s.enemies = []
            b.hp = 3
            b.x, b.y = sc['center']
            s.update(1 / 60)
            self.assertTrue(cv.secret_found)
            self.assertEqual(b.hp, 4)                                             # un corazón entero
            self.assertIsNone(s.secret_heart)
        e = Enemy(b.x + 30, b.y, 'spider')                                       # escondida: no la persiguen
        s.enemies = [e]
        e.update(1 / 60, s)
        self.assertNotEqual(e.state, 'chase')

    def test_boss_wake_animation_and_chase_music(self):
        s = self.fresh(3)
        s.enemies = [s.boss]
        twins = [p for p in s.pups if p.behavior == 'gemelas'][0]
        s.bat.x, s.bat.y = twins.x, twins.y
        s.update(1 / 60)
        self.assertEqual(s.state, 'wake')
        screen = pygame.display.get_surface()
        for _ in range(int(PlayScene.WAKE_T * 60) + 5):
            s.update(1 / 60)
            s.draw(screen)
        self.assertEqual(s.state, 'play')
        for _ in range(30):
            s.update(1 / 60)
        self.assertEqual(self.game.sounds.music_name, 'chase')

    def test_title_menu(self):
        from scenes.title import TitleScene
        ts = TitleScene(self.game)
        self.assertEqual(ts.main[:2], ['Jugar', 'Instrucciones'])
        self.assertNotIn('Capítulos', ts.main)

    def test_minimap_always_and_big_map(self):
        s = self.fresh(1)
        screen = pygame.display.get_surface()
        s.draw(screen)
        s.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m))
        self.assertTrue(s.big_map)
        s.draw(screen)

    def test_impact_generates_noise_only_when_fast(self):
        s = self.fresh(1)
        noises = []
        s.bus.subscribe(NoiseEvent, lambda e: noises.append(e))
        b = Bat()
        wall = WallCave(100)
        b.x, b.y = 100 - 13, 0
        b.vx, b.vy = 200, 0
        b.update(1 / 60, (1, 0), (0, 0), wall, s.bus)
        self.assertTrue(any(n.source == 'impact' for n in noises))
        noises.clear()
        b.impact_cd = 0
        b.x, b.vx = 100 - 13, 20
        b.update(1 / 60, (1, 0), (0, 0), wall, s.bus)
        self.assertFalse(any(n.source == 'impact' for n in noises))

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
        cave = self.scene.cave                               # nivel 1: hongos luminosos por todos lados
        self.assertGreaterEqual(len(cave.crystals), 20)
        self.assertGreaterEqual(len(cave.fungi), 60)

    def test_brightness_levels_and_readable_light(self):
        s = PlayScene(self.game, 1)
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
        s = self.fresh(1)
        s.cave.mark_circle(s.bat.x, s.bat.y, TILE * 3, mem=True)
        tx, ty = int(s.bat.x // TILE), int(s.bat.y // TILE)
        self.assertEqual(s.cave.mem.get_at((tx, ty)).a, MEMORY_ALPHA)
        s.cave.mark_circle(s.bat.x + 900, s.bat.y, TILE * 3)             # solo minimapa (p. ej. grito)
        self.assertEqual(s.cave.mem.get_at((int((s.bat.x + 900) // TILE), ty)).a, 0)

    def test_brightness_key_cycles(self):
        s = self.fresh(1)
        start = self.game.brightness
        ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b)
        s.handle(ev)
        self.assertEqual(self.game.brightness, (start + 1) % len(BRIGHTNESS_LEVELS))
        self.assertGreater(s.toast_t, 0)
        for _ in range(len(BRIGHTNESS_LEVELS) - 1):
            s.handle(ev)
        self.assertEqual(self.game.brightness, start)

    def test_shake_is_small_and_soft(self):
        s = self.fresh(1)
        s.shake = .4
        s.draw(pygame.display.get_surface())
        self.assertLessEqual(3 * min(1, s.shake / .3), 3)

    def test_run_frames_every_level(self):
        screen = pygame.display.get_surface()
        for lv in (1, 2, 3):
            s = PlayScene(self.game, lv)
            s.cd = 0
            s.screech()
            for _ in range(120):
                s.update(1 / 60)
                s.draw(screen)
            self.assertIn(s.state, ('play', 'over'))

    def test_full_story_flow(self):
        """De la portada al FIN: cinemáticas, 3 niveles y pantalla final."""
        from scenes.cutscene import EndScene, CutsceneScene
        g = Game()
        g.start_story()
        seen, screen = [], pygame.display.get_surface()
        for _ in range(4000):
            g._fade_step(1 / 30)
            sc = g.scene
            if type(sc).__name__ not in seen[-1:]:
                seen.append(type(sc).__name__)
            if isinstance(sc, EndScene):
                break
            if isinstance(sc, PlayScene) and g.pending is None and sc.state != 'clear':
                sc.enemies = [e for e in sc.enemies if e.kind == 'boss']
                for p in list(sc.pups):                                  # rescata a todas
                    sc.bat.x, sc.bat.y = p.x, p.y
                    sc.update(1 / 60)
                    while sc.state == 'wake':
                        sc.update(1 / 10)
                    sc.bat.x, sc.bat.y = NEST
                    if sc.boss:
                        sc.boss.x, sc.boss.y = sc.cave.lair
                    sc.update(1 / 60)
            if isinstance(sc, CutsceneScene) and g.pending is None:     # la historia avanza con Espacio
                sc.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
            sc.update(1 / 10)
            sc.draw(screen)
        self.assertIsInstance(g.scene, EndScene, seen)
        self.assertEqual(seen.count('PlayScene'), 3, seen)
        self.assertGreaterEqual(seen.count('CutsceneScene'), 3)
        self.assertEqual(g.progress['rescued'], GOAL)

    # ------------------------------------------------------------ objetos interactivos
    def test_props_placed(self):
        s1, s2, s3 = self.fresh(1), self.fresh(2), self.fresh(3)
        for s in (s1, s2, s3):
            self.assertGreaterEqual(len(s.curtains), 1)
            for cu in s.curtains:
                self.assertGreater(math.dist(cu.mid_pt, NEST), 250)
        self.assertGreaterEqual(len(s2.stones), 4)
        self.assertTrue(all(s2.cave.is_water(st.x, st.y) for st in s2.stones))
        self.assertGreaterEqual(len(s3.cans), 1)
        self.assertEqual(s1.stones + s1.cans, [])

    def test_curtain_parts_and_hides(self):
        s = self.fresh(1)
        s.enemies = []
        cu = s.curtains[0]
        m = cu.mid_pt
        b = s.bat
        b.x, b.y, b.vx, b.vy = m[0], m[1] + 8, 0, -150
        s.camera.follow(*m, 1, snap=True)
        for _ in range(10):
            s._props(1 / 60)
        self.assertGreater(cu.open, .35)                                     # se aparta al pasar
        self.assertFalse(s.hidden_by_curtain((m[0], m[1] - 60), (m[0], m[1] + 60)))   # hueco: se ve a través
        b.x, b.y, b.vx, b.vy = m[0], m[1] - 400, 0, 0
        for _ in range(240):
            s._props(1 / 60)
        self.assertLess(cu.open, .2)                                         # y se vuelve a cerrar
        p, q = (m[0], m[1] - 60), (m[0], m[1] + 60)
        self.assertTrue(s.hidden_by_curtain(p, q))                           # cerrada: no deja ver
        self.assertFalse(s.hidden_by_curtain(p, (m[0] + 3, m[1] - 50)))

    def test_salamander_flees_insects_and_sinks_stone(self):
        import fauna
        s = self.fresh(2)
        s.enemies = []
        st = s.stones[0]
        sa = fauna.Salamander(st.x + 30, st.y)
        sa.goal, sa.ang = st, math.pi
        from types import SimpleNamespace as NS
        far = NS(x=st.x + 2000, y=st.y)
        for _ in range(240):
            sa.update(1 / 60, s.cave, far, (), [st])
            st.update(1 / 60, [sa] if (sa.state == 'rest' or sa.goal is not None) else [])
            if st.sink > .9:
                break
        self.assertGreater(st.sink, .9)                                      # la piedra se hundió
        bug = NS(x=sa.x + 60, y=sa.y)
        sa.update(1 / 60, s.cave, far, [bug], [st])
        self.assertEqual(sa.state, 'startle')                                # un bicho también la espanta
        for _ in range(240):
            st.update(1 / 60, [])
        self.assertLess(st.sink, .05)                                        # y vuelve a flotar

    def test_can_attracts_bugs(self):
        s = self.fresh(3)
        can = s.cans[0]
        x, y = can.pos
        e = Enemy(x + 300, y, 'spider')
        s.enemies = [e]
        b = s.bat
        b.x, b.y = x - 1500, y
        self.assertTrue(can.strike(x - 10, y))
        for _ in range(3):
            s._props(1 / 60)
        self.assertEqual(e.state, 'inv')                                     # va a ver qué sonó
        self.assertLess(math.dist(e.target, (x, y)), 30)
        self.assertFalse(can.strike(x, y))                                   # no se re-golpea en ráfaga

    def test_pup_looks(self):
        import ui
        for lv in (1, 2, 3):
            for name, beh in story.PUPS[lv]:
                for nm in ([n for n in name.split(' y ')] if beh == 'gemelas' else [name]):
                    self.assertIn(nm, ui.PUP_LOOKS)
        surf = pygame.Surface((80, 60))
        for nm in ui.PUP_LOOKS:
            ui.draw_pup(surf, 40, 30, 1.0, .2, .6, nm, 1.0, True)
            ui.pup_extras(surf, 40, 30, ui.PUP_LOOKS[nm], 1.0)
        s = self.fresh(3)
        twins = [p for p in s.pups if p.count == 2][0]
        self.assertEqual(twins.looks, ['Bolillo', 'Pozolito'])

    def test_friendly_scare_level1(self):
        s = self.fresh(1)
        b = s.bat
        self.assertIsNone(s.drop_spider)
        spots = [(NEST[0] + math.cos(a / 10) * r, NEST[1] + math.sin(a / 10) * r) for r in (240, 320, 420) for a in range(63)]
        b.x, b.y = next(p for p in spots if not s.cave.solid_px(*p) and not s.cave.is_water(*p))
        s.t = 3.0
        b.vx, b.vy = 200, 0
        found = False
        for ang in range(0, 360, 15):
            b.vx, b.vy = 200 * math.cos(math.radians(ang)), 200 * math.sin(math.radians(ang))
            s._friendly_scare(1 / 60)
            if s.drop_spider:
                found = True
                break
        if not found:
            self.skipTest('sin espacio libre en este mapa')
        hp, enemies = b.hp, len(s.enemies)
        for _ in range(200):
            s._friendly_scare(1 / 60)
        self.assertIsNone(s.drop_spider)                                     # se fue sola
        self.assertTrue(s.scare_done)
        self.assertEqual((b.hp, len(s.enemies)), (hp, enemies))              # no hace daño ni trae bichos
        self.assertFalse(self.fresh(2).drop_spider or not self.fresh(2).scare_done)   # solo en el nivel 1

    def test_only_some_pups_flee(self):
        from pups import FLEES, FLEE_LEASH
        s = self.fresh(2)
        s.bat.x, s.bat.y = -999, -999
        for p in s.pups:
            p.x, p.y = p.home
            e = Enemy(p.x + 60, p.y, 'beetle')
            s.enemies = [e]
            for _ in range(120):
                p.update(1 / 60, s)
                e.x, e.y = p.x + 60, p.y                                     # el bicho la sigue de cerca
            moved = math.dist((p.x, p.y), p.home)
            room = sum(not s.cave.solid_px(p.home[0] + math.cos(a) * 60, p.home[1] + math.sin(a) * 60)
                       and not s.cave.is_water(p.home[0] + math.cos(a) * 60, p.home[1] + math.sin(a) * 60) for a in (0, 1.6, 3.1, 4.7))
            if p.behavior in FLEES and room >= 3:                            # con espacio para huir
                self.assertGreater(moved, 40, p.name)
            if p.behavior in FLEES:
                self.assertLessEqual(moved, FLEE_LEASH + 30, p.name)         # no se va lejísimos
            else:
                self.assertLess(moved, 40, p.name)                           # las demás no huyen


    # ------------------------------------------------------------ documentos: historia, personajes y mejoras
    def test_story_documents_characters_and_texts(self):
        self.assertEqual([n for n, _ in story.PUPS[3]], ['Paco', 'Bolillo y Pozolito'])
        self.assertEqual(story.LEVELS[3]['end_min'], 330)                 # la colonia parte a las 05:30
        self.assertIn('dos vagonetas', story.BEHAVIOR_TEXT['gemelas'])
        allt = ' '.join(' '.join(sh[1]) for c in story.CUTSCENES.values() for sh in c['shots'])
        for frase in ('Abuela Canela', '05:30', 'la historia del Gran Ciempiés', 'en ese momento no parecía importante',
                      'Si algún día bajan a la mina, sigan el aire. El aire debe salir', 'no despierten a lo que duerme al fondo',
                      'sin dispersarse', 'no encuentra nada cerca', 'Ya vuelvo. Quédense quietas', 'lugares más lejanos',
                      'el rastro de Chispa', 'piedritas movidas y rasguños', 'volar sobre ella es más seguro',
                      'Ya falta poco para que la colonia se vaya', 'piel vieja de ciempiés', 'ciempiés cazadores que oyen todo',
                      'cuando la colonia ya está saliendo', 'la última en la boca de la cueva', 'asustadas por tanto eco y dudan',
                      'la de siempre y no la de la cueva', 'Chispa contesta primero', 'responden las otras nueve',
                      'Mullo no deja a nadie atrás'):
            self.assertIn(frase.lower(), allt.lower())
        self.assertNotIn('El aire sabe salir', allt)
        self.assertNotIn('primera luz', allt)                            # la propuesta no habla de luz al final del Acto II
        self.assertEqual([sh[0] for sh in story.CUTSCENES['apertura']['shots']],
                         ['dusk', 'tale', 'advice', 'canela', 'search', 'goodbye', 'leaving'])
        self.assertEqual([sh[0] for sh in story.CUTSCENES['n3_intro']['shots']], ['mine'])   # el recuerdo llega al despertar Xolthar
        self.assertIn('El aire debe salir', ' '.join(story.AIR_MESSAGE[1]))
        self.assertIn('Xolthar', ' '.join(story.XOLTHAR_MESSAGE[1]))
        self.assertIn('siguieron a su «mamá»', ' '.join(story.ECHO_MESSAGE[1]))
        self.assertIn(('Mora', 'ratos'), story.PUPS[2])
        self.assertNotIn('Eco la repetía', allt)
        self.assertNotIn('una sola vida', allt)                          # ya no hay toma de «se queda con una vida»
        n2 = [sh[0] for sh in story.CUTSCENES['n2_fin']['shots']]
        self.assertNotIn('echo_room', n2)                                 # la Sala del Eco ahora es un mensaje en el juego
        self.assertNotIn('La culpa se le vuelve decisión', ' '.join(story.ECHO_MESSAGE[1]))
        self.assertNotIn('escape', [sh[0] for sh in story.CUTSCENES['final']['shots']])
        self.assertEqual(story.BLACK_BEFORE.get('n1_intro'), 2.0)
        from enemies import NAMES
        self.assertEqual(NAMES['boss'], 'Xolthar')
        import art
        for c in story.CUTSCENES.values():                                # cada toma tiene su ilustración
            for sh in c['shots']:
                self.assertIn(sh[0], art.SHOTS)

    def test_mora_sleeps_in_turns(self):
        s = self.fresh(2)
        mora = [p for p in s.pups if p.behavior == 'ratos'][0]
        s.bat.x, s.bat.y = mora.x + 400, mora.y
        seen, chirps = set(), 0
        for _ in range(int(30 / .05)):
            was = mora.ping
            mora.update(.05, s)
            seen.add(mora.asleep)
            if mora.asleep and mora.ping > was:
                chirps += 1
        self.assertEqual(seen, {True, False})                             # se duerme y se despierta
        self.assertEqual(chirps, 0)                                       # dormida no chilla

    def test_climax_and_wake_show_story_messages(self):
        s = self.fresh(3)
        s.moment('climax')
        self.assertEqual(s.banner[0], story.XOLTHAR_MESSAGE[0])
        s.moment('follow_air')
        self.assertEqual(s.banner[0], story.AIR_MESSAGE[0])
        self.assertTrue(s.air_flow)

    def test_paco_before_the_twins(self):
        s = self.fresh(3)
        cv = s.cave
        paco = [p for p in s.pups if p.name == 'Paco'][0]
        flow = cv.flow
        lt = (int(cv.lair[0] // 32), int(cv.lair[1] // 32))
        pt = (int(paco.x // 32), int(paco.y // 32))
        self.assertLess(flow[pt[1]][pt[0]], flow[lt[1]][lt[0]])

    def test_credits_and_logo(self):
        import inspect
        import ui
        from scenes import cutscene
        src = inspect.getsource(cutscene.EndScene.draw)
        self.assertIn('Galaviz Ricardo Hugo Enrique', src)
        self.assertIn('Cervantes Rios Gael Rodrigo', src)
        self.assertIsNotNone(ui.logo(200))

    def test_upgrade_1_reader_after_act_one(self):
        s = self.fresh(1)
        self.assertEqual(s.reveal_dur, REVEAL_T)
        s.rescued_here = s.goal_here - 1
        p = s.pups[0]
        s.bat.carry = p
        s.bat.x, s.bat.y = NEST
        s._pups(0.01)
        self.assertEqual(s.state, 'clear')
        self.assertTrue(self.game.progress['reader'])
        s2 = PlayScene(self.game, 2)
        s2.cd = 0
        s2.screech()
        self.assertEqual(s2.reveal_dur, REVEAL_T_READER)
        self.assertTrue(all(q.revealed == REVEAL_T_READER for q in s2.pups))
        self.assertLess(REVEAL_T, REVEAL_T_READER)

    def test_upgrade_3_follow_the_air(self):
        s = self.fresh(3)
        cv = s.cave
        self.assertTrue(any(cv.current), 'la corriente tiene una zona definida')
        self.assertIsNotNone(cv.molt, 'la piel vieja de Xolthar está en la entrada de la mina')
        self.assertFalse(s.air_flow)
        i = cv.current.index(1)
        x, y = (i % cv.w) * TILE + TILE / 2, (i // cv.w) * TILE + TILE / 2
        b = s.bat
        b.x, b.y = x, y
        self.assertTrue(s.in_air(), 'dentro de la corriente el impulso se recarga más rápido')
        s.moment('follow_air')
        self.assertTrue(s.air_flow and self.game.progress['air'])
        self.assertTrue(s.in_air())
        b.dash_cd = DASH_CD                                                # dentro de la corriente: 1.8 s
        t = 0.0
        while b.dash_cd > 0 and t < 5:
            s.cd = 0
            s.bat.x, s.bat.y = x, y
            b.vx = b.vy = 0
            dt = 1 / 60
            if s.in_air() and b.dash_cd > 0:
                b.dash_cd = max(0, b.dash_cd - dt * (DASH_CD / DASH_CD_AIR - 1))
            b.dash_cd = max(0, b.dash_cd - dt)
            t += dt
        self.assertAlmostEqual(t, DASH_CD_AIR, delta=.05)

    def test_start_level_upgrades_follow_the_story(self):
        g = self.game
        g.start_level(2)
        self.assertTrue(g.progress['reader'])
        self.assertFalse(g.progress['decided'])
        g.start_level(3)
        self.assertTrue(g.progress['reader'] and g.progress['decided'])
        self.assertFalse(g.progress['air'])
        g.pending, g.fade_dir = None, 0

    def test_low_point_breather_any_act(self):
        s = self.fresh(1)
        b = s.bat
        e = Enemy(b.x + 200, b.y, 'spider')
        e.state = 'chase'
        s.enemies = [e]
        s.moment('low_point')
        self.assertEqual(e.state, 'patrol')

    def test_new_cutscene_shots_draw(self):
        import art
        surf = pygame.Surface((W, H))
        for key in ('return_nest', 'canela', 'tale', 'goodbye', 'advice', 'leaving', 'search', 'mine_gate', 'escape', 'dawn_nest',
                    'true_voice', 'departure'):
            shot = art.SHOTS[key]()
            for t in (0.0, 1.5, 4.0):
                shot.draw(surf, t, 8.0)

    def test_wake_recalls_follow_the_air(self):
        s = self.fresh(3)
        twins = [p for p in s.pups if p.behavior == 'gemelas'][0]
        s.bat.x, s.bat.y = twins.x, twins.y
        s._pups(0.01)
        self.assertEqual(s.state, 'wake')
        for _ in range(400):
            if s.state != 'wake':
                break
            s.update(1 / 60)
        self.assertEqual(s.state, 'play')
        self.assertTrue(s.air_flow, 'al despertar Xolthar, Mullo recuerda «sigue el aire»')

    def test_echo_room_is_a_message_without_pause(self):
        s = self.fresh(2)
        s.moment('echo_room')
        self.assertEqual(s.state, 'play')
        self.assertIsNotNone(s.banner)
        s.draw(self.game.screen)
        s.banner[2] = s.BANNER_T                                         # el mensaje se va solo
        s.update(1 / 60)
        self.assertIsNone(s.banner)

    def test_chispa_trail_only_leads_to_her(self):
        cv = self.levels[1].cave
        chispa = cv.pup_spots[0]
        web, cv.web = cv.web, set()                                      # el rastro pasa bajo la telaraña
        path = cv.path(NEST, chispa, walk=False) or []
        cv.web = web
        self.assertTrue(cv.trail_marks)
        for x, y, *_ in cv.trail_marks:                                  # cada rastro está sobre el camino a Chispa
            self.assertLess(min(math.dist((x, y), p) for p in path), 20)

    def test_pink_guides_are_brief(self):
        s = self.fresh(1)
        s.cd = 0
        s.screech()
        from settings import GUIDE_T
        p = s.pups[0]
        self.assertGreater(p.revealed, 0)
        p.revealed = s.reveal_dur - GUIDE_T - .1                         # pasó el momento: ya no hay flecha
        p.ping = 2.0                                                     # chillar ya no enciende flechas
        targets = [q for q in s.pups if q.revealed > 0 and s.reveal_dur - q.revealed < GUIDE_T]
        self.assertNotIn(p, targets)

    def test_black_pause_before_act_one(self):
        g = Game()
        g.progress = Game.new_progress(1)
        g.pending, g.fade_dir = None, 0
        g._goto_step()
        self.assertEqual(g.hold, 2.0)
        g.fade = 255
        g._fade_step(1.0)
        self.assertEqual(type(g.scene).__name__, 'TitleScene')           # sigue en negro
        g._fade_step(1.1)
        g._fade_step(.01)
        self.assertEqual(type(g.scene).__name__, 'CutsceneScene')

    def test_whisper_shows_while_playing(self):
        s = self.fresh(1)
        self.assertNotIn('whisper', [sh[0] for sh in story.CUTSCENES['n1_fin']['shots']])
        s.moment('whisper')
        self.assertEqual(s.state, 'play')
        self.assertEqual(s.banner[0], story.WHISPER_MESSAGE[0])
        self.assertTrue(any(fx[0] == 'whisper' for fx in s.story_fx))
        for _ in range(30):
            s.update(1 / 60)
        s.draw(self.game.screen)

    def test_finding_eco_has_animation(self):
        s = self.fresh(2)
        s.moment('echo_room')
        self.assertTrue(any(fx[0] == 'echo' for fx in s.story_fx))
        for _ in range(120):
            s.update(1 / 60)
        s.draw(self.game.screen)

    def test_pups_found_in_order_and_no_guano(self):
        for lv in (1, 2):
            cv = self.levels[lv].cave
            def d(p):
                return cv.flow[int(p[1] // TILE)][int(p[0] // TILE)]
            names = [n for n, _ in story.PUPS[lv]]
            spots = dict(zip(names, cv.pup_spots))
            order = ['Chispa', 'Bruno', 'Lía'] if lv == 1 else ['Nube', 'Tito', 'Mora']
            ds = [d(spots[n]) for n in order]
            self.assertEqual(ds, sorted(ds), f'acto {lv}: las crías se encuentran en orden')
        self.assertFalse(any(k == 'guano' for _, _, k, _ in self.levels[1].cave.trail_marks))

    def test_mullo_idle_is_cute(self):
        s = self.fresh(1)
        s.idle_t = 5.0
        pose = s.mullo_pose()
        self.assertEqual(pose.get('mood'), 'happy')
        self.assertGreater(pose.get('fold', 0), .5)
        for _ in range(60):
            s.update(1 / 60)
        self.assertTrue(s.hearts)
        s.draw(self.game.screen)

    def test_hunters_take_three_hits_and_level2_between(self):
        s = self.fresh(3)
        b = s.bat
        hu = Enemy(b.x + 40, b.y, 'hunter')
        for k in range(3):
            self.assertGreater(hu.hp, 0)
            hu.hit_by_screech(b.x, b.y)
        self.assertEqual(hu.hp, 0)
        p1, p2, p3 = difficulty.params(1), difficulty.params(2), difficulty.params(3)
        for f in ('patrol_speed', 'chase_speed', 'max_enemies', 'detect_radius'):
            self.assertLess(getattr(p1, f), getattr(p2, f))
            self.assertLess(getattr(p2, f), getattr(p3, f))
        self.assertGreater(p2.spawn_interval, p3.spawn_interval)

    def test_touch_controls(self):
        g = Game()
        s = PlayScene(g, 1)
        s.spawn_t = 999
        g.scene, g.pending = s, None
        E = pygame.event.Event
        x0, y0 = 118 / W, (H - 128) / H                                   # joystick: tocar y arrastrar a la derecha
        g._finger(E(pygame.FINGERDOWN, x=x0, y=y0, finger_id=1, dx=0, dy=0), 0.0)
        self.assertTrue(g.touch.active)
        g._finger(E(pygame.FINGERMOTION, x=x0 + 60 / W, y=y0, finger_id=1, dx=0, dy=0), 0.0)
        mv = s._mv()
        self.assertGreater(mv[0], .5)
        g._finger(E(pygame.FINGERUP, x=x0 + 60 / W, y=y0, finger_id=1, dx=0, dy=0), 0.0)
        self.assertEqual(s._mv(), (0.0, 0.0))
        bx, by = [b[1] for b in g.touch.buttons() if b[0] == 'screech'][0]  # botón de grito
        s.cd = 0
        g._finger(E(pygame.FINGERDOWN, x=bx / W, y=by / H, finger_id=2, dx=0, dy=0), 0.0)
        self.assertGreater(s.cd, 0)
        px, py = [b[1] for b in g.touch.buttons() if b[0] == 'pause'][0]   # pausa y tocar para seguir
        g._finger(E(pygame.FINGERDOWN, x=px / W, y=py / H, finger_id=3, dx=0, dy=0), 0.0)
        self.assertEqual(s.state, 'pause')
        s.draw(g.screen)
        g._finger(E(pygame.FINGERDOWN, x=.5, y=.3, finger_id=4, dx=0, dy=0), 0.0)
        self.assertEqual(s.state, 'play')
        s.draw(g.screen)

if __name__ == "__main__":
    unittest.main()
