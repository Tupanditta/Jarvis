// Partículas: puntos pequeños y tenues que se alejan despacio del centro.
//
// Un solo reloj mueve todos los puntos de una pasada (`refresh`): ninguno tiene animación ni
// enlaces de propiedades propios.
import QtQuick
import ".."

Item {
    id: field

    property real d: 100             // D del orbe
    property int count: 120
    property real strength: 0        // 0–1: visibilidad del conjunto
    property bool running: true
    property color color: Theme.primary
    property real time: 0            // segundos animados

    // Dirección de cada punto (ángulo áureo: reparto uniforme) y duración de su viaje.
    readonly property var seeds: {
        var result = []
        for (var i = 0; i < count; i++) {
            var angle = i * 2.39996
            result.push({ cos: Math.cos(angle), sin: Math.sin(angle), offset: i * 0.618,
                          rate: 1 / (7 + (i % 5) * 0.9) })
        }
        return result
    }

    function refresh() {
        if (dots.count !== seeds.length)
            return
        var middle = width / 2
        for (var i = 0; i < seeds.length; i++) {
            var s = seeds[i]
            var progress = (time * s.rate + s.offset) % 1
            var distance = d * (0.2 + 0.5 * progress)
            var dot = dots.itemAt(i)
            dot.x = middle + s.cos * distance
            dot.y = middle + s.sin * distance
            dot.opacity = 0.5 * Math.sin(Math.PI * progress)
        }
    }

    width: d * 1.4
    height: width
    opacity: strength
    visible: strength > 0

    onWidthChanged: refresh()

    FrameAnimation {
        running: field.running && field.strength > 0
        onTriggered: {
            field.time += frameTime
            field.refresh()
        }
    }

    Repeater {
        id: dots

        model: field.count
        onItemAdded: Qt.callLater(field.refresh)

        Rectangle {
            width: 2
            height: 2
            radius: 1
            color: field.color
            opacity: 0
        }
    }
}
