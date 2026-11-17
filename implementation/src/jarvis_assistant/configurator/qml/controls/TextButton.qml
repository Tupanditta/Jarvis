// Botón de texto de la ventana de configuración. `primary`: la acción principal (Guardar,
// Aceptar). `danger`: una acción que borra. Desactivado se ve atenuado.
import QtQuick
import "../../../ui/qml"

Rectangle {
    id: button

    property string text: ""
    property string icon: ""
    property bool primary: false
    property bool danger: false
    readonly property color tone: danger ? Theme.statusError : Theme.primary

    signal clicked()

    implicitWidth: row.implicitWidth + 2 * Theme.space16
    implicitHeight: 32
    radius: Theme.radiusCard
    opacity: enabled ? 1 : 0.4
    color: primary ? (hover.hovered && enabled ? Theme.alpha(tone, 0.30) : Theme.alpha(tone, 0.20))
                   : (hover.hovered && enabled ? Theme.bgHover : "transparent")
    border.width: 1
    border.color: primary || hover.hovered ? Theme.alpha(tone, 0.7) : Theme.lineStrong

    Row {
        id: row

        anchors.centerIn: parent
        spacing: Theme.space8

        Image {
            width: 14
            height: 14
            sourceSize.width: 28
            sourceSize.height: 28
            visible: button.icon.length > 0
            source: button.icon.length > 0 ? Theme.icon(button.icon) : ""
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            text: button.text
            color: button.danger ? Theme.statusError : Theme.textPrimary
            font.family: Theme.fontBody
            font.pixelSize: Theme.sizeSecondary
            font.weight: button.primary ? Font.Medium : Font.Normal
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    HoverHandler {
        id: hover
        cursorShape: Qt.PointingHandCursor
    }

    TapHandler {
        enabled: button.enabled
        onTapped: button.clicked()
    }
}
