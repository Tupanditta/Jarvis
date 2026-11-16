# Diseño de la interfaz

Diseño visual del asistente. El comportamiento (qué ventana se muestra y cuándo, qué paneles existen, cómo llegan los datos) está en [hud.md](../Modulos/Infraestructura/hud.md). Las secciones 3 y 4 conservan el diseño original del autor para el orbe y sus animaciones; el resto lo completa para que toda la interfaz sea coherente.

## 1. Principios

La interfaz debe ser **atractiva y, a la vez, profesional** (RNF-29). En la práctica:

1. **Un solo protagonista.** El orbe es el único elemento espectacular. Todo lo demás es sobrio: texto claro, líneas finas, mucho espacio vacío.
2. **Luz sobre oscuridad.** Fondo casi negro; el color aparece solo donde aporta información.
3. **Paleta corta.** Un color principal (cian) y tres colores de estado. Nada más.
4. **El movimiento significa algo.** Cada animación comunica un cambio de estado. No hay movimiento decorativo en los paneles.
5. **Legible de un vistazo.** El usuario mira la interfaz un segundo mientras trabaja en otra cosa: estado, última orden y resultado deben leerse sin esfuerzo.
6. **Coherencia total.** Todos los valores salen de los tokens de la sección 2; ningún componente define colores o tamaños propios.

## 2. Sistema de diseño

Los tokens viven en `ui/qml/Theme.qml`.

### Color

| Token | Valor | Uso |
|---|---|---|
| `bg.base` | `#05070B` | Fondo de la pantalla de sesión (gris espacial casi negro). |
| `bg.panel` | `#0C121C` al 78 % | Fondo de paneles y del HUD (translúcido). |
| `bg.raised` | `#121B28` | Tarjetas dentro de un panel. |
| `line.soft` | `#1B2A3A` | Bordes y separadores de 1 px. |
| `line.strong` | `#2A4560` | Borde del panel activo. |
| `primary` | `#22D3EE` | Cian principal: orbe, acentos, elemento activo. |
| `primary.bright` | `#7DF3FF` | Centro del núcleo, destellos. |
| `primary.hot` | `#E8FDFF` | Blanco cian: centro del plasma al máximo brillo y sinapsis al dispararse. |
| `primary.dim` | `#0E7490` | Elementos del orbe en reposo. |
| `primary.deep` | `#0B2A4A` | Azul marino profundo: final de la animación de dormirse. |
| `text.primary` | `#E6F1F8` | Texto principal. |
| `text.secondary` | `#8FA6B8` | Texto secundario, etiquetas. |
| `text.muted` | `#5B7083` | Texto atenuado, horas, no reconocido. |
| `status.pending` | `#F5B544` | Tarea `pendiente`. |
| `status.done` | `#34D399` | Tarea `completado`. |
| `status.error` | `#F2555A` | Tarea `error`. |

Los colores de estado solo se usan para los estados de tarea y el diálogo en espera (`status.pending`). Contraste mínimo del texto sobre su fondo: 4,5 : 1.

### Tipografía

Fuentes libres (licencia OFL), incluidas en `ui/assets/fonts/`; no se descargan.

| Token | Fuente | Uso |
|---|---|---|
| `font.display` | Rajdhani SemiBold, mayúsculas, espaciado 8 % | Estado del asistente, títulos de panel, marca. |
| `font.body` | Inter Regular / Medium | Todo el texto. |
| `font.mono` | JetBrains Mono Regular | Rutas, listados, salida de comandos, datos de los anillos. |

Tamaños (px lógicos): 11 (etiquetas), 13 (texto secundario), 15 (texto), 18 (subtítulos, títulos de panel), 24 (estado en la pantalla de sesión), 40 (reloj). Interlineado 1,4.

### Espaciado, forma y profundidad

- Escala de espaciado: 4, 8, 12, 16, 24, 32, 48.
- Radio: 10 en paneles, 6 en tarjetas y distintivos.
- Bordes de 1 px `line.soft`. El panel activo usa `line.strong` y cuatro esquinas marcadas en `primary` (trazos de 12 px), el único guiño «HUD» de los paneles.
- Sin sombras. La profundidad se consigue con la translucidez de `bg.panel`.
- Resplandor (`MultiEffect`): solo en el orbe y en el punto de estado de una tarea `pendiente`.
- Neón: un trazo de luz de grosor uniforme (`neon.width`, 1,5 px) que recorre un borde a `neon.speed` (70 px/s), con un resplandor tenue, la cabeza casi blanca y una cola que se desvanece. Solo en la caja de texto y en el borde de las ventanas flotantes.

