// Satélites: puntos brillantes en órbitas excéntricas, con estela. Destellan cuando la onda
// del latido pasa por ellos.
import QtQuick
import ".."
import "field.js" as Field

Item {
    id: sats

    property real d: 100             // D del orbe
    property int count: 5
    property bool trails: true
    property color color: Theme.primary
    property real spin: 0            // segundos de giro (`flow` del orbe)
    property real strength: 0        // 0–1: visibilidad del conjunto
    property Item conductor          // el orbe: da la onda del latido

    width: d * 1.4
    height: width
    visible: strength > 0.01

    Repeater {
        model: sats.count

        Item {
            id: sat

            required property int index
            readonly property real major: sats.d * (0.47 + 0.045 * index)
            readonly property real minor: major * (0.36 + 0.2 * Field.hash(index, 1))
            readonly property real tilt: index * 1.9
            readonly property real turn: (0.5 + 0.6 * Field.hash(index, 2)) * (index % 2 ? -1 : 1)
            readonly property real theta: sats.spin * turn + Field.hash(index, 3) * 6.28

            Repeater {
                model: sats.trails ? 7 : 1

                Rectangle {
                    id: dot

                    required property int index
                    readonly property real at: sat.theta - index * 0.07 * (sat.turn > 0 ? 1 : -1)
                    readonly property real ex: sat.major * Math.cos(at)
                    readonly property real ey: sat.minor * Math.sin(at)
                    readonly property real px: ex * Math.cos(sat.tilt) - ey * Math.sin(sat.tilt)
                    readonly property real py: ex * Math.sin(sat.tilt) + ey * Math.cos(sat.tilt)
                    readonly property real shine: index === 0 && sats.conductor
                        ? sats.conductor.wave(Math.sqrt(px * px + py * py) / sats.d) : 0

                    width: Math.max(2, sats.d * 0.013) * (1 - index * 0.11) * (1 + 1.2 * shine)
                    height: width
                    radius: width / 2
                    x: sats.width / 2 + px - width / 2
                    y: sats.height / 2 + py - height / 2
                    color: index === 0 ? Theme.primaryBright : sats.color
                    opacity: sats.strength * (index === 0 ? 1 : 0.5 * (1 - index / 7))
                }
            }
        }
    }
}
