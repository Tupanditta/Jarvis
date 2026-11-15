// Distintivo pequeño: «actual», «importante», «vencido», «limitada», «no reconocido».
import QtQuick
import ".."

Rectangle {
    id: badge

    property string text: ""
    property color tone: Theme.textMuted

    implicitWidth: label.implicitWidth + 2 * Theme.space8
    implicitHeight: label.implicitHeight + Theme.space4
    width: implicitWidth
    height: implicitHeight
    radius: Theme.radiusCard
    color: "transparent"
    border.width: 1
    border.color: tone

    Text {
        id: label

        anchors.centerIn: parent
        text: badge.text
        color: badge.tone
        font.family: Theme.fontBody
        font.pixelSize: Theme.sizeLabel
    }
}
