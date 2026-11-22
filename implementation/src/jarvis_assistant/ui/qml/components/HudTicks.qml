// Marcas radiales de los medidores: `count` rayas o bloques repartidos de `from` a `to`
// (grados, 0 a las tres, en el sentido de las agujas del reloj), de `inner` hacia fuera
// `length` píxeles. Las `lit` primeras se encienden en `litColor`, la última de ellas en
// `hotColor`; cada `majorEvery`, una más larga. Ocupa todo su padre.
import QtQuick
import ".."

Item {
    id: ticks

    property int count: 12
    property real from: -90
    property real to: 270                // con una vuelta entera, la última no pisa la primera
    property real inner: 40
    property real length: 4
    property real thickness: 1
    property color color: Theme.neonDim
    property int lit: 0
    property color litColor: Theme.neonCyan
    property color hotColor: Theme.primaryHot
    property int majorEvery: 0
    property real majorLength: length * 1.8
    readonly property bool closed: Math.abs(to - from) >= 359.9
    readonly property real step: count > 1 ? (to - from) / (closed ? count : count - 1) : 0

    anchors.fill: parent

    Repeater {
        model: ticks.count

        Item {
            id: tick

            required property int index
            readonly property bool major: ticks.majorEvery > 0 && index % ticks.majorEvery === 0

            x: ticks.width / 2
            y: ticks.height / 2
            rotation: ticks.from + ticks.step * index

            Rectangle {
                x: ticks.inner
                y: -height / 2
                width: tick.major ? ticks.majorLength : ticks.length
                height: ticks.thickness
                antialiasing: true
                color: tick.index >= ticks.lit ? ticks.color
                     : tick.index === ticks.lit - 1 ? ticks.hotColor : ticks.litColor
            }
        }
    }
}
