"""Historia de BATling Rescue: niveles (actos), crías con nombre, escenas y textos de pantalla.

Todo el texto sale de la «Propuesta» del equipo (elementos de la historia, personajes e historia completa):
3 niveles = 3 actos, 10 crías (3 + 4 + 3), una sola noche: de la medianoche a la partida de la colonia
a las 05:30, antes del amanecer. Personajes: Mullo (protagonista), Xolthar el Gran Ciempiés (antagonista)
y los bichos de la cueva, Chispa (coprotagonista) y la Abuela Canela (secundario).
"""

# ---------------------------------------------------------------- crías
# comportamiento: 'inquieta' revolotea y huye a brinquitos, 'dormilona' sigue dormida como si nada (chilla poco),
# 'ratos' duerme a ratos (dormida no chilla; despierta, sí), 'llorona' chilla seguido, 'asustadiza' huye de
# cualquier bicho (hay que alcanzarla), 'eco' espera en la Sala del Eco, 'gemelas' son dos, cada una en su vagoneta
PUPS = {
    1: [('Chispa', 'inquieta'), ('Bruno', 'dormilona'), ('Lía', 'llorona')],
    2: [('Nube', 'asustadiza'), ('Tito', 'llorona'), ('Eco', 'eco'), ('Mora', 'ratos')],
    3: [('Paco', 'inquieta'), ('Bolillo y Pozolito', 'gemelas')],
}
BEHAVIOR_TEXT = {
    'inquieta': 'inquieta: no se queda quieta',
    'dormilona': 'dormilona: sigue dormida como si nada',
    'ratos': 'duerme a ratos',
    'llorona': 'llorona: no para de llorar',
    'asustadiza': 'asustadiza: huye de cualquier bicho',
    'eco': 'espera en la Sala del Eco',
    'gemelas': 'gemelas, en dos vagonetas',
}


def pup_count(level):
    return sum(2 if b == 'gemelas' else 1 for _, b in PUPS[level])


def rescued_before(level):
    return sum(pup_count(lv) for lv in range(1, level))


# ---------------------------------------------------------------- niveles
# reloj: minutos desde la medianoche. La colonia parte a las 05:30 (330 min), antes de que salga el sol (06:00).
DEPARTURE_MIN = 330
DAWN_MIN = 360
LEVELS = {
    1: dict(name='Las Galerías de los Hongos', act='Acto I', act_name='Planteamiento', theme='fungi',
            enemies={'spider': 1.0}, duration=300, start_min=0, end_min=120,
            deliver='El nido', entrance=(20, 34, 92), difficulty='Baja'),
    2: dict(name='El Lago Negro', act='Acto II', act_name='Confrontación', theme='lake',
            enemies={'spider': .55, 'beetle': .45}, duration=420, start_min=120, end_min=270,
            deliver='El nido', entrance=(96, 52, 140), difficulty='Media'),
    3: dict(name='La Mina Vieja', act='Acto III', act_name='Resolución', theme='mine',
            enemies={'spider': .35, 'beetle': .35, 'hunter': .30}, duration=330, start_min=270, end_min=DEPARTURE_MIN,
            deliver='El nido', entrance=(255, 140, 60), difficulty='Alta'),
}


def clock_text(minutes):
    m = int(max(0, minutes))
    return f'{m // 60:02d}:{m % 60:02d}'


