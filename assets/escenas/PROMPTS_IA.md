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
> Protagonista: Mullo, una murciélaga joven y pequeña, silueta negra violácea con orejas grandes,
> alas membranosas con dedos marcados y ojos ámbar brillantes. Crías: murciélagos diminutos y redondos
> con ojitos rosados. Tono apto para 10+ años: tenso pero tierno, sin sangre ni violencia.
> Composición horizontal 3:2, sin texto.

### Rasgos de los personajes (agrega el que aparezca en la escena)

- **Abuela Canela:** murciélaga anciana, un poco más grande que Mullo, pelaje gris canela y hocico canoso,
  una muesca en la oreja izquierda, alas con cicatrices pequeñas, ojos ámbar opacos. Planea más de lo que
  aletea; en reposo cuelga boca abajo con las alas cerradas, como los murciélagos reales.
- **Chispa:** cría redonda y diminuta, pelaje violeta rosado, ojos grandes y un mechón naranja en la cabeza.
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

| Archivo | Escena | Prompt (después del estilo común) |
|---|---|---|
| `dusk.png` | Prólogo 1 | Atardecer de sequía en un paisaje árido con tierra agrietada y un árbol seco; a la derecha un acantilado con la boca de una cueva; una nube de murciélagos sale a cazar; Mullo da vueltas cerca del acantilado buscando comida. Cielo violeta a naranja, sol bajo. |
| `canela.png` | Prólogo 2 | Dentro de la cueva, junto a la boca que enmarca un atardecer naranja: la Abuela Canela cuelga boca abajo con las alas cerradas y habla a la colonia; varios murciélagos cuelgan del techo y otros salen volando; Mullo la escucha a un lado. |
| `goodbye.png` | Prólogo 4 | Desde dentro de la cueva, cielo violeta en la salida; Mullo flota en el borde de un nido de ramitas con 10 crías que la miran (una con mechón naranja); al fondo, en la roca, la Abuela Canela colgada. |
| `advice.png` | Prólogo 3 | La Abuela Canela, colgada del techo de roca, habla a toda la colonia (muchos murciélagos colgados escuchan); Mullo, en primer plano, escucha con atención; rizos de aire suben hacia la salida y muy al fondo un brillo rojo apenas visible. |
| `leaving.png` | Prólogo 5 | Afuera de la cueva al anochecer: acantilado con la boca de la cueva, campo seco y agrietado, árbol seco, luna creciente y primeras estrellas; Mullo sale volando de la boca y se aleja, mirando una vez hacia atrás. |
| `empty_nest.png` | Acto I · inicio | Interior de cueva a medianoche, una abertura arriba a la izquierda deja ver una luna creciente y cielo azul oscuro; un haz de luna cae sobre un nido vacío; marcas de garras bajan hacia la oscuridad; Mullo aterriza. |
| `debate.png` | Acto I · debate | Mullo en el borde del nido mirando hacia abajo, a un abismo oscuro con puntos de hongos verdes luminosos muy lejos; una onda rosada de sonido sube desde el fondo. |
| `nest_three.png` | Primer punto de giro 1 | El nido con tres crías dormidas; Mullo a un lado, de pie; ondas de sonido rosadas vienen desde abajo de la escena. Cielo de la abertura más violeta. |
| `descent.png` | Primer punto de giro 2 | Pozo vertical de roca; Mullo se lanza en picada hacia abajo; arriba hongos verdes azulados, abajo un brillo azul índigo de un lago. |
| `lake.png` | Acto II · inicio | Lago subterráneo negro y quieto con islotes de roca y niebla baja; algas verdes que brillan débilmente en la orilla; Mullo vuela bajo, su reflejo en el agua; ojos naranjas de escarabajos en la orilla. Azul índigo casi negro. |
| `near_dawn.png` | Segundo punto de giro 1 | Techo de roca con una grieta por donde entra la primera luz gris del amanecer; Mullo vuela mirando la luz: ya casi amanece. |
| `mine_gate.png` | Segundo punto de giro 2 | Entrada a una mina abandonada dentro de la cueva: marcos de madera en perspectiva, rieles oxidados, lámparas apagadas, tres pares de ojos rojos en la oscuridad; en el suelo, junto a los rieles, la piel vieja de un ciempiés gigante, pálida y vacía, tan larga como una vagoneta; Mullo se detiene a mirarla. Marrón y ámbar. |
| `mine.png` | Acto III · inicio 1 | Túnel de mina abandonada en perspectiva, vigas de madera, rieles, una vagoneta oxidada, polvo flotando con luz ámbar muy tenue; Mullo vuela por el túnel. |
| `recall.png` | Acto III · inicio 2 | En el túnel de la mina, rizos de aire fresco corren hacia la salida; Mullo flota pensativa y, en un recuerdo luminoso y translúcido, aparece la Abuela Canela colgada hablando. |
| `escape.png` | Clímax | Túnel de mina hacia una luz cálida; Mullo vuela con dos crías gemelas; la corriente de aire la empuja hacia la salida; detrás, abajo, la cabeza de Xolthar con ojos rojos y mandíbulas abiertas. |
| `dawn_nest.png` | Resolución 1 | Boca de la cueva antes del amanecer, cielo naranja y dorado; la colonia empieza a salir en una cinta de murciélagos; la Abuela Canela cuelga en el borde de la boca, la última en irse; en el suelo, el nido con 10 crías que dudan; Mullo llega volando. |
| `true_voice.png` | Resolución 2 | Mullo al centro con las alas abiertas, ondas doradas y limpias salen de ella; alrededor ecos grises y deformes que se desvanecen; abajo, 10 crías en fila; la del centro (Chispa, mechón naranja) contesta primero con una onda rosada. Fondo cálido. |
| `departure.png` | Imagen final | Paisaje al amanecer con el sol saliendo; una larga cinta de murciélagos sale del acantilado hacia el horizonte; Mullo vuela con 10 crías pequeñas detrás y la Abuela Canela planea cerca. |

## Portada (opcional)

`tools/make_cover.py` exporta la portada dibujada por código en `assets/promo/` (portada, banner para itch.io
e icono). Si quieren una portada con IA, usen este prompt y pongan encima el logo del juego:

> Boca de cueva gigante que enmarca un cielo de madrugada (índigo arriba, violeta y un filo naranja abajo),
> luna creciente, una colonia de murciélagos en remolino; al centro Mullo con las alas abiertas, ojos ámbar,
> borde de luz lila; hongos verdes luminosos en las rocas de los lados y diez pares de ojitos rosados en la
> oscuridad de abajo. Espacio libre arriba para el título. Sin texto.
