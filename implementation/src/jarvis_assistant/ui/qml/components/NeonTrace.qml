// Neón que recorre un contorno: uno o varios trazos de luz de grosor uniforme, con la cabeza
// casi blanca, una cola que se desvanece y un resplandor alrededor. Es el toque vivo de la
// caja de texto y de las ventanas flotantes.
//
// Cada trazo es una cadena de eslabones cortos que avanzan por el contorno. Cada eslabón es
// un solo rectángulo con el núcleo y el resplandor en su degradado, y moverlo solo cambia su
// posición y su giro: no se vuelve a calcular ninguna forma en cada fotograma.
//
// Sigue al asistente como el resto de la interfaz: brilla con la voz, acelera mientras suena
// una frase, toma el color de espera cuando el asistente espera una respuesta y se queda
// quieto con `reduceMotion`. `boost` añade el brillo del latido del orbe a quien lo conozca.
// Sin aceleración gráfica tampoco avanza: obligaría a repintar todo lo que tiene debajo.
import QtQuick
import ".."

Item {
    id: trace

    property string path: ""             // ruta SVG del contorno (`outline.js`)
    property real length: 0              // su longitud, en píxeles
    property int count: 1                // trazos repartidos por el contorno
    property real tail: 80               // longitud de cada trazo, en píxeles
    property real speed: Theme.neonSpeed // píxeles por segundo
    property real strength: 1            // 0 apagado – 1 encendido
    property real boost: 0               // brillo añadido (latido del orbe), de 0 a 1
    property bool running: true

    property real voice: assistant.level
    // Empuje de la frase: sube mientras el asistente habla y baja al callar. La velocidad lo
    // sigue a él y no al nivel de cada sílaba, para que el trazo no avance a tirones.
    property real drive: assistant.level > 0.01 ? 1 : 0
    property color tone: assistant.activity === "esperando" ? Theme.statusPending : Theme.primary
    property real phase: 0               // 0–1: avance por el contorno

    readonly property real linkLength: 8
    readonly property real glowWidth: Theme.neonWidth * 5
    // Reparto del degradado: resplandor, núcleo de `neonWidth` y resplandor.
    readonly property real coreEdge: 0.5 - Theme.neonWidth / (2 * glowWidth)
    readonly property int links: Math.max(1, Math.round(tail / linkLength))
    readonly property real level: Math.min(1, strength * (0.7 + 0.3 * voice) + 0.5 * boost)
    readonly property bool drawn: length > 0 && path.length > 0 && level > 0.01
    readonly property bool accelerated: GraphicsInfo.api !== GraphicsInfo.Software

    visible: drawn
    opacity: level

    Behavior on voice {
        NumberAnimation { duration: Theme.motionLevel }
    }
    Behavior on drive {
        NumberAnimation { duration: 600; easing.type: Easing.InOutQuad }
    }
    Behavior on tone {
        ColorAnimation { duration: Theme.motionState }
    }
    Behavior on strength {
        NumberAnimation { duration: Theme.motionState }
    }

    FrameAnimation {
        running: trace.running && trace.drawn && trace.accelerated && !ui.reduceMotion
        onTriggered: {
            var step = trace.speed * (1 + 1.6 * trace.drive) * frameTime / trace.length
            trace.phase = (trace.phase + step) % 1
        }
    }

    Path {
        id: route

        PathSvg { path: trace.path }
    }

    Repeater {
        model: trace.drawn ? trace.count * trace.links : 0

        Rectangle {
            id: link

            required property int index
            readonly property int place: index % trace.links          // 0: la cabeza
            readonly property real lead: Math.floor(index / trace.links) / trace.count
            readonly property color core: place === 0 ? Theme.primaryHot : trace.tone

            x: spot.x - width / 2
            y: spot.y - height / 2
            width: trace.linkLength
            height: trace.glowWidth
            rotation: spot.angle
            opacity: 1 - 0.85 * place / trace.links                   // la cola se desvanece

            gradient: Gradient {
                GradientStop { position: 0; color: Theme.alpha(trace.tone, 0) }
                GradientStop { position: trace.coreEdge - 0.01; color: Theme.alpha(trace.tone, 0.22) }
                GradientStop { position: trace.coreEdge; color: link.core }
                GradientStop { position: 1 - trace.coreEdge; color: link.core }
                GradientStop { position: 1.01 - trace.coreEdge; color: Theme.alpha(trace.tone, 0.22) }
                GradientStop { position: 1; color: Theme.alpha(trace.tone, 0) }
            }

            PathInterpolator {
                id: spot

                path: route
                progress: {
                    var at = trace.phase + link.lead - link.place * trace.linkLength / trace.length
                    return at - Math.floor(at)
                }
            }
        }
    }
}
