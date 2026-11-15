// Fila con un número grande en `primary`: el número es lo que el usuario escribe en la orden.
import QtQuick
import ".."

Item {
    id: row

    property int number: 0
    property string title: ""
    property string subtitle: ""
    property string icon: ""

    implicitHeight: 44

    Text {
        id: index

        width: 28
        anchors.verticalCenter: parent.verticalCenter
        text: row.number
        color: Theme.primary
        font.family: Theme.fontMono
        font.pixelSize: Theme.sizeTitle
        horizontalAlignment: Text.AlignRight
    }

    Image {
        id: glyph

        x: index.width + Theme.space8
        width: 16
        height: 16
        sourceSize.width: 32
        sourceSize.height: 32
        visible: row.icon.length > 0
        source: row.icon.length > 0 ? Theme.icon(row.icon) : ""
        anchors.verticalCenter: parent.verticalCenter
    }

    Column {
        x: glyph.x + (glyph.visible ? glyph.width + Theme.space8 : 0)
        width: parent.width - x
        anchors.verticalCenter: parent.verticalCenter

        Text {
            width: parent.width
            text: row.title
            color: Theme.textPrimary
            font.family: Theme.fontBody
            font.pixelSize: Theme.sizeText
            elide: Text.ElideRight
        }

        Text {
            width: parent.width
            visible: row.subtitle.length > 0
            text: row.subtitle
            color: Theme.textMuted
            font.family: Theme.fontBody
            font.pixelSize: Theme.sizeSecondary
            elide: Text.ElideMiddle
        }
    }
}