### Movimiento

| Token | Valor | Uso |
|---|---|---|
| `motion.transition` | 2000 ms | Animaciones de despertar y dormirse (RF-80, RF-81). |
| `motion.panel` | 220 ms, salida suave | Aparición y cambio de panel, expansión del HUD. |
| `motion.state` | 400 ms | Cambio de color o brillo por cambio de actividad. |
| `motion.level` | 80 ms | Suavizado del nivel de audio. |

Con ⚙ `ui.reduce_motion`, las transiciones del orbe se sustituyen por un fundido de 400 ms y se detienen los giros.

### Iconos

Trazo fino de 1,5 px, en `text.secondary`, de un único conjunto libre incluido en `ui/assets/icons/` (SVG). Un icono por módulo y por tipo de elemento (archivo, carpeta, aplicación, página).

## 3. El orbe

### Aspecto general (diseño del autor)

El fondo de la pantalla completa es negro puro o gris espacial muy oscuro, para contrastar con los elementos luminosos. El color principal es cian/azul neón. El elemento central es una esfera u orbe holográfico tridimensional rodeado de anillos concéntricos con datos, números y líneas de código. Los elementos tienen un efecto visual de fusión aditiva, para simular luz proyectada pura.

Referencia: [referencia-orbe-general.jpg](referencia-orbe-general.jpg).

### Anatomía

Tamaños relativos a `D` = 42 % del lado menor de la pantalla. De dentro afuera:

| Capa | Radio | Descripción |
|---|---|---|
| Halo | 0,60 D | Resplandor difuso detrás de todo; da la sensación de luz proyectada. Crece y se aviva con `energy`. |
| Núcleo (plasma) | 0,16 D | Tres capas translúcidas de contorno irregular que se deforman cada una a su ritmo, de `primary.hot` en el centro a `primary` en la membrana. La deformación crece con `chaos` y con la voz. Liso en calidad baja. |
| Red neuronal | 0,20 D | Nodos repartidos en una esfera que gira en 3D alrededor del núcleo, unidos a sus vecinos por enlaces que se encienden y se apagan como sinapsis. 28 nodos en calidad alta, 14 en media, ninguno en baja. |
| Arcos giroscópicos | 0,27 – 0,32 D | Tres arcos inclinados que giran en planos distintos. `chaos` los desalinea. |
| Anillo de espectro | 0,24 D | 64 barras radiales cuya longitud sigue el nivel de audio (ver «Reacción a la voz»). |
| Anillo de datos 1 | 0,30 D | Línea fina con marcas cada 5°. Gira en sentido horario. |
| Anillo de datos 2 | 0,36 D | Arcos segmentados con números y valores hexadecimales en `font.mono`. Gira en sentido antihorario. |
| Anillo de datos 3 | 0,43 D | Línea discontinua con fragmentos de código en cuatro puntos. Gira en sentido horario, más lento. |
| Satélites | 0,47 – 0,65 D | Cinco puntos brillantes en órbitas excéntricas, con estela en calidad alta. Destellan al paso del latido. |
| Glifos | 0,47 – 0,67 D | Fragmentos de código en `font.mono` que aparecen y se desvanecen, cada vez en un sitio. Se ven más con `chaos`. 10 en calidad alta, 5 en media, ninguno en baja. |
| Partículas | hasta 0,70 D | Puntos pequeños que se alejan despacio del centro, muy tenues. 120 en calidad alta, 60 en media, ninguna en baja. |
| Onda del latido | hasta 2,5 D | Anillo fino que nace en el núcleo con cada latido y cruza toda la pantalla. |

Los anillos de datos llevan además cinco segmentos cada uno que parpadean a ritmos distintos.

### El director

Hay muchos elementos y son distintos entre sí, pero se mueven como uno solo porque todos, los del orbe y los del fondo de la pantalla (sección 5), leen las mismas señales del componente `Orb`:

