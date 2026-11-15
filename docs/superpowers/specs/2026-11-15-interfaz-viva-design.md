# Interfaz viva: orbe pensante y pantalla con vida

Fecha: 2026-11-15. Tamaño: cambio mediano, solo en la capa visual (QML) y su documentación.

## Intención

La fase 2 funciona, pero la pantalla de sesión se queda corta como experiencia visual:

- Reposo y despierto se parecen demasiado. Deben distinguirse de un vistazo.
- El orbe central es simple. Jarvis piensa, y pensar implica caos: el centro debe mostrarlo.
- El resto de la pantalla está vacío. Debe parecer que tiene vida.
- Debe haber muchos elementos y distintos entre sí, pero que se unan y se fusionen como una
  sinfonía: variedad con un mismo pulso, no ruido.

## Objetivos

1. Contraste fuerte entre reposo y despierto.
2. Un centro con varias capas distintas que sugieran actividad mental.
3. Elementos repartidos por toda la pantalla.
4. Un mecanismo común que haga que todos los elementos se muevan a la vez.

## Fuera de alcance

- El aspecto de dormido no cambia: fondo oscuro, punto marino y caja de texto.
- El mini orbe del HUD flotante, los paneles, los subtítulos y la caja de texto no cambian.
- No cambia nada fuera de `ui/qml` y de `software/Interfaz/README.md`: ni eventos, ni
  `view_models.py`, ni la secuencia de `preview.py`.

## Lo que haría que fallase aunque funcione

- Que los elementos se vean como efectos sueltos, cada uno a su ritmo.
- Que el fondo distraiga de los paneles o dificulte leer el texto.
- Bajar de 30 fps en el equipo de referencia (RNF-21); el objetivo sigue siendo 60.
- Que en reposo quede movimiento llamativo.

## Enfoques considerados

| Enfoque | Ventaja | Inconveniente |
|---|---|---|
| **A. Elementos QML en GPU con un director común** (elegido) | Usa lo que ya hay (Shape, Repeater, FrameAnimation). Cada elemento es un archivo pequeño y ajustable. | Muchos enlaces de propiedades por fotograma: hay que limitar las cantidades. |
| B. Sombreadores de fragmentos (`ShaderEffect`) | El plasma y el fondo quedarían más ricos con menos elementos. | Qt 6 exige compilar los sombreadores a `.qsb`: paso de compilación nuevo y ajuste más lento. |
| C. `Canvas` a pantalla completa | Libertad total de dibujo. | Se dibuja en CPU: no llega a 60 fps a 1920 × 1080. |

Se elige A porque continúa el diseño actual y permite ajustar cada elemento viéndolo en
`--preview`. Es decisión mía; el propietario no pidió una técnica concreta.

## Diseño

### El director (lo que hace la sinfonía)

El orbe ya tiene propiedades de control y un reloj. Se añaden tres señales que leen **todos**
los elementos, del centro y del fondo:

| Señal | Qué es |
|---|---|
| `energy` | 0–1 según la actividad. Marca velocidad, cantidad visible y brillo. |
| `chaos` | 0–1 según la actividad. Marca la irregularidad: deformación, parpadeo, saltos. |
| `beat` | Latido periódico que nace en el núcleo y se propaga hacia fuera como una onda. Cada elemento se ilumina cuando la onda pasa por su distancia al centro. |

A esto se suman el nivel de la voz (`smoothLevel`) y el color (`main`), que ya existen. Como
todos los elementos comparten reloj, latido, voz y color, se mueven juntos aunque sean
distintos. La onda del latido es lo que une el centro con el fondo.

Valores por actividad (punto de partida; se ajustan viéndolo):

| Propiedad | Reposo | Escuchando / Hablando | Procesando | Esperando |
|---|---|---|---|---|
| `brightness` | 0,22 | 1 | 1 | 1 |
| `tint` (0 cian – 1 marino) | 0,7 | 0 | 0 | 0 |
| `energy` | 0,08 | 0,6 | 1 | 0,45 |
| `chaos` | 0 | 0,35 | 1 | 0,2 |
| Periodo del latido | sin latido | 2,4 s | 0,9 s | 1,8 s, en ámbar |

### Contraste reposo / despierto

