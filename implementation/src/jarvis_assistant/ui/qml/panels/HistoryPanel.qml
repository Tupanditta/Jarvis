// Panel de historial: la tabla de sesiones (identificador, nombre, fecha, importancia) o las
// actividades de una sesión (hud.md, sección 3).
//
// En su ventana se navega con el ratón: un clic en una sesión muestra sus actividades y el
// botón de volver regresa a la tabla. Añade el filtro de sesiones por nombre, el de
// actividades con error y el botón de actualizar. Al abrirse carga las sesiones.
import QtQuick
import ".."
import "../components"

PanelFrame {
    id: panel

    readonly property bool showsActivities: history.mode === "activities"
    property string needle: ""           // filtro de sesiones, en minúsculas
    property bool onlyErrors: false
    readonly property var sessionRows: needle.length === 0
        ? history.sessions
        : history.sessions.filter((row) => row.name.toLowerCase().indexOf(needle) >= 0)
    readonly property var activityRows: onlyErrors
        ? history.activities.filter((row) => row.status === "error")
        : history.activities

    title: "Historial"
    summary: showsActivities
             ? history.activities.length + (history.activities.length === 1 ? " actividad"
                                                                             : " actividades")
             : history.sessions.length + (history.sessions.length === 1 ? " sesión" : " sesiones")

    // Carga las sesiones al abrir la ventana a mano. Espera un momento: si la ha abierto una
    // orden del historial, su contenido está a punto de llegar y no hay que pedirlo otra vez.
    Timer {
        interval: 400
        running: panel.rich
        onTriggered: {
            if (history.mode === "" && assistant.sessionOpen)
                history.refresh()
        }
    }

    Item {
        id: head

        width: parent.width
        height: panel.rich ? 30 : panel.showsActivities ? 24 : 0

        // Tabla de sesiones: filtro y actualizar.
        TextField {
            width: parent.width - refresh.width - Theme.space4
            visible: panel.rich && !panel.showsActivities
            icon: "filtro"
            placeholder: "Filtrar sesiones"
            onEdited: (text) => panel.needle = text.trim().toLowerCase()
        }

        IconButton {
            id: refresh

            x: parent.width - width
            icon: "actualizar"
            visible: panel.rich && !panel.showsActivities
            enabled: assistant.sessionOpen
            anchors.verticalCenter: parent.verticalCenter
            onClicked: history.refresh()
        }

        // Actividades de una sesión: volver, su nombre y el filtro de errores.
        IconButton {
            id: back

            icon: "atras"
            visible: panel.rich && panel.showsActivities
            anchors.verticalCenter: parent.verticalCenter
            onClicked: history.refresh()
        }

        Text {
            x: back.visible ? back.width + Theme.space4 : 0
            width: Math.max(0, parent.width - x - (errors.visible ? errors.width + Theme.space8 : 0))
            visible: panel.showsActivities
            text: history.sessionTitle
            color: Theme.textSecondary
            font.family: Theme.fontBody
            font.pixelSize: Theme.sizeSecondary
            elide: Text.ElideRight
            anchors.verticalCenter: parent.verticalCenter
        }

        Chip {
            id: errors

            x: parent.width - width
            visible: panel.rich && panel.showsActivities
            text: "Errores"
            count: history.errorCount
            tone: Theme.statusError
            selected: panel.onlyErrors
            anchors.verticalCenter: parent.verticalCenter
            onClicked: panel.onlyErrors = !panel.onlyErrors
        }
    }

    ListView {
        id: sessions

        y: head.height + (head.height > 0 ? Theme.space8 : 0)
        width: parent.width
        height: Math.max(0, parent.height - y)
        clip: true
        model: panel.sessionRows
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        visible: !panel.showsActivities && count > 0

        delegate: Item {
            id: entry

            required property var modelData

            width: ListView.view.width
            height: 48

            Rectangle {
                anchors.fill: parent
                radius: Theme.radiusCard
                color: Theme.bgHover
                visible: entryHover.hovered
            }

            HoverHandler {
                id: entryHover
                enabled: panel.rich
                cursorShape: Qt.PointingHandCursor
            }

            TapHandler {
                enabled: panel.rich
                onTapped: history.open(entry.modelData.id)
            }

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

        y: sessions.y
        width: parent.width
        height: Math.max(0, parent.height - y)
        clip: true
        model: panel.activityRows
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
        y: sessions.y
        width: parent.width
        height: sessions.height
        visible: panel.showsActivities ? activities.count === 0 : sessions.count === 0
        text: panel.showsActivities ? (panel.onlyErrors ? "Sin errores" : "Sin actividades")
              : panel.needle.length > 0 ? "Ninguna sesión coincide"
              : history.mode === "" && panel.rich ? "Pulse actualizar para ver las sesiones"
              : "Sin sesiones"
    }
}
