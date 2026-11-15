// Marco de un panel: título, borde y, en el panel activo, cuatro esquinas marcadas.
// Dentro de una ventana flotante (`embedded`) no dibuja marco ni título: los pone la ventana.
// Dentro del HUD (`flat`) el panel es compacto: solo muestra el contenido, sin controles.
import QtQuick
import ".."

Rectangle {
    id: frame

    property string title: ""
    property bool active: false
    property bool flat: false            // dentro del HUD: sin fondo ni borde propios
    property bool embedded: false        // dentro de una ventana flotante
    property string summary: ""          // una línea de estado para la cabecera de la ventana
    default property alias content: body.data
    readonly property bool bare: flat || embedded
    readonly property bool rich: !flat   // con barra de herramientas, filtros y campos
    readonly property real headerHeight: embedded ? 0
                                                  : header.y + header.height + Theme.space8

    color: bare ? "transparent" : Theme.bgPanel
    radius: Theme.radiusPanel
    border.width: bare ? 0 : 1
    border.color: active ? Theme.lineStrong : Theme.lineSoft

    DisplayText {
        id: header

        x: Theme.space16
        y: frame.flat ? 0 : Theme.space12
        width: parent.width - 2 * Theme.space16
        visible: !frame.embedded
        text: frame.title
        size: Theme.sizeSecondary
    }

    Item {
        id: body

        anchors.fill: parent
        anchors.topMargin: frame.headerHeight
        anchors.leftMargin: frame.embedded ? 0 : Theme.space16
        anchors.rightMargin: frame.embedded ? 0 : Theme.space16
        anchors.bottomMargin: frame.bare ? 0 : Theme.space12
        clip: true
    }

    // Esquinas en `primary`, trazos de 12 px: el único guiño «HUD» de los paneles.
    Repeater {
        model: frame.active && !frame.bare ? 4 : 0

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
