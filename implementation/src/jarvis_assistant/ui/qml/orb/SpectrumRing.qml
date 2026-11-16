// Anillo de espectro: barras radiales cuya longitud es `nivel × perfil[i]` (RF-83).
// El perfil es fijo, simétrico y suave, y se desplaza despacio alrededor del anillo.
//
// `refresh` ajusta todas las barras de una pasada; con nivel 0 no hace nada.
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

    function refresh() {
        if (spokes.count !== bars)
            return
        var on = level > 0.001
        if (!on && !lit)
            return
        var reach = on ? level * maxLength : 0
        for (var i = 0; i < bars; i++)
            spokes.itemAt(i).reach = on ? reach * sample(i) : 0
        lit = on
    }

    property bool lit: false         // hay barras a la vista

    width: diameter
    height: diameter

    onLevelChanged: refresh()
    onShiftChanged: refresh()
    onMaxLengthChanged: refresh()

    Repeater {
        id: spokes

        model: ring.bars

        Item {
            required property int index
            property alias reach: bar.height

            anchors.fill: parent
            rotation: index * 360 / ring.bars

            Rectangle {
                id: bar

                width: Math.max(2, ring.diameter * 0.012)
                height: 0
                antialiasing: true
                color: ring.color
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.top
            }
        }
    }
}
