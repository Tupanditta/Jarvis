// Barra de herramientas de un panel: una fila de botones de icono y, a la derecha, el nombre
// del botón bajo el cursor.
//
// `actions` es una lista de objetos `{ icon, hint, enabled, run }`: `run` es la función que
// ejecuta el botón y `enabled`, opcional, lo desactiva cuando es `false`.
import QtQuick
import ".."

Item {
    id: bar

    property var actions: []
    property string hint: ""

    implicitHeight: 28
    height: implicitHeight

    Row {
        id: row

        spacing: 2

        Repeater {
            model: bar.actions.length

            IconButton {
                required property int index
                readonly property var action: bar.actions[index]

                icon: action.icon
                enabled: action.enabled !== false
                onClicked: action.run()
                onHoveredChanged: {
                    if (hovered)
                        bar.hint = action.hint
                    else if (bar.hint === action.hint)
                        bar.hint = ""
                }
            }
        }
    }

    Text {
        x: row.width + Theme.space8
        width: Math.max(0, parent.width - x)
        text: bar.hint
        color: Theme.textMuted
        font.family: Theme.fontBody
        font.pixelSize: Theme.sizeLabel
        horizontalAlignment: Text.AlignRight
        elide: Text.ElideRight
        anchors.verticalCenter: parent.verticalCenter
    }
}