# ---------------------------------------------------------------- cinemáticas
# Cada escena: lista de tomas. Cada toma: (ilustración, [líneas], duración mínima opcional).
# Vista de lado con siluetas, como un cuento ilustrado, y siempre siguiendo a Mullo.
# Las frases entre «» son voces: lila para Mullo y canela para la Abuela (ver VOICE).
CUTSCENES = {
    # 6.1 Prólogo: atardecer
    'apertura': dict(label='Prólogo · Atardecer', shots=[
        ('dusk', ['Año de sequía: afuera casi no hay insectos.',
                  'Al atardecer, la colonia sale sin dispersarse sobre el campo seco.',
                  'Las crías se quedan en el nido.']),
        ('tale', ['Antes de que todos se alejen, la Abuela Canela, la más vieja de la colonia,',
                  'cuenta la historia del Gran Ciempiés que duerme al fondo de la Mina Vieja.']),
        ('advice', ['Y menciona algo que en ese momento no parecía importante:',
                    '«Si algún día bajan a la mina, sigan el aire. El aire debe salir.',
                    'Y no despierten a lo que duerme al fondo».']),
        ('canela', ['Además, avisa que no hay comida para los próximos días',
                    'y que antes del amanecer todos se irán a un refugio nuevo:',
                    '«A las 05:30 nos vamos».']),
        ('search', ['Mullo comienza a buscar alimento,',
                    'pero no encuentra nada cerca.']),
        ('goodbye', ['Desde el borde del nido les dice a sus diez crías:',
                     '«Ya vuelvo. Quédense quietas».']),
        ('leaving', ['Y se marcha a buscar por lugares más lejanos.',
                     'Por primera vez, sus crías se quedan solas.']),
    ]),
    # 6.2 Acto I: Las Galerías de los Hongos (planteamiento)
    'n1_intro': dict(label='Acto I · Las Galerías de los Hongos', shots=[
        ('empty_nest', ['Mullo regresa a medianoche con poca comida y el nido está vacío.',
                        'Solo quedan marcas de garras que bajan.']),
        ('debate', ['Está cansada y nunca ha pasado de la primera galería,',
                    'pero oye a lo lejos un chillido que conoce y se lanza.']),
        ('gallery', ['En las galerías los hongos le dan luz y el rastro de Chispa le marca',
                     'un camino: piedritas movidas y rasguños. Ahí aprende a usar el grito',
                     'contra las arañas y para abrir las cortinas de telarañas.']),
    ]),
    'n1_fin': dict(label='Acto I · Primer punto de giro', shots=[
        ('nest_three', ['Chispa, Bruno y Lía ya están a salvo en el nido.',
                        'Chispa fue dejando esos rastros para que su mamá la siguiera.']),
        ('descent', ['Con tres crías a salvo, Mullo baja hacia el lago',
                     'y ya no hay vuelta atrás.']),
    ]),
    # 6.3 Acto II: El Lago Negro (confrontación)
    'n2_intro': dict(label='Acto II · El Lago Negro', shots=[
        ('lake', ['Abajo huele a piedra mojada y casi no hay luz. El agua tiene sus reglas:',
                  'los escarabajos y las arañas no la cruzan, así que volar sobre ella es más seguro.',
                  'Las salamandras se hunden cuando la ven pasar.']),
    ]),
    'n2_fin': dict(label='Acto II · Segundo punto de giro', shots=[
        ('mine_far', ['Ya falta poco para que la colonia se vaya. Las tres últimas crías',
                      'chillan desde la Mina Vieja, territorio de los cazadores.']),
        ('mine_gate', ['Mullo entra de todos modos. En la entrada encuentra una piel vieja',
                       'de ciempiés, vacía y tan larga como una vagoneta.',
                       'Algo muy grande vive allá al fondo.']),
    ]),
    # 6.4 Acto III: La Mina Vieja (resolución). El recuerdo de «sigan el aire» llega en pleno juego,
    # cuando despierta el Gran Ciempiés (ver AIR_MESSAGE).
    'n3_intro': dict(label='Acto III · La Mina Vieja', shots=[
        ('mine', ['La mina está abandonada hace años. Hay vigas, rieles, vagonetas oxidadas',
                  'y ciempiés cazadores que oyen todo.']),
    ]),
    # 6.5 Final: antes del amanecer
    'final': dict(label='Final · Antes del amanecer', shots=[
        ('return_nest', ['Mullo llega al nido con Bolillo y Pozolito',
                         'cuando la colonia ya está saliendo.']),
        ('dawn_nest', ['La Abuela Canela es la última en la boca de la cueva.',
                       'Las crías están asustadas por tanto eco y dudan.']),
        ('true_voice', ['Mullo las llama con su voz verdadera, la de siempre y no la de la cueva.',
                        'Chispa contesta primero; detrás de ella responden las otras nueve.']),
        ('departure', ['La colonia parte completa hacia su nuevo hogar',
                       'y esta vez Mullo no deja a nadie atrás.']),
    ]),
}

