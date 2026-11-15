// Texto en `font.display`: mayúsculas con espaciado del 8 %.
import QtQuick
import ".."

Text {
    property int size: Theme.sizeSecondary

    color: Theme.textSecondary
    font.family: Theme.fontDisplay
    font.weight: Font.DemiBold
    font.pixelSize: size
    font.capitalization: Font.AllUppercase
    font.letterSpacing: size * Theme.displaySpacing
    elide: Text.ElideRight
}
