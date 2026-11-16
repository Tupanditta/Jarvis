// Panel de recordatorios (hud.md, sección 3; Interfaz, sección 8): una fila numerada por
// recordatorio con su texto y, debajo, el próximo aviso y la fecha límite en `text.secondary`;
// distintivo «vencido» en `status.error`; el notificado o leído, con fondo `bg.raised` y borde
// `primary`. El número es el que el usuario escribe en la orden.
//
// En su ventana, el botón de actualizar vuelve a pedir la lista.
import QtQuick
import ".."
import "../components"

PanelFrame {
    id: panel

    title: "Recordatorios"
    summary: reminders.items.length === 1 ? "1 recordatorio"
                                          : reminders.items.length + " recordatorios"

    Item {
        id: head

        width: parent.width
        height: panel.rich ? 30 : 0
        visible: panel.rich

        Text {
            width: parent.width - refresh.width - Theme.space8
            text: reminders.overdueCount === 0 ? ""
                  : reminders.overdueCount === 1 ? "1 vencido"
                  : reminders.overdueCount + " vencidos"
            color: Theme.statusError
            font.family: Theme.fontBody
            font.pixelSize: Theme.sizeSecondary
            elide: Text.ElideRight
            anchors.verticalCenter: parent.verticalCenter
        }

        IconButton {
            id: refresh

            x: parent.width - width
            icon: "actualizar"
            enabled: assistant.sessionOpen
            anchors.verticalCenter: parent.verticalCenter
            onClicked: reminders.refresh()
        }
    }

    ListView {
        id: list

        y: head.height + (head.height > 0 ? Theme.space8 : 0)
        width: parent.width
        height: Math.max(0, parent.height - y)
        clip: true
        spacing: Theme.space4
        model: reminders.items
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        visible: count > 0

        delegate: Item {
            id: entry

            required property var modelData
            readonly property string when: [
                modelData.next.length > 0 ? "Aviso " + modelData.next : "",
                modelData.deadline.length > 0 ? "Límite " + modelData.deadline : ""
            ].filter((part) => part.length > 0).join(" · ")

            width: ListView.view.width
            height: 48

            Rectangle {
                anchors.fill: parent
                radius: Theme.radiusCard
                color: Theme.bgRaised
                border.width: 1
                border.color: Theme.primary
                visible: entry.modelData.highlighted === true
            }

            NumberedRow {
                x: Theme.space4
                width: parent.width - x - (overdue.visible ? overdue.width + Theme.space12 : 0)
                height: parent.height
                number: entry.modelData.index
                title: entry.modelData.content
                subtitle: entry.when
            }

            Badge {
                id: overdue

                x: parent.width - width - Theme.space8
                visible: entry.modelData.overdue === true
                text: "vencido"
                tone: Theme.statusError
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    EmptyState {
        y: list.y
        width: parent.width
        height: list.height
        visible: list.count === 0
        text: "Sin recordatorios"
    }
}