| Señal | Qué es |
|---|---|
| `energy` | 0–1 según la actividad. Marca la velocidad y el brillo de los elementos vivos. |
| `chaos` | 0–1 según la actividad. Marca la irregularidad: deformación del plasma, sinapsis, glifos, señales. |
| Latido (`beat`) | Onda periódica que nace en el núcleo y se propaga hacia fuera. Cada elemento se ilumina cuando la onda pasa por su distancia al centro. Es lo que une el centro con el fondo. |
| Nivel de la voz y color | Los mismos para todos. En «esperando», los acentos pasan a `status.pending`. |

Las capas vivas (red, arcos, satélites, glifos, partículas, segmentos y fondo) solo se ven con el asistente despierto.

Los datos de los anillos son decorativos y fijos (no muestran información real), en `primary` al 60 %.

**Fusión aditiva:** sobre fondo negro, las capas se superponen sumando luz. Se consigue con capas translúcidas y resplandor; donde haga falta suma real, con un sombreador sencillo. El criterio de aceptación es visual: donde dos capas se cruzan, la zona es más clara, nunca más oscura.

### Aspecto según la actividad (diseño del autor, ampliado)

| Actividad | Aspecto |
|---|---|
| **Escuchando** | Atención activa. El orbe pulsa con una «respiración» luminosa (resplandor interior que aumenta y disminuye, periodo de 2,4 s). El asistente atiende las órdenes escritas. El plasma ondula despacio y el espectro no se ve: no hay audio que seguir. Los anillos giran a velocidad media-alta y todas las capas vivas están activas. Late cada 2,4 s. Brillo 100 %. |
| **Hablando** | Igual que escuchando, y además el núcleo y el espectro reaccionan a la voz del asistente: ondas de espectro a lo largo del anillo interior, sincronizadas con su volumen. Incluye las frases que coinciden con la animación de dormirse («A su disposición.», «Buenas noches. Sesión cerrada.»). |
| **Procesando** | Entre el fin de la orden y la respuesta. El espectro se sustituye por un arco luminoso que recorre el anillo interior (una vuelta cada 1,2 s) y los anillos giran más deprisa. Es el momento de más caos: el plasma se deforma al máximo, las sinapsis se disparan sin parar, el fondo acelera y el latido baja a 0,9 s. Indica «trabajando» sin texto. |
| **Esperando** | Más calmado que escuchando, con el anillo de datos 2, la onda del latido, la retícula y los orbes satélite en `status.pending`: el asistente ha hecho una pregunta. Late cada 1,8 s. |
| **Reposo** | El orbe se mantiene estable en el centro, con una flotación muy sutil (±4 px, periodo de 6 s). Sin picos de espectro ni reacción al audio una vez terminada la frase del asistente: el núcleo queda quieto. El giro de los anillos es constante pero mucho más lento. Solo quedan el núcleo y los anillos de datos, casi en marino, al 22 %: sin red, arcos, satélites, glifos, partículas ni latido. El contraste con el asistente despierto se nota de un vistazo; aun así el brillo es persistente: el sistema está latente, no apagado. |

Valores de control (cada uno es una propiedad animable del componente `Orb`):

| Propiedad | Reposo | Escuchando / Hablando | Procesando | Esperando |
|---|---|---|---|---|
| `brightness` | 0,22 | 1,0 | 1,0 | 1,0 |
| `spin` (°/s de los anillos 1, 2 y 3) | 3 / −2 / 1 | 18 / −12 / 8 | 40 / −30 / 20 | 18 / −12 / 8 |
| `breath` (amplitud del resplandor) | 0 | 0,25 | 0,1 | 0,25 |
| `spectrum` (visibilidad del espectro) | 0 | 1 | 0 (arco) | 1 |
| `assembly` (0 colapsado – 1 formado) | 1 | 1 | 1 | 1 |
| `tint` (0 cian – 1 marino) | 0,6 | 0 | 0 | 0 |
| `energy` | 0,08 | 0,6 | 1 | 0,45 |
| `chaos` | 0 | 0,35 | 1 | 0,2 |
| `beatRate` (latidos por segundo) | 0 | 1 / 2,4 | 1 / 0,9 | 1 / 1,8 |
| `particles` (capas vivas) | 0 | 1 | 1 | 1 |

Referencia de escucha: [referencia-escucha-espectro.jpg](referencia-escucha-espectro.jpg).

### Reacción a la voz (RF-83)

