// Panel de historial: la tabla de sesiones (identificador, nombre, fecha, importancia) o las
// actividades de una sesión (hud.md, sección 3).
import QtQuick
import ".."
import "../components"

PanelFrame {
    id: panel

    readonly property bool showsActivities: history.mode === "activities"

    title: "Historial"

    Text {
        id: head

        width: parent.width
        height: panel.showsActivities ? 24 : 0
        visible: panel.showsActivities
        text: history.sessionTitle
        color: Theme.textSecondary
        font.family: Theme.fontBody
        font.pixelSize: Theme.sizeSecondary
        elide: Text.ElideRight
        verticalAlignment: Text.AlignVCenter
    }

    ListView {
        id: sessions

        anchors.fill: parent
        clip: true
        model: history.sessions
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        visible: !panel.showsActivities && count > 0

        delegate: Item {
            id: entry

            required property var modelData

            width: ListView.view.width
            height: 48

            Text {
                id: number

                width: 36
                text: entry.modelData.id
                color: Theme.primary
                font.family: Theme.fontMono
                font.pixelSize: Theme.sizeTitle
                horizontalAlignment: Text.AlignRight
                anchors.verticalCenter: parent.verticalCenter
            }

            Column {
                x: number.width + Theme.space12
                width: parent.width - x
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    width: parent.width
                    text: entry.modelData.name
                    color: Theme.textPrimary
                    font.family: Theme.fontBody
                    font.pixelSize: Theme.sizeText
                    elide: Text.ElideRight
                }

                Row {
                    width: parent.width
                    height: 18
                    spacing: Theme.space8

                    Text {
                        text: entry.modelData.date
                        color: Theme.textMuted
                        font.family: Theme.fontBody
                        font.pixelSize: Theme.sizeSecondary
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Image {
                        width: 14
                        height: 14
                        sourceSize.width: 28
                        sourceSize.height: 28
                        visible: entry.modelData.important === true
                        source: Theme.icon("estrella")
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Badge {
                        visible: entry.modelData.current === true
                        text: "actual"
                        tone: Theme.primary
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }
        }
    }

    ListView {
        id: activities

        y: head.height + Theme.space8
        width: parent.width
        height: Math.max(0, parent.height - y)
        clip: true
        model: history.activities
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        visible: panel.showsActivities && count > 0

        delegate: TaskCard {
            required property var modelData

            width: ListView.view.width
            module: modelData.module
            description: modelData.description
            status: modelData.status
            time: modelData.time
        }
    }

    EmptyState {
        anchors.fill: parent
        visible: panel.showsActivities ? activities.count === 0 : sessions.count === 0
        text: panel.showsActivities ? "Sin actividades" : "Sin sesiones"
    }
}
