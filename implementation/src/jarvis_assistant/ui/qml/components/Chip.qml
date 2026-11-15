// Píldora seleccionable: filtros de una lista y accesos rápidos. `count` < 0 no se muestra.
import QtQuick
import ".."

Rectangle {
    id: chip

    property string text: ""
    property string icon: ""
    property int count: -1
    property bool selected: false
    property color tone: Theme.primary

    signal clicked()

    implicitWidth: content.implicitWidth + 2 * Theme.space8
    implicitHeight: 24
    width: implicitWidth
    height: implicitHeight
    radius: height / 2
    color: selected ? Theme.bgSelected : hover.hovered ? Theme.bgHover : "transparent"
    border.width: 1
    border.color: selected ? Theme.alpha(tone, 0.7) : Theme.lineSoft

    Row {
        id: content

        anchors.centerIn: parent
        spacing: Theme.space4

        Image {
            width: 12
            height: 12
            sourceSize.width: 24
            sourceSize.height: 24
            visible: chip.icon.length > 0
            source: chip.icon.length > 0 ? Theme.icon(chip.icon) : ""
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            text: chip.text
            color: chip.selected ? Theme.textPrimary : Theme.textSecondary
            font.family: Theme.fontBody
            font.pixelSize: Theme.sizeLabel
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            visible: chip.count >= 0
            text: chip.count
            color: chip.selected ? chip.tone : Theme.textMuted
            font.family: Theme.fontMono
            font.pixelSize: Theme.sizeLabel
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    HoverHandler {
        id: hover
        cursorShape: Qt.PointingHandCursor
    }

    TapHandler {
        onTapped: chip.clicked()
    }
}
