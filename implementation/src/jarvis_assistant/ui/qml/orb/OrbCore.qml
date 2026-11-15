// Núcleo del orbe: esfera con degradado radial y meridianos elípticos que giran para dar
// volumen. Su resplandor crece con el nivel de la voz.
import QtQuick
import QtQuick.Shapes
import ".."

Item {
    id: core

    property real diameter: 100
    property color color: Theme.primary
    property real glow: 0            // 0–1: nivel de la voz y respiración
    property real phase: 0           // fase del giro de los meridianos, en radianes

    width: diameter
    height: diameter

    Shape {
        anchors.centerIn: parent
        width: core.diameter * 1.5
        height: width
        opacity: 0.35 + 0.65 * core.glow

        ShapePath {
            strokeWidth: -1
            fillGradient: RadialGradient {
                centerX: core.diameter * 0.75
                centerY: core.diameter * 0.75
                focalX: centerX
                focalY: centerY
                centerRadius: core.diameter * 0.75
                GradientStop { position: 0.0; color: Theme.alpha(core.color, 0.55) }
                GradientStop { position: 1.0; color: Theme.alpha(core.color, 0.0) }
            }
            PathAngleArc {
                centerX: core.diameter * 0.75
                centerY: core.diameter * 0.75
                radiusX: core.diameter * 0.75
                radiusY: radiusX
                sweepAngle: 360
            }
        }
    }

    Shape {
        anchors.fill: parent

        ShapePath {
            strokeWidth: -1
            fillGradient: RadialGradient {
                centerX: core.diameter / 2
                centerY: core.diameter / 2
                focalX: centerX
                focalY: centerY
                centerRadius: core.diameter / 2
                GradientStop { position: 0.0; color: Theme.primaryBright }
                GradientStop { position: 0.45; color: core.color }
                GradientStop { position: 1.0; color: Theme.alpha(core.color, 0.0) }
            }
            PathAngleArc {
                centerX: core.diameter / 2
                centerY: core.diameter / 2
                radiusX: core.diameter / 2
                radiusY: radiusX
                sweepAngle: 360
            }
        }
    }

    Repeater {
        model: 3

        Rectangle {
            id: meridian

            required property int index

            anchors.centerIn: parent
            width: core.diameter * 0.82
            height: width
            radius: width / 2
            color: "transparent"
            border.width: 1
            border.color: Theme.alpha(Theme.primaryBright, 0.45)
            transform: Scale {
                origin.x: meridian.width / 2
                origin.y: meridian.height / 2
                xScale: Math.cos(core.phase + meridian.index * Math.PI / 3)
            }
        }
    }
}
