"""El murciélago: movimiento fluido, colisión con la cueva, sonar y escudo."""
import math

from settings import (SHIELD_T, BAT_SPEED, BAT_ACCEL, BAT_FRICTION, BAT_TURN_BOOST, BAT_CARRY_MULT, KNOCK_DECAY,
                      PHYS_DT, BAT_RADIUS, BAT_HP, NEST, SONAR_SPEED, SONAR_MAX_R, SONAR_TOTAL_T,
                      SONAR_WAVE_T, SONAR_FADE_T, SONAR_EXPOSE_T, SONAR_NOISE_R, C_SONAR,
                      IMPACT_MIN_SPEED, IMPACT_CD)
from events import ImpactEvent, NoiseEvent, SonarEvent


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
        # sonar
        self.sonar_cd = 0.0
        self.sonar_t = None            # segundos desde que se emitió (None = inactivo)
        self.sonar_origin = (0, 0)
        self.exposed = 0.0             # segundos restantes en que los enemigos cercanos te ven

    # --------------------------------------------------------------- movimiento
    def knockback(self, dx, dy, force):
        """Empuja al murciélago (dx, dy normalizados) cancelando su velocidad propia."""
        self.vx = self.vy = 0.0
        self.kx, self.ky = dx * force, dy * force

    def update(self, dt, mv, aim_world, cave, bus):
        n = math.hypot(*mv)
        sp = BAT_SPEED * (BAT_CARRY_MULT if self.carry else 1)
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
        if speed > 150 and self.trail_t <= 0:
            self.trail.append([self.x, self.y, .35])
            self.trail_t = .035
        for p in self.trail:
            p[2] -= dt
        self.trail = [p for p in self.trail if p[2] > 0]
        self.wall_t = max(0, self.wall_t - dt)
        self.inv = max(0, self.inv - dt)
        self.impact_cd = max(0, self.impact_cd - dt)
        self.sonar_cd = max(0, self.sonar_cd - dt)
        self.shield_t = max(0, self.shield_t - dt)
        self.shield_cd = max(0, self.shield_cd - dt)
        self.exposed = max(0, self.exposed - dt)
        if self.sonar_t is not None:
            self.sonar_t += dt
            if self.sonar_t >= SONAR_TOTAL_T:
                self.sonar_t = None

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

    # --------------------------------------------------------------- sonar
    def try_sonar(self, cd, bus):
        if self.sonar_cd > 0 or self.sonar_t is not None:
            return False
        self.sonar_t, self.sonar_origin = 0.0, (self.x, self.y)
        self.sonar_cd, self.exposed = cd, SONAR_EXPOSE_T
        bus.emit(SonarEvent(self.x, self.y))
        bus.emit(NoiseEvent(self.x, self.y, SONAR_NOISE_R, C_SONAR, 'sonar'))
        return True

    @property
    def sonar_radius(self):
        return None if self.sonar_t is None else min(SONAR_MAX_R, self.sonar_t * SONAR_SPEED)

    @property
    def sonar_strength(self):
        """1 mientras la onda se expande y luego decae a 0 durante el desvanecimiento."""
        if self.sonar_t is None:
            return 0.0
        if self.sonar_t <= SONAR_WAVE_T:
            return 1.0
        return max(0.0, 1 - (self.sonar_t - SONAR_WAVE_T) / SONAR_FADE_T)

    # --------------------------------------------------------------- escudo
    def try_shield(self, cd):
        if self.shield_cd > 0:
            return False
        self.shield_t, self.shield_cd = SHIELD_T, cd
        return True
