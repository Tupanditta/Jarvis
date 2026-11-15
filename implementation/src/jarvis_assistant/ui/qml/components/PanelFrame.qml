// Marco de un panel: título, borde y, en el panel activo, cuatro esquinas marcadas.
import QtQuick
import ".."

Rectangle {
    id: frame

    property string title: ""
    property bool active: false
    property bool flat: false            // dentro del HUD: sin fondo ni borde propios
    default property alias content: body.data
    readonly property real headerHeight: header.y + header.height + Theme.space8

    color: flat ? "transparent" : Theme.bgPanel
    radius: Theme.radiusPanel
    border.width: flat ? 0 : 1
    border.color: active ? Theme.lineStrong : Theme.lineSoft

    DisplayText {
        id: header

        x: Theme.space16
        y: frame.flat ? 0 : Theme.space12
        width: parent.width - 2 * Theme.space16
        text: frame.title
        size: Theme.sizeSecondary
    }

    Item {
        id: body

        anchors.fill: parent
        anchors.topMargin: frame.headerHeight
        anchors.leftMargin: Theme.space16
        anchors.rightMargin: Theme.space16
        anchors.bottomMargin: frame.flat ? 0 : Theme.space12
        clip: true
    }

    // Esquinas en `primary`, trazos de 12 px: el único guiño «HUD» de los paneles.
    Repeater {
        model: frame.active && !frame.flat ? 4 : 0

        Item {
            id: corner

            required property int index
            readonly property bool atRight: index % 2 === 1
            readonly property bool atBottom: index >= 2

            x: atRight ? frame.width - Theme.cornerMark : 0
            y: atBottom ? frame.height - Theme.cornerMark : 0
            width: Theme.cornerMark
            height: Theme.cornerMark

            Rectangle {
                width: parent.width
                height: 1
                y: corner.atBottom ? parent.height - 1 : 0
                color: Theme.primary
            }

            Rectangle {
                width: 1
                height: parent.height
                x: corner.atRight ? parent.width - 1 : 0
                color: Theme.primary
            }
        }
    }
}
