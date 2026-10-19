"""Historia de BATling Rescue: niveles (actos), crías con nombre, escenas y textos de pantalla.

Todo el texto sale de los documentos «Historia y personajes» y «Otros elementos en la historia»:
3 niveles = 3 actos, 10 crías (3 + 4 + 3), una sola noche: de la medianoche a la partida de la colonia
a las 05:30, antes del amanecer. Personajes: Mullo (protagonista), Xolthar el Gran Ciempiés (antagonista)
y los bichos de la cueva, Chispa (coprotagonista) y la Abuela Canela (secundario).
"""

# ---------------------------------------------------------------- crías
# comportamiento: 'inquieta' revolotea y huye a brinquitos, 'dormilona' chilla poco, 'llorona' chilla seguido,
# 'asustadiza' se aleja de los bichos, 'eco' espera en la Sala del Eco, 'gemelas' son dos, cada una en su vagoneta
PUPS = {
    1: [('Chispa', 'inquieta'), ('Bruno', 'dormilona'), ('Lía', 'llorona')],
    2: [('Nube', 'asustadiza'), ('Tito', 'llorona'), ('Eco', 'eco'), ('Mora', 'dormilona')],
    3: [('Paco', 'inquieta'), ('Bolillo y Pozolito', 'gemelas')],
}
BEHAVIOR_TEXT = {
    'inquieta': 'inquieta: no se queda quieta',
    'dormilona': 'dormilona: casi no chilla',
    'llorona': 'llorona: chilla muy seguido',
    'asustadiza': 'asustadiza: huye de los bichos',
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
    'apertura': dict(label='Prólogo · Atardecer fuera de la cueva', shots=[
        ('dusk', ['Año de sequía: afuera casi no hay insectos.',
                  'Al atardecer, la colonia sale a cazar sobre el campo seco. Las crías se quedan en el nido.']),
        ('tale', ['En el árbol seco, la Abuela Canela, la más vieja de la colonia,',
                  'les cuenta a los grandes la historia del ciempiés gigante',
                  'que duerme al fondo de la Mina Vieja. Mullo escucha con ellas.']),
        ('advice', ['Y dice algo que en ese momento no parecía importante:',
                    '«Si algún día bajan a la mina, sigan el aire. El aire sabe salir.',
                    'Y no despierten a lo que duerme al fondo».']),
        ('canela', ['Antes de volver a cazar, la Abuela les avisa a todas:',
                    '«No hay comida para otro par de días. Los veo aquí antes del amanecer:',
                    'a las 05:30 nos vamos a un refugio nuevo».']),
        ('goodbye', ['Mullo no encuentra nada cerca: tendrá que volar más lejos que nunca.',
                     'Vuelve un momento al nido y les dice a sus diez crías:',
                     '«Ya vuelvo. Quédense quietas».']),
        ('leaving', ['Mullo sale de la cueva y vuela hacia la noche, más lejos que nunca.',
                     'Por primera vez, sus crías se quedan solas.']),
    ]),
    'n1_intro': dict(label='Acto I · Las Galerías de los Hongos', shots=[
        ('empty_nest', ['Mullo vuelve a medianoche con poca comida. El nido está vacío.',
                        'Solo quedan marcas de garras que bajan hacia las galerías.']),
        ('debate', ['Está cansada y nunca ha pasado de la primera galería.',
                    'Entonces oye, muy lejos, un chillido que conoce, y se lanza.']),
        ('gallery', ['Los hongos le dan luz y unos rastros le marcan el camino:',
                     'piedritas movidas y rasguños. Su grito aturde a las arañas',
                     'y abre las cortinas de telarañas.']),
    ]),
    'n1_fin': dict(label='Acto I · Primer punto de giro', shots=[
        ('nest_three', ['Chispa, Bruno y Lía ya están a salvo. Chispa había dejado esos rastros',
                        'para que su mamá la encontrara. Seguirlos le enseñó a Mullo a leer la cueva.']),
        ('descent', ['Los demás chillidos llegan de mucho más abajo. Mullo baja hacia el lago.',
                     'Ya no hay vuelta atrás.']),
    ]),
    'n2_intro': dict(label='Acto II · El Lago Negro', shots=[
        ('lake', ['Abajo huele a piedra mojada y casi no hay luz. El agua tiene sus reglas:',
                  'las arañas y los escarabajos no la cruzan, pero el aire húmedo frena a Mullo.',
                  'Las salamandras se hunden cuando la ven pasar.']),
    ]),
    'n2_fin': dict(label='Acto II · Segundo punto de giro', shots=[
        ('near_dawn', ['Por una grieta del techo entra la primera luz gris: ya casi va a amanecer.',
                       'Si no se apura, la colonia se irá sin ella.']),
        ('mine_far', ['Las tres últimas crías chillan desde la Mina Vieja,',
                      'territorio de los cazadores.']),
        ('mine_gate', ['Mullo entra de todos modos. En la entrada encuentra una piel vieja de ciempiés,',
                       'vacía y tan larga como una vagoneta.',
                       'Algo muy grande vive allá al fondo.']),
    ]),
    'n3_intro': dict(label='Acto III · La Mina Vieja', shots=[
        ('mine', ['La mina lleva años abandonada: vigas, rieles y vagonetas oxidadas.',
                  'Tres chillidos, tres crías, y los cazadores también los oyen.']),
        ('recall', ['Una corriente fresca le roza las alas. Mullo recuerda lo que la Abuela les dijo:',
                    '«Sigan el aire. El aire sabe salir».']),
    ]),
    'final': dict(label='Resolución · Antes del amanecer', shots=[
        ('return_nest', ['Mullo lleva a Bolillo y Pozolito de regreso al nido de siempre.',
                         'Por fin, las diez crías están juntas otra vez.']),
        ('dawn_nest', ['La colonia ya está saliendo y la Abuela Canela es la última en irse.',
                       'Mullo vuela hacia la boca de la cueva, pero sus crías,',
                       'asustadas por tanto eco, dudan en seguirla.']),
        ('true_voice', ['Mullo las llama con su voz verdadera, la de siempre y no la de la cueva.',
                        'Chispa contesta primero y detrás de ella van las otras nueve, con su mamá.']),
        ('departure', ['Volvió, como lo prometió, por las diez. La colonia parte completa',
                       'hacia su nuevo hogar. Esta vez, Mullo no deja a nadie atrás.']),
    ]),
}

