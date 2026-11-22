// Lectura del centro de un medidor: la cifra grande en `fontTech` con su unidad pequeña al
// lado y, debajo, la etiqueta. Con menos de 10, un decimal.
import QtQuick
import ".."

Column {
    id: readout

    property real value: 0
    property string unit: "%"
    property string label: ""
    property real size: 30               // altura de la cifra, en píxeles
    property color color: Theme.neonCyan

    spacing: 0

    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 1

        Text {
            id: figure

            objectName: "neon-value"
            text: readout.value < 10 ? readout.value.toFixed(1) : Math.round(readout.value)
            color: Theme.primaryHot
            font.family: Theme.fontTech
            font.weight: Font.Bold
            font.pixelSize: readout.size
            style: Text.Outline
            styleColor: Theme.alpha(readout.color, 0.35)
        }

        Text {
            text: readout.unit
            color: Theme.primaryHot
            font.family: Theme.fontTech
            font.weight: Font.Medium
            font.pixelSize: Math.round(readout.size * 0.45)
            anchors.baseline: figure.baseline
        }
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        text: readout.label
        color: Theme.textPrimary
        font.family: Theme.fontTech
        font.weight: Font.Medium
        font.pixelSize: Math.round(readout.size * 0.42)
        font.letterSpacing: readout.size * 0.06
    }
}
