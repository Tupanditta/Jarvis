// Constelación: mini orbes a la deriva por toda la pantalla, enlaces tenues entre vecinos y
// señales que viajan por los enlaces. Los mini orbes se iluminan cuando la onda del latido
// pasa por ellos.
//
// Los elementos no tienen enlaces de propiedades que dependan del reloj: `refresh` los
// coloca a todos de una pasada en cada fotograma. Solo cambia posiciones, giros, escalas y
// opacidades, así que no se recalcula ninguna forma.
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
                phase: Field.hash(i, 7) * 2 * Math.PI,
                // En reposo solo queda a la vista uno de cada cuatro.
                rest: i % 4 === 0 ? 0.5 : 0,
                twinkleRate: 0.5 + Field.hash(i, 11),
                twinklePhase: Field.hash(i, 12) * 6.28
            })
        }
        return result
    }
    // Enlaces: cada mini orbe con sus dos vecinos más cercanos, y el ritmo de su señal.
    readonly property var pairs: Field.nearest(seeds, 2).map(function (pair, index) {
        return { a: pair[0], b: pair[1], rate: 0.1 + 0.2 * Field.hash(index, 1),
                 offset: Field.hash(index, 2), reverse: index % 2 === 1 }
    })

    // Posición y brillo de cada mini orbe en este fotograma. No avisa de sus cambios.
    readonly property var now: ({ x: [], y: [], shine: [] })

    // Coloca los mini orbes, los enlaces y las señales según los relojes del orbe.
    function refresh() {
        var n = seeds.length
        if (!conductor || motes.count !== n || links.count !== pairs.length)
            return
        var flow = conductor.flow
        var mind = conductor.mind
        var presence = live
        var xs = now.x
        var ys = now.y
        var shines = now.shine
        var i

        for (i = 0; i < n; i++) {
            var s = seeds[i]
            var x = centerX + (s.x + s.reach * Math.sin(flow * s.speedX + s.phase) - centerX) * gather
            var y = centerY + (s.y + s.reach * Math.cos(flow * s.speedY + s.phase * 1.7) - centerY)
                              * gather
            var dx = x - centerX
            var dy = y - centerY
            var shine = conductor.wave(Math.sqrt(dx * dx + dy * dy) / d)
            xs[i] = x
            ys[i] = y
            shines[i] = shine

            var mote = motes.itemAt(i)
            var twinkle = 1 - 0.3 * Math.sin(mind * s.twinkleRate + s.twinklePhase)
            mote.x = x
            mote.y = y
            mote.opacity = Math.min(1, Math.max(s.rest, presence) * (0.3 + 0.5 * s.z) * twinkle
                                       + presence * 0.6 * shine)
            mote.glow = 0.12 + 0.25 * shine
            mote.swell = 1 + 0.6 * shine
            mote.heat = 0.3 + 0.7 * shine
        }

        var reachLimit = d * 1.1
        var signal = presence * (0.25 + 0.75 * conductor.chaos)
        for (i = 0; i < pairs.length; i++) {
            var pair = pairs[i]
            var ax = xs[pair.a]
            var ay = ys[pair.a]
            var bx = xs[pair.b] - ax
            var by = ys[pair.b] - ay
            var span = Math.sqrt(bx * bx + by * by)
            var travel = mind * pair.rate + pair.offset
            travel -= Math.floor(travel)
            if (pair.reverse)
                travel = 1 - travel

            var link = links.itemAt(i)
            link.x = ax
            link.y = ay
            link.rotation = Math.atan2(by, bx) * 180 / Math.PI
            link.span = span
            link.line = presence * Math.max(0, 1 - span / reachLimit)
                        * (0.22 + 0.25 * (shines[pair.a] + shines[pair.b]))
            link.spark = travel * span - 1.5
            link.sparkle = signal * Math.sin(Math.PI * travel)
        }
    }

    onSeedsChanged: Qt.callLater(refresh)
    onGatherChanged: refresh()
    onLiveChanged: refresh()

    Connections {
        target: sky.conductor

        function onClockChanged() {
            sky.refresh()
        }
    }

    // Enlaces y señales.
    Repeater {
        id: links

        model: sky.pairs.length
        onItemAdded: Qt.callLater(sky.refresh)

        Item {
            required property int index
            property alias span: thread.width
            property alias line: thread.opacity
            property alias spark: dot.x
            property alias sparkle: dot.opacity

            transformOrigin: Item.TopLeft
            visible: sky.live > 0.01

            Rectangle {
                id: thread

                height: 1
                color: sky.color
                opacity: 0
            }

            Rectangle {
                id: dot

                width: 3
                height: 3
                radius: 1.5
                y: -1
                color: Theme.primaryBright
                opacity: 0
                visible: parent.index % 3 !== 2
            }
        }
    }

    // Mini orbes.
    Repeater {
        id: motes

        model: sky.count
        onItemAdded: Qt.callLater(sky.refresh)

        Item {
            required property int index
            readonly property real size: {
                var seed = sky.seeds[index]
                return Math.max(3, sky.d * (0.006 + 0.016 * (seed ? seed.z : 0)))
            }
            property alias glow: halo.opacity
            property alias swell: body.scale
            property alias heat: hot.opacity

            opacity: 0

            // Halo.
            Rectangle {
                id: halo

                anchors.centerIn: parent
                width: parent.size * 3.4
                height: width
                radius: width / 2
                color: sky.color
                opacity: 0.12
            }

            // Cuerpo: del color del orbe, más claro al paso de la onda.
            Rectangle {
                id: body

                anchors.centerIn: parent
                width: parent.size
                height: width
                radius: width / 2
                color: sky.color

                Rectangle {
                    id: hot

                    anchors.fill: parent
                    radius: width / 2
                    color: Theme.primaryBright
                    opacity: 0.3
                }
            }
        }
    }
}
