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
| Halo | 0,60 D | Resplandor difuso detrás de todo; da la sensación de luz proyectada. |
| Núcleo | 0,16 D | Esfera: degradado radial de `primary.bright` en el centro a `primary` y a transparente en el borde, con dos o tres meridianos elípticos finos que giran para dar volumen. |
| Anillo de espectro | 0,24 D | 64 barras radiales cuya longitud sigue el nivel de audio (ver «Reacción a la voz»). |
| Anillo de datos 1 | 0,30 D | Línea fina con marcas cada 5°. Gira en sentido horario. |
| Anillo de datos 2 | 0,36 D | Arcos segmentados con números y valores hexadecimales en `font.mono`. Gira en sentido antihorario. |
| Anillo de datos 3 | 0,43 D | Línea discontinua con fragmentos de código en cuatro puntos. Gira en sentido horario, más lento. |
| Partículas | hasta 0,70 D | Puntos pequeños que se alejan despacio del centro, muy tenues. 120 en calidad alta, 60 en media, ninguna en baja. |

Los datos de los anillos son decorativos y fijos (no muestran información real), en `primary` al 60 %.

**Fusión aditiva:** sobre fondo negro, las capas se superponen sumando luz. Se consigue con capas translúcidas y resplandor; donde haga falta suma real, con un sombreador sencillo. El criterio de aceptación es visual: donde dos capas se cruzan, la zona es más clara, nunca más oscura.

### Aspecto según la actividad (diseño del autor, ampliado)

| Actividad | Aspecto |
|---|---|
| **Escuchando** | Atención activa. El orbe pulsa con una «respiración» luminosa (resplandor interior que aumenta y disminuye, periodo de 2,4 s). El asistente atiende las órdenes escritas. El núcleo queda quieto y el espectro no se ve: no hay audio que seguir. Los anillos giran a velocidad media-alta. Brillo 100 %. |
| **Hablando** | Igual que escuchando, y además el núcleo y el espectro reaccionan a la voz del asistente: ondas de espectro a lo largo del anillo interior, sincronizadas con su volumen. Incluye las frases que coinciden con la animación de dormirse («A su disposición.», «Buenas noches. Sesión cerrada.»). |
| **Procesando** | Entre el fin de la orden y la respuesta. El espectro se sustituye por un arco luminoso que recorre el anillo interior (una vuelta cada 1,2 s) y los anillos giran más deprisa. Indica «trabajando» sin texto. |
| **Esperando** | Como escuchando, con el anillo de datos 2 en `status.pending`: el asistente ha hecho una pregunta. |
| **Reposo** | El orbe se mantiene estable en el centro, con una flotación muy sutil (±4 px, periodo de 6 s). Sin picos de espectro ni reacción al audio una vez terminada la frase del asistente: el núcleo queda quieto. El giro de los anillos es constante pero mucho más lento. El brillo es más tenue (45 %) pero persistente: el sistema está latente, no apagado. |

Valores de control (cada uno es una propiedad animable del componente `Orb`):

| Propiedad | Reposo | Escuchando / Hablando | Procesando | Esperando |
|---|---|---|---|---|
| `brightness` | 0,45 | 1,0 | 0,9 | 1,0 |
| `spin` (°/s de los anillos 1, 2 y 3) | 3 / −2 / 1 | 18 / −12 / 8 | 40 / −30 / 20 | 18 / −12 / 8 |
| `breath` (amplitud del resplandor) | 0 | 0,25 | 0,1 | 0,25 |
| `spectrum` (visibilidad del espectro) | 0 | 1 | 0 (arco) | 1 |
| `assembly` (0 colapsado – 1 formado) | 1 | 1 | 1 | 1 |
| `tint` (0 cian – 1 marino) | 0,35 | 0 | 0 | 0 |

Referencia de escucha: [referencia-escucha-espectro.jpg](referencia-escucha-espectro.jpg).

### Reacción a la voz (RF-83)

- La interfaz recibe un nivel de 0 a 1, 20 veces por segundo, con su origen (asistente o ninguno), y lo suaviza con `motion.level`.
- **Núcleo:** su escala es `1 + 0,12 × nivel` y su resplandor crece con el nivel.
- **Espectro:** la longitud de cada barra es `nivel × perfil[i]`, donde `perfil` es un patrón fijo de 64 valores, simétrico y suave, que se desplaza lentamente alrededor del anillo. El resultado se percibe como un ecualizador sincronizado con el volumen, sin necesidad de analizar frecuencias.
- Con nivel 0 (el asistente no habla), el espectro no se ve.

## 4. Animaciones de transición

Cada una dura 2 s fijos y empieza a la vez que su frase de voz, sin esperar a que la frase termine.

### Despertar (diseño del autor)

Se muestra al abrir la sesión y al volver a escuchar desde reposo.

La pantalla pasa de vacío absoluto a iluminarse. Un único punto de luz cian aparece en el centro exacto, emitiendo un destello brillante. Desde ese punto se expanden rápidamente los anillos geométricos y los componentes de la interfaz en 360 grados. Los anillos giran en direcciones opuestas y se «ensamblan» mediante interpolación de escala y rotación, con salida suave, hasta formar el núcleo central estabilizado. La opacidad de todo el conjunto sube del 0 % al 100 % en el primer segundo.

