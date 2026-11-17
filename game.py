"""Bucle principal y gestor de escenas con fundido entre ellas."""
import asyncio
import time
from collections import deque

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


def canvas_size(iw, ih, w=W, h=H):
    """Tamaño (en la página) del lienzo del juego: lo más grande que quepa en la ventana SIN deformarlo."""
    k = min(iw / w, ih / h)
    return max(1, int(w * k)), max(1, int(h * k))


def fit_canvas(canvas, iw, ih):
    """En el navegador: acomoda el lienzo a la ventana conservando la proporción 3:2.
    pygbag lo mide una sola vez al arrancar, cuando el lienzo aún mide 1x1, y lo deja CUADRADO; solo lo corrige
    si la ventana cambia de tamaño. En la app de Android (pantalla completa) eso no pasa nunca y el juego se
    veía aplastado. Aquí se revisa cada segundo (también sirve al girar el teléfono)."""
    if canvas is None:
        return False
    cw, ch = canvas_size(iw, ih)
    if canvas.style.width != f"{cw}px" or canvas.style.height != f"{ch}px":
        canvas.style.position = "absolute"
        canvas.style.left = canvas.style.right = canvas.style.top = canvas.style.bottom = "0"
        canvas.style.margin = "auto"
        canvas.style.width = f"{cw}px"
        canvas.style.height = f"{ch}px"
        return True
    return False


HEAVY_SCENES = ('play', 'cut', 'end')         # escenas que tardan en prepararse
HUSH_T = .3                                  # silencio antes de prepararlas (navegador)


