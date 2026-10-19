"""Bucle principal y gestor de escenas con fundido entre ellas."""
import asyncio
import time

import pygame

import ui
from settings import IS_WEB, W, H, FPS, TITLE, DEFAULT_BRIGHTNESS
from sound import SoundManager


def _web_log(msg):
    """Escribe en la consola del navegador (F12) cuando corre con pygbag."""
    try:
        import platform
        platform.window.console.log(msg)
    except Exception:
        print(msg)


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        ui.init_fonts()
        self.screen.fill((4, 3, 10))                 # sintetizar los sonidos tarda un par de segundos
        ui.text(self.screen, ui.F_M, 'BATling Rescue', W // 2, H // 2 - 14, (210, 190, 255), True)
        ui.text(self.screen, ui.F_XS, 'Cargando...', W // 2, H // 2 + 20, (150, 135, 180), True)
        pygame.display.flip()
        self.sounds = SoundManager()
        self.backdrop = ui.Backdrop()
        self.running = True
        self.brightness = DEFAULT_BRIGHTNESS         # nivel de brillo (tecla B), se conserva entre partidas
        self.pending = None
        self.hold = 0.0                              # segundos en negro antes de mostrar la siguiente escena
        self.fade, self.fade_dir = 255.0, -1        # 255 = negro total
        self.veil = pygame.Surface((W, H))
        self.progress = self.new_progress()
        from touch import TouchControls
        self.touch = TouchControls()                 # controles táctiles (se activan al primer toque)
        self._last_finger = -9.0
        self.scene = self._make(('title', {}))
        self.scene.enter()

    # ------------------------------------------------------------ historia
    @staticmethod
    def new_progress(step=0):
        # mejoras de Mullo (una por acto, por la historia): reader (I), decided (II), air (III)
        return dict(step=step, reader=False, decided=False, air=False, retries=0, play_time=0.0, rescued=0)

    def start_story(self):
        """Historia completa desde el prólogo."""
        self.progress = self.new_progress(0)
        self._goto_step()

    def start_level(self, level):
        """Empieza directo en un nivel (desde el menú de capítulos), con su cinemática de entrada."""
        from story import flow_index, rescued_before
        self.progress = self.new_progress(flow_index('play', level) - 1)
        self.progress['reader'] = level >= 2             # desde el acto II ya aprendió a leer la cueva
        self.progress['decided'] = level >= 3            # en el acto III Mullo ya usa el grito a propósito
        self.progress['rescued'] = rescued_before(level)
        self._goto_step()

    def retry_level(self, level):
        self.goto('play', level=level)

    def advance(self):
        if self.pending is not None:                 # ya hay una transición en curso
            return
        self.progress['step'] += 1
        self._goto_step()

    def _goto_step(self):
        from story import FLOW
        kind, key = FLOW[min(self.progress['step'], len(FLOW) - 1)]
        if kind == 'cut':
            from story import BLACK_BEFORE
            self.goto('cut', key=key)
            if self.pending and self.pending[0] == 'cut':
                self.hold = BLACK_BEFORE.get(key, 0.0)
        elif kind == 'play':
            self.goto('play', level=key)
        else:
            self.goto('end')

    def _make(self, pending):
        name, kw = pending
        from scenes.title import TitleScene
        from scenes.instructions import InstructionsScene
        from scenes.play import PlayScene
        from scenes.cutscene import CutsceneScene, EndScene
        if name == 'play':                           # generar la cueva tarda un instante
            self.screen.fill((0, 0, 0))
            ui.text(self.screen, ui.F_M, 'La cueva cambia cada noche...', W // 2, H // 2, (170, 150, 210), True)
            pygame.display.flip()
        return {'title': TitleScene, 'instructions': InstructionsScene, 'play': PlayScene,
                'cut': CutsceneScene, 'end': EndScene}[name](self, **kw)

    def goto(self, name, **kw):
        if self.pending is None:
            self.pending, self.fade_dir = (name, kw), 1

    def _fade_step(self, dt):
        if self.fade_dir == 0:
            return
        self.fade = min(255, max(0, self.fade + self.fade_dir * dt * 1100))
        if self.fade_dir > 0 and self.fade >= 255:
            if self.hold > 0:                        # pantalla en negro un momento (antes del Acto I)
                self.hold -= dt
                return
            self.scene = self._make(self.pending)
            self.scene.enter()
            self.pending, self.fade_dir = None, -1
        elif self.fade_dir < 0 and self.fade <= 0:
            self.fade_dir = 0

    def _portrait(self, now):
        """¿El navegador está en vertical? (se revisa cada segundo)"""
        if now - getattr(self, '_orient_t', -9) > 1.0:
            self._orient_t = now
            try:
                import platform as _pf
                self._is_portrait = int(_pf.window.innerHeight) > int(_pf.window.innerWidth)
            except Exception:
                self._is_portrait = False
        return self._is_portrait

    def _draw_rotate_hint(self):
        s = self.screen
        s.fill((6, 4, 14))
        t = time.perf_counter()
        cx, cy = W // 2, H // 2 - 40
        a = min(1.0, (t % 2.4) / 1.2) * 90                     # un teléfono que gira
        ph = pygame.Surface((90, 150), pygame.SRCALPHA)
        pygame.draw.rect(ph, (200, 160, 255), ph.get_rect(), 6, border_radius=14)
        pygame.draw.circle(ph, (200, 160, 255), (45, 136), 5)
        rot = pygame.transform.rotate(ph, -a)
        s.blit(rot, rot.get_rect(center=(cx, cy)))
        ui.text(s, ui.F_L, 'Gira tu teléfono', cx, cy + 140, (240, 232, 255), True)
        ui.text(s, ui.F_M, 'BATling Rescue se juega en horizontal', cx, cy + 200, (200, 190, 230), True)

    def _finger(self, ev, now):
        """Toques: el joystick y los botones van a la escena de juego; en menús y cinemáticas un toque es un clic."""
        name = self.touch.handle(ev)
        if IS_WEB and ev.type == pygame.FINGERUP:            # al primer toque: pantalla completa y horizontal
            self.touch.go_fullscreen()
        if self.pending is not None:
            return
        if hasattr(self.scene, 'on_touch'):
            self.scene.on_touch(ev, name)
        elif ev.type == pygame.FINGERDOWN:
            self._last_finger = now
            pos = (int(ev.x * W), int(ev.y * H))
            self.scene.handle(pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0)))
            self.scene.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
        if ev.type == pygame.FINGERDOWN:
            self._last_finger = now

    async def run(self):
        frames, t_upd, t_drw, t_log = 0, 0.0, 0.0, time.perf_counter()
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000, .1 if IS_WEB else .05)
            now = time.perf_counter()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                elif ev.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
                    self._finger(ev, now)
                elif ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION) and \
                        (getattr(ev, 'touch', False) or now - self._last_finger < .6):
                    continue                             # clic falso generado por un toque: ya se atendió
                elif self.pending is None:
                    self.scene.handle(ev)
            self.touch.update(dt)
            t0 = time.perf_counter()
            self.scene.update(dt)
            self._fade_step(dt)
            t1 = time.perf_counter()
            self.scene.draw(self.screen)
            t_upd, t_drw = t_upd + t1 - t0, t_drw + time.perf_counter() - t1
            if self.fade > 0:
                self.veil.set_alpha(int(self.fade))
                self.screen.blit(self.veil, (0, 0))
            if IS_WEB and self._portrait(now):                # teléfono vertical: pide girarlo
                self._draw_rotate_hint()
            pygame.display.flip()
            await asyncio.sleep(0)               # cede el control al navegador (pygbag)
            if IS_WEB:                            # rendimiento visible en la consola del navegador
                frames += 1
                now = time.perf_counter()
                if now - t_log >= 3:                # cada 3 s de reloj real
                    _web_log(f"[perf] {frames / (now - t_log):.1f} fps | update {t_upd / frames * 1000:.1f} ms | draw {t_drw / frames * 1000:.1f} ms")
                    frames, t_upd, t_drw, t_log = 0, 0.0, 0.0, now
