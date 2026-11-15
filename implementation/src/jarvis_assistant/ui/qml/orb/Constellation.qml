// Constelación: mini orbes a la deriva por toda la pantalla, enlaces tenues entre vecinos y
// señales que viajan por los enlaces. Los mini orbes se iluminan cuando la onda del latido
// pasa por ellos.
import QtQuick
import ".."
import "field.js" as Field

Item {
    id: sky

    property Item conductor          // el orbe
    property real centerX: width / 2
    property real centerY: height / 2
    property real d: 100             // D del orbe
    property int count: 45
    property real gather: 1          // 0: recogidos en el núcleo; 1: en su sitio

    readonly property real flow: conductor ? conductor.flow : 0
    readonly property real mind: conductor ? conductor.mind : 0
    readonly property real chaos: conductor ? conductor.chaos : 0
    readonly property real live: conductor ? conductor.live : 0
    readonly property color color: conductor ? conductor.main : Theme.primary

    // Sitio de cada mini orbe y forma de su deriva. Ninguno queda dentro del orbe.
    readonly property var seeds: {
        var result = []
        var keepOut = d * 0.8
        for (var i = 0; i < count; i++) {
            var x = Field.hash(i, 1) * width
            var y = Field.hash(i, 2) * height
            var dx = x - centerX
            var dy = y - centerY
            var distance = Math.sqrt(dx * dx + dy * dy)
            if (distance < keepOut) {
                var angle = distance > 1 ? Math.atan2(dy, dx) : Field.hash(i, 9) * 2 * Math.PI
                var out = keepOut + Field.hash(i, 8) * d * 0.4
                x = centerX + Math.cos(angle) * out
                y = centerY + Math.sin(angle) * out
            }
            result.push({
                x: x, y: y, z: Field.hash(i, 3),
                reach: (0.03 + 0.06 * Field.hash(i, 4)) * Math.min(width, height),
                speedX: 0.25 + 0.5 * Field.hash(i, 5),
                speedY: 0.25 + 0.5 * Field.hash(i, 6),
                phase: Field.hash(i, 7) * 2 * Math.PI
            })
        }
        return result
    }
    readonly property var pairs: Field.nearest(seeds, 2)

    // Posición actual de cada mini orbe; `r` es su distancia al centro en unidades de D.
    readonly property var pts: {
        var result = []
        for (var i = 0; i < seeds.length; i++) {
            var s = seeds[i]
            var x = s.x + s.reach * Math.sin(flow * s.speedX + s.phase)
            var y = s.y + s.reach * Math.cos(flow * s.speedY + s.phase * 1.7)
            x = centerX + (x - centerX) * gather
            y = centerY + (y - centerY) * gather
            var dx = x - centerX
            var dy = y - centerY
            result.push({ x: x, y: y, z: s.z, r: Math.sqrt(dx * dx + dy * dy) / d })
        }
        return result
    }
    readonly property var origin: ({ x: centerX, y: centerY, z: 0, r: 0 })

    // Enlaces y señales.
    Repeater {
        model: sky.pairs

        Item {
            id: link

            required property var modelData
            required property int index
            readonly property var a: sky.pts[modelData[0]] || sky.origin
            readonly property var b: sky.pts[modelData[1]] || sky.origin
            readonly property real nearness: Math.max(0, 1 - width / (sky.d * 1.1))
            readonly property real shine: sky.conductor ? sky.conductor.wave((a.r + b.r) / 2) : 0
            // Avance de la señal por el enlace; la mitad viaja en sentido contrario.
            readonly property real travel: {
                var t = sky.mind * (0.1 + 0.2 * Field.hash(index, 1)) + Field.hash(index, 2)
                t -= Math.floor(t)
                return index % 2 ? 1 - t : t
            }

            x: a.x
            y: a.y
            width: Math.sqrt((b.x - a.x) * (b.x - a.x) + (b.y - a.y) * (b.y - a.y))
            height: 1
            transformOrigin: Item.Left
            rotation: Math.atan2(b.y - a.y, b.x - a.x) * 180 / Math.PI
            visible: sky.live > 0.01

            Rectangle {
                width: parent.width
                height: 1
                color: sky.color
                opacity: sky.live * link.nearness * (0.22 + 0.5 * link.shine)
            }

            Rectangle {
                width: 3
                height: 3
                radius: 1.5
                x: link.travel * link.width - 1.5
                y: -1
                color: Theme.primaryBright
                opacity: sky.live * (0.25 + 0.75 * sky.chaos) * Math.sin(Math.PI * link.travel)
                visible: link.index % 3 !== 2
            }
        }
    }

    // Mini orbes.
    Repeater {
        model: sky.count

        Item {
            id: mote

            required property int index
            readonly property var p: sky.pts[index] || sky.origin
            readonly property real size: Math.max(3, sky.d * (0.006 + 0.016 * p.z))
            readonly property real shine: sky.conductor ? sky.conductor.wave(p.r) : 0
            readonly property real twinkle: 1 - 0.3 * Math.sin(
                sky.mind * (0.5 + Field.hash(index, 11)) + Field.hash(index, 12) * 6.28)
            // En reposo solo queda a la vista uno de cada cuatro.
            readonly property real presence: index % 4 === 0 ? Math.max(0.5, sky.live) : sky.live

            x: p.x
            y: p.y
            opacity: Math.min(1, presence * (0.3 + 0.5 * p.z) * twinkle + sky.live * 0.6 * shine)
            visible: opacity > 0.01

            // Halo.
            Rectangle {
                anchors.centerIn: parent
                width: mote.size * 3.4
                height: width
                radius: width / 2
                color: Theme.alpha(sky.color, 0.12 + 0.25 * mote.shine)
            }

            Rectangle {
                anchors.centerIn: parent
                width: mote.size * (1 + 0.6 * mote.shine)
                height: width
                radius: width / 2
                color: Theme.mix(sky.color, Theme.primaryBright, 0.3 + 0.7 * mote.shine)
            }
        }
    }
}