| Tiempo | Qué ocurre |
|---|---|
| 0 – 0,15 s | Aparece el punto de luz en el centro; destello (halo al máximo). |
| 0 – 1,0 s | Opacidad global de 0 a 100 %. |
| 0,15 – 1,2 s | Los anillos se expanden desde el punto, escalonados 80 ms del interior al exterior: escala de 0 a 1 y media vuelta de giro, en sentidos opuestos, con salida suave. `assembly` de 0 a 1. |
| 1,2 – 2,0 s | Estabilización: el núcleo se asienta con un leve rebote (1,06 → 1), aparece el espectro, empiezan las partículas y los giros convergen a los valores de «escuchando». |
| 0,6 – 1,6 s | Los paneles laterales aparecen con un fundido (solo al abrir la sesión). |

**Desde reposo**, el orbe ya está formado: no hay punto de luz ni vacío. Las propiedades pasan de sus valores de reposo a los de escucha en 2 s, y un anillo de luz fino se expande una vez desde el núcleo hacia fuera, como eco del destello.

Referencia: [referencia-orbe-general.jpg](referencia-orbe-general.jpg).

### Dormirse (diseño del autor)

Se muestra al pasar a reposo y al cerrar la sesión.

Es un efecto de colapso y disipación, inverso al despertar. Los anillos exteriores frenan su rotación con una fricción suave (entrada suave). Toda la estructura geométrica colapsa hacia el centro, absorbida por el núcleo. A la vez, el cian brillante se degrada hacia un azul marino profundo. En los últimos instantes el orbe se reduce a una única chispa que desaparece por completo, dejando unas ligeras partículas o chispas digitales que se disipan en el fondo oscuro.

| Tiempo | Qué ocurre |
|---|---|
| 0 – 0,8 s | Los anillos frenan (entrada suave); el espectro se desvanece, salvo que el asistente siga hablando. |
| 0,4 – 1,6 s | La estructura se contrae hacia el centro, escalonada del exterior al interior. `tint` avanza hacia el marino. |
| 1,6 – 2,0 s | Variante **cierre**: el orbe se reduce a una chispa que desaparece; las partículas se disipan; al terminar, la interfaz se oculta. Variante **reposo**: la contracción se detiene y el orbe se asienta en su aspecto de reposo. |

La diferencia entre las dos variantes es el valor final de `assembly`: 0 en el cierre (desaparece) y 1 en el reposo (queda formado, tenue y lento). En el paso a reposo la estructura se contrae hasta 0,8 a mitad de la animación y vuelve a 1, de modo que se percibe el colapso sin que el orbe desaparezca. Mientras suena la frase («A su disposición.», «Buenas noches. Sesión cerrada.») el núcleo sigue reaccionando a la voz.

Referencia: [referencia-dormirse-colapso.jpg](referencia-dormirse-colapso.jpg).

### Fundido entre animaciones

El orbe no tiene animaciones cerradas que se «reproducen»: tiene propiedades de control (`brightness`, `spin`, `breath`, `spectrum`, `assembly`, `tint`) y cada fase fija sus valores finales. Una transición siempre parte de los valores actuales. Por eso, si llega una transición con otra en curso, la nueva continúa desde donde estaba la anterior, sin saltos; en particular, «Hey Jarvis» durante la animación de cierre funde el colapso con el despertar sin que la pantalla llegue a ocultarse.

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
| Caja de texto | Bajo los subtítulos, centrada, ancho máximo 900 px: una línea, fondo `bg.panel`, borde `line.soft` (`line.strong` con el foco), radio 6, texto en `text.primary` y texto de ayuda en `text.muted`. Es la única entrada de órdenes ([entrada-texto.md](../Modulos/Infraestructura/entrada-texto.md)). Tiene el foco siempre que la pantalla es la ventana activa. No se atenúa en reposo. |

En reposo, los paneles y los subtítulos bajan su opacidad al 50 % junto con el orbe.

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

- ⚙ `ui.quality`: `high` (todo), `medium` (la mitad de partículas, resplandor más barato), `low` (sin partículas ni resplandor; anillos sin texto).
- Las animaciones son declarativas de Qt Quick; no se ejecuta código Python por frame.
- Una ventana oculta o tapada no se dibuja. En reposo solo se anima lo que está a la vista.
- Objetivo: 60 fps en el equipo de referencia y nunca menos de 30 (RNF-21).

## 11. Lista de comprobación visual

Se revisa con `--preview` y en uso real al cerrar las fases 2 y 7.

- [ ] El orbe se parece a las tres imágenes de referencia: esfera luminosa, anillos concéntricos con datos, cian sobre negro.
- [ ] Donde se cruzan dos capas del orbe, la zona es más clara.
- [ ] Despertar: punto de luz, destello, expansión de anillos en sentidos opuestos, estabilización. Dura 2 s.
- [ ] Dormirse: frenado, colapso, viraje a marino; en el cierre, chispa y partículas; en reposo, orbe tenue y lento.
- [ ] Interrumpir una animación con la contraria no produce ningún salto.
- [ ] Al hablar el asistente, el núcleo y el espectro siguen su voz; en escucha y en reposo, quietos.
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
