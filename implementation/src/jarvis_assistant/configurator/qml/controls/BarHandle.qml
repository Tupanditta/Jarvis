// Capa sobre una barra del editor de plantillas: recoge todos los clics (la barra no responde)
// y la arrastra. `dragged(dx, dy)`: desplazamiento desde el último movimiento, en píxeles.
// `released(startX, startY)`: al soltar, con la posición que tenía al empezar (`startX`,
// `startY`, en fracciones), para volver a ella si el sitio no vale.
import QtQuick
import "../../../ui/qml"

MouseArea {
    id: handle

    property string hint: ""
    property real startX: 0
    property real startY: 0
    property real fromX: 0
    property real fromY: 0
    property point last

    signal dragged(real dx, real dy)
    signal released(real startX, real startY)

    hoverEnabled: true
    cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
    preventStealing: true

    onPressed: (mouse) => {
        fromX = startX
        fromY = startY
        last = mapToItem(null, mouse.x, mouse.y)
    }
    onPositionChanged: (mouse) => {
        if (!pressed)
            return
        var point = mapToItem(null, mouse.x, mouse.y)
        handle.dragged(point.x - last.x, point.y - last.y)
        last = point
    }
    onReleased: handle.released(fromX, fromY)

    // Marco que señala que la barra se puede mover.
    Rectangle {
        anchors.fill: parent
        anchors.margins: -3
        radius: height / 2
        color: "transparent"
        border.width: 1
        border.color: Theme.alpha(Theme.primary, handle.containsMouse || handle.pressed ? 0.8 : 0.3)
    }

    Text {
        anchors.top: parent.bottom
        anchors.topMargin: Theme.space8
        anchors.horizontalCenter: parent.horizontalCenter
        visible: handle.containsMouse && !handle.pressed
        text: handle.hint
        color: Theme.textSecondary
        font.family: Theme.fontBody
        font.pixelSize: Theme.sizeLabel
    }
}