- La interfaz recibe un nivel de 0 a 1, 20 veces por segundo, con su origen (asistente o ninguno), y lo suaviza con `motion.level`.
- **Núcleo y halo:** la escala del núcleo es `1 + 0,2 × nivel` y su resplandor crece con el nivel; el halo se hincha hasta un 12 %.
- **Ondas de la voz:** mientras suena una frase, dos anillos seguidos salen del núcleo (1,3 por segundo) y cruzan la pantalla; su grosor y su brillo siguen al nivel. Se suman a la onda del latido (`wave`), así que los elementos del fondo y el borde de las ventanas se encienden a su paso.
- **Neón:** los trazos de la caja de texto y de las ventanas brillan más con el nivel y corren hasta 2,6 veces más rápido mientras dura la frase (la velocidad sigue a la frase, no a cada sílaba, para que no avancen a tirones).
- **Espectro:** las barras se alargan con el nivel (hasta 0,12 D); la longitud de cada barra es `nivel × perfil[i]`, donde `perfil` es un patrón fijo de 64 valores, simétrico y suave, que se desplaza lentamente alrededor del anillo. El resultado se percibe como un ecualizador sincronizado con el volumen, sin necesidad de analizar frecuencias.
- Con nivel 0 (el asistente no habla), el espectro no se ve.

## 4. Animaciones de transición

Cada una dura 2 s fijos y empieza a la vez que su frase de voz, sin esperar a que la frase termine.

### Despertar (diseño del autor)

Se muestra al abrir la sesión y al volver a escuchar desde reposo.

Es un estallido. La pantalla pasa de vacío absoluto a iluminarse en dos tiempos: primero la masa se concentra en el centro y el punto del modo dormido se convierte en una masa con vida; después estalla, y de ese estallido salen los anillos y todos los componentes de la interfaz en 360 grados. Los anillos giran en direcciones opuestas y se «ensamblan» mediante interpolación de escala y rotación hasta formar el núcleo central estabilizado.

| Tiempo | Qué ocurre |
|---|---|
| 0 – 1,0 s | **Concentración.** Materia que cae en espiral hacia el centro (trazos que se alargan al acelerar y anillos que se cierran sobre el núcleo: `inflow`). El núcleo crece desde el punto (`mass`), se agita (`chaos` alto) y vira del marino al cian. Opacidad global de 0 a 100 %. |
| 0,8 – 1,0 s | El núcleo se comprime (0,72) justo antes de estallar. |
| 1,0 s | **Estallido.** Destello, el núcleo salta a 1,35 y vuelve a 1, y un anillo de luz grueso sale del centro. Empieza el primer latido, cuya onda cruza toda la pantalla. |
| 1,0 – 1,5 s | Los anillos salen despedidos desde el centro, escalonados del interior al exterior, con un leve rebasamiento: `assembly` de 0 a 1. El fondo vivo sale del núcleo con ellos. Los giros arrancan muy deprisa. |
| 1,0 – 2,0 s | Estabilización: aparecen las capas vivas y el espectro, y energía, caos, giros y latido convergen a los valores de «escuchando». |
| 1,0 – 1,8 s | Los paneles laterales aparecen con un fundido (solo al abrir la sesión). |

**Desde reposo**, el orbe ya está formado: no hay punto de luz ni vacío. Las propiedades pasan de sus valores de reposo a los de escucha en 2 s, y un anillo de luz fino se expande una vez desde el núcleo hacia fuera, como eco del destello.

Referencia: [referencia-orbe-general.jpg](referencia-orbe-general.jpg).

### Dormirse (diseño del autor)

Se muestra al pasar a reposo y al cerrar la sesión.

Es un efecto de colapso, inverso al despertar. Toda la estructura geométrica cae hacia el centro, absorbida por el núcleo. A la vez, el cian brillante se degrada hacia un azul marino profundo.

**Variante reposo** (al pasar a reposo): un colapso contenido.

| Tiempo | Qué ocurre |
|---|---|
| 0 – 0,8 s | Los anillos frenan (entrada suave); el espectro se desvanece, salvo que el asistente siga hablando. Las capas vivas se apagan. |
| 0,4 – 1,6 s | La estructura se contrae hasta 0,8 y vuelve a 1. `tint` avanza hacia el marino. |
| 1,6 – 2,0 s | El orbe se asienta en su aspecto de reposo. |

**Variante cierre** (al cerrar la sesión): el núcleo se vuelve un agujero negro y lo atrae todo.

