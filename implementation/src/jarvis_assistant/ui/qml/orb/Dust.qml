// Polvo: puntos diminutos que cruzan la pantalla muy despacio. Dan profundidad.
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

    Repeater {
        model: dust.count

        Rectangle {
            id: mote

            required property int index
            readonly property real depth: Field.hash(index, 3)
            // Los cercanos se mueven más deprisa que los lejanos.
            readonly property real px: Field.hash(index, 1) * dust.width
                                       + dust.flow * (6 + 22 * depth)
            readonly property real py: Field.hash(index, 2) * dust.height
                                       - dust.flow * (3 + 10 * depth)

            width: 1 + 1.5 * depth
            height: width
            radius: width / 2
            x: dust.width > 0 ? px % dust.width : 0
            y: dust.height > 0 ? ((py % dust.height) + dust.height) % dust.height : 0
            color: dust.color
            // En reposo queda una parte, quieta y muy tenue.
            opacity: dust.fade * (0.15 + 0.35 * depth) * (index % 3 === 0 ? Math.max(0.6, dust.live)
                                                                          : dust.live)
        }
    }
}
