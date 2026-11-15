// Partículas: puntos pequeños y tenues que se alejan despacio del centro.
import QtQuick
import ".."

Item {
    id: field

    property real d: 100             // D del orbe
    property int count: 120
    property real strength: 0        // 0–1: visibilidad del conjunto
    property bool running: true
    property color color: Theme.primary

    width: d * 1.4
    height: width

    Repeater {
        model: field.count

        Rectangle {
            id: dot

            required property int index
            property real cycle: 0
            readonly property real progress: (cycle + index * 0.618) % 1
            readonly property real angle: index * 2.39996  // ángulo áureo: reparto uniforme
            readonly property real distance: field.d * (0.2 + 0.5 * progress)

            width: 2
            height: 2
            radius: 1
            color: field.color
            opacity: field.strength * 0.5 * Math.sin(Math.PI * progress)
            x: field.width / 2 + Math.cos(angle) * distance
            y: field.height / 2 + Math.sin(angle) * distance

            NumberAnimation on cycle {
                from: 0
                to: 1
                duration: 7000 + (dot.index % 5) * 900
                loops: Animation.Infinite
                running: field.running && field.strength > 0
            }
        }
    }
}
