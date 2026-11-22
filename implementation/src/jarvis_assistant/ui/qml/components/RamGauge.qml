// Esfera de RAM: una corona de bloques que se encienden desde arriba en el sentido de las
// agujas del reloj, todos en el 100 %, dentro de un marco octogonal. En el centro, la cifra
// y "RAM". Desde `alert`, en rojo.
import QtQuick
import QtQuick.Shapes
import ".."

Item {
    id: gauge

    property real value: 0               // 0-100
    property real alert: 85
    property bool animated: true
    readonly property real shown: Math.max(0, Math.min(100, value))
    readonly property color tint: shown >= alert ? Theme.statusError : Theme.neonCyan
    readonly property real r: width / 2
    readonly property real dial: r * 0.88    // radio de la esfera: deja las esquinas a los rótulos
    readonly property int blocks: 48

    property real sweep: 360 * shown / 100
    Behavior on sweep {
        enabled: gauge.animated
        NumberAnimation { duration: 600; easing.type: Easing.OutCubic }
    }

    // Respiración lenta del halo, como un tubo de neón.
    property real glow: 1
    SequentialAnimation on glow {
        running: gauge.animated && gauge.visible
        loops: Animation.Infinite
        NumberAnimation { to: 0.6; duration: 1600; easing.type: Easing.InOutSine }
        NumberAnimation { to: 1; duration: 1600; easing.type: Easing.InOutSine }
    }

    width: 160
    height: width

    // Vértices de un octógono con los lados planos arriba, abajo y a los lados.
    function octagon(apothem) {
        var points = []
        var reach = apothem / Math.cos(Math.PI / 8)
        for (var i = 0; i <= 8; i++) {
            var angle = Math.PI / 8 + i * Math.PI / 4
            points.push(Qt.point(r + reach * Math.cos(angle), r + reach * Math.sin(angle)))
        }
        return points
    }

    component Tag: Text {
        color: Theme.textSecondary
        font.family: Theme.fontTech
        font.pixelSize: Math.max(6, Math.round(gauge.r * 0.075))
        font.letterSpacing: 0.6
        lineHeight: 0.9
    }

    // Rótulos de las esquinas.
    Tag {
        x: gauge.width - width
        y: 0
        text: "SYSTEM\nMEMORY"
    }
    Tag {
        x: gauge.width - width
        y: gauge.height - height
        text: "SYSTEM\nMEMORY"
    }
    Tag {
        x: 0
        y: gauge.height - height
        text: "DSB"
    }

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer

        // Marco: octógono exterior y otro tenue por dentro.
        ShapePath {
            fillColor: "transparent"
            strokeColor: Theme.alpha(gauge.tint, 0.5)
            strokeWidth: 1
            joinStyle: ShapePath.MiterJoin

            PathPolyline { path: gauge.octagon(gauge.dial * 0.97) }
        }
        ShapePath {
            fillColor: "transparent"
            strokeColor: Theme.alpha(gauge.tint, 0.18)
            strokeWidth: 1
            joinStyle: ShapePath.MiterJoin

            PathPolyline { path: gauge.octagon(gauge.dial * 0.9) }
        }

        // Circunferencia fina por dentro de la corona.
        ShapePath {
            fillColor: "transparent"
            strokeColor: Theme.alpha(Theme.neonDim, 0.9)
            strokeWidth: 1

            PathAngleArc {
                centerX: gauge.r
                centerY: gauge.r
                radiusX: gauge.dial * 0.56
                radiusY: radiusX
                startAngle: 0
                sweepAngle: 360
            }
        }
    }

    // Arco fino de adorno, arriba a la derecha, por dentro de la corona.
    HudArc {
        radius: gauge.dial * 0.56
        startAngle: -78
        sweep: 58
        thickness: 1.5
        color: gauge.tint
        halo: 3
        glow: gauge.glow
        core: false
    }

    // Halo detrás de los bloques encendidos.
    HudArc {
        radius: gauge.dial * 0.73
        sweep: gauge.sweep
        thickness: gauge.dial * 0.18
        color: gauge.tint
        halo: 6
        glow: gauge.glow
        body: 0.08
        core: false
    }

    // La corona: los bloques encendidos son el valor.
    HudTicks {
        count: gauge.blocks
        inner: gauge.dial * 0.64
        length: gauge.dial * 0.18
        thickness: Math.max(2, 2 * Math.PI * gauge.dial * 0.73 / gauge.blocks * 0.62)
        color: Theme.alpha(Theme.neonDim, 1)
        lit: Math.round(gauge.blocks * gauge.sweep / 360)
        litColor: gauge.tint
    }

    // Disco del centro.
    Rectangle {
        anchors.centerIn: parent
        width: gauge.dial * 0.94
        height: width
        radius: width / 2
        color: Theme.neonCore
        border.width: 1
        border.color: Theme.alpha(gauge.tint, 0.3)
    }

    HudReadout {
        anchors.centerIn: parent
        value: gauge.shown
        label: "RAM"
        size: Math.round(gauge.dial * 0.32)
        color: gauge.tint
    }
}
