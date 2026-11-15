// Acreción: materia que cae en espiral hacia el núcleo. Solo se ve durante el despertar
// (la masa se concentra antes del estallido) y durante el cierre (el núcleo lo atrae todo).
// No tiene reloj propio: la mueve `phase`, que anima la transición.
import QtQuick
import ".."
import "field.js" as Field

Item {
    id: disc

    property real d: 100             // D del orbe
    property int count: 36           // trazos; los anillos convergentes se dibujan siempre
    property color color: Theme.primary
    property real phase: 0           // avance de la caída: cada unidad es una caída completa
    property real strength: 0        // 0–1: visibilidad del conjunto

    width: d * 1.6
    height: width
    visible: strength > 0.01

    // Anillos que se cierran sobre el núcleo.
    Repeater {
        model: 2

        Rectangle {
            id: hoop

            required property int index
            readonly property real t: (disc.phase * 0.7 + index * 0.5) % 1

            anchors.centerIn: parent
            width: disc.d * (0.1 + 1.3 * Math.pow(1 - t, 1.5))
            height: width
            radius: width / 2
            color: "transparent"
            border.width: 1 + 1.5 * t
            border.color: disc.color
            opacity: disc.strength * 0.55 * Math.sin(Math.PI * t)
        }
    }

    // Trazos: cada uno apunta hacia donde cae y se alarga al acelerar.
    Repeater {
        model: disc.count

        Item {
            id: arm

            required property int index
            readonly property real t: (disc.phase + Field.hash(index, 1)) % 1

            anchors.centerIn: parent
            // El giro crece al acercarse: la caída es una espiral.
            rotation: Field.hash(index, 2) * 360 + 150 * t * t

            Rectangle {
                x: disc.d * (0.05 + 0.75 * Math.pow(1 - arm.t, 1.6))
                y: -height / 2
                width: disc.d * (0.012 + 0.07 * arm.t)
                height: 1.5
                radius: 0.75
                color: Theme.mix(disc.color, Theme.primaryBright, arm.t)
                opacity: disc.strength * Math.min(1, arm.t * 5) * (0.35 + 0.65 * arm.t)
            }
        }
    }
}