# quién habla en cada toma (color de las frases «...» y sonido de su voz)
VOICE = {'canela': 'canela', 'advice': 'canela', 'tale': 'canela'}
# sonido que acompaña el inicio de cada toma
SHOT_SFX = {'canela': ('canela', .8), 'tale': ('canela', .7), 'advice': ('canela', .8),
            'goodbye': ('call', .35), 'whisper': ('whisper', .6),
            'mine_gate': ('growl', .25), 'return_nest': ('deliver', .5), 'true_voice': ('call', .8)}

# Mensajes de la historia que aparecen mientras se juega (no pausan el juego).
# El susurro (Acto I): al llevar la segunda cría al nido. Mullo habla poco y con frases cortas.
WHISPER_MESSAGE = ('Un susurro',
                   ['Desde abajo sube un susurro con una voz parecida a la de Mullo.',
                    '«¿Esa voz?...». Le suena familiar y no sabe por qué.'])
# La Sala del Eco (punto medio del Acto II): al encontrar a Eco, con su animación.
ECHO_MESSAGE = ('La Sala del Eco',
                ['Mullo por fin escucha el eco de la cueva: el aire que la recorre',
                 'produce ecos que suenan como su voz. Sus crías no se fueron',
                 'por desobedientes: siguieron a su «mamá».'])
# Acto III: al acercarse al rincón de las gemelas.
XOLTHAR_MESSAGE = ('Xolthar',
                   ['Las gemelas Bolillo y Pozolito tiemblan sobre dos vagonetas, junto a',
                    'una forma enroscada enorme. Es Xolthar, el Gran Ciempiés del cuento',
                    'de la Abuela. «No despierten a lo que duerme al fondo».'])
# Acto III: cuando Xolthar despierta, Mullo recuerda el consejo de la Abuela (3.ª mejora).
AIR_MESSAGE = ('Sigue el aire',
               ['La mina retumba y el Gran Ciempiés despierta. Mullo recuerda el consejo:',
                '«Si algún día bajan a la mina, sigan el aire. El aire debe salir».',
                'No hay forma de vencerlo. Solo volar bien y no chocar.'])

# antes de empezar el Acto I la pantalla se queda en negro un momento (segundos)
BLACK_BEFORE = {'n1_intro': 2.0}

# orden de la historia completa: (tipo, clave)
FLOW = [('cut', 'apertura'), ('cut', 'n1_intro'), ('play', 1), ('cut', 'n1_fin'),
        ('cut', 'n2_intro'), ('play', 2), ('cut', 'n2_fin'),
        ('cut', 'n3_intro'), ('play', 3), ('cut', 'final'), ('end', None)]


def flow_index(kind, key):
    return FLOW.index((kind, key))


# Mejoras de Mullo (una por acto, por la historia y no por puntos). Se notan porque el grito o el impulso
# vuelven antes y suenan un poco distinto; nunca se anuncian con texto.
#   I   'reader'  · Leer la cueva: al llevar al nido a las tres crías de las galerías (minimapa 3 s -> 4 s)
#   II  'decided' · Grito decidido: en la Sala del Eco (recarga del grito 2.3 s -> 1.7 s)
#   III 'air'     · Vuelo con la corriente: al recordar «sigue el aire» cuando despierta Xolthar
#                   (dentro de la corriente el impulso se recarga en 1.8 s en lugar de 2.8 s)
#
# Los momentos que ocurren a mitad de un nivel se viven en tiempo real, sin pausar: el susurro, la Sala del Eco,
# Xolthar dormido y su despertar («sigue el aire») se acompañan de un mensaje breve en pantalla; la cortina de
# telarañas y el punto más bajo solo suenan y se ven.