| Tiempo | Qué ocurre |
|---|---|
| 0 – 0,5 s | Se abre el horizonte en el centro: un disco negro con un filo de luz que se traga el núcleo (`horizon`). Empieza a caer materia en espiral (`inflow`). |
| 0 – 1,5 s | Los anillos no frenan: giran cada vez más deprisa mientras caen. |
| 0,25 – 1,6 s | Toda la estructura cae hacia el centro, cada vez más deprisa, del exterior al interior (`assembly` de 1 a 0), y el fondo vivo con ella. `tint` avanza hacia el marino. Los paneles se apagan. |
| 1,2 – 1,6 s | El horizonte se cierra sobre sí mismo. |
| 1,6 – 2,0 s | La singularidad: una chispa que se apaga. Queda el punto del modo dormido. |

En el reposo `assembly` termina en 1 (queda formado, tenue y lento) y en el cierre en 0 (desaparece). En el paso a reposo la estructura se contrae hasta 0,8 a mitad de la animación y vuelve a 1, de modo que se percibe el colapso sin que el orbe desaparezca. Mientras suena la frase («A su disposición.», «Buenas noches. Sesión cerrada.») el núcleo sigue reaccionando a la voz.

Referencia: [referencia-dormirse-colapso.jpg](referencia-dormirse-colapso.jpg).

### Fundido entre animaciones

El orbe no tiene animaciones cerradas que se «reproducen»: tiene propiedades de control (`brightness`, `spin`, `breath`, `spectrum`, `assembly`, `tint`, `energy`, `chaos`, `beatRate`, y las de las transiciones: `mass`, `inflow`, `horizon`) y cada fase fija sus valores finales. Una transición siempre parte de los valores actuales. Por eso, si llega una transición con otra en curso, la nueva continúa desde donde estaba la anterior, sin saltos; en particular, «Hey Jarvis» durante la animación de cierre funde el colapso con el despertar sin que la pantalla llegue a ocultarse.

## 5. Pantalla de sesión

