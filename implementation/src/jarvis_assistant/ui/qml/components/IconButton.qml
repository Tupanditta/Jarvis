// Botón de icono de 28 px con realce al pasar el cursor. Desactivado se ve atenuado.
import QtQuick
import ".."

Rectangle {
    id: button

    property string icon: "expandir"
    readonly property alias hovered: hover.hovered
    signal clicked()

    width: 28
    height: 28
    radius: Theme.radiusCard
    color: hover.hovered && enabled ? Theme.bgRaised : "transparent"
    opacity: enabled ? 1 : 0.35

    Image {
        anchors.centerIn: parent
        width: 18
        height: 18
        sourceSize.width: 36
        sourceSize.height: 36
        source: Theme.icon(button.icon)
    }

    HoverHandler {
        id: hover
        cursorShape: Qt.PointingHandCursor
    }

    TapHandler {
        onTapped: button.clicked()
    }
}
