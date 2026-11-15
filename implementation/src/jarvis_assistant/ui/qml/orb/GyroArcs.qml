// Arcos giroscópicos: tres arcos inclinados que giran en planos distintos alrededor del
// núcleo. El caos los desalinea.
import QtQuick
import QtQuick.Shapes
import ".."

Item {
    id: gyro

    property real diameter: 100
    property color color: Theme.primary
    property real spin: 0            // segundos de giro (`flow` del orbe)
    property real time: 0            // reloj del pensamiento (`mind` del orbe)
    property real chaos: 0
    property real strength: 0        // 0–1: visibilidad del conjunto

    width: diameter * 1.2
    height: width
    opacity: strength
    visible: strength > 0.01

    Repeater {
        model: 3

        Shape {
            id: arc

            required property int index
            readonly property real middle: width / 2
            readonly property real lean: index * 1.2 + gyro.spin * 0.15

            anchors.centerIn: parent
            width: gyro.diameter * (1 + index * 0.09)
            height: width
            preferredRendererType: Shape.CurveRenderer
            transform: [
                // Giro dentro de su plano.
                Rotation {
                    origin.x: arc.middle
                    origin.y: arc.middle
                    angle: gyro.spin * (45 + arc.index * 19) * (arc.index % 2 ? -1 : 1)
                },
                // Inclinación del plano.
                Rotation {
                    origin.x: arc.middle
                    origin.y: arc.middle
                    axis.x: Math.cos(arc.lean)
                    axis.y: Math.sin(arc.lean)
                    axis.z: 0
                    angle: 62 + arc.index * 9
                           + 16 * gyro.chaos * Math.sin(gyro.time * 0.9 + arc.index * 2)
                }
            ]

            ShapePath {
                strokeColor: Theme.alpha(gyro.color, 0.75)
                strokeWidth: 1.5
                fillColor: "transparent"
                capStyle: ShapePath.RoundCap
                PathAngleArc {
                    centerX: arc.middle
                    centerY: arc.middle
                    radiusX: arc.middle - 3
                    radiusY: radiusX
                    startAngle: 0
                    sweepAngle: 200 - arc.index * 40
                }
            }

            ShapePath {
                strokeColor: Theme.primaryBright
                strokeWidth: 2.5
                fillColor: "transparent"
                capStyle: ShapePath.RoundCap
                PathAngleArc {
                    centerX: arc.middle
                    centerY: arc.middle
                    radiusX: arc.middle - 3
                    radiusY: radiusX
                    startAngle: 238
                    sweepAngle: 24
                }
            }
        }
    }
}
