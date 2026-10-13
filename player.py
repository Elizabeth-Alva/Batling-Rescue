"""Mullo, la murciélaga: movimiento fluido, colisión con la cueva, impulso y escudo."""
import math

from settings import (SHIELD_T, BAT_SPEED, BAT_ACCEL, BAT_FRICTION, BAT_TURN_BOOST, BAT_CARRY_MULT, KNOCK_DECAY,
                      PHYS_DT, BAT_RADIUS, BAT_HP, NEST, IMPACT_MIN_SPEED, IMPACT_CD, WATER_MULT,
                      DASH_SPEED, DASH_T, DASH_CD)
from events import ImpactEvent


class Bat:
    def __init__(self):
        self.x, self.y = NEST[0] + 70, NEST[1] + 40
        self.vx = self.vy = self.flap = self.inv = 0.0
        self.kx = self.ky = 0.0        # empujón por golpes (decae solo, no lo anula el input)
        self.aim = self.tilt = 0.0
        self.hp, self.carry = BAT_HP, None
        self.impact_cd = 0.0
        self.wall_n, self.wall_t = (0.0, 0.0), 0.0   # última pared tocada (para deslizar en vez de pegarse)
        self.trail, self.trail_t = [], 0.0
        self.shield_t = 0.0            # segundos de escudo restantes
        self.shield_cd = 0.0
        self.dash_t = self.dash_cd = 0.0
        self.dash_dir = (1.0, 0.0)
        self.over_water = False

    # --------------------------------------------------------------- movimiento
    def knockback(self, dx, dy, force):
        """Empuja al murciélago (dx, dy normalizados) cancelando su velocidad propia."""
        self.vx = self.vy = 0.0
        self.kx, self.ky = dx * force, dy * force

    def update(self, dt, mv, aim_world, cave, bus):
        n = math.hypot(*mv)
        self.over_water = bool(getattr(cave, 'is_water', None) and cave.is_water(self.x, self.y))
        sp = BAT_SPEED * (BAT_CARRY_MULT if self.carry else 1) * (WATER_MULT if self.over_water else 1)
        dx, dy = (mv[0] / n, mv[1] / n) if n else (0.0, 0.0)
        if self.wall_t > 0 and n:                 # contra una pared: se desliza por ella a velocidad completa
            dot = dx * self.wall_n[0] + dy * self.wall_n[1]
            if dot < 0:
                tx, ty = dx - dot * self.wall_n[0], dy - dot * self.wall_n[1]
                tl = math.hypot(tx, ty)
                if tl > .2:
                    dx, dy = tx / tl, ty / tl
                elif tl > .03:                    # casi de frente (p. ej. la punta de una roca): resbala a un lado
                    dx, dy = tx / tl * .6, ty / tl * .6
                else:
                    dx = dy = 0.0
        steps = max(1, min(8, math.ceil(dt / PHYS_DT)))
        h = dt / steps
        decay = math.exp(-KNOCK_DECAY * h)
        for _ in range(steps):
            if self.dash_t > 0:                    # impulso: velocidad fija en la dirección elegida
                self.dash_t -= h
                self.vx, self.vy = self.dash_dir[0] * DASH_SPEED, self.dash_dir[1] * DASH_SPEED
                if self.dash_t <= 0:               # al terminar conserva la velocidad normal
                    self.vx, self.vy = self.dash_dir[0] * sp, self.dash_dir[1] * sp
            else:
                self._accelerate(dx, dy, sp, h)
            self.x += (self.vx + self.kx) * h
            self.y += (self.vy + self.ky) * h
            hit, nx, ny = cave.resolve(self, BAT_RADIUS)
            if hit:
                self._on_wall(nx, ny, bus)
            self.kx *= decay
            self.ky *= decay
        speed = math.hypot(self.vx, self.vy)
        self.aim = math.atan2(aim_world[1] - self.y, aim_world[0] - self.x)
        self.flap += dt * (14 + speed / 20 + (6 if (dx or dy) else 0))
        target = max(-1, min(1, (self.vx + self.kx) / BAT_SPEED)) * .28          # inclinación al girar
        self.tilt += (target - self.tilt) * min(1, dt * 10)
        self.trail_t -= dt
        if speed > 150 and self.trail_t <= 0 or self.dash_t > 0:
            self.trail.append([self.x, self.y, .35])
            self.trail_t = .035
        for p in self.trail:
            p[2] -= dt
        self.trail = [p for p in self.trail if p[2] > 0]
        self.wall_t = max(0, self.wall_t - dt)
        self.inv = max(0, self.inv - dt)
        self.impact_cd = max(0, self.impact_cd - dt)
        self.dash_cd = max(0, self.dash_cd - dt)
        self.shield_t = max(0, self.shield_t - dt)
        self.shield_cd = max(0, self.shield_cd - dt)

    def _accelerate(self, dx, dy, sp, h):
        if dx or dy:                               # acelera hacia la velocidad deseada
            tvx, tvy = dx * sp, dy * sp
            ex, ey = tvx - self.vx, tvy - self.vy
            dist = math.hypot(ex, ey)
            step = BAT_ACCEL * (BAT_TURN_BOOST if self.vx * dx + self.vy * dy < 0 else 1) * h
            if dist <= step:
                self.vx, self.vy = tvx, tvy
            else:
                self.vx += ex / dist * step
                self.vy += ey / dist * step
        else:                                      # sin input: fricción
            spd = math.hypot(self.vx, self.vy)
            step = BAT_FRICTION * h
            if spd <= step:
                self.vx = self.vy = 0.0
            else:
                f = (spd - step) / spd
                self.vx *= f
                self.vy *= f

    def _on_wall(self, nx, ny, bus):
        """Choque: se quita solo la componente que entra en la pared (se resbala, no se pega)."""
        vn = (self.vx + self.kx) * nx + (self.vy + self.ky) * ny
        if vn < 0:
            speed = -vn
            c = self.vx * nx + self.vy * ny
            if c < 0:
                self.vx -= c * nx
                self.vy -= c * ny
            c = self.kx * nx + self.ky * ny
            if c < 0:
                self.kx -= c * nx
                self.ky -= c * ny
            if speed > IMPACT_MIN_SPEED * 1.6:     # solo los choques fuertes rebotan un poco
                self.vx += nx * speed * .08
                self.vy += ny * speed * .08
            if speed > IMPACT_MIN_SPEED and self.impact_cd <= 0:
                self.impact_cd = IMPACT_CD
                bus.emit(ImpactEvent(self.x, self.y, speed))
        self.wall_n, self.wall_t = (nx, ny), .1

    # --------------------------------------------------------------- impulso
    def try_dash(self, mv, aim_world):
        """Impulso en la dirección de vuelo (o hacia el ratón si no te mueves)."""
        if self.dash_cd > 0:
            return False
        dx, dy = mv
        if not (dx or dy):
            dx, dy = aim_world[0] - self.x, aim_world[1] - self.y
        n = math.hypot(dx, dy)
        if n < 1e-6:
            return False
        self.dash_dir = (dx / n, dy / n)
        self.dash_t, self.dash_cd = DASH_T, DASH_CD
        self.kx = self.ky = 0.0
        return True

    # --------------------------------------------------------------- escudo
    def try_shield(self, cd):
        if self.shield_cd > 0:
            return False
        self.shield_t, self.shield_cd = SHIELD_T, cd
        return True
