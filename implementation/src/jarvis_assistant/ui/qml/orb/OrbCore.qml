// Núcleo del orbe: plasma. Tres capas translúcidas de contorno irregular que se deforman
// cada una a su ritmo. La deformación crece con el caos (pensar) y con el nivel de la voz.
import QtQuick
import QtQuick.Shapes
import ".."

Item {
    id: core

    property real diameter: 100
    property color color: Theme.primary
    property real glow: 0            // 0–1: nivel de la voz y respiración
    property real time: 0            // reloj del pensamiento (`mind` del orbe)
    property real chaos: 0
    property real level: 0           // nivel de la voz, de 0 a 1
    property bool fluid: true        // falso: contorno liso (calidad baja, movimiento reducido)

    readonly property int points: 64
    readonly property real middle: diameter * 0.75
    readonly property real ripple: fluid ? 0.03 + 0.1 * chaos + 0.07 * level : 0

    // Contorno cerrado de radio `radius`, deformado por tres ondas de distinta frecuencia.
    function outline(radius, seed, turn) {
        var result = []
        var t = time * turn
        for (var i = 0; i < points; i++) {
            var a = i * 2 * Math.PI / points
            var k = 1 + ripple * (0.5 * Math.sin(3 * a + t * 1.3 + seed)
                                  + 0.3 * Math.sin(5 * a - t * 1.9 + seed * 2)
                                  + 0.2 * Math.sin(8 * a + t * 2.9 + seed * 3))
            result.push(Qt.point(middle + Math.cos(a) * radius * k,
                                 middle + Math.sin(a) * radius * k))
        }
        result.push(result[0])
        return result
    }

    width: diameter
    height: diameter

    // Resplandor.
    Shape {
        anchors.centerIn: parent
        width: core.diameter * 1.5
        height: width
        opacity: 0.35 + 0.65 * core.glow

        ShapePath {
            strokeWidth: -1
            fillGradient: RadialGradient {
                centerX: core.middle
                centerY: core.middle
                focalX: centerX
                focalY: centerY
                centerRadius: core.middle
                GradientStop { position: 0.0; color: Theme.alpha(core.color, 0.55) }
                GradientStop { position: 1.0; color: Theme.alpha(core.color, 0.0) }
            }
            PathAngleArc {
                centerX: core.middle
                centerY: core.middle
                radiusX: core.middle
                radiusY: radiusX
                sweepAngle: 360
            }
        }
    }

    Shape {
        anchors.centerIn: parent
        width: core.diameter * 1.5
        height: width
        // El contorno cambia en cada fotograma: se dibuja con el trazador sencillo, que es
        // mucho más barato de recalcular, y el suavizado lo pone la capa.
        layer.enabled: true
        layer.samples: 4

        // Capa exterior: membrana.
        ShapePath {
            strokeColor: Theme.alpha(core.color, 0.6)
            strokeWidth: 1
            fillGradient: RadialGradient {
                centerX: core.middle
                centerY: core.middle
                focalX: centerX
                focalY: centerY
                centerRadius: core.diameter * 0.55
                GradientStop { position: 0.0; color: Theme.alpha(core.color, 0.5) }
                GradientStop { position: 1.0; color: Theme.alpha(core.color, 0.1) }
            }
            PathPolyline { path: core.outline(core.diameter * 0.47, 0.0, 1) }
        }

        // Capa media: gira al revés que la membrana.
        ShapePath {
            strokeColor: Theme.alpha(Theme.primaryBright, 0.45)
            strokeWidth: 1
            fillGradient: RadialGradient {
                centerX: core.middle
                centerY: core.middle
                focalX: centerX
                focalY: centerY
                centerRadius: core.diameter * 0.4
                GradientStop { position: 0.0; color: Theme.alpha(Theme.primaryBright, 0.55) }
                GradientStop { position: 1.0; color: Theme.alpha(core.color, 0.15) }
            }
            PathPolyline { path: core.outline(core.diameter * 0.33, 2.1, -1.4) }
        }

        // Centro: casi blanco; es lo más brillante de la pantalla.
        ShapePath {
            strokeWidth: -1
            fillGradient: RadialGradient {
                centerX: core.middle
                centerY: core.middle
                focalX: centerX
                focalY: centerY
                centerRadius: core.diameter * 0.24
                GradientStop {
                    position: 0.0
                    color: Theme.mix(Theme.primaryBright, Theme.primaryHot, core.glow)
                }
                GradientStop { position: 0.6; color: Theme.alpha(Theme.primaryBright, 0.7) }
                GradientStop { position: 1.0; color: Theme.alpha(core.color, 0.0) }
            }
            PathPolyline { path: core.outline(core.diameter * 0.2, 4.4, 2.2) }
        }
    }
}