- **Reposo**: solo quedan el núcleo quieto y los anillos de datos, lentos, casi marinos, al
  22 %. Sin red, sin satélites, sin ondas, sin glifos y sin partículas. En el fondo quedan
  unos pocos puntos fijos muy tenues, sin enlaces. Los paneles siguen al 50 %.
- **Despierto**: halo más grande y brillante, núcleo casi blanco en el centro, todas las capas
  activas y el fondo en movimiento.

### Elementos del centro (cada uno distinto)

| Elemento | Qué se ve | Cómo sigue al director |
|---|---|---|
| Plasma | Sustituye la esfera lisa: contorno irregular que se deforma, con dos o tres capas translúcidas desfasadas. | `chaos` da la amplitud de la deformación; la voz lo hincha. |
| Red neuronal | Nodos repartidos en una esfera que gira en 3D, con enlaces entre vecinos que se encienden y se apagan como sinapsis. | `chaos` da la frecuencia de disparo; la esfera gira con `energy`. |
| Arcos giroscópicos | Dos o tres elipses inclinadas que giran en planos distintos alrededor del núcleo. | Velocidad con `energy`; se desalinean con `chaos`. |
| Satélites | Puntos brillantes en órbitas excéntricas, con estela. | Velocidad con `energy`; destellan al paso del latido. |
| Ondas de pulso | Anillo fino que nace en el núcleo con cada latido y se expande hasta salir del orbe. | Es el propio `beat`. |
| Glifos | Fragmentos de código y hexadecimales que aparecen y se desvanecen cerca de los anillos. | Aparecen más con `chaos`. |
| Anillos de datos, espectro, arco de «procesando» | Los actuales. Los anillos ganan segmentos que parpadean. | Como hoy. |

### Elementos del fondo (toda la pantalla)

| Elemento | Qué se ve | Cómo sigue al director |
|---|---|---|
| Mini orbes | Unos 45 puntos con halo, de tamaños distintos, a la deriva. Los más grandes y nítidos parecen cercanos; los pequeños y tenues, lejanos. | Deriva con `energy`; se iluminan al paso de la onda. |
| Orbes satélite | Cuatro o cinco orbes pequeños con su propio anillo, a media distancia. | Giran con `energy`; el anillo pasa a ámbar en «esperando». |
| Constelación | Líneas tenues entre mini orbes cercanos. | Opacidad según la distancia y `energy`. |
| Señales | Puntos de luz que viajan por las líneas hacia el núcleo y desde él. Unen visualmente el fondo con el centro. | Frecuencia con `chaos`; con la voz salen del núcleo. |
| Polvo | Puntos diminutos, lentos, que dan profundidad. | Solo `energy`. |
| Retícula | Malla muy tenue que se ondula cuando pasa la onda del latido. | `beat`. |

El fondo se dibuja por debajo de los paneles y con opacidad baja, de modo que no compite con
el texto.

### Transiciones

Se conservan las cuatro (despertar, despertar desde reposo, dormirse a reposo, dormirse y
cerrar) con su duración de 2 s. Las capas nuevas se forman y colapsan con `assembly`, igual
que los anillos: al dormirse, el fondo se retira hacia el centro antes que la estructura.
`energy` y `chaos` se suman a las propiedades que anima cada transición.

### Calidad y movimiento reducido

| `ui.quality` | Qué se dibuja |
|---|---|
| `high` | Todo. |
| `medium` | La mitad de mini orbes, nodos y polvo; sin retícula ni estelas. |
| `low` | Sin fondo, sin red, sin plasma deformado (núcleo liso); anillos sin texto, como hoy. |

Con `reduceMotion` los elementos se muestran quietos y el cambio de estado es un fundido
corto, como hoy. Con la ventana oculta no se anima nada.

## Lo que queda a quien lo construya

- Las cantidades y los valores exactos, dentro del presupuesto de fotogramas.
- La forma concreta del plasma y la colocación de los nodos.
- Cómo se dibujan los enlaces (se sugieren rectángulos girados entre parejas fijas, con la
  opacidad según la distancia, para no recalcular vecinos en cada fotograma).

## Comprobación

- `--preview` recorre todos los estados: revisar cada uno, y con `--debug` el contador de
  fotogramas.
- Las pruebas actuales de la interfaz siguen pasando.
- `software/Interfaz/README.md` queda actualizado: secciones 3 (anatomía y tabla de
  propiedades), 5 (fondo), 10 (calidad) y 11 (lista de comprobación).
