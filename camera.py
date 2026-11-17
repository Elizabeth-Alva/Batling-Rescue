"""Cámara con seguimiento amortiguado y anticipación hacia donde vuelas."""
from settings import VIEW_W, VIEW_H, WORLD_W, WORLD_H, CAM_OMEGA, CAM_LOOKAHEAD, CAM_MAX_LEAD, ZOOM


def smooth_damp(cur, vel, target, omega, dt):
    """Seguimiento críticamente amortiguado (sin rebote ni oscilación)."""
    x = omega * dt
    ex = 1 / (1 + x + .48 * x * x + .235 * x * x * x)
    change = cur - target
    tmp = (vel + omega * change) * dt
    return target + (change + tmp) * ex, (vel - omega * tmp) * ex


def _lead(v):
    return max(-CAM_MAX_LEAD, min(CAM_MAX_LEAD, v * CAM_LOOKAHEAD))


class Camera:
    """vw, vh: cuánto se ve del mundo (en el juego, VIEW_W x VIEW_H: con zoom en el navegador; la portada usa la
    pantalla completa). zoom: cuántas veces se amplía esa vista para llenar la pantalla."""
    def __init__(self, x, y, vw=VIEW_W, vh=VIEW_H, zoom=ZOOM):
        self.vw, self.vh, self.zoom = vw, vh, zoom
        self.x = self.y = 0.0
        self.cvx = self.cvy = 0.0
        self.follow(x, y, 1, snap=True)

    def follow(self, tx, ty, dt, snap=False, vx=0.0, vy=0.0):
        vw, vh = self.vw, self.vh
        gx = min(max(tx + _lead(vx) - vw / 2, 0), WORLD_W - vw)
        gy = min(max(ty + _lead(vy) - vh / 2, 0), WORLD_H - vh)
        if snap:
            self.x, self.y, self.cvx, self.cvy = gx, gy, 0.0, 0.0
            return
        self.x, self.cvx = smooth_damp(self.x, self.cvx, gx, CAM_OMEGA, dt)
        self.y, self.cvy = smooth_damp(self.y, self.cvy, gy, CAM_OMEGA, dt)
        self.x = min(max(self.x, 0), WORLD_W - vw)
        self.y = min(max(self.y, 0), WORLD_H - vh)

    def apply(self, x, y):
        """Mundo -> lienzo del mundo (antes del zoom)."""
        return x - int(self.x), y - int(self.y)

    def to_screen(self, x, y):
        """Mundo -> pantalla (después del zoom): para lo que se dibuja encima, como avisos en el borde."""
        return (x - int(self.x)) * self.zoom, (y - int(self.y)) * self.zoom

    def to_world(self, sx, sy):
        """Pantalla (p. ej. el mouse) -> mundo."""
        return sx / self.zoom + self.x, sy / self.zoom + self.y

    def visible(self, x, y, m=60):
        return -m <= x - self.x <= self.vw + m and -m <= y - self.y <= self.vh + m
