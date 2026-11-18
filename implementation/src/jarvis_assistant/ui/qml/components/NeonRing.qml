// Anillo de neón: una pista de segmentos tenues y, encima, el arco del valor como un tubo de
// luz (halo en capas y núcleo casi blanco), con un punto brillante en su extremo. Crece desde
// arriba en el sentido de las agujas del reloj; da la vuelta entera en `maximum`. Desde
// `alert` se pone rojo. En el centro, la cifra con su unidad y la etiqueta en `fontTech`.
// Por defecto es un porcentaje: de 0 a 100, en rojo desde el 85 %.
import QtQuick
import QtQuick.Shapes
import ".."

Item {
    id: ring

    property real value: 0               // 0-`maximum`
    property real maximum: 100
    property real alert: 85              // desde aquí, en rojo
    property string unit: "%"
    property string label: ""
    property color color: Theme.neonCyan
    property bool animated: true
    readonly property real shown: Math.max(0, Math.min(maximum, value))
    readonly property color tint: shown >= alert ? Theme.statusError : color
    readonly property real thickness: Math.round(width * 0.055)
    readonly property real radius: width / 2 - thickness * 2.2   // deja sitio al halo
    readonly property real centre: width / 2
    readonly property int labelSize: Math.max(9, Math.round(width * 0.075))

    property real sweep: 360 * shown / maximum
    Behavior on sweep {
        enabled: ring.animated
        NumberAnimation { duration: 600; easing.type: Easing.OutCubic }
    }

    // Respiración lenta del halo, como un tubo de neón.
    property real glow: 1
    SequentialAnimation on glow {
        running: ring.animated && ring.visible
        loops: Animation.Infinite
        NumberAnimation { to: 0.7; duration: 1600; easing.type: Easing.InOutSine }
        NumberAnimation { to: 1; duration: 1600; easing.type: Easing.InOutSine }
    }

    width: 120
    height: width

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer

        // Pista: segmentos tenues alrededor.
        ShapePath {
            fillColor: "transparent"
            strokeColor: Theme.alpha(ring.tint, 0.16)
            strokeWidth: ring.thickness
            strokeStyle: ShapePath.DashLine
            dashPattern: [0.5, 0.6]
            capStyle: ShapePath.FlatCap

            PathAngleArc {
                centerX: ring.centre
                centerY: ring.centre
                radiusX: ring.radius
                radiusY: ring.radius
                startAngle: -90
                sweepAngle: 360
            }
        }

        // Círculo fino interior.
        ShapePath {
            fillColor: "transparent"
            strokeColor: Theme.alpha(ring.tint, 0.22)
            strokeWidth: 1

            PathAngleArc {
                centerX: ring.centre
                centerY: ring.centre
                radiusX: ring.radius - ring.thickness * 1.6
                radiusY: radiusX
                startAngle: 0
                sweepAngle: 360
            }
        }
    }

    // El valor: halo ancho, halo medio, tubo y núcleo.
    Repeater {
        model: [
            { width: 4.2, alpha: 0.07 },
            { width: 2.6, alpha: 0.16 },
            { width: 1.6, alpha: 0.32 },
            { width: 1.0, alpha: 1.0 },
            { width: 0.35, alpha: 0.85, core: true },
        ]

        Shape {
            id: layer

            required property var modelData

            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            opacity: modelData.core || modelData.alpha >= 1 ? 1 : ring.glow
            visible: ring.sweep > 0.2

            ShapePath {
                fillColor: "transparent"
                strokeColor: layer.modelData.core ? Theme.primaryHot
                                                  : Theme.alpha(ring.tint, layer.modelData.alpha)
                strokeWidth: ring.thickness * layer.modelData.width
                capStyle: ShapePath.RoundCap

                PathAngleArc {
                    centerX: ring.centre
                    centerY: ring.centre
                    radiusX: ring.radius
                    radiusY: ring.radius
                    startAngle: -90
                    sweepAngle: Math.max(0.01, ring.sweep)
                }
            }
        }
    }

    // Chispa en el extremo del arco.
    Item {
        readonly property real angle: (ring.sweep - 90) * Math.PI / 180

        x: ring.centre + ring.radius * Math.cos(angle)
        y: ring.centre + ring.radius * Math.sin(angle)
        visible: ring.sweep > 0.2

        Rectangle {
            anchors.centerIn: parent
            width: ring.thickness * 3.4
            height: width
            radius: width / 2
            color: Theme.alpha(ring.tint, 0.25 * ring.glow)
        }

        Rectangle {
            anchors.centerIn: parent
            width: ring.thickness * 1.3
            height: width
            radius: width / 2
            color: Theme.primaryHot
        }
    }

    Column {
        anchors.centerIn: parent
        spacing: 0

        Row {
            anchors.horizontalCenter: parent.horizontalCenter

            Text {
                id: figure

                objectName: "neon-value"
                text: ring.shown < 10 ? ring.shown.toFixed(1) : Math.round(ring.shown)
                color: Theme.primaryHot
                font.family: Theme.fontTech
                font.weight: Font.Bold
                font.pixelSize: Math.round(ring.width * 0.2)
                style: Text.Outline
                styleColor: Theme.alpha(ring.tint, 0.35)
            }

            Text {
                text: ring.unit
                color: ring.tint
                font.family: Theme.fontTech
                font.weight: Font.Medium
                font.pixelSize: Math.round(ring.width * 0.09)
                anchors.baseline: figure.baseline
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: ring.label
            color: ring.tint
            font.family: Theme.fontTech
            font.weight: Font.DemiBold
            font.pixelSize: ring.labelSize
            font.letterSpacing: ring.labelSize * 0.3
        }
    }
}
