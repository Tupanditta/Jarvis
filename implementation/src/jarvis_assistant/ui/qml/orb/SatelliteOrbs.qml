// Orbes satélite: cinco orbes pequeños con su propio anillo alrededor del orbe, unidos a él
// por un hilo por el que viajan señales. Su anillo pasa a ámbar en «esperando».
// El origen de este elemento es el centro del orbe.
import QtQuick
import ".."
import "field.js" as Field

Item {
    id: moons

    property Item conductor          // el orbe
    property real d: 100             // D del orbe
    property real gather: 1          // 0: recogidos en el núcleo; 1: en su sitio

    readonly property real flow: conductor ? conductor.flow : 0
    readonly property real mind: conductor ? conductor.mind : 0
    readonly property real chaos: conductor ? conductor.chaos : 0
    readonly property real level: conductor ? conductor.smoothLevel : 0
    readonly property real live: conductor ? conductor.live : 0
    readonly property color color: conductor ? conductor.accent : Theme.primary

    // Ángulo (grados; 0 a la derecha, −90 arriba) y distancia (en D) de cada uno: a los lados
    // y arriba, donde no hay subtítulos ni caja de texto.
    readonly property var places: [
        { angle: -90, distance: 0.9 }, { angle: -34, distance: 1.04 },
        { angle: 21, distance: 0.98 }, { angle: 159, distance: 1.0 },
        { angle: 214, distance: 1.06 }
    ]

    opacity: live
    visible: live > 0.01

    Repeater {
        model: moons.places

        // Eje del satélite: gira alrededor del centro del orbe.
        Item {
            id: axis

            required property var modelData
            required property int index
            readonly property real size: moons.d * 0.075
            readonly property real inner: moons.d * 0.72 * moons.gather
            readonly property real distance: moons.d * moons.gather
                * (modelData.distance + 0.03 * Math.sin(moons.flow * 0.3 + index * 2.4))
            readonly property real shine: moons.conductor
                ? moons.conductor.wave(distance / moons.d) : 0
            // Señal por el hilo: los pares hacia fuera, los impares hacia el núcleo.
            readonly property real travel: {
                var t = moons.mind * (0.22 + 0.1 * Field.hash(index, 1)) + Field.hash(index, 2)
                t -= Math.floor(t)
                return index % 2 ? 1 - t : t
            }

            rotation: modelData.angle + 7 * Math.sin(moons.flow * 0.12 + index * 1.3)

            // Hilo.
            Item {
                id: thread

                x: axis.inner
                width: Math.max(0, axis.distance - axis.size * 0.6 - axis.inner)

                Rectangle {
                    y: -0.5
                    width: thread.width
                    height: 1
                    color: moons.color
                    opacity: 0.12 + 0.4 * axis.shine
                }

                Rectangle {
                    width: 4
                    height: 4
                    radius: 2
                    x: axis.travel * thread.width - 2
                    y: -2
                    color: Theme.primaryBright
                    opacity: Math.min(1, (0.3 + 0.7 * moons.chaos + moons.level)
                                         * Math.sin(Math.PI * axis.travel))
                }
            }

            Item {
                x: axis.distance
                scale: 1 + 0.3 * axis.shine

                // Halo.
                Rectangle {
                    anchors.centerIn: parent
                    width: axis.size * 1.9
                    height: width
                    radius: width / 2
                    color: Theme.alpha(moons.color, 0.08 + 0.2 * axis.shine)
                }

                // Anillo con una marca que hace visible su giro.
                Rectangle {
                    anchors.centerIn: parent
                    width: axis.size
                    height: width
                    radius: width / 2
                    color: "transparent"
                    border.width: 1
                    border.color: Theme.alpha(moons.color, 0.75)
                    rotation: moons.flow * (50 + axis.index * 13) * (axis.index % 2 ? -1 : 1)

                    Rectangle {
                        width: 3
                        height: 3
                        radius: 1.5
                        color: Theme.primaryBright
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.verticalCenter: parent.top
                    }
                }

                Rectangle {
                    anchors.centerIn: parent
                    width: axis.size * (0.3 + 0.15 * moons.level)
                    height: width
                    radius: width / 2
                    color: Theme.mix(moons.color, Theme.primaryBright, 0.5 + 0.5 * axis.shine)
                }
            }
        }
    }
}
