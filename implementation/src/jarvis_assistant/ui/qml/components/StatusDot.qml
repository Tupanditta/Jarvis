// Punto de 8 px con el color del estado. En `pendiente` late, con resplandor.
import QtQuick
import ".."

Item {
    id: dot

    property string status: "completado"
    property color color: Theme.statusColor(status)
    readonly property bool pending: status === "pendiente"

    width: 8
    height: 8

    // Resplandor: solo en una tarea pendiente.
    Rectangle {
        anchors.centerIn: parent
        width: 16
        height: 16
        radius: 8
        color: Theme.alpha(dot.color, 0.25)
        visible: dot.pending
        opacity: core.opacity
    }

    Rectangle {
        id: core

        anchors.fill: parent
        radius: width / 2
        color: dot.color

        SequentialAnimation on opacity {
            running: dot.pending && dot.visible
            loops: Animation.Infinite
            alwaysRunToEnd: true
            NumberAnimation { to: 0.4; duration: 600 }
            NumberAnimation { to: 1; duration: 600 }
        }
    }
}
