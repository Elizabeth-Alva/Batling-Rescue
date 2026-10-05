"""Cámara con seguimiento amortiguado y anticipación hacia donde vuelas."""
from settings import W, H, WORLD_W, WORLD_H, CAM_OMEGA, CAM_LOOKAHEAD, CAM_MAX_LEAD


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
    def __init__(self, x, y):
        self.x = self.y = 0.0
        self.cvx = self.cvy = 0.0
        self.follow(x, y, 1, snap=True)

    def follow(self, tx, ty, dt, snap=False, vx=0.0, vy=0.0):
        gx = min(max(tx + _lead(vx) - W / 2, 0), WORLD_W - W)
        gy = min(max(ty + _lead(vy) - H / 2, 0), WORLD_H - H)
        if snap:
            self.x, self.y, self.cvx, self.cvy = gx, gy, 0.0, 0.0
            return
        self.x, self.cvx = smooth_damp(self.x, self.cvx, gx, CAM_OMEGA, dt)
        self.y, self.cvy = smooth_damp(self.y, self.cvy, gy, CAM_OMEGA, dt)
        self.x = min(max(self.x, 0), WORLD_W - W)
        self.y = min(max(self.y, 0), WORLD_H - H)

    def apply(self, x, y):
        return x - int(self.x), y - int(self.y)

    def to_world(self, sx, sy):
        return sx + self.x, sy + self.y

    def visible(self, x, y, m=60):
        return -m <= x - self.x <= W + m and -m <= y - self.y <= H + m
