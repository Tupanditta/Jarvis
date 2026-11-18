// Arco de neón de los medidores: un tubo de luz sobre una circunferencia, con halo en capas
// y, si `core`, un núcleo casi blanco en el centro. Los ángulos van en grados, 0 a las tres
// y en el sentido de las agujas del reloj (-90 es arriba). Ocupa todo su padre.
import QtQuick
import QtQuick.Shapes
import ".."

Shape {
    id: arc

    property real centre: width / 2
    property real radius: 0
    property real startAngle: -90
    property real sweep: 0
    property real thickness: 2
    property color color: Theme.neonCyan
    property real halo: 6                // anchura extra del halo, en píxeles
    property real glow: 1                // intensidad del halo (respiración)
    property real body: 1                // opacidad del tubo: con 0, solo el halo
    property bool core: true
    property int cap: ShapePath.FlatCap

    anchors.fill: parent
    preferredRendererType: Shape.CurveRenderer
    visible: sweep > 0.2

    component Layer: ShapePath {
        property real extra: 0
        property real strength: 1

        fillColor: "transparent"
        strokeColor: Theme.alpha(arc.color, arc.color.a * strength)
        strokeWidth: arc.thickness + extra
        capStyle: arc.cap

        PathAngleArc {
            centerX: arc.centre
            centerY: arc.centre
            radiusX: arc.radius
            radiusY: arc.radius
            startAngle: arc.startAngle
            sweepAngle: Math.max(0.01, arc.sweep)
        }
    }

    Layer { extra: arc.halo * 2; strength: 0.06 * arc.glow }
    Layer { extra: arc.halo; strength: 0.14 * arc.glow }
    Layer { extra: arc.halo * 0.4; strength: 0.32 * arc.glow }
    Layer { strength: arc.body }

    ShapePath {
        fillColor: "transparent"
        strokeColor: arc.core ? Theme.alpha(Theme.primaryHot, 0.85) : "transparent"
        strokeWidth: Math.max(1, arc.thickness * 0.3)
        capStyle: arc.cap

        PathAngleArc {
            centerX: arc.centre
            centerY: arc.centre
            radiusX: arc.radius
            radiusY: arc.radius
            startAngle: arc.startAngle
            sweepAngle: Math.max(0.01, arc.sweep)
        }
    }
}
