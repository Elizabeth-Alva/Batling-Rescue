# Imágenes con IA para las cinemáticas (opcional)

El juego **ya trae todas las escenas dibujadas por código**. Si quieren una versión con ilustraciones
generadas por IA, basta con guardar la imagen en esta carpeta con el nombre de la escena
(por ejemplo `assets/escenas/dusk.png`). Al iniciar, la cinemática usa la imagen con un paneo lento
y pone el texto encima. Si una imagen no existe, se usa la versión por código.

**Formato:** PNG o JPG, proporción 3:2 (960 × 640 o más grande, por ejemplo 1536 × 1024).
Dejen "aire" arriba (~75 px) y abajo (~110 px), porque ahí van las franjas de cine con el texto.
**Sin texto, sin letras, sin marcas de agua.**

## Estilo común (pégalo al inicio de cada prompt)

> Ilustración digital 2D para un videojuego indie, estilo de siluetas planas con degradados suaves y luz
> ambiental, parecido a un cuento ilustrado nocturno. Formas simples, sin detalle fotorrealista.
> Protagonista: Mullo, una murciélaga joven y pequeña de pelaje violeta muy oscuro, casi negro, orejas grandes
> y puntiagudas, alas de membrana con los dedos marcados y un borde lila, ojos color ámbar brillantes.
> Crías: murciélagos diminutos y redondos de pelaje violeta rosado y ojitos grandes. Tono apto para 10+ años: tenso pero tierno, sin sangre ni violencia.
> Composición horizontal 3:2, sin texto.

### Rasgos de los personajes (agrega el que aparezca en la escena)

- **Abuela Canela:** murciélaga anciana, un poco más grande que Mullo, pelaje gris canela y hocico canoso,
  una muesca en la oreja izquierda, alas con cicatrices pequeñas, ojos ámbar opacos. Planea más de lo que
  aletea; en reposo cuelga boca abajo con las alas cerradas, como los murciélagos reales.
- **Chispa:** cría redonda y diminuta, pelaje violeta rosado, ojos grandes y un mechón naranja en el pecho.
- **Xolthar, el Gran Ciempiés:** ciempiés enorme de dieciséis segmentos, coraza negra con vetas rojas, púas,
  patas articuladas y mandíbulas grandes; despierto, ojos rojos y un brillo rojo. Formas angulosas (peligro),
  nunca sangre.
- **Piel vieja de Xolthar:** la muda vacía del ciempiés, una silueta pálida y quieta, tan larga como una vagoneta.

Las formas dicen quién es quién: Mullo, Canela y las crías son redondas y de ojos cálidos; los ciempiés son
angulosos, con púas y ojos rojos. Paleta por acto: verde de hongos (I), azul índigo (II), café ámbar (III).

Para que **no se exagere el alcance del juego**: pidan siempre siluetas y luz ambiental (como en el juego),
no escenas hiperdetalladas ni personajes en 3D. Si la imagen se ve mucho más "rica" que el juego, bájenle con
"minimalista, pocas formas, paleta limitada".

## Escenas

Están en el orden de la historia (Propuesta, sección 6).

