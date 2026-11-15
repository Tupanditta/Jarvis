// Glifos: fragmentos de código que aparecen y se desvanecen alrededor de los anillos, cada
// vez en un sitio distinto. Son decorativos. Con más caos se ven más.
import QtQuick
import ".."
import "field.js" as Field

Item {
    id: glyphs

    property real d: 100             // D del orbe
    property int count: 10
    property color color: Theme.primary
    property real time: 0            // reloj del pensamiento (`mind` del orbe)
    property real chaos: 0
    property real strength: 0        // 0–1: visibilidad del conjunto

    readonly property var words: ["0x3F", "sync()", "λ", "if (ready)", "0b1011", "await io",
                                  "Δt", "ack", "0xA7", "parse", "node[7]", "2048", "route",
                                  "0x1C", "emit", "64"]

    width: d * 1.4
    height: width
    visible: strength > 0.01

    Repeater {
        model: glyphs.count

        Text {
            id: glyph

            required property int index
            readonly property real t: glyphs.time * (0.18 + 0.22 * Field.hash(index, 1))
                                      + Field.hash(index, 2)
            readonly property int cycle: Math.floor(t)
            readonly property real life: t - cycle
            readonly property real angle: Field.hash(index + cycle * 7, 3) * 2 * Math.PI
            readonly property real distance: glyphs.d * (0.47 + 0.2 * Field.hash(index + cycle * 3, 4))

            text: glyphs.words[(index * 5 + cycle * 3) % glyphs.words.length]
            color: glyphs.color
            font.family: Theme.fontMono
            font.pixelSize: Math.max(8, Math.round(glyphs.d * 0.026))
            x: glyphs.width / 2 + Math.cos(angle) * distance - width / 2
            y: glyphs.height / 2 + Math.sin(angle) * distance - height / 2
            opacity: glyphs.strength * (0.25 + 0.75 * glyphs.chaos) * 0.85
                     * Math.pow(Math.sin(Math.PI * life), 2)
        }
    }
}
