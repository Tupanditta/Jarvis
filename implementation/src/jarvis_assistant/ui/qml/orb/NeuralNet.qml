// Red neuronal: nodos repartidos en una esfera que gira en 3D alrededor del núcleo, unidos
// a sus vecinos por enlaces que se encienden y se apagan como sinapsis.
import QtQuick
import ".."
import "field.js" as Field

Item {
    id: net

    property real radius: 100
    property int count: 28
    property color color: Theme.primary
    property real spin: 0            // giro de la esfera, en radianes
    property real time: 0            // reloj del pensamiento (`mind` del orbe)
    property real chaos: 0
    property real strength: 0        // 0–1: visibilidad del conjunto

    // Reparto uniforme en la esfera (espiral de Fibonacci).
    readonly property var nodes: {
        var result = []
        for (var i = 0; i < count; i++) {
            var y = 1 - 2 * (i + 0.5) / count
            var ring = Math.sqrt(1 - y * y)
            var a = i * 2.39996
            result.push({ x: Math.cos(a) * ring, y: y, z: Math.sin(a) * ring })
        }
        return result
    }
    readonly property var pairs: Field.nearest(nodes, 2)

    // Posición en pantalla de cada nodo; `z` de −1 (detrás) a 1 (delante).
    readonly property var pts: {
        var result = []
        var ca = Math.cos(spin)
        var sa = Math.sin(spin)
        var tilt = 0.5 + 0.3 * Math.sin(spin * 0.37)
        var cb = Math.cos(tilt)
        var sb = Math.sin(tilt)
        for (var i = 0; i < nodes.length; i++) {
            var n = nodes[i]
            var x = n.x * ca + n.z * sa
            var z = -n.x * sa + n.z * ca
            var y = n.y * cb - z * sb
            z = n.y * sb + z * cb
            var r = radius * (1 + 0.1 * chaos * Math.sin(time * 2 + i * 1.7))
            result.push({ x: radius + x * r, y: radius + y * r, z: z })
        }
        return result
    }
    readonly property var origin: ({ x: radius, y: radius, z: 0 })

    width: radius * 2
    height: width
    visible: strength > 0.01

    Repeater {
        model: net.pairs

        Rectangle {
            id: link

            required property var modelData
            required property int index
            readonly property var a: net.pts[modelData[0]] || net.origin
            readonly property var b: net.pts[modelData[1]] || net.origin
            readonly property real depth: 0.25 + 0.75 * ((a.z + b.z) / 2 + 1) / 2
            // Disparo de la sinapsis: breve, a un ritmo propio de cada enlace.
            readonly property real fire: Math.pow(Math.max(0, Math.sin(
                net.time * (0.8 + 2 * Field.hash(index, 1)) + Field.hash(index, 2) * 6.28)), 6)
                * (0.3 + 0.7 * net.chaos)

            x: a.x
            y: a.y - height / 2
            width: Math.sqrt((b.x - a.x) * (b.x - a.x) + (b.y - a.y) * (b.y - a.y))
            height: 1
            transformOrigin: Item.Left
            rotation: Math.atan2(b.y - a.y, b.x - a.x) * 180 / Math.PI
            color: Theme.mix(net.color, Theme.primaryHot, fire)
            opacity: net.strength * depth * (0.3 + 0.7 * fire)
        }
    }

    Repeater {
        model: net.count

        Rectangle {
            id: node

            required property int index
            readonly property var p: net.pts[index] || net.origin
            readonly property real near: (p.z + 1) / 2

            width: Math.max(2, net.radius * 0.035) * (0.6 + 0.8 * near)
            height: width
            radius: width / 2
            x: p.x - width / 2
            y: p.y - height / 2
            color: Theme.primaryBright
            opacity: net.strength * (0.25 + 0.75 * near)
        }
    }
}
