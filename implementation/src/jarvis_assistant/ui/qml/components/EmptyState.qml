// Texto atenuado centrado cuando un panel no tiene contenido.
import QtQuick
import ".."

Text {
    color: Theme.textMuted
    font.family: Theme.fontBody
    font.pixelSize: Theme.sizeSecondary
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
    elide: Text.ElideRight
}