class WebPacer:
    """Ritmo de cuadros en el navegador (y la app de Android).
    Allí el navegador da un turno cada 1/60 s, pero un cuadro del juego tarda 20-50 ms: unos cuadros salían a
    los 17 ms, otros a los 33, otros a los 50, y el movimiento se veía a tirones aunque el promedio fuera bueno.
    Aquí se elige un ritmo FIJO que el teléfono sí aguanta (60, 30 o 20 cuadros por segundo, según lo que
    tarde dibujar) y cada cuadro avanza exactamente ese tiempo: así todo se mueve parejo. Si el teléfono se
    alivia, vuelve a subir el ritmo."""
    RATES = (60, 30, 20)

    def __init__(self):
        self.level = 1                                # empieza a 30 (lo seguro); sube a 60 si sobra tiempo
        self.last = None
        self.cost = deque(maxlen=20)                  # lo que tardaron los últimos cuadros (actualizar + dibujar)
        self.t_start = 0.0
        self.since_change = 0

    @property
    def rate(self):
        return self.RATES[self.level]

    def next_frame(self, now):
        """dt del cuadro si ya toca dibujar; None si hay que esperar al siguiente turno del navegador."""
        if self.last is None:
            self.last = now
            self.t_start = now
            return 1 / self.rate
        period = 1 / self.rate
        el = now - self.last
        if el < period - .004:                         # (margen: los turnos del navegador no son exactos)
            return None
        steps = max(1, round(el / period))
        if steps > 3:                                 # se congeló (cambió de pestaña, cargó algo): no salta
            steps = 1
            self.last = now
        else:
            self.last += steps * period
            if now - self.last > period:              # se quedó atrás: se resincroniza
                self.last = now
        self.t_start = now
        return min(.1, steps * period)

    def frame_done(self, now):
        self.cost.append(now - self.t_start)
        self.since_change += 1
        if len(self.cost) < self.cost.maxlen or self.since_change < 60:
            return
        avg = sorted(self.cost)[len(self.cost) * 3 // 4]   # (el 75 %: ignora un cuadro raro)
        period = 1 / self.rate
        if avg > period * .9 and self.level < len(self.RATES) - 1:
            self.level += 1                           # no le alcanza: baja el ritmo
            self.since_change = 0
        elif self.level > 0 and avg < (1 / self.RATES[self.level - 1]) * .6:
            self.level -= 1                           # le sobra de verdad: sube el ritmo
            self.since_change = 0


def _smooth_dt(hist, raw, cap):
    """Paso de tiempo suavizado: el reloj del sistema da cuadros de 15, 17, 16, 18 ms... y ese vaivén se nota como
    tirones al mover la cámara. Se usa el promedio de los últimos cuadros (y un tope para cuando la ventana se
    congela un momento), así todo avanza parejo sin cambiar la velocidad del juego."""
    raw = min(raw, cap)
    if hist and raw > 2.5 * (sum(hist) / len(hist)):    # un cuadro muy lento (p. ej. al cargar): no contamina el promedio
        return raw
    hist.append(raw)
    return sum(hist) / len(hist)


class Game:
    @staticmethod
    def _open_window():
        """En la computadora pide sincronía vertical (vsync): cada cuadro sale justo cuando el monitor se refresca,
        sin cortes a media pantalla. Si la tarjeta de video no la acepta, abre la ventana normal."""
        if not IS_WEB:
            try:
                screen = pygame.display.set_mode((W, H), pygame.SCALED, vsync=1)
                return screen, bool(getattr(pygame.display, 'is_vsync', lambda: True)())
            except pygame.error:
                pass
        return pygame.display.set_mode((W, H)), False

    def __init__(self):
        self.screen, self.vsync = self._open_window()
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        ui.init_fonts()
        self._set_icon()
        self.screen.fill((4, 3, 10))                 # sintetizar los sonidos tarda un par de segundos
        logo = ui.logo(360)
        if logo is not None:
            self.screen.blit(logo, logo.get_rect(center=(W // 2, H // 2 - 30)))
            ui.text(self.screen, ui.F_XS, 'Cargando...', W // 2, H // 2 + 150, (150, 135, 180), True)
        else:
            ui.text(self.screen, ui.F_M, 'BATling Rescue', W // 2, H // 2 - 14, (210, 190, 255), True)
            ui.text(self.screen, ui.F_XS, 'Cargando...', W // 2, H // 2 + 20, (150, 135, 180), True)
        pygame.display.flip()
        self.sounds = SoundManager()
        self.backdrop = ui.Backdrop()
        self.running = True
        self.brightness = DEFAULT_BRIGHTNESS         # nivel de brillo (tecla B), se conserva entre partidas
        self.pending = None
        self.hold = 0.0                              # segundos en negro antes de mostrar la siguiente escena
        self._hushed = False                         # (ya se apagó el sonido para la escena que viene)
        self.fade, self.fade_dir = 255.0, -1        # 255 = negro total
        self.veil = pygame.Surface((W, H))
        self.progress = self.new_progress()
        from touch import TouchControls
        self.touch = TouchControls()                 # controles táctiles (se activan al primer toque)
        self._last_finger = -9.0
        self.scene = self._make(('title', {}))
        self.scene.enter()

    @staticmethod
    def _set_icon():
        """Ícono de la ventana: el logo del juego (si está assets/logo.png)."""
        img = ui.logo(64)
        if img is None or IS_WEB:
            return
        icon = pygame.Surface((64, 64), pygame.SRCALPHA)
        icon.blit(img, img.get_rect(center=(32, 32)))
        try:
            pygame.display.set_icon(icon)
        except pygame.error:
            pass

    # ------------------------------------------------------------ historia
    @staticmethod
    def new_progress(step=0):
        # mejoras de Mullo (una por acto, por la historia): reader (I), decided (II), air (III)
        # play_time: tiempo jugado (sin pausas ni cinemáticas, incluye los reintentos) -> récord de la historia
        # full_run: la partida empezó desde el prólogo (solo así cuenta para la tabla de la historia completa)
        return dict(step=step, reader=False, decided=False, air=False, retries=0, play_time=0.0, rescued=0,
                    full_run=False)

    def start_story(self):
        """Historia completa desde el prólogo."""
        self.progress = self.new_progress(0)
        self.progress['full_run'] = True
        self._goto_step()

    def start_level(self, level):
        """Empieza directo en un nivel (desde el menú de capítulos), con su cinemática de entrada."""
        from story import flow_index, rescued_before
        self.progress = self.new_progress(flow_index('play', level) - 1)
        self.progress['reader'] = level >= 2             # desde el acto II ya aprendió a leer la cueva
        self.progress['decided'] = level >= 3            # en el acto III Mullo ya usa el grito a propósito
        self.progress['rescued'] = rescued_before(level)
        self._goto_step()

    def quit(self):
        """Botón «Salir»: cierra el juego (en el navegador no se puede cerrar la pestaña)."""
        if not IS_WEB:
            self.running = False

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
        from scenes.records import RecordsScene
        if name == 'play':                           # generar la cueva tarda un instante
            self.screen.fill((0, 0, 0))
            ui.text(self.screen, ui.F_M, 'La cueva cambia cada noche...', W // 2, H // 2, (170, 150, 210), True)
            pygame.display.flip()
        return {'title': TitleScene, 'instructions': InstructionsScene, 'play': PlayScene,
                'cut': CutsceneScene, 'end': EndScene, 'records': RecordsScene}[name](self, **kw)

    def goto(self, name, **kw):
        if self.pending is None:
            self.pending, self.fade_dir = (name, kw), 1

    def _fade_step(self, dt):
        if self.fade_dir == 0:
            return
        self.fade = min(255, max(0, self.fade + self.fade_dir * dt * 1100))
        if self.fade_dir > 0 and self.fade >= 255:
            if self.pending[0] in HEAVY_SCENES and not self._hushed:
                # Antes de generar la cueva o preparar una cinemática se apaga el sonido y se espera un instante
                # en negro: en el navegador el sonido solo se rellena entre cuadro y cuadro, y si el juego se
                # queda pensando (generar un nivel tarda unos segundos) el navegador repite el último pedacito
                # de sonido una y otra vez. Así, lo que se repite es silencio.
                self.sounds.stop(now=True)
                self._hushed = True
                if IS_WEB:
                    self.hold = max(self.hold, HUSH_T)
            if self.hold > 0:                        # pantalla en negro un momento (antes del Acto I)
                self.hold -= dt
                return
            self.scene = self._make(self.pending)
            self._hushed = False
            self.scene.enter()
            self.pending, self.fade_dir = None, -1
        elif self.fade_dir < 0 and self.fade <= 0:
            self.fade_dir = 0

    def _portrait(self, now):
        """¿El navegador está en vertical? (se revisa cada segundo, y de paso se acomoda el lienzo)"""
        if now - getattr(self, '_orient_t', -9) > 1.0:
            self._orient_t = now
            try:
                import platform as _pf
                iw, ih = int(_pf.window.innerWidth), int(_pf.window.innerHeight)
                self._is_portrait = ih > iw
                fit_canvas(_pf.window.document.getElementById('canvas'), iw, ih)
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
        hist = deque(maxlen=8)
        cap_fps = 165 if self.vsync else FPS             # con vsync manda el monitor (60, 75, 144 Hz...); tope por seguridad
        pace = WebPacer() if IS_WEB else None
        while self.running:
            if pace is not None:                         # navegador: cuadros a ritmo PAREJO (ver WebPacer)
                dt = pace.next_frame(time.perf_counter())
                if dt is None:
                    await asyncio.sleep(0)               # aún no toca dibujar: se cede el turno al navegador
                    continue
            else:
                dt = _smooth_dt(hist, self.clock.tick(cap_fps) / 1000, .05)
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
            if pace is not None:
                pace.frame_done(time.perf_counter())
            await asyncio.sleep(0)               # cede el control al navegador (pygbag)
            if IS_WEB:                            # rendimiento visible en la consola del navegador
                frames += 1
                now = time.perf_counter()
                if now - t_log >= 3:                # cada 3 s de reloj real
                    _web_log(f"[perf] {frames / (now - t_log):.1f} fps (ritmo {pace.rate}) | update {t_upd / frames * 1000:.1f} ms"
                             f" | draw {t_drw / frames * 1000:.1f} ms")
                    frames, t_upd, t_drw, t_log = 0, 0.0, 0.0, now
