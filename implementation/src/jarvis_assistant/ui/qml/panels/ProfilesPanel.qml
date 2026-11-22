// Panel Perfiles (solo el Acedor): los perfiles que puede eliminar. «Eliminar» pide la
// confirmación de siempre (una pregunta del asistente) antes de quitarlo y retirar sus datos.
// Lee el modelo `admin` (`ui/panel_models.py`, AdminModel).
import QtQuick
import ".."
import "../components"

PanelFrame {
    id: panel

    title: "Perfiles"
    summary: admin.profiles.length === 1 ? "1 perfil" : admin.profiles.length + " perfiles"

    ListView {
        id: list

        width: parent.width
        height: parent.height
        clip: true
        spacing: Theme.space4
        model: admin.profiles
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        visible: count > 0

        delegate: Rectangle {
            id: entry

            required property var modelData

            width: ListView.view.width
            height: 40
            radius: Theme.radiusCard
            color: Theme.bgRaised

            Text {
                x: Theme.space12
                width: parent.width - x - remove.width - Theme.space16
                anchors.verticalCenter: parent.verticalCenter
                text: entry.modelData.name
                color: Theme.textPrimary
                font.family: Theme.fontBody
                font.pixelSize: Theme.sizeSecondary
                elide: Text.ElideRight
            }

            Chip {
                id: remove

                objectName: "removeProfile-" + entry.modelData.id
                x: parent.width - width - Theme.space8
                anchors.verticalCenter: parent.verticalCenter
                text: "Eliminar"
                tone: Theme.statusError
                enabled: assistant.sessionOpen && admin.profiles.length > 1
                opacity: enabled ? 1 : 0.4
                onClicked: admin.removeProfile(entry.modelData.id)
            }
        }
    }

    EmptyState {
        anchors.fill: parent
        visible: list.count === 0
        text: "Sin perfiles"
    }
}
