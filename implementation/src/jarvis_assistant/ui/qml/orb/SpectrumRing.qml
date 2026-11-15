// Anillo de espectro: barras radiales cuya longitud es `nivel × perfil[i]` (RF-83).
// El perfil es fijo, simétrico y suave, y se desplaza despacio alrededor del anillo.
import QtQuick
import ".."

Item {
    id: ring

    property real diameter: 100
    property real level: 0           // nivel ya suavizado, de 0 a 1
    property real shift: 0           // desplazamiento del perfil, en barras
    property real maxLength: diameter * 0.16
    property int bars: 64
    property color color: Theme.primary

    readonly property var profile: {
        var values = []
        for (var i = 0; i < bars; i++) {
            var wave = Math.pow(Math.abs(Math.sin(i * Math.PI * 4 / bars)), 1.5)
            values.push(0.3 + 0.7 * wave * (0.55 + 0.45 * Math.cos(i * Math.PI * 2 / (bars / 2))))
        }
        return values
    }

    function sample(index) {
        var position = index + shift
        var base = Math.floor(position)
        var rest = position - base
        var a = profile[((base % bars) + bars) % bars]
        var b = profile[(((base + 1) % bars) + bars) % bars]
        return a + (b - a) * rest
    }

    width: diameter
    height: diameter

    Repeater {
        model: ring.bars

        Item {
            id: spoke

            required property int index

            anchors.fill: parent
            rotation: index * 360 / ring.bars

            Rectangle {
                width: Math.max(2, ring.diameter * 0.012)
                height: ring.level > 0.001 ? ring.level * ring.sample(spoke.index) * ring.maxLength : 0
                radius: width / 2
                color: ring.color
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.top
            }
        }
    }
}
