// Selector de perfiles de la pantalla dormida, en el centro, bajo el orbe: un botón por
// perfil, el elegido resaltado. Se cambia con el ratón o con ←/→ en la caja vacía. La sesión
// se abre con el perfil elegido (`ui/profiles.py`). Con un solo perfil no se muestra.
import QtQuick
import ".."

Column {
    id: picker

    property bool shown: false

    spacing: Theme.space12
    visible: opacity > 0
    opacity: shown && profiles.count > 1 ? 1 : 0

    Behavior on opacity {
        NumberAnimation { duration: Theme.motionPanel }
    }

    DisplayText {
        anchors.horizontalCenter: parent.horizontalCenter
        text: "Perfil"
        size: Theme.sizeLabel
        color: Theme.textMuted
    }

    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: Theme.space12

        Repeater {
            model: profiles

            Rectangle {
                id: option

                required property int index
                required property string name
                required property bool selected

                objectName: "profile-" + index
                width: label.implicitWidth + 2 * Theme.space24
                height: 40
                radius: height / 2
                color: selected ? Theme.bgSelected : hover.hovered ? Theme.bgHover : Theme.bgPanel
                border.width: 1
                border.color: selected ? Theme.primary : Theme.lineSoft

                Behavior on border.color {
                    ColorAnimation { duration: Theme.motionWindow }
                }

                Text {
                    id: label

                    anchors.centerIn: parent
                    text: option.name
                    color: option.selected ? Theme.textPrimary : Theme.textSecondary
                    font.family: Theme.fontBody
                    font.pixelSize: Theme.sizeText
                }

                HoverHandler {
                    id: hover
                    cursorShape: Qt.PointingHandCursor
                }

                TapHandler {
                    onTapped: profiles.select(option.index)
                }
            }
        }
    }
}