| Archivo | Escena | Prompt (después del estilo común) |
|---|---|---|
| `dusk.png` | Prólogo 1 | Atardecer de sequía en un campo seco con tierra agrietada y un árbol seco; a la derecha un acantilado con la boca de una cueva; la colonia de murciélagos sale junta, sin dispersarse; Mullo y la Abuela Canela vuelan entre ellas. Cielo violeta a naranja, sol bajo. |
| `tale.png` | Prólogo 2 | En el árbol seco, la Abuela Canela cuelga boca abajo con las alas cerradas y cuenta un cuento; sobre ella, una nube de cuento translúcida muestra a un ciempiés gigante dormido y enroscado; los murciélagos grandes (Mullo entre ellos) cuelgan de las ramas y escuchan. |
| `advice.png` | Prólogo 3 | Misma rama del árbol seco al atardecer: la Abuela Canela, colgada boca abajo, da un consejo; Mullo cuelga a su lado y asiente; rizos de aire cruzan la escena. |
| `canela.png` | Prólogo 4 | La Abuela Canela sigue colgada boca abajo con las alas cerradas en el árbol seco y avisa a todas; varias murciélagas ya salen volando a cazar sobre el campo seco; Mullo escucha colgada en la rama. |
| `search.png` | Prólogo 5 | El cielo se apaga sobre el campo seco; la colonia ya está lejos; Mullo vuela sola cerca del acantilado buscando insectos y no encuentra nada (ondas de ecolocación vacías). |
| `goodbye.png` | Prólogo 6 | Desde dentro de la cueva, cielo violeta en la salida; Mullo flota en el borde de un nido de ramitas con 10 crías que la miran (una con mechón naranja en el pecho). |
| `leaving.png` | Prólogo 7 | Afuera de la cueva al anochecer: acantilado con la boca de la cueva, campo seco y agrietado, árbol seco, luna creciente y primeras estrellas; Mullo sale volando de la boca y se aleja, mirando una vez hacia atrás. |
| `empty_nest.png` | Acto I · inicio 1 | Interior de cueva a medianoche, una abertura arriba a la izquierda deja ver una luna creciente; un haz de luna cae sobre un nido vacío; marcas de garras bajan hacia la oscuridad; Mullo aterriza cansada. |
| `debate.png` | Acto I · inicio 2 | Mullo en el borde del nido mirando hacia abajo, a un abismo oscuro con puntos de hongos verdes luminosos muy lejos; una onda rosada de sonido (un chillido conocido) sube desde el fondo. |
| `gallery.png` | Acto I · inicio 3 | Galería de cueva con hongos verdes que dan luz; en el suelo, piedritas movidas y rasguños que marcan un camino; una cortina de telarañas al fondo; Mullo vuela siguiendo el rastro. |
| `nest_three.png` | Primer punto de giro 1 | El nido con tres crías (Chispa, Bruno dormido y Lía); Mullo a un lado; ondas de sonido rosadas vienen desde abajo. |
| `descent.png` | Primer punto de giro 2 | Pozo vertical de roca; Mullo se lanza en picada hacia abajo; arriba hongos verdes azulados, abajo un brillo azul índigo de un lago. |
| `lake.png` | Acto II · inicio | Lago subterráneo negro y quieto con islotes de roca y niebla baja; casi no hay luz; Mullo vuela bajo sobre el agua; salamandras pálidas se hunden al verla pasar. Azul índigo casi negro. |
| `mine_far.png` | Segundo punto de giro 1 | Desde el lago se ve a lo lejos la boca de una mina con marco de madera; de ahí salen ondas rosadas de chillidos; salamandras en el agua. |
| `mine_gate.png` | Segundo punto de giro 2 | Entrada a una mina abandonada dentro de la cueva: marcos de madera en perspectiva, rieles oxidados, lámparas apagadas, pares de ojos rojos de cazadores en la oscuridad; en el suelo, junto a los rieles, la piel vieja de un ciempiés gigante, pálida y vacía, tan larga como una vagoneta; Mullo se detiene a mirarla. Marrón y ámbar. |
| `mine.png` | Acto III · inicio | Túnel de mina abandonada en perspectiva, vigas de madera, rieles, una vagoneta oxidada, polvo flotando con luz ámbar muy tenue y ojos rojos de cazadores al fondo; Mullo vuela por el túnel. |
| `return_nest.png` | Final 1 | Interior de la cueva antes del amanecer, la abertura se pinta de violeta; Mullo llega volando al nido con dos crías gemelas (una dorada y una rojiza); en el nido la esperan las otras ocho. |
| `dawn_nest.png` | Final 2 | Boca de la cueva antes del amanecer, cielo naranja sin sol todavía; la colonia sale en una cinta de murciélagos; la Abuela Canela es la última en la boca de la cueva; en el suelo, el nido con 10 crías asustadas que dudan; Mullo se voltea a verlas. |
| `true_voice.png` | Final 3 | Mullo al centro con las alas abiertas, ondas doradas y limpias salen de ella; alrededor ecos grises y deformes que se desvanecen; abajo, 10 crías en fila; la del centro (Chispa, mechón naranja en el pecho) contesta primero con una onda rosada. Fondo cálido. |
| `departure.png` | Final 4 | Paisaje antes del amanecer, el sol todavía bajo el horizonte; una larga cinta de murciélagos sale del acantilado hacia el horizonte; Mullo vuela con 10 crías pequeñas detrás y la Abuela Canela planea cerca. |

## Portada (opcional)

`tools/make_cover.py` exporta la portada en `assets/promo/` (portada, banner para itch.io e icono) usando el
logo oficial `assets/logo.png`. Si quieren un fondo con IA, usen este prompt y pongan encima el logo:

> Boca de cueva gigante que enmarca un cielo de madrugada (índigo arriba, violeta y un filo naranja abajo),
> luna creciente, una colonia de murciélagos en remolino; al centro Mullo con las alas abiertas, ojos ámbar,
> borde de luz lila; hongos verdes luminosos en las rocas de los lados y diez pares de ojitos rosados en la
> oscuridad de abajo. Espacio libre al centro para el logo. Sin texto.
