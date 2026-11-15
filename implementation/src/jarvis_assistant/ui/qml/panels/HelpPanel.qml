// Panel de ayuda: las órdenes disponibles agrupadas por módulo, cada una con su descripción y
// un ejemplo entre comillas (hud.md, sección 3). Sale del registro de intenciones.
import QtQuick
import ".."
import "../components"

PanelFrame {
    id: panel

    title: "Ayuda"

    ListView {
        id: list

        anchors.fill: parent
        clip: true
        model: help.rows
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        visible: count > 0

        delegate: Item {
            id: entry

            required property var modelData
            readonly property bool isHeader: modelData.header === true

            width: ListView.view.width
            height: isHeader ? 32 : 42

            DisplayText {
                width: parent.width
                visible: entry.isHeader
                text: entry.modelData.title
                color: Theme.primary
                anchors.bottom: parent.bottom
                anchors.bottomMargin: Theme.space4
            }

            Column {
                width: parent.width
                visible: !entry.isHeader
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    width: parent.width
                    text: entry.modelData.title
                    color: Theme.textPrimary
                    font.family: Theme.fontBody
                    font.pixelSize: Theme.sizeText
                    elide: Text.ElideRight
                }

                Text {
                    width: parent.width
                    text: "«" + entry.modelData.example + "»"
                    color: Theme.textSecondary
                    font.family: Theme.fontBody
                    font.pixelSize: Theme.sizeSecondary
                    elide: Text.ElideRight
                }
            }
        }
    }

    EmptyState {
        anchors.fill: parent
        visible: list.count === 0
        text: "Sin órdenes"
    }
}
