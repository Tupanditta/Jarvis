// Polvo: puntos diminutos que cruzan la pantalla muy despacio. Dan profundidad.
//
// `refresh` mueve todos los puntos de una pasada cuando avanza el reloj del orbe: ningún
// punto tiene enlaces de propiedades que se evalúen en cada fotograma.
import QtQuick
import ".."
import "field.js" as Field

Item {
    id: dust

    property Item conductor          // el orbe
    property int count: 70
    property real fade: 1            // 0–1: visibilidad al formarse y al colapsar

    readonly property real flow: conductor ? conductor.flow : 0
    readonly property real live: conductor ? conductor.live : 0
    readonly property color color: conductor ? conductor.main : Theme.primary

    // Sitio de partida y velocidad de cada punto. Los cercanos se mueven más deprisa.
    readonly property var seeds: {
        var result = []
        for (var i = 0; i < count; i++) {
            var depth = Field.hash(i, 3)
            result.push({ x: Field.hash(i, 1), y: Field.hash(i, 2),
                          speedX: 6 + 22 * depth, speedY: 3 + 10 * depth })
        }
        return result
    }

    function refresh() {
        if (motes.count !== seeds.length || width <= 0 || height <= 0)
            return
        for (var i = 0; i < seeds.length; i++) {
            var s = seeds[i]
            var y = (s.y * height - flow * s.speedY) % height
            var mote = motes.itemAt(i)
            mote.x = (s.x * width + flow * s.speedX) % width
            mote.y = y < 0 ? y + height : y
        }
    }

    onFlowChanged: refresh()
    onWidthChanged: refresh()
    onHeightChanged: refresh()

    Repeater {
        id: motes

        model: dust.count
        onItemAdded: Qt.callLater(dust.refresh)

        Rectangle {
            required property int index
            readonly property real depth: Field.hash(index, 3)

            width: 1 + 1.5 * depth
            height: width
            radius: width / 2
            color: dust.color
            // En reposo queda una parte, quieta y muy tenue.
            opacity: dust.fade * (0.15 + 0.35 * depth) * (index % 3 === 0 ? Math.max(0.6, dust.live)
                                                                          : dust.live)
        }
    }
}
