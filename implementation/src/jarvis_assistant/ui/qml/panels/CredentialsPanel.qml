// Panel Credenciales (solo el Acedor): las contraseñas de los perfiles protegidos. Cada una
// está oculta hasta pulsar su ojo, y vuelve a ocultarse al pulsarlo otra vez o al cerrar la
// sesión. Jarvis nunca las dice en voz alta. Una contraseña puesta antes de activar al Acedor
// no se puede ver hasta que su dueño vuelva a entrar con ella.
// Lee el modelo `admin` (`ui/panel_models.py`, AdminModel).
import QtQuick
import ".."
import "../components"

PanelFrame {
    id: panel

    title: "Credenciales"
    summary: admin.credentials.length === 1 ? "1 perfil protegido"
                                             : admin.credentials.length + " perfiles protegidos"

    Item {
        id: head

        width: parent.width
        height: panel.rich ? 30 : 0
        visible: panel.rich

        Text {
            width: parent.width - refresh.width - Theme.space8
            text: "Confidencial: no las deje a la vista"
            color: Theme.statusPending
            font.family: Theme.fontBody
            font.pixelSize: Theme.sizeLabel
            elide: Text.ElideRight
            anchors.verticalCenter: parent.verticalCenter
        }

        IconButton {
            id: refresh

            x: parent.width - width
            icon: "actualizar"
            enabled: assistant.sessionOpen
            anchors.verticalCenter: parent.verticalCenter
            onClicked: admin.showCredentials()
        }
    }

    ListView {
        id: list

        y: head.height + (head.height > 0 ? Theme.space8 : 0)
        width: parent.width
        height: Math.max(0, parent.height - y)
        clip: true
        spacing: Theme.space4
        model: admin.credentials
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        visible: count > 0

        delegate: Rectangle {
            id: entry

            required property var modelData
            property bool revealed: false

            width: ListView.view.width
            height: 48
            radius: Theme.radiusCard
            color: Theme.bgRaised

            Column {
                x: Theme.space12
                width: parent.width - x - eye.width - Theme.space16
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2

                Text {
                    width: parent.width
                    text: entry.modelData.name
                    color: Theme.textPrimary
                    font.family: Theme.fontBody
                    font.pixelSize: Theme.sizeSecondary
                    elide: Text.ElideRight
                }

                Text {
                    objectName: "credential-" + entry.modelData.id
                    width: parent.width
                    text: !entry.modelData.available ? "No disponible hasta que su dueño entre"
                          : entry.revealed ? entry.modelData.password : "••••••••"
                    color: entry.modelData.available ? Theme.textSecondary : Theme.textMuted
                    font.family: Theme.fontMono
                    font.pixelSize: Theme.sizeSecondary
                    elide: Text.ElideRight
                }
            }

            IconButton {
                id: eye

                objectName: "reveal-" + entry.modelData.id
                x: parent.width - width - Theme.space8
                anchors.verticalCenter: parent.verticalCenter
                icon: entry.revealed ? "ocultar" : "llave"
                enabled: entry.modelData.available
                onClicked: entry.revealed = !entry.revealed
            }
        }
    }

    EmptyState {
        y: list.y
        width: parent.width
        height: list.height
        visible: list.count === 0
        text: "Pida «muestra las contraseñas»"
    }
}
