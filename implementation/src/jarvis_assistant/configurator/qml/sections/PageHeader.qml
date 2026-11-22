// Cabecera de un apartado: título, explicación y, a la derecha, su acción principal. Si el
// apartado está bloqueado (su archivo tiene errores), lo explica.
import QtQuick
import "../../../ui/qml"
import "../../../ui/qml/components"
import "../controls"

Column {
    id: header

    property string title: ""
    property string detail: ""
    property string action: ""        // texto del botón; vacío: sin botón
    property string locked: ""

    signal triggered()

    spacing: Theme.space8

    Item {
        width: header.width
        height: Math.max(titleText.implicitHeight, button.implicitHeight)

        DisplayText {
            id: titleText

            text: header.title
            size: Theme.sizeTitle
            color: Theme.textPrimary
            anchors.verticalCenter: parent.verticalCenter
        }

        TextButton {
            id: button

            objectName: "headerAction"
            anchors.right: parent.right
            visible: header.action.length > 0
            enabled: header.locked.length === 0
            text: "+  " + header.action
            onClicked: header.triggered()
        }
    }

    Text {
        width: header.width
        text: header.detail
        visible: text.length > 0
        color: Theme.textSecondary
        font.family: Theme.fontBody
        font.pixelSize: Theme.sizeSecondary
        wrapMode: Text.WordWrap
    }

    Notice {
        width: header.width
        text: header.locked
        kind: "error"
    }
}
