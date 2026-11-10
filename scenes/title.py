"""Portada con menú: Jugar / Instrucciones / Récords. El fondo son las cuevas reales del juego (title_cave.py)."""
import math

import pygame

import ui
from scenes import Scene
from settings import IS_WEB, W, H

_LOGO = {}


def _logo_parts():
    if not _LOGO:
        big = ui.F_XL
        word = big.render('BATLING', True, (255, 255, 255))
        grad = pygame.Surface(word.get_size())
        for y in range(word.get_height()):                    # relleno degradado: lila claro -> dorado del amanecer
            f = y / word.get_height()
            col = (int(235 + 20 * f), int(225 - 40 * f), int(255 - 150 * f))
            grad.fill(col, (0, y, word.get_width(), 1))
        word = word.copy()
        word.blit(grad, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        _LOGO['word'] = word
        _LOGO['shadow'] = big.render('BATLING', True, (30, 10, 60))
        _LOGO['glow'] = ui.make_glow(big, 'BATLING', (150, 90, 255), blur=6, pad=40)
        sub = ui.F_L.render('R E S C U E', True, (255, 200, 130))
        _LOGO['sub'] = sub
        _LOGO['sub_glow'] = ui.make_glow(ui.F_L, 'R E S C U E', (255, 120, 60), blur=5, pad=30)
    return _LOGO


LOGO_W = 390                                                  # ancho del logo en la portada
LOGO_CY = 214                                                 # centro vertical del logo


def draw_text_logo(s, t, cy=86):
    """Respaldo por código si falta assets/logo.png."""
    L = _logo_parts()
    pulse = .55 + .45 * math.sin(t * 2.2)
    cx = W // 2
    L['glow'].set_alpha(int(120 + 110 * pulse))
    s.blit(L['glow'], L['glow'].get_rect(center=(cx, cy)))
    s.blit(L['shadow'], L['shadow'].get_rect(center=(cx + 4, cy + 6)))
    s.blit(L['word'], L['word'].get_rect(center=(cx, cy)))
    L['sub_glow'].set_alpha(int(110 + 80 * pulse))
    s.blit(L['sub_glow'], L['sub_glow'].get_rect(center=(cx, cy + 74)))
    s.blit(L['sub'], L['sub'].get_rect(center=(cx, cy + 74)))


LOGO_BOB = 5                                                  # píxeles que sube y baja el logo
LOGO_BOB_T = 3.2                                              # segundos por vuelta (sube y baja)
_SUB = 4                                                      # posiciones intermedias entre píxel y píxel
_LOGO_FRAMES = {}


def _shifted(img, f):
    """El logo corrido f píxeles hacia abajo (0 <= f < 1), con suavizado: así el movimiento no da saltitos."""
    w, h = img.get_size()
    big = pygame.Surface((w, (h + 1) * _SUB), pygame.SRCALPHA)
    big.blit(pygame.transform.scale(img, (w, h * _SUB)), (0, int(f * _SUB)))
    return pygame.transform.smoothscale(big, (w, h + 1))


def draw_logo(s, t, cy=LOGO_CY, width=LOGO_W):
    """Logo oficial de BATling Rescue sobre la cueva: flota despacito de arriba hacia abajo."""
    img = ui.logo(width)
    if img is None:
        draw_text_logo(s, t)
        return False
    frames = _LOGO_FRAMES.get(width)
    if frames is None:                                        # se calculan una sola vez
        frames = _LOGO_FRAMES[width] = [_shifted(img, k / _SUB) for k in range(_SUB)]
    y = cy - img.get_height() / 2 + LOGO_BOB * math.sin(t * math.tau / LOGO_BOB_T)
    base = math.floor(y)
    s.blit(frames[min(_SUB - 1, int((y - base) * _SUB))], (W // 2 - img.get_width() // 2, base))
    return True


_SHADE = {}


def _text_shade(w, h):
    """Penumbra suave detrás del lema para que se lea sobre la cueva."""
    k = (w, h)
    if k not in _SHADE:
        sh = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(h // 2, 0, -1):
            a = int(150 * (1 - i / (h / 2)) ** .8)
            pygame.draw.ellipse(sh, (0, 0, 0, a), (w / 2 - i * w / h, h / 2 - i, 2 * i * w / h, 2 * i))
        _SHADE[k] = sh
    return _SHADE[k]


def draw_cover(s, t, cover, tagline=True):
    """Portada completa (también se exporta como imagen con tools/make_cover.py)."""
    cover.draw(s, t)
    has_logo = draw_logo(s, t)
    if tagline:
        y = LOGO_CY + 212 if has_logo else 196
        sh = _text_shade(560, 90)
        s.blit(sh, (W // 2 - 280, y - 33))
        ui.text(s, ui.F_S, 'Una madre. Diez crías. Una sola noche.', W // 2, y, (255, 236, 210), True)
        ui.text(s, ui.F_XS, '¿El amor puede más que el miedo?', W // 2, y + 24, (210, 190, 245), True)


# Fondo de la portada al ritmo del Can-Can: (segundo de la canción, nivel cuya cueva se ve).
# Intro lenta -> Galerías de los Hongos; cuando la canción se pone rápida -> Lago Negro;
# después del cambio de sección -> Mina Vieja; al repetirse la canción vuelve a empezar.
SONG_SCENES = ((0.0, 1), (10.6, 2), (64.1, 3))


def scene_for(pos):
    lv = 1
    for start, level in SONG_SCENES:
        if pos >= start:
            lv = level
    return lv


def title_cave(game):
    """Las cuevas de la portada (niveles 1, 2 y 3) se generan una sola vez por partida (siempre las mismas)."""
    cv = getattr(game, 'title_cave', None)
    if cv is None:
        from title_cave import TitleBackdrop
        cv = game.title_cave = TitleBackdrop()
    return cv


class TitleScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.main = ['Jugar', 'Instrucciones', 'Récords']               # (sin «Salir»: Esc o cerrar la ventana)
        n = len(self.main)
        self.menu = ui.Menu(self.main, W // 2, 566, gap=236 if n <= 3 else 226, w=220 if n <= 3 else 208, h=44,
                            horizontal=True)
        self.t = 0.0
        self.cover = title_cave(game)
        self.dt = 1 / 60
        self.panel = pygame.Surface((W, 92), pygame.SRCALPHA)
        for y in range(92):
            self.panel.fill((0, 0, 0, int(200 * (y / 92) ** .7)), (0, y, W, 1))

    def enter(self):
        self.game.sounds.stop(keep_song=True)
        self.game.sounds.ambient(.18, 'amb_fungi')       # (AMBIENT_MULT en sound.py lo baja un poco más)
        from sound import TITLE_SONG_VOL
        self.game.sounds.menu_music(TITLE_SONG_VOL)                     # Can-Can bajito (solo en el menú)
        pos = self.game.sounds.song_pos()
        self.cover.set_level(scene_for(pos) if pos is not None else 1, instant=True)

    def handle(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            if not IS_WEB:
                self.game.running = False
            return
        choice = self.menu.handle(ev, self.game.sounds)
        if choice == 0:
            self.game.start_story()
        elif choice == 1:
            self.game.goto('instructions')
        elif choice == 2:
            self.game.goto('records')

    def update(self, dt):
        self.t += dt
        self.dt = dt
        pos = self.game.sounds.song_pos()                               # la cueva cambia con la canción
        if pos is not None:
            self.cover.set_level(scene_for(pos))
        self.cover.update(dt)

    def draw(self, screen):
        draw_cover(screen, self.cover.t, self.cover)
        screen.blit(self.panel, (0, H - 92))
        self.menu.draw(screen, self.dt)
        ui.text(screen, ui.F_XS, '← → Elegir        Enter → Aceptar', W // 2, H - 14, (170, 155, 200), True)
