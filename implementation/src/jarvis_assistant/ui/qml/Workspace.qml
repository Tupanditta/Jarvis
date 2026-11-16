// Área de trabajo de la pantalla de sesión: las ventanas flotantes de los módulos.
// Una por fila de `workspace` (`ui/workspace.py`). El panel de cada ventana solo se carga
// mientras la ventana está abierta.
//
// Al abrir sesión (`hold`, luego `release`) las ventanas esperan ocultas a que termine el
// despertar del orbe y salen de él una a una, de la de abajo a la de arriba. Las que se abren
// mientras tanto se suman a la cola.
//
// Cada ventana que aparece suena con un aviso corto. Si aparecen varias a la vez (sin
// animaciones), suena una sola vez.
import QtQuick
import QtMultimedia
import "components"

Item {
    id: area

    property Item conductor              // el orbe: su latido enciende el borde de las ventanas
    property real centerX: width / 2     // centro del orbe, en coordenadas de esta área
    property real centerY: height / 2
    property bool staging: false         // abriendo sesión: las ventanas esperan al orbe

    // Empieza el despertar: ninguna ventana se ve hasta `release`.
    function hold() {
        launches.stop()
        if (ui.reduceMotion) {
            staging = false
            return
        }
        staging = true
        for (var i = 0; i < stack.count; ++i)
            stack.itemAt(i).held = true
    }

    // El orbe ya ha despertado: lanza las ventanas abiertas, una a una.
    function release() {
        if (!staging)
            return
        launchNext()
        launches.start()
    }

    // Deja de esperar sin animación: otra transición ha cortado el despertar.
    function cancel() {
        launches.stop()
        staging = false
        for (var i = 0; i < stack.count; ++i)
            stack.itemAt(i).held = false
    }

    // Lanza la ventana abierta que queda más abajo; si no queda ninguna, termina.
    function launchNext() {
        var next = null
        for (var i = 0; i < stack.count; ++i) {
            var win = stack.itemAt(i)
            if (win.held && win.open && (next === null || win.order < next.order))
                next = win
        }
        if (next !== null) {
            next.emerge()
            return
        }
        cancel()
    }

    SoundEffect {
        id: chime

        property double lastPlayed: 0

        source: Qt.resolvedUrl("../assets/sounds/window_open.wav")
        volume: 0.6

        function ring() {
            var now = Date.now()
            if (now - lastPlayed < 120)
                return
            lastPlayed = now
            play()
        }
    }

    Timer {
        id: launches

        interval: Theme.motionEmergeGap
        repeat: true
        onTriggered: area.launchNext()
    }

    Repeater {
        id: stack

        model: workspace

        FloatingWindow {
            id: win

            required property string component
            required property string style
            required property int order
            required windowId
            required title
            required icon
            required open
            required focused
            required fx
            required fy
            required fw
            required fh
            required minWidth
            required minHeight

            areaWidth: area.width
            areaHeight: area.height
            originX: area.centerX
            originY: area.centerY
            frameStyle: style
            beat: {
                if (!area.conductor || !open)
                    return 0
                var dx = x + width / 2 - area.centerX
                var dy = y + height / 2 - area.centerY
                return area.conductor.wave(Math.sqrt(dx * dx + dy * dy) / area.conductor.d)
            }
            z: order
            subtitle: loader.item ? loader.item.summary : ""

            onMoved: (left, top) => workspace.move(windowId, left, top)
            onResized: (left, top, wide, tall) => workspace.resize(windowId, left, top, wide, tall)
            onClosed: workspace.close(windowId)
            onActivated: workspace.show(windowId)
            onAppeared: chime.ring()

            Loader {
                id: loader

                anchors.fill: parent
                active: win.open
                source: Qt.resolvedUrl("panels/" + win.component)
                onLoaded: {
                    item.embedded = true
                    item.active = Qt.binding(() => win.focused)
                }
            }
        }
    }
}
