// Esfera de CPU: una banda gruesa de luz con el valor, que crece desde arriba en el sentido
// de las agujas del reloj y da la vuelta entera en el 100 %, sobre una corona de segmentos
// tenues. Fuera, un arco azul a la izquierda, una escala arriba y un arco fino con marcas a
// la derecha. En el centro, la cifra y "CPU". Desde `alert`, en rojo.
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

    component Tag: Text {
        color: Theme.textSecondary
        font.family: Theme.fontTech
        font.pixelSize: Math.max(6, Math.round(gauge.r * 0.075))
        font.letterSpacing: 0.6
        lineHeight: 0.9
    }

    // Rótulos de las esquinas.
    Tag {
        x: 0
        y: 0
        text: "CORE\nSTATUS"
    }
    Tag {
        x: gauge.width - width
        y: 0
        text: "CORE\nSTATUS"
        horizontalAlignment: Text.AlignRight
    }

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer

        // Escala de arriba y arco fino de la derecha.
        ShapePath {
            fillColor: "transparent"
            strokeColor: Theme.alpha(gauge.tint, 0.55)
            strokeWidth: 1

            PathAngleArc {
                centerX: gauge.r
                centerY: gauge.r
                radiusX: gauge.r * 0.9
                radiusY: radiusX
                startAngle: 248
                sweepAngle: 160
            }
        }

        // Cola fina del arco azul.
        ShapePath {
            fillColor: "transparent"
            strokeColor: Theme.alpha(Theme.neonBlue, 0.5)
            strokeWidth: 1

            PathAngleArc {
                centerX: gauge.r
                centerY: gauge.r
                radiusX: gauge.r * 0.9
                radiusY: radiusX
                startAngle: 118
                sweepAngle: 24
            }
        }

        // Pista de la banda: dos circunferencias tenues.
        ShapePath {
            fillColor: "transparent"
            strokeColor: Theme.alpha(Theme.neonDim, 0.9)
            strokeWidth: 1

            PathAngleArc {
                centerX: gauge.r
                centerY: gauge.r
                radiusX: gauge.r * 0.79
                radiusY: radiusX
                startAngle: 0
                sweepAngle: 360
            }
        }
        ShapePath {
            fillColor: "transparent"
            strokeColor: Theme.alpha(Theme.neonDim, 0.7)
            strokeWidth: 1

            PathAngleArc {
                centerX: gauge.r
                centerY: gauge.r
                radiusX: gauge.r * 0.62
                radiusY: radiusX
                startAngle: 0
                sweepAngle: 360
            }
        }
    }

    // Arco azul de la izquierda.
    HudArc {
        radius: gauge.r * 0.9
        startAngle: 142
        sweep: 96
        thickness: Math.max(3, gauge.r * 0.06)
        color: Theme.neonBlue
        halo: 5
        glow: gauge.glow
        core: false
    }

    // Marcas de la escala de arriba y del arco de la derecha.
    HudTicks {
        count: 11
        from: 248
        to: 292
        inner: gauge.r * 0.9
        length: 3
        majorEvery: 5
        majorLength: 7
        color: Theme.alpha(gauge.tint, 0.7)
    }
    HudTicks {
        count: 9
        from: 330
        to: 402
        inner: gauge.r * 0.9
        length: 3
        majorEvery: 4
        majorLength: 6
        color: Theme.alpha(gauge.tint, 0.6)
    }

    // Corona interior de segmentos.
    HudTicks {
        count: 28
        inner: gauge.r * 0.5
        length: gauge.r * 0.09
        thickness: Math.max(2, gauge.r * 0.05)
        color: Theme.alpha(Theme.neonDim, 1)
    }

    // El valor: banda gruesa de luz.
    HudArc {
        radius: gauge.r * 0.705
        sweep: gauge.sweep
        thickness: gauge.r * 0.13
        color: Theme.mix(gauge.tint, Theme.primaryHot, 0.15)
        halo: 6
        glow: gauge.glow
        core: false
    }

    // Disco del centro.
    Rectangle {
        anchors.centerIn: parent
        width: gauge.r * 0.92
        height: width
        radius: width / 2
        color: Theme.neonCore
        border.width: 1
        border.color: Theme.alpha(gauge.tint, 0.3)
    }

    HudReadout {
        anchors.centerIn: parent
        value: gauge.shown
        label: "CPU"
        size: Math.round(gauge.r * 0.32)
        color: gauge.tint
    }
}