Pantalla completa, fondo `bg.base`. Referencia a 1920 × 1080; los márgenes y columnas se reducen proporcionalmente en pantallas menores (mínimo 1366 × 768).

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ JARVIS · 2026-11-14 ★                                    ● ESCUCHANDO  18:32 │
│                                                                              │
│ ┌ ACTIVIDAD ───────────┐                               ┌ COMANDOS ─────────┐ │
│ │ ● cd proyectos  18:31│              ·  ·             │ D:\Proyectos      │ │
│ │ ● abrir VS Code 18:31│          ╭─────────╮          │ ───────────────── │ │
│ │ ◐ git status    18:32│        ╭─┤  ORBE   ├─╮        │ ▸ jarvis          │ │
│ │                      │        ╰─┤         ├─╯        │ ▸ web             │ │
│ │                      │          ╰─────────╯          │   notas.txt       │ │
│ │                      │              ·  ·             │                   │ │
│ └──────────────────────┘                               └───────────────────┘ │
│                                                                              │
│                        «ejecuta git status»                                  │
│                        Ejecutando git status.                                │
│              ┌──────────────────────────────────────────────┐                │
│              │ Escriba una orden                            │                │
│              └──────────────────────────────────────────────┘                │
└──────────────────────────────────────────────────────────────────────────────┘
```

| Zona | Contenido |
|---|---|
| Barra superior (48 px de margen) | Izquierda: marca «JARVIS» en `font.display`, nombre de la sesión y estrella si es importante. Derecha: punto y etiqueta del estado del asistente, y hora. |
| Columna izquierda (360 px) | Panel de actividad. |
| Centro | El orbe, centrado en la pantalla. |
| Columna derecha (420 px) | Panel activo. Vacía hasta que un módulo activa un panel. El panel de diálogo se superpone a ella mientras hay una pregunta. |
| Franja inferior | Subtítulos, centrados, ancho máximo 900 px: la última orden entre comillas en `text.secondary` (en `text.muted` y con la marca «no reconocido» si lo es) y, debajo, la última respuesta en `text.primary`, tamaño 18. Se desvanecen a los 6 s. |
| Caja de texto | Bajo los subtítulos, centrada, ancho máximo 450 px y 40 px de alto: una cápsula de una línea, fondo `bg.panel`, borde `line.soft` (`line.strong` con el foco), marca de entrada «›» en `primary`, texto en `text.primary` y texto de ayuda en `text.muted`. Dos trazos de neón recorren su borde: lentos y tenues en dormido y en reposo, vivos con la sesión despierta, más brillantes con el foco. Es la única entrada de órdenes ([entrada-texto.md](../Modulos/Infraestructura/entrada-texto.md)). Tiene el foco siempre que la pantalla es la ventana activa. No se atenúa en reposo. |

En reposo, los paneles y los subtítulos bajan su opacidad al 50 %.

### Marcos de las ventanas flotantes

Cada ventana declara su forma de marco en el registro (`ui/workspace.py`, campo `style`). La forma fija también la textura del fondo. Dos ventanas pueden compartir forma.

| Forma | Marco | Fondo | Ventanas |
|---|---|---|---|
| `round` | Cuatro esquinas redondeadas (radio 12). | Resplandor suave que cae desde la cabecera. | Actividad |
| `cut` | Chaflán de 16 px arriba a la izquierda y abajo a la derecha (hace de asa de tamaño). | Líneas de barrido, como una terminal. | Comandos, Historial |
| `leaf` | Esquinas alternas: radio 16 y radio 3. | Retícula de puntos. Dos trazos de neón cortos. | Aperturas, Búsqueda |
| `bracket` | Recto, con cuatro esquinas marcadas por fuera que se abren con el latido. | Trama diagonal en la esquina inferior izquierda. | Ayuda |

Un trazo de neón recorre el borde de cada ventana: más rápido y brillante en la que está encima, encendido al paso del latido y de las ondas de la voz, apagado en reposo. La esquina superior derecha nunca va en chaflán: ahí está el botón de cerrar. Sin aceleración gráfica el marco es un rectángulo liso y el neón no avanza.

### Fondo vivo

Toda la pantalla tiene vida mientras el asistente está despierto. El fondo se dibuja por debajo del orbe y de los paneles, con poca opacidad, y no tiene reloj propio: lo mueve el director del orbe (sección 3).

| Elemento | Descripción |
|---|---|
| Retícula | Malla de puntos muy tenue, centrada en el orbe, que se ondula al paso del latido. Solo en calidad alta. |
| Polvo | Puntos diminutos que cruzan la pantalla muy despacio; los cercanos, más deprisa. 70 en calidad alta, 35 en media. |
| Constelación | Mini orbes con halo, de tamaños distintos, a la deriva (45 en calidad alta, 22 en media), unidos a sus vecinos por líneas tenues por las que viajan señales. Se iluminan al paso del latido. Ninguno queda dentro del orbe. |
| Orbes satélite | Cinco orbes pequeños con su propio anillo, a 1 D del centro (arriba y a los lados), unidos al orbe por un hilo por el que viajan señales. En «esperando», en `status.pending`. |

Al despertar, el fondo sale del núcleo; al dormirse, vuelve a él antes de que colapsen los anillos. En reposo solo queda una parte del polvo y uno de cada cuatro mini orbes, quietos y muy tenues, sin enlaces. En dormido no hay fondo.

En modo dormido la pantalla sigue visible: fondo `bg.base`, el orbe apagado (un punto en `primary.deep`), sin paneles ni subtítulos, y la caja de texto con la ayuda «Escriba «Hey Jarvis» para iniciar la sesión».

## 6. HUD flotante

Ventana de 380 px de ancho, a 16 px de la esquina elegida, fondo `bg.panel`, radio 10, borde `line.soft`. No toma el foco por su cuenta: solo lo recibe con un clic en su caja de texto.

```text
Contraído (104 px)                         Expandido (hasta el 60 % del alto)
┌──────────────────────────────────┐      ┌──────────────────────────────────┐
│ (orbe) ESCUCHANDO           ⌄    │      │ (orbe) ESCUCHANDO           ⌃    │
│        «ejecuta git status»      │      │        Ejecutando git status.    │
│ [ Escriba una orden            ] │      │ [ Escriba una orden            ] │
└──────────────────────────────────┘      ├──────────────────────────────────┤
                                          │ COMANDOS                         │
                                          │ D:\Proyectos\jarvis              │
                                          │ On branch main …                 │
                                          └──────────────────────────────────┘
