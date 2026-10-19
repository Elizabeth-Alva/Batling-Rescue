"""Controles táctiles para jugar en el teléfono (o en una pantalla táctil).

Aparecen solos la primera vez que se toca la pantalla; con teclado y ratón el juego queda igual.
  Izquierda: joystick para volar (arrastra el dedo; el joystick aparece donde tocas).
  Derecha:   GRITO (grande), IMPULSO y ESCUDO.   Arriba: pausa y mapa.
Los toques llegan como FINGERDOWN / FINGERMOTION / FINGERUP con coordenadas normalizadas (0-1).
"""
import math

import pygame

from settings import W, H, DASH_CD

JOY_R = 66                      # radio del joystick
JOY_DEAD = .22                  # zona muerta (fracción del radio)


class TouchControls:
    def __init__(self):
        self.active = False                     # se activa con el primer toque
        self.joy_id = None                      # dedo que mueve el joystick
        self.joy_home = (118, H - 128)
        self.joy_c = self.joy_home
        self.joy_v = (0.0, 0.0)
        self.pressed = {}                       # botón -> tiempo de brillo al tocarlo
        self.t = 0.0

    @staticmethod
    def buttons():
        """(nombre, centro, radio, etiqueta)"""
        return [('screech', (W - 92, H - 112), 54, 'GRITO'),
                ('dash', (W - 214, H - 62), 40, 'IMPULSO'),
                ('shield', (W - 196, H - 178), 40, 'ESCUDO'),
                ('pause', (W // 2 + 146, 36), 22, 'II'),
                ('map', (W // 2 + 196, 36), 22, 'MAPA')]

    @staticmethod
    def pos(ev):
        return ev.x * W, ev.y * H

    def handle(self, ev):
        """Procesa un evento táctil. Devuelve el nombre del botón tocado (o None)."""
        if ev.type not in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            return None
        self.active = True
        x, y = self.pos(ev)
        if ev.type == pygame.FINGERDOWN:
            for name, (bx, by), r, _ in self.buttons():
                if math.dist((x, y), (bx, by)) < r + 14:
                    self.pressed[name] = .25
                    return name
            if x < W * .45 and y > H * .3 and self.joy_id is None:   # mitad izquierda: el joystick sigue al dedo
                self.joy_id = ev.finger_id
                self.joy_c = (x, y)
                self.joy_v = (0.0, 0.0)
        elif ev.type == pygame.FINGERMOTION and ev.finger_id == self.joy_id:
            dx, dy = x - self.joy_c[0], y - self.joy_c[1]
            d = math.hypot(dx, dy)
            if d > JOY_R:                                             # la base sigue al dedo si se aleja mucho
                self.joy_c = (x - dx / d * JOY_R, y - dy / d * JOY_R)
                dx, dy, d = dx / d * JOY_R, dy / d * JOY_R, JOY_R
            self.joy_v = (dx / JOY_R, dy / JOY_R) if d > JOY_R * JOY_DEAD else (0.0, 0.0)
        elif ev.type == pygame.FINGERUP and ev.finger_id == self.joy_id:
            self.joy_id = None
            self.joy_c = self.joy_home
            self.joy_v = (0.0, 0.0)
        return None

    def move(self):
        return self.joy_v

    def update(self, dt):
        self.t += dt
        for k in list(self.pressed):
            self.pressed[k] -= dt
            if self.pressed[k] <= 0:
                del self.pressed[k]

    # ------------------------------------------------------------ dibujo
    def _disc(self, r, fill, ring=None, width=3):
        """Círculo semitransparente ya dibujado (se guarda: dibujar en el teléfono cuesta)."""
        key = (r, fill, ring, width)
        cache = self.__dict__.setdefault('_discs', {})
        img = cache.get(key)
        if img is None:
            img = cache[key] = pygame.Surface((2 * r + 2, 2 * r + 2), pygame.SRCALPHA)
            pygame.draw.circle(img, fill, (r + 1, r + 1), r)
            if ring:
                pygame.draw.circle(img, ring, (r + 1, r + 1), r, width)
        return img

    def draw(self, s, g, font):
        """Joystick y botones semitransparentes; los botones muestran su recarga. Todo va precalculado."""
        if not self.active:
            return
        cx, cy = self.joy_c
        base = self._disc(JOY_R, (20, 14, 40, 110), (190, 160, 255, 150))
        s.blit(base, (int(cx) - JOY_R - 1, int(cy) - JOY_R - 1))
        kx, ky = cx + self.joy_v[0] * JOY_R, cy + self.joy_v[1] * JOY_R
        knob = self._disc(28, (190, 160, 255, 170), (240, 230, 255, 200), 2)
        s.blit(knob, (int(kx) - 29, int(ky) - 29))
        b = getattr(g, 'bat', None)
        ready = {'screech': 1 - g.cd / g.cd_max if b else 1,
                 'dash': 1 - b.dash_cd / DASH_CD if b else 1,
                 'shield': (1 - b.shield_cd / 15.0) if b and b.shield_t <= 0 else 1}
        cols = {'screech': (120, 210, 255), 'dash': (255, 200, 120), 'shield': (90, 220, 170),
                'pause': (210, 200, 235), 'map': (210, 200, 235)}
        labels = self.__dict__.setdefault('_labels', {})
        for name, (bx, by), r, label in self.buttons():
            col = cols[name]
            lit = name in self.pressed
            k = max(0.0, min(1.0, ready.get(name, 1)))
            full = k >= 1
            disc = self._disc(r, (*[int(c * .25) for c in col], 210 if lit else 150),
                              (*col, 255 if lit else 230) if full else None)
            s.blit(disc, (bx - r - 1, by - r - 1))
            if not full:                                              # recarga: arco que se llena
                pygame.draw.arc(s, col, pygame.Rect(bx - r, by - r, 2 * r, 2 * r), math.pi / 2, math.pi / 2 + math.tau * k, 4)
            img = labels.get(label)
            if img is None:
                img = labels[label] = font.render(label, True, (245, 240, 255))
            s.blit(img, img.get_rect(center=(bx, by)))

    def go_fullscreen(self):
        """En el navegador: pantalla completa y horizontal (si el teléfono lo permite)."""
        if getattr(self, '_fs_done', False):
            return
        self._fs_done = True
        try:
            import platform as _pf
            win = _pf.window
            doc = win.document
            el = doc.documentElement
            if hasattr(el, 'requestFullscreen'):
                el.requestFullscreen()
            elif hasattr(el, 'webkitRequestFullscreen'):
                el.webkitRequestFullscreen()
            try:
                win.screen.orientation.lock('landscape')
            except Exception:
                pass
        except Exception:
            pass