# quién habla en cada toma (color de las frases «...» y sonido de su voz)
VOICE = {'canela': 'canela', 'advice': 'canela', 'recall': 'canela', 'tale': 'canela'}
# sonido que acompaña el inicio de cada toma
SHOT_SFX = {'canela': ('canela', .8), 'tale': ('canela', .7), 'advice': ('canela', .8), 'recall': ('canela', .45),
            'goodbye': ('call', .35), 'whisper': ('whisper', .6),
            'mine_gate': ('growl', .25), 'return_nest': ('deliver', .5), 'true_voice': ('call', .8)}

# Mensajes de la historia que aparecen mientras se juega (no pausan el juego).
# El susurro (Acto I): al llevar a la segunda cría al nido.
WHISPER_MESSAGE = ('Mullo',                       # contado desde ella: lo que piensa al oírlo
                   ['«¿Y esa voz? Viene de allá abajo... suena como yo.',
                    'Se me hace conocida... pero no sé por qué».'])
# La Sala del Eco (punto medio): al encontrar a Eco, con su animación.
ECHO_MESSAGE = ('La Sala del Eco',
                ['Mullo encuentra a Eco y por fin escucha la cueva:',
                 'el aire y los rebotes sonaban parecido a su voz.',
                 'Sus crías no se fueron por desobedientes: siguieron a su mamá.'])

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
#   I   'reader'  · Leer la cueva: al llevar al nido a las tres crías de las galerías (minimapa 6 s -> 8 s)
#   II  'decided' · Grito decidido: en la Sala del Eco (recarga del grito 2.3 s -> 1.7 s)
#   III 'air'     · Vuelo con la corriente: al recordar «sigue el aire» cuando despierta Xolthar
#                   (dentro de la corriente el impulso se recarga en 1.8 s en lugar de 2.8 s)
#
# Los momentos que ocurren a mitad de un nivel (susurro, cortina de telarañas, Sala del Eco, punto más bajo,
# clímax) se viven en tiempo real sin texto: suenan, se ven y cambian la mecánica; las cinemáticas de inicio y
# fin de cada acto los cuentan con palabras.