```

- **Cabecera:** mini orbe de 44 px (núcleo, un anillo y el espectro simplificado; reacciona al nivel de la voz del asistente), estado en `font.display`, una línea de subtítulo (la respuesta si la hay; si no, la orden) y el botón de expandir o contraer. Mientras el asistente habla, aparece el botón de silencio.
- **Caja de texto:** una línea bajo la cabecera, visible también con el HUD contraído. Un clic en ella le da el foco; Enter envía la orden y el foco se queda en la caja.
- **Cuerpo:** el panel activo, con desplazamiento vertical si no cabe.
- **Animaciones:** despertar es un pulso del mini orbe y un fundido de entrada del HUD; dormirse, el mini orbe se atenúa y el HUD se contrae; en el cierre, el HUD se desvanece. Duran los mismos 2 s.
- En reposo el HUD no tiene ninguna animación continua.

## 7. Componentes

Todos en `ui/qml/components/`, usados por igual en las dos superficies.

| Componente | Descripción |
|---|---|
| `PanelFrame` | Marco de un panel: título en `font.display` de 13, borde, y esquinas marcadas cuando es el panel activo. |
| `StatusDot` | Punto de 8 px con el color del estado. En `pendiente`, late (opacidad de 100 a 40 %, periodo de 1,2 s) con resplandor. |
| `TaskCard` | Fila de tarea: `StatusDot`, icono del módulo, descripción (una línea, con elipsis), hora en `text.muted`. Una tarea en `error` muestra debajo su motivo en `status.error`, tamaño 13. Las tareas de un protocolo se sangran bajo la suya. |
| `Subtitles` | Las dos líneas de orden y respuesta. |
| `StateLabel` | Punto y texto del estado del asistente. Color: `primary` escuchando y hablando, `text.secondary` reposo, `status.pending` esperando, `primary.bright` con latido procesando. |
| `DialogCard` | Pregunta en tamaño 18, elemento sobre el que se pregunta, respuestas admitidas como distintivos («Sí», «No», «Cancelar») y una barra fina que se vacía con el tiempo de espera. Borde `status.pending`. |
| `NumberedRow` | Fila con un número grande en `primary` (`font.mono`), para recordatorios y resultados: el número es lo que el usuario escribe en la orden. |
| `IconButton` | Botón de icono de 28 px con realce al pasar el cursor. Solo para «traer al frente», silencio y expandir. |
| `NeonTrace` | Trazo de neón que recorre un contorno (`outline.js`): sigue la voz, toma `status.pending` en «esperando» y se detiene con `ui.reduce_motion`. |
| `Badge` | Distintivo pequeño: «actual», «importante», «vencido», «limitada», «no reconocido». |
| `EmptyState` | Texto atenuado centrado cuando un panel no tiene contenido («Sin recordatorios»). |

## 8. Paneles

| Panel | Diseño |
|---|---|
| Actividad | Lista de `TaskCard`, la más reciente arriba. En el HUD, las 6 últimas. |
| Comandos | Ruta del directorio de trabajo en `font.mono` con icono de carpeta. Debajo, uno de: listado (icono, nombre; carpetas primero), árbol (sangría de 16 px por nivel, líneas guía en `line.soft`, línea final «… (árbol recortado)» si procede), o salida de un comando (`font.mono` de 13; la salida de errores en `status.error`; cabecera con el comando y su `StatusDot`). |
| Aperturas | Una tarjeta por elemento: icono de su tipo, nombre, `StatusDot` y botón «traer al frente» a la derecha (desactivado si la ventana ya no existe; ausente si el sistema no lo permite). |
| Búsqueda | Cabecera con la consulta y el total; `NumberedRow` por resultado con nombre y, debajo, su carpeta en `text.muted`; distintivo «limitada» si procede. |
| Recordatorios | `NumberedRow` por recordatorio: texto, próximo aviso y fecha límite en `text.secondary`; distintivo «vencido» en `status.error`; el recordatorio notificado o leído, con fondo `bg.raised` y borde `primary`. |
| Protocolo | Nombre del protocolo, barra de progreso fina en `primary` (tareas terminadas / total) y la lista de sus tareas como `TaskCard`. |
| Historial | Tabla: identificador en `font.mono` y `primary`, nombre, fecha, estrella si es importante, distintivo «actual». En la vista de actividades, cabecera con la sesión y lista de `TaskCard`. |
| Ayuda | Grupos por módulo; cada orden con su descripción y un ejemplo entre comillas en `text.secondary`. |

## 9. Icono de la bandeja

Un círculo con un anillo, en cuatro variantes: dormido (gris), reposo (cian tenue), activo (cian; para escuchando, procesando y hablando) y esperando (ámbar). Formato ICO con tamaños de 16 a 48 px.

## 10. Calidad y rendimiento

- ⚙ `ui.quality`: `high` (todo), `medium` (la mitad de partículas, nodos, glifos, mini orbes y polvo; sin retícula ni estelas), `low` (sin fondo, red, glifos, partículas ni resplandor; núcleo liso; anillos sin texto).
- Las animaciones son declarativas de Qt Quick; no se ejecuta código Python por frame.
- Los conjuntos de muchos elementos (constelación, polvo, partículas, espectro) no tienen enlaces de propiedades que dependan del reloj: una función `refresh` los coloca a todos de una pasada por fotograma. Lo que se mueve en cada fotograma solo cambia de posición, giro, escala u opacidad; las formas (`Shape`) que sí cambian de contorno en cada fotograma no usan `CurveRenderer`.
- Una ventana oculta o tapada no se dibuja. En reposo solo se anima lo que está a la vista.
- Objetivo: 60 fps en el equipo de referencia y nunca menos de 30 (RNF-21).

## 11. Lista de comprobación visual

Se revisa con `--preview` y en uso real al cerrar las fases 2 y 7.

- [ ] El orbe se parece a las tres imágenes de referencia: esfera luminosa, anillos concéntricos con datos, cian sobre negro.
- [ ] Donde se cruzan dos capas del orbe, la zona es más clara.
- [ ] Despertar: la masa se concentra en el centro, estalla, los anillos salen despedidos en sentidos opuestos y todo se estabiliza. Dura 2 s.
- [ ] Dormirse: en el cierre, horizonte negro, caída en espiral cada vez más rápida, viraje a marino y chispa final; en reposo, contracción contenida y orbe tenue y lento.
- [ ] Interrumpir una animación con la contraria no produce ningún salto.
- [ ] Al hablar el asistente se nota en toda la pantalla: ondas que salen del núcleo y neón más rápido en la caja de texto y en las ventanas.
- [ ] El neón tiene el mismo grosor en todo su recorrido, también en las esquinas y los chaflanes, y no distrae de leer los paneles.
- [ ] Las ventanas no son todas iguales: se distinguen cuatro formas de marco, y ninguna parece forzada.
- [ ] Al hablar el asistente, el núcleo y el espectro siguen su voz; en escucha el plasma ondula despacio; en reposo, quieto.
- [ ] Reposo y despierto se distinguen de un vistazo: en reposo solo quedan el núcleo y los anillos, tenues.
- [ ] Los elementos del centro y del fondo se mueven a la vez: la onda del latido los ilumina a su paso.
- [ ] El fondo no dificulta leer los paneles ni los subtítulos.
- [ ] Los cinco aspectos (escuchando, hablando, procesando, esperando, reposo) se distinguen sin leer el texto.
- [ ] Ningún color fuera de la tabla de tokens. Los colores de estado solo indican estado.
- [ ] Todo el texto se lee a un metro de la pantalla; ningún texto se corta sin elipsis.
- [ ] Los paneles se ven igual en la pantalla de sesión y en el HUD.
- [ ] El HUD no tapa más del 60 % del alto, no parpadea al actualizarse y no toma el foco salvo con un clic en su caja de texto.
- [ ] La caja de texto se ve en dormido, en reposo y en escucha, con la ayuda de cada estado, y recibe el teclado al abrir la pantalla.
- [ ] A 1366 × 768 nada se solapa.
- [ ] Con `ui.reduce_motion`, no hay giros ni colapsos, solo fundidos.

## 12. Imágenes de referencia

| Archivo | Qué muestra |
|---|---|
| [referencia-orbe-general.jpg](referencia-orbe-general.jpg) | Estética general: esfera holográfica con anillos. |
| [referencia-escucha-espectro.jpg](referencia-escucha-espectro.jpg) | Estado de escucha, con espectro de audio. |
| [referencia-dormirse-colapso.jpg](referencia-dormirse-colapso.jpg) | Colapso de los anillos en un punto y disipación de partículas. |

Son las imágenes originales del autor; solo se ha cambiado el nombre del archivo.
