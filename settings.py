"""Constantes globales del juego (todo lo balanceable vive aquí, en difficulty.py o en story.py)."""
import math
import sys

IS_WEB = sys.platform == "emscripten"     # ejecutándose en el navegador (pygbag)

W, H = 960, 640
FPS = 60
TAU = math.tau
TITLE = "BATling Rescue"

# --- Mundo -------------------------------------------------------------
TILE = 32
MAP_W, MAP_H = 96, 64                  # en tiles -> 3072 x 2048 px (~3x3 pantallas)
WORLD_W, WORLD_H = MAP_W * TILE, MAP_H * TILE
NEST_T = (7, 7)                        # tile del punto de entrega ("el nido está en lo alto")
NEST = (NEST_T[0] * TILE + TILE // 2, NEST_T[1] * TILE + TILE // 2)
NEST_R = 55
SAFE_R = NEST_R + 45                   # zona segura: los enemigos no entran
GOAL = 10                              # crías en total (3 + 4 + 3)

# --- Jugador (Mullo) ---------------------------------------------------
BAT_SPEED = 235
BAT_ACCEL = 2400                       # px/s²: llega a velocidad máxima en ~0.1 s
BAT_FRICTION = 2200                    # px/s²: frena en ~0.11 s al soltar las teclas
BAT_TURN_BOOST = 1.8                   # más aceleración al invertir el sentido (giros ágiles)
BAT_CARRY_MULT = 0.9                   # penalización de velocidad al llevar una cría
WATER_MULT = 0.8                       # sobre el agua del Lago Negro "el aire pesa"
KNOCK_DECAY = 7.0                      # decaimiento del empujón al recibir un golpe
PHYS_DT = 1 / 120                      # subpaso máximo de la física (independiente de los FPS)
BAT_RADIUS = 12
BAT_HP = 5                             # vidas por nivel

# --- Grito sónico (aturde, daña y revela a las crías en el minimapa) ----
SCREECH_CD = 2.3                       # "tarda en recargarse" (un poco menos que antes)
SCREECH_CD_DECIDED = 1.7               # tras la Sala del Eco usa el grito "a propósito"
SCREECH_R = 165                        # alcance del aturdimiento
REVEAL_T = 3.0                         # segundos que las crías quedan marcadas en el minimapa (breve)
REVEAL_T_READER = 4.0                  # 1.ª mejora (Leer la cueva, desde el Acto II): se quedan un poco más
GUIDE_T = 1.8                          # segundos que se ven las flechas rosas después de un grito
ECHO_FLASH_T = 0.9                     # destello de ecolocación alrededor de Mullo

# --- Impulso -----------------------------------------------------------
DASH_SPEED = 640
DASH_T = 0.2
DASH_CD = 2.8
DASH_CD_AIR = 1.8                      # 3.ª mejora (Vuelo con la corriente): recarga dentro de la corriente de la mina

# --- Escudo ------------------------------------------------------------
SHIELD_T = 5.0                         # segundos de duración
SHIELD_CD = 15.0                       # enfriamiento desde la activación
SHIELD_R = 30

# --- Impactos ----------------------------------------------------------
IMPACT_MIN_SPEED = 110                 # por debajo, rozar la pared no hace ruido
IMPACT_CD = 0.45
IMPACT_NOISE_MIN, IMPACT_NOISE_MAX = 120, 330

# --- Cámara ------------------------------------------------------------
CAM_OMEGA = 9.0                        # rigidez del seguimiento (amortiguación crítica)
CAM_LOOKAHEAD = 0.22                   # segundos de velocidad por delante
CAM_MAX_LEAD = 70

# --- Visibilidad -------------------------------------------------------
# (nombre, opacidad de la oscuridad ambiente, radio de la luz del murciélago)
BRIGHTNESS_LEVELS = (('Oscuro', 226, 150), ('Normal', 204, 205), ('Claro', 172, 250))
DEFAULT_BRIGHTNESS = 1
MEMORY_ALPHA = 58                      # cuánto se aclara lo ya recorrido

# --- Colores -----------------------------------------------------------
C_TEXT = (235, 225, 245)
C_PURPLE = (190, 150, 255)
C_GREEN = (160, 255, 190)
C_RED = (255, 110, 110)
C_PUP = (255, 150, 210)
C_SONAR = (120, 190, 255)
C_IMPACT = (255, 190, 120)
C_GOLD = (255, 205, 120)
