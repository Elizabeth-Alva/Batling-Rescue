"""Historia de BATling Rescue: niveles (actos), crías con nombre, escenas y textos de pantalla.

Todo el texto sale del documento "Historia" y respeta el documento de concepto:
3 niveles = 3 actos, 10 crías (3 + 4 + 3), una sola noche de la medianoche al amanecer.
"""

# ---------------------------------------------------------------- crías
# comportamiento: 'inquieta' se mueve un poco, 'dormilona' chilla poco, 'llorona' chilla seguido,
# 'asustadiza' se aleja de los enemigos, 'eco' repite la frase de su madre, 'gemelas' son dos en una vagoneta
PUPS = {
    1: [('Chispa', 'inquieta'), ('Bruno', 'dormilona'), ('Lía', 'llorona')],
    2: [('Nube', 'asustadiza'), ('Tito', 'llorona'), ('Eco', 'eco'), ('Mora', 'dormilona')],
    3: [('Pipo', 'inquieta'), ('Bolillo y Pozolito', 'gemelas')],
}
BEHAVIOR_TEXT = {
    'inquieta': 'inquieta: no se queda quieta',
    'dormilona': 'dormilona: casi no chilla',
    'llorona': 'llorona: chilla muy seguido',
    'asustadiza': 'asustadiza: huye de los bichos',
    'eco': 'repite la frase de su madre',
    'gemelas': 'gemelas, juntas en una vagoneta',
}


def pup_count(level):
    return sum(2 if b == 'gemelas' else 1 for _, b in PUPS[level])


def rescued_before(level):
    return sum(pup_count(lv) for lv in range(1, level))


# ---------------------------------------------------------------- niveles
# reloj: minutos desde la medianoche. Amanece a las 06:00 (360 min).
LEVELS = {
    1: dict(name='Las Galerías de los Hongos', act='Acto I', act_name='Planteamiento', theme='fungi',
            enemies={'spider': 1.0}, duration=300, start_min=0, end_min=120,
            deliver='El nido', entrance=(20, 34, 92), difficulty='Baja'),
    2: dict(name='El Lago Negro', act='Acto II', act_name='Confrontación', theme='lake',
            enemies={'spider': .55, 'beetle': .45}, duration=420, start_min=120, end_min=270,
            deliver='Saliente seguro', entrance=(96, 52, 140), difficulty='Media'),
    3: dict(name='La Mina Vieja', act='Acto III', act_name='Resolución', theme='mine',
            enemies={'spider': .35, 'beetle': .35, 'hunter': .30}, duration=330, start_min=270, end_min=360,
            deliver='Salida hacia la luz', entrance=(255, 140, 60), difficulty='Alta'),
}


def clock_text(minutes):
    m = int(max(0, minutes))
    return f'{m // 60:02d}:{m % 60:02d}'


# ---------------------------------------------------------------- cinemáticas
# Cada escena: lista de tomas. Cada toma: (ilustración, [líneas], duración mínima opcional).
# El cielo cambia de color y la silueta de Mullo cruza la escena.
CUTSCENES = {
    'apertura': dict(label='Prólogo · Atardecer fuera de la cueva', shots=[
        ('dusk', ['Año de sequía. La colonia se irá de la cueva al amanecer',
                  'y Mullo vuela lejos a buscar comida.']),
        ('leaving', ['Hoy sus 10 crías se quedan solas por primera vez.',
                     '«Ya vuelvo. Quédense quietas».']),
    ]),
    'n1_intro': dict(label='Acto I · Planteamiento', shots=[
        ('empty_nest', ['Mullo vuelve a medianoche con poca comida. El nido está vacío.',
                        'Solo hay marcas de garras que bajan hacia las galerías.']),
        ('debate', ['Está agotada y nunca ha pasado de la primera galería.',
                    'Entonces oye, muy lejos, un chillido que conoce.']),
        ('gallery', ['Sigue los rastros: piedritas, marcas de garras y guano. Los hongos le dan luz segura.',
                     'Su grito aturde a las arañas y despeja las telarañas,',
                     'y el impulso la saca de apuros.']),
    ]),
    'n1_fin': dict(label='Primer punto de giro', shots=[
        ('whisper', ['Casi al final de las galerías oyó, desde abajo, un susurro de madre:',
                     '«...ya vuelvo... quédense quietas...»',
                     'Le sonó familiar, pero no supo por qué.']),
        ('nest_three', ['Tres crías ya duermen en el nido.',
                        'Pero los chillidos siguen llegando, cada vez desde más abajo.']),
        ('descent', ['Quedan siete crías perdidas. Mullo baja hacia el lago.',
                     'Ya no hay vuelta atrás.']),
    ]),
    'n2_intro': dict(label='Acto II · Confrontación', shots=[
        ('lake', ['Abajo el aire huele a piedra mojada y casi no llega la luz.',
                  'Cada chillido rebota en el agua, y los escarabajos también lo oyen.']),
    ]),
    'n2_fin': dict(label='Punto medio y segundo punto de giro', shots=[
        ('echo_room', ['En la Sala del Eco el susurro sonó claro: era su propia voz,',
                       '«Ya vuelvo, quédense quietas», deformada por horas de rebotes. Eco la repetía.',
                       'No se fueron por desobedientes: siguieron a su madre. La culpa se volvió decisión.']),
        ('low_point', ['Mullo sabía que ya faltaba mucho menos para que la colonia partiera.',
                       'Los chillidos de sus crías ya casi no se escuchaban.']),
        ('mine_far', ['Quedan tres crías y sus chillidos vienen de las minas.']),
        ('mine_gate', ['La Mina Vieja es territorio de cazadores.',
                       'Mullo decide entrar de todos modos.']),
    ]),
    'n3_intro': dict(label='Acto III · Resolución', shots=[
        ('mine', ['La mina lleva años abandonada. Aquí abajo hasta la oscuridad es distinta.',
                  'Tres chillidos, tres crías, y todo lo que vive aquí también los oye.']),
    ]),
    'final': dict(label='Clímax, huida y resolución', shots=[
        ('escape', ['Al fondo de la mina, Bolillo y Pozolito temblaban en dos vagonetas,',
                    'al pie de un gigante que nadie puede vencer. Mullo las tomó y huyó:',
                    'el aire fresco y la luz del amanecer la guiaron a la salida.']),
        ('dawn_nest', ['Llega al nido justo cuando amanece y la colonia empieza a salir.',
                       'Las crías, asustadas por los ecos, todavía dudan.']),
        ('true_voice', ['Amanece. Mullo las llama con su voz verdadera',
                        'y las diez la reconocen entre todos los susurros falsos.']),
        ('departure', ['La colonia parte hacia un nuevo hogar.',
                       'Esta vez, Mullo no deja a nadie atrás.']),
    ]),
}

# orden de la historia completa: (tipo, clave)
FLOW = [('cut', 'apertura'), ('cut', 'n1_intro'), ('play', 1), ('cut', 'n1_fin'),
        ('cut', 'n2_intro'), ('play', 2), ('cut', 'n2_fin'),
        ('cut', 'n3_intro'), ('play', 3), ('cut', 'final'), ('end', None)]


def flow_index(kind, key):
    return FLOW.index((kind, key))


# Los momentos que ocurren a mitad de un nivel (susurro, cortina de telarañas, Sala del Eco, punto más bajo,
# clímax) se viven en tiempo real sin texto: suenan, se ven y cambian la mecánica; las cinemáticas de inicio y
# fin de cada acto los cuentan con palabras.
