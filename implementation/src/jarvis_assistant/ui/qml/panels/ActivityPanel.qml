// Panel de actividad: las tareas de la sesión, la más reciente arriba (hud.md, sección 3).
// En su ventana añade las órdenes que esperan en la cola, filtros por estado y el botón que
// cancela todo lo que está en curso.
import QtQuick
import ".."
import "../components"

PanelFrame {
    id: panel

    property int limit: -1               // en el HUD, las 6 últimas
    property string filter: ""           // "", "pendiente" o "error"
    readonly property int maxQueued: 5
    readonly property int matching: filter === "pendiente" ? tasks.pendingCount
                                    : filter === "error" ? tasks.errorCount : tasks.count
    readonly property bool busy: tasks.pendingCount > 0 || tasks.queue.length > 0
    readonly property real contentHeight: headerHeight
                                          + (tasks.count > 0 ? list.contentHeight : 48)

    title: "Actividad"
    summary: tasks.queue.length > 0 ? tasks.pendingCount + " en curso · "
                                      + tasks.queue.length + " en cola"
             : tasks.pendingCount > 0 ? tasks.pendingCount + " en curso"
             : tasks.count === 1 ? "1 tarea" : tasks.count + " tareas"

    Column {
        id: head

        width: parent.width
        height: visible ? implicitHeight : 0
        spacing: Theme.space8
        visible: panel.rich

        Item {
            width: parent.width
            height: 28

            Row {
                spacing: Theme.space4
                anchors.verticalCenter: parent.verticalCenter

                Chip {
                    text: "Todas"
                    count: tasks.count
                    selected: panel.filter === ""
                    onClicked: panel.filter = ""
                }

                Chip {
                    text: "En curso"
                    count: tasks.pendingCount
                    tone: Theme.statusPending
                    selected: panel.filter === "pendiente"
                    onClicked: panel.filter = "pendiente"
                }

                Chip {
                    text: "Errores"
                    count: tasks.errorCount
                    tone: Theme.statusError
                    selected: panel.filter === "error"
                    onClicked: panel.filter = "error"
                }
            }

            // Cancela las órdenes en curso y en cola: lo mismo que escribir «cancelar».
            IconButton {
                x: parent.width - width
                icon: "cancelar"
                enabled: panel.busy
                anchors.verticalCenter: parent.verticalCenter
                onClicked: assistant.submit("cancelar")
            }
        }

        // Órdenes que esperan su turno, en el orden en que se ejecutarán.
        Column {
            width: parent.width
            spacing: Theme.space4
            visible: tasks.queue.length > 0

            DisplayText {
                text: "En cola · " + tasks.queue.length
                size: Theme.sizeLabel
                color: Theme.statusPending
            }

            Repeater {
                model: Math.min(tasks.queue.length, panel.maxQueued)

                Row {
                    required property int index

                    width: head.width
                    height: 20
                    spacing: Theme.space8

                    Text {
                        width: 16
                        text: index + 1
                        color: Theme.textMuted
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.sizeLabel
                        horizontalAlignment: Text.AlignRight
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Text {
                        width: parent.width - 16 - Theme.space8
                        text: tasks.queue[index] !== undefined ? tasks.queue[index] : ""
                        color: Theme.textSecondary
                        font.family: Theme.fontBody
                        font.pixelSize: Theme.sizeSecondary
                        elide: Text.ElideRight
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }

            Text {
                visible: tasks.queue.length > panel.maxQueued
                text: "… y " + (tasks.queue.length - panel.maxQueued) + " más"
                color: Theme.textMuted
                font.family: Theme.fontBody
                font.pixelSize: Theme.sizeLabel
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.lineSoft
        }
    }

    ListView {
        id: list

        y: head.height + (panel.rich ? Theme.space8 : 0)
        width: parent.width
        height: Math.max(0, parent.height - y)
        clip: panel.rich
        model: tasks
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        visible: panel.matching > 0

        delegate: TaskCard {
            required property int index
            required module
            required description
            required status
            required detail
            required time
            required child
            readonly property bool shown: (panel.limit < 0 || index < panel.limit)
                                          && (panel.filter === "" || status === panel.filter)

            width: ListView.view.width
            height: shown ? implicitHeight : 0
            visible: shown
        }
    }

    EmptyState {
        y: list.y
        width: parent.width
        height: list.height
        visible: panel.matching === 0
        text: panel.filter === "pendiente" ? "Nada en curso"
              : panel.filter === "error" ? "Sin errores" : "Sin actividad"
    }
}
