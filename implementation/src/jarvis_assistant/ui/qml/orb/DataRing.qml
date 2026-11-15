// Anillo de datos del orbe (Interfaz, sección 3). Los datos son decorativos y fijos.
// Se dibuja una vez; el giro y la escala se aplican al elemento, sin volver a dibujar.
import QtQuick
import ".."

Canvas {
    id: ring

    property int variant: 1          // 1: marcas cada 5°; 2: arcos con valores; 3: discontinua con código
    property real diameter: 100
    property color color: Theme.primary
    property bool showText: true
    property real sparks: 0          // 0–1: visibilidad de los segmentos que parpadean
    property real time: 0            // reloj del pensamiento (`mind` del orbe)
    readonly property real pad: 26   // margen para el texto que queda fuera del anillo

    readonly property var values: ["0x3F", "128", "0xA7", "64", "0x1C", "2048"]
    readonly property var fragments: ["if (ready)", "sync()", "0b1011", "await io"]

    width: diameter + 2 * pad
    height: width
    antialiasing: true

    onColorChanged: requestPaint()
    onDiameterChanged: requestPaint()
    onShowTextChanged: requestPaint()

    function label(ctx, text, angle, radius) {
        ctx.save()
        ctx.rotate(angle)
        ctx.translate(0, -radius)
        ctx.fillText(text, 0, 0)
        ctx.restore()
    }

    // Segmentos que parpadean sobre el anillo, cada uno a su ritmo. Giran con él.
    Repeater {
        model: 5

        Item {
            id: spark

            required property int index

            anchors.fill: parent
            rotation: index * 72 + ring.variant * 23

            Rectangle {
                width: ring.diameter * 0.06
                height: 2
                radius: 1
                y: ring.pad - 1
                anchors.horizontalCenter: parent.horizontalCenter
                color: Theme.primaryBright
                opacity: ring.sparks * Math.pow(Math.max(0, Math.sin(
                    ring.time * (1.1 + spark.index * 0.43) + spark.index * 2.3 + ring.variant)), 8)
                visible: opacity > 0.01
            }
        }
    }

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        var r = diameter / 2
        ctx.translate(width / 2, height / 2)
        ctx.strokeStyle = Theme.alpha(color, 0.6)
        ctx.fillStyle = Theme.alpha(color, 0.6)
        ctx.lineWidth = 1
        ctx.font = Math.max(8, Math.round(diameter * 0.028)) + 'px "' + Theme.fontMono + '"'
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"
        var i, a

        if (variant === 1) {
            ctx.beginPath()
            ctx.arc(0, 0, r, 0, 2 * Math.PI)
            ctx.stroke()
            for (i = 0; i < 72; i++) {
                a = i * Math.PI / 36
                var len = i % 6 === 0 ? r * 0.06 : r * 0.03
                ctx.beginPath()
                ctx.moveTo(Math.cos(a) * r, Math.sin(a) * r)
                ctx.lineTo(Math.cos(a) * (r - len), Math.sin(a) * (r - len))
                ctx.stroke()
            }
        } else if (variant === 2) {
            ctx.lineWidth = 2
            for (i = 0; i < 6; i++) {
                a = i * Math.PI / 3
                ctx.beginPath()
                ctx.arc(0, 0, r, a, a + Math.PI * 2 / 9)
                ctx.stroke()
                if (showText)
                    label(ctx, values[i], a + Math.PI * 5 / 18 + Math.PI / 2, r)
            }
        } else {
            for (i = 0; i < 60; i++) {
                a = i * Math.PI / 30
                ctx.beginPath()
                ctx.arc(0, 0, r, a, a + Math.PI / 50)
                ctx.stroke()
            }
            if (showText) {
                for (i = 0; i < 4; i++)
                    label(ctx, fragments[i], i * Math.PI / 2 + Math.PI / 4, r + pad * 0.5)
            }
        }
    }
}
