"""Curva de dificultad: todo en función de las crías rescatadas."""
from dataclasses import dataclass

from settings import GOAL


@dataclass(frozen=True)
class Params:
    level: int
    patrol_speed: float
    investigate_speed: float
    chase_speed: float
    max_enemies: int
    spawn_interval: float
    detect_radius: float        # a qué distancia te ve un enemigo normal
    expose_radius: float        # a qué distancia te ve si usaste el sonar
    hear_mult: float            # multiplicador del radio de ruido que les afecta
    pup_interval: float         # segundos entre chillidos de cría
    pup_noise_r: float
    sonar_cd: float
    runner_chance: float
    listener_chance: float
    predator_chance: float      # depredadores grandes (escorpión)
    behemoth_chance: float      # el más grande de todos
    max_predators: int          # tope de grandes a la vez


def params(rescued: int) -> Params:
    r = max(0, min(rescued, GOAL))
    return Params(
        level=r + 1,
        patrol_speed=42 + 3 * r,
        investigate_speed=70 + 5 * r,
        chase_speed=min(185, 95 + 9 * r),
        max_enemies=min(14, 5 + (r + 1) // 2 + r // 3),
        spawn_interval=max(1.8, 5.0 - 0.35 * r),
        detect_radius=120 + 5 * r,
        expose_radius=480 + 12 * r,
        hear_mult=1 + 0.04 * r,
        pup_interval=max(1.3, 3.8 - 0.22 * r),
        pup_noise_r=300 + 14 * r,
        sonar_cd=8 + 0.35 * r,
        runner_chance=0.0 if r < 4 else min(0.35, 0.10 * (r - 3)),
        listener_chance=0.0 if r < 7 else min(0.30, 0.10 * (r - 6)),
        predator_chance=0.0 if r < 3 else min(0.40, 0.10 * (r - 2)),
        behemoth_chance=0.0 if r < 6 else min(0.22, 0.06 * (r - 5)),
        max_predators=0 if r < 3 else 1 if r < 6 else 2 if r < 9 else 3,
    )
