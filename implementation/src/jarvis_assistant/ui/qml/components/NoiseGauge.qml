// Esfera de ruido: un anillo con la escala en decibelios alrededor y el valor como un arco
// de luz que crece desde arriba en el sentido de las agujas del reloj (vuelta entera en
// `maximum`), con un espectro de barras a cada lado que se agita más cuanto más ruido hay.
// En el centro, la cifra y "RUIDO", del color `tint` (por defecto, desde `alert` en rojo). Sin
// movimiento (`animated` falso), las barras se quedan quietas.
import QtQuick
import QtQuick.Shapes
import ".."

Item {
    id: gauge

    property real value: 0               // dB, 0-`maximum`
    property real maximum: 100
    property real alert: 65
    property bool animated: true
    property real ringSize: 140
    readonly property real shown: Math.max(0, Math.min(maximum, value))
    property color tint: shown >= alert ? Theme.statusError : Theme.neonCyan

    Behavior on tint {
        enabled: gauge.animated
        ColorAnimation { duration: 600 }
    }
    readonly property real r: ringSize / 2
    readonly property real wing: ringSize * 0.46     // ancho del espectro de cada lado
    readonly property int bars: 16                   // barras por lado
    // Cuánto se agita el espectro: algo incluso en silencio, del todo con mucho ruido.
    readonly property real stir: 0.45 + 0.55 * Math.min(1, shown / alert)

    property real sweep: 360 * shown / maximum
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

    // Altura de cada barra, de 0 a 1: primero las de la izquierda, luego las de la derecha.
    property var jitter: steady()
    function steady() {
        var heights = []
        for (var i = 0; i < 2 * bars; i++)
            heights.push(0.7 + 0.3 * Math.abs(Math.sin(i * 2.3)))
        return heights
    }
    Timer {
        interval: Theme.motionLevel
        repeat: true
        running: gauge.animated && gauge.visible
        onTriggered: {
            var heights = []
            for (var i = 0; i < 2 * gauge.bars; i++)
                heights.push(0.5 + 0.5 * Math.random())
            gauge.jitter = heights
        }
    }

    width: ringSize + 2 * wing
    height: ringSize

    // Un lado del espectro; la barra 0 es la más cercana al anillo.
    component Wing: Item {
        id: side

        property bool mirrored: false

        y: 0
        width: gauge.wing
        height: gauge.ringSize

        Repeater {
            model: gauge.bars

            Rectangle {
                id: bar

                required property int index
                readonly property real fade: 1 - index / gauge.bars
                readonly property real reach: gauge.jitter[index + (side.mirrored ? 0 : gauge.bars)]

                width: Math.max(1.5, gauge.ringSize * 0.012)
                height: gauge.ringSize * 0.98 * Math.pow(fade, 0.8) * gauge.stir * reach
                x: side.mirrored ? side.width - (index + 1) * (side.width / gauge.bars)
                             : index * (side.width / gauge.bars) + side.width / gauge.bars - width
                y: (side.height - height) / 2
                radius: width / 2
                opacity: 0.25 + 0.75 * Math.pow(fade, 0.7)

                Behavior on height {
                    enabled: gauge.animated
                    NumberAnimation { duration: Theme.motionLevel }
                }

                gradient: Gradient {
                    GradientStop { position: 0.0; color: Theme.alpha(gauge.tint, 0) }
                    GradientStop { position: 0.3; color: Theme.alpha(gauge.tint, 0.55) }
                    GradientStop { position: 0.5; color: Theme.mix(gauge.tint, Theme.primaryHot, 0.4) }
                    GradientStop { position: 0.7; color: Theme.alpha(gauge.tint, 0.55) }
                    GradientStop { position: 1.0; color: Theme.alpha(gauge.tint, 0) }
                }
            }
        }
    }

    Wing { x: 0; mirrored: true }
    Wing { x: gauge.wing + gauge.ringSize }

    // El anillo, en el centro.
    Item {
        id: dial

        x: gauge.wing
        width: gauge.ringSize
        height: width

        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer

            // Disco del centro, con un brillo tenue hacia dentro.
            ShapePath {
                strokeColor: Theme.alpha(gauge.tint, 0.4)
                strokeWidth: 1
                fillGradient: RadialGradient {
                    centerX: gauge.r
                    centerY: gauge.r
                    centerRadius: gauge.r * 0.62
                    focalX: gauge.r
                    focalY: gauge.r
                    GradientStop { position: 0.0; color: Theme.mix(Theme.neonCore, gauge.tint, 0.18) }
                    GradientStop { position: 1.0; color: Theme.mix(Theme.neonCore, gauge.tint, 0.04) }
                }

                PathAngleArc {
                    centerX: gauge.r
                    centerY: gauge.r
                    radiusX: gauge.r * 0.62
                    radiusY: radiusX
                    startAngle: 0
                    sweepAngle: 360
                }
            }

            // Circunferencia discontinua de fuera.
            ShapePath {
                fillColor: "transparent"
                strokeColor: Theme.alpha(gauge.tint, 0.5)
                strokeWidth: 1
                strokeStyle: ShapePath.DashLine
                dashPattern: [7, 4]

                PathAngleArc {
                    centerX: gauge.r
                    centerY: gauge.r
                    radiusX: gauge.r * 0.97
                    radiusY: radiusX
                    startAngle: 0
                    sweepAngle: 360
                }
            }

            // Pista del valor.
            ShapePath {
                fillColor: "transparent"
                strokeColor: Theme.alpha(Theme.neonDim, 0.9)
                strokeWidth: 1

                PathAngleArc {
                    centerX: gauge.r
                    centerY: gauge.r
                    radiusX: gauge.r * 0.75
                    radiusY: radiusX
                    startAngle: 0
                    sweepAngle: 360
                }
            }
        }

        // Tramos de adorno sobre la pista, girando muy despacio.
        Repeater {
            model: [[-84, 46], [-22, 64], [62, 38], [118, 78], [214, 52]]

            HudArc {
                required property var modelData

                radius: gauge.r * 0.75
                startAngle: modelData[0]
                sweep: modelData[1]
                thickness: Math.max(2, gauge.r * 0.05)
                color: Theme.alpha(gauge.tint, 0.3)
                halo: 0
                core: false
                rotation: gauge.spin
            }
        }

        // Escala en decibelios alrededor, cada 10.
        Repeater {
            model: 10

            Item {
                id: mark

                required property int index

                x: gauge.r
                y: gauge.r
                rotation: mark.index * 36

                Text {
                    x: -width / 2
                    y: -gauge.r * 0.87 - height / 2
                    text: mark.index * gauge.maximum / 10
                    color: Theme.alpha(gauge.tint, 0.55)
                    font.family: Theme.fontTech
                    font.pixelSize: Math.max(6, Math.round(gauge.r * 0.08))
                    rotation: mark.index > 2 && mark.index < 8 ? 180 : 0   // abajo, del derecho
                }
            }
        }

        // El valor.
        HudArc {
            radius: gauge.r * 0.75
            sweep: gauge.sweep
            thickness: Math.max(2.5, gauge.r * 0.055)
            color: gauge.tint
            halo: 5
            glow: gauge.glow
            cap: ShapePath.RoundCap
        }

        HudReadout {
            anchors.centerIn: parent
            value: gauge.shown
            unit: "dB"
            label: "RUIDO"
            size: Math.round(gauge.r * 0.32)
            color: gauge.tint
        }
    }

    property real spin: 0
    NumberAnimation on spin {
        running: gauge.animated && gauge.visible
        loops: Animation.Infinite
        from: 0
        to: 360
        duration: 90000
    }
}
