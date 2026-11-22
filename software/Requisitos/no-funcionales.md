# Requisitos no funcionales

Cualidades y límites medibles del asistente. Todos están confirmados. Los valores con ⚙ son configurables.

**Equipo de referencia** para todas las medidas: el portátil del autor (Intel Core de 12.ª generación, gráficos integrados Iris Xe, 16 GB de RAM, pantalla de 60 Hz, Windows 11), enchufado a la corriente. **Equipo mínimo:** CPU x86-64 de 4 núcleos físicos con AVX2, 8 GB de RAM, gráficos integrados.

**Cómo se verifican:** salvo que se indique otra cosa, cada medida se comprueba con la lista de comprobación manual de la fase correspondiente del [plan](../plan-implementacion.md) y con el guion `scripts/measure.py`, que registra CPU, RAM y latencias. Ninguna medida de rendimiento bloquea las pruebas automáticas.

## 1. Privacidad y conectividad

| ID | Requisito | Medida |
|---|---|---|
| RNF-01 | **Privacidad.** El sistema no envía fuera del dispositivo ningún dato de audio ni de texto. | 0 conexiones de red abiertas por el proceso del asistente durante una sesión que recorra todas las funciones. Las pruebas automáticas bloquean los sockets y fallan si el código intenta abrir uno. |
| RNF-02 | **Funcionamiento sin conexión.** | El 100 % de los requisitos funcionales se cumplen con la red desactivada. |
| RNF-34 | **Micrófono del medidor de ruido.** Solo se usa el nivel de entrada: el audio no se graba, no se guarda y no sale del proceso. | El micrófono solo está abierto con el medidor de ruido a la vista; de cada intervalo solo se conserva la energía media (prueba automática con un flujo de entrada falso). |

## 2. Rendimiento

| ID | Requisito | Medida |
|---|---|---|
| RNF-03 | **Latencia de respuesta.** | Desde que el usuario pulsa Enter hasta el inicio de la respuesta por voz o del efecto visible: mediana ≤ 0,5 s y percentil 95 ≤ 1 s. Desde que envía «Hey Jarvis» hasta el inicio de la animación: ≤ 0,5 s. |
| RNF-04 | **Consumo sin órdenes.** | Dormido: CPU media ≤ 2 % del total en 60 s y RAM ≤ 400 MB. Reposo: CPU media ≤ 2 % y RAM ≤ 400 MB. En reposo y en dormido la interfaz no anima nada de forma continua que no esté visible. |
| RNF-05 | **Consumo en uso.** | RAM ≤ 600 MB. |
| RNF-06 | **Equipo objetivo.** Funciona en un portátil sin GPU dedicada. | Toda la inferencia en CPU. Cumple RNF-03 en el equipo de referencia. En el equipo mínimo funciona con la latencia que resulte. |
| RNF-07 | **Entrada no bloqueada.** La caja de texto admite texto en todo momento, también mientras se ejecutan acciones, binarios externos y diálogos. Lo enviado durante una frase del ciclo de vida se atiende al terminar; durante cualquier otra locución, «Hey Jarvis» la interrumpe (RN-48). | «Hey Jarvis» se atiende con un binario externo en ejecución, en el 100 % de 10 intentos. |
| RNF-08 | **Acceso concurrente a los datos.** | 0 errores de bloqueo de la base de datos al consultar el historial mientras se registra una actividad. |
| RNF-09 | **Búsqueda rápida.** | Con *Everything*: resultado en ≤ 2 s. Búsqueda limitada: se corta a los 5 s ⚙. |
| RNF-33 | **Consumo de los medidores.** Un medidor oculto no gasta nada. | Con un medidor oculto, su temporizador está parado y, en el de ruido, el micrófono cerrado (prueba automática). Con los dos a la vista se cumplen RNF-04 y RNF-05. |
| RNF-25 | **Arranque.** | Ventana visible y proceso listo en dormido en ≤ 10 s desde su inicio. Tras «Hey Jarvis» en dormido, listo para atender órdenes al terminar la frase de apertura. |

## 3. Fiabilidad

| ID | Requisito | Medida |
|---|---|---|
| RNF-10 | **Determinismo.** | El mismo texto, en el mismo estado, produce la misma intención, las mismas entidades y el mismo mensaje en el 100 % de las repeticiones (prueba automática). |
| RNF-11 | **Precisión del reconocimiento de intenciones.** | Umbral de aceptación de una intención: similitud ≥ 80 ⚙ sobre 100 en el texto fijo del patrón. Umbral de una entidad buscada en una lista: ≥ 75 ⚙. Sobre el juego de frases de prueba de [catalogo-intenciones.md](../catalogo-intenciones.md) ≥ 95 % de aciertos y 0 intenciones equivocadas en las frases de control negativo. |
| RNF-12 | **Integridad de los datos borrados.** | Tras eliminar un recordatorio, su fila sigue existiendo. Tras eliminar sesiones, ni ellas ni sus actividades quedan en la base de datos, las demás conservan sus actividades y sus marcas de desbordamiento con el id nuevo, y los ids son 1..N sin huecos (pruebas automáticas). |
| RNF-23 | **Tolerancia a fallos.** Un error en un módulo de acción, en el enrutado o en la síntesis no termina el proceso ni deja la máquina de estados bloqueada. | Una excepción no controlada en un módulo deja su tarea en `error`, el asistente dice «Ha ocurrido un error» y sigue atendiendo órdenes (prueba automática con un módulo que falla). |

