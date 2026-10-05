"""Constantes globales del juego (todo lo balanceable vive aquí o en difficulty.py)."""
import math

W, H = 960, 640
FPS = 60
TAU = math.tau
TITLE = "Batling Rescue"

# --- Mundo -------------------------------------------------------------
TILE = 32
MAP_W, MAP_H = 96, 64                  # en tiles -> 3072 x 2048 px (~3x3 pantallas)
WORLD_W, WORLD_H = MAP_W * TILE, MAP_H * TILE
NEST_T = (7, 7)                        # tile del nido
NEST = (NEST_T[0] * TILE + TILE // 2, NEST_T[1] * TILE + TILE // 2)
NEST_R = 55
GOAL = 10                              # crías a rescatar para ganar

# --- Jugador -----------------------------------------------------------
BAT_SPEED = 235
BAT_ACCEL = 2400                       # px/s²: llega a velocidad máxima en ~0.1 s
BAT_FRICTION = 2200                    # px/s²: frena en ~0.11 s al soltar las teclas
BAT_TURN_BOOST = 1.8                   # más aceleración al invertir el sentido (giros ágiles)
BAT_CARRY_MULT = 0.9                   # penalización de velocidad al llevar una cría
KNOCK_DECAY = 7.0                      # decaimiento del empujón al recibir un golpe
PHYS_DT = 1 / 120                      # subpaso máximo de la física (independiente de los FPS)
BAT_RADIUS = 12
BAT_HP = 5
SCREECH_CD = 1.1
SCREECH_R = 150

# --- Escudo ------------------------------------------------------------
SHIELD_T = 5.0                         # segundos de duración
SHIELD_CD = 15.0                       # enfriamiento desde la activación
SHIELD_R = 30

# --- Sonar -------------------------------------------------------------
SONAR_SPEED = 1500                     # px/s de expansión de la onda
SONAR_MAX_R = 3800                     # cubre todo el mundo
SONAR_WAVE_T = SONAR_MAX_R / SONAR_SPEED
SONAR_FADE_T = 1.6                     # desvanecimiento de lo revelado
SONAR_TOTAL_T = SONAR_WAVE_T + SONAR_FADE_T
SONAR_EXPOSE_T = SONAR_TOTAL_T         # el murciélago es visible mientras dure
SONAR_NOISE_R = 300

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
AMBIENT_RGB = (6, 10, 28)              # tinte azulado de la penumbra
MEMORY_ALPHA = 58                      # cuánto se aclara lo ya recorrido

# --- Colores -----------------------------------------------------------
C_TEXT = (235, 225, 245)
C_PURPLE = (190, 150, 255)
C_GREEN = (160, 255, 190)
C_RED = (255, 110, 110)
C_PUP = (255, 150, 210)
C_SONAR = (120, 190, 255)
C_IMPACT = (255, 190, 120)
