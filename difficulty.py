"""Curva de dificultad: sube por nivel (acto) y un poco con cada cría rescatada dentro del nivel."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Params:
    level: int
    patrol_speed: float
    investigate_speed: float
    chase_speed: float
    max_enemies: int
    spawn_interval: float
    detect_radius: float        # a qué distancia te ve un enemigo
    hear_mult: float            # multiplicador del radio de ruido que les afecta
    pup_interval: float         # segundos entre chillidos de cría
    pup_noise_r: float


BASE = {
    #    patrulla, investiga, persecución, máx., aparición, detección, oído, chillido, ruido
    1: (40, 64, 96, 5, 6.5, 112, 1.00, 3.6, 290),
    2: (49, 79, 124, 9, 4.1, 130, 1.11, 2.9, 334),
    3: (52, 84, 134, 10, 3.6, 136, 1.15, 2.7, 350),
}


def params(level: int, rescued_here: int = 0) -> Params:
    lv = max(1, min(3, level))
    p, i, c, m, s, d, h, pi, pn = BASE[lv]
    r = max(0, rescued_here)
    return Params(
        level=lv,
        patrol_speed=p + 2 * r,
        investigate_speed=i + 3 * r,
        chase_speed=min(170, c + 5 * r),
        max_enemies=m + r,
        spawn_interval=max(2.2, s - .4 * r),
        detect_radius=d + 4 * r,
        hear_mult=h + .03 * r,
        pup_interval=max(1.4, pi - .2 * r),
        pup_noise_r=pn + 12 * r,
    )
