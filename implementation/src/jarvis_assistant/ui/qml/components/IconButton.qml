// Botón de icono de 28 px con realce al pasar el cursor.
// Solo para «traer al frente», silencio, expandir y ocultar (hud.md, sección 3).
import QtQuick
import ".."

Rectangle {
    id: button

    property string icon: "expandir"
    signal clicked()

    width: 28
    height: 28
    radius: Theme.radiusCard
    color: hover.hovered ? Theme.bgRaised : "transparent"

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
