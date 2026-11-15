// Área de trabajo de la pantalla de sesión: las ventanas flotantes de los módulos.
// Una por fila de `workspace` (`ui/workspace.py`). El panel de cada ventana solo se carga
// mientras la ventana está abierta.
import QtQuick
import "components"

Item {
    id: area

    Repeater {
        model: workspace

        FloatingWindow {
            id: win

            required property string component
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
            z: order
            subtitle: loader.item ? loader.item.summary : ""

            onMoved: (left, top) => workspace.move(windowId, left, top)
            onResized: (left, top, wide, tall) => workspace.resize(windowId, left, top, wide, tall)
            onClosed: workspace.close(windowId)
            onActivated: workspace.show(windowId)

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
