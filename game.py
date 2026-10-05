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
        self.sounds = SoundManager()
        self.backdrop = ui.Backdrop()
        self.running = True
        self.brightness = DEFAULT_BRIGHTNESS         # nivel de brillo (tecla B), se conserva entre partidas
        self.pending = None
        self.fade, self.fade_dir = 255.0, -1        # 255 = negro total
        self.veil = pygame.Surface((W, H))
        self.scene = self._make('title')
        self.scene.enter()

    def _make(self, name):
        from scenes.title import TitleScene
        from scenes.instructions import InstructionsScene
        from scenes.play import PlayScene
        if name == 'play':                           # generar la cueva tarda un instante
            self.screen.fill((0, 0, 0))
            ui.text(self.screen, ui.F_M, 'Generando la cueva...', W // 2, H // 2, (170, 150, 210), True)
            pygame.display.flip()
        return {'title': TitleScene, 'instructions': InstructionsScene, 'play': PlayScene}[name](self)

    def goto(self, name):
        if self.pending is None:
            self.pending, self.fade_dir = name, 1

    def _fade_step(self, dt):
        if self.fade_dir == 0:
            return
        self.fade = min(255, max(0, self.fade + self.fade_dir * dt * 1100))
        if self.fade_dir > 0 and self.fade >= 255:
            self.scene = self._make(self.pending)
            self.scene.enter()
            self.pending, self.fade_dir = None, -1
        elif self.fade_dir < 0 and self.fade <= 0:
            self.fade_dir = 0

    async def run(self):
        frames, t_upd, t_drw, t_log = 0, 0.0, 0.0, time.perf_counter()
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000, .1 if IS_WEB else .05)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                elif self.pending is None:
                    self.scene.handle(ev)
            t0 = time.perf_counter()
            self.scene.update(dt)
            self._fade_step(dt)
            t1 = time.perf_counter()
            self.scene.draw(self.screen)
            t_upd, t_drw = t_upd + t1 - t0, t_drw + time.perf_counter() - t1
            if self.fade > 0:
                self.veil.set_alpha(int(self.fade))
                self.screen.blit(self.veil, (0, 0))
            pygame.display.flip()
            await asyncio.sleep(0)               # cede el control al navegador (pygbag)
            if IS_WEB:                            # rendimiento visible en la consola del navegador
                frames += 1
                now = time.perf_counter()
                if now - t_log >= 3:                # cada 3 s de reloj real
                    _web_log(f"[perf] {frames / (now - t_log):.1f} fps | update {t_upd / frames * 1000:.1f} ms | draw {t_drw / frames * 1000:.1f} ms")
                    frames, t_upd, t_drw, t_log = 0, 0.0, 0.0, now