| RNF-30 | **Fiabilidad de la activación.** Retirado: entrada por texto. La frase de activación escrita se reconoce de forma determinista (RNF-10, RNF-11). | — |
| RNF-31 | **Fiabilidad de las entidades escritas.** Rutas, nombres de archivo y comandos se resuelven bien a la primera. | Lista manual de 30 órdenes escritas con entidades (rutas, nombres con extensión, comandos con opciones): ≥ 95 % resueltas correctamente sin repetir. |

## 4. Usabilidad

| ID | Requisito | Medida |
|---|---|---|
| RNF-13 | **Interfaz no intrusiva.** El HUD flotante está siempre encima, sin bordes y no toma el foco por su cuenta; solo lo recibe cuando el usuario hace clic en su caja de texto. Abrir aplicaciones o actualizar la interfaz no cambia la ventana con foco, salvo cuando la pantalla de sesión pasa al frente al arrancar, al abrir la sesión o al pedirlo el usuario (RES-32). | Al mostrar o actualizar el HUD y al abrir una aplicación, la ventana activa es la que corresponde en el 100 % de 10 pruebas. |
| RNF-14 | **Actualización en tiempo real.** | Retardo ≤ 200 ms entre el cambio de estado de una tarea y su visualización. |
| RNF-15 | **Idioma.** El español es el único idioma de las órdenes escritas y de las respuestas; la voz es de español de España. Excepciones: «Hey Jarvis» es una frase fija en inglés; dentro de una orden en español, las entidades (comandos, nombres de carpetas, archivos y aplicaciones) pueden estar en otro idioma. La voz pronuncia esas entidades con las reglas del español, sin tratamiento especial. | El juego de frases de prueba incluye entidades en inglés y cumple RNF-11. |
| RNF-29 | **Calidad visual.** La interfaz sigue el sistema de diseño de [Interfaz/README.md](../Interfaz/README.md): atractiva y profesional. | Revisión contra la lista de comprobación visual de ese documento. |

## 5. Compatibilidad

| ID | Requisito | Medida |
|---|---|---|
| RNF-16 | **Windows.** | El 100 % de los requisitos funcionales se cumplen en Windows 11. |
| RNF-17 | **Linux (fase final).** | Con el adaptador de Linux: el 100 % de los requisitos en X11; en Wayland, todos salvo RF-25. Distribución de referencia: Ubuntu LTS vigente. |

## 6. Mantenibilidad

| ID | Requisito | Medida |
|---|---|---|
| RNF-18 | **Ampliación con nuevos comandos.** | Añadir un comando solo crea o modifica el archivo del módulo y la lista de módulos de `main.py`. |
| RNF-19 | **Módulos desacoplados.** | El 100 % de las acciones de los módulos se pueden invocar como tarea de un protocolo con la misma interfaz (prueba automática que recorre el registro). |
| RNF-20 | **Interfaz desacoplada.** | Ningún archivo de `action_modules/` ni de `core/` importa `ui/` ni Qt (prueba automática de importaciones). |
| RNF-24 | **Capacidad de prueba.** | Las pruebas sin hardware ni modelos se ejecutan en ≤ 60 s y cubren ≥ 80 % de las líneas de `core/`, `intent_router/` y `action_modules/`. |
| RNF-26 | **Configuración sin tocar código.** | Catálogos, protocolos, lugares, binarios permitidos, umbrales y tiempos se cambian editando archivos TOML. |
| RNF-28 | **Coste cero.** | Todas las dependencias son gratuitas (RES-44). |

## 7. Seguridad

| ID | Requisito | Medida |
|---|---|---|
| RNF-27 | **Ejecución segura.** El asistente no ejecuta órdenes arbitrarias. | Los binarios se lanzan sin intérprete de órdenes y solo desde la lista permitida; las páginas, solo del catálogo; nada se sobrescribe ni se borra del disco (pruebas automáticas). El asistente no requiere privilegios de administrador. |
| RNF-32 | **Protección de las contraseñas.** Ninguna contraseña de perfil ni la clave privada del Acedor se guarda en claro, se dice en voz alta o se escribe en el registro. | Contraseñas: hash scrypt (N = 2¹⁴, r = 8, p = 1) con sal aleatoria de 16 bytes, comparado en tiempo constante. Custodia para el Acedor: sello X25519 + HKDF-SHA256 + AES-GCM; su clave privada, cifrada con scrypt + AES-GCM a partir de su contraseña y solo en memoria durante su sesión. Pruebas automáticas: la contraseña no aparece en la base de datos, en `profiles.toml`, en el registro ni en el `repr` de los eventos. |

## 8. Fluidez de la interfaz

| ID | Requisito | Medida |
|---|---|---|
| RNF-21 | **Fluidez.** La pantalla de sesión y sus animaciones se dibujan sin tirones perceptibles, también mientras se atiende una orden. | En el equipo de referencia: objetivo de 60 fps y nunca menos de 30 fps, medido con el contador de frames del modo de diagnóstico de la interfaz. Cada animación de transición dura 2 s ± 0,1 s. |
| RNF-22 | **Sincronía de animación y voz.** | La animación de transición y su frase empiezan con un desfase ≤ 150 ms, medido con las marcas de tiempo del registro de diagnóstico. |

## Cambios respecto a la versión anterior

RNF-21 y RNF-22 sustituyen las medidas por frame (99 % en un intervalo de refresco, ±1 frame, 45 ms) por medidas perceptibles; motivo en [README.md](../README.md). RNF-03, RNF-04, RNF-05, RNF-09, RNF-11 y RNF-14 pasan a tener cifra. RNF-23 a RNF-31 son nuevos. RNF-32 a RNF-34 acompañan a los perfiles protegidos y a los medidores.
