// Panel de búsqueda: cabecera con la consulta y el total, y los resultados numerados con su
// nombre y su carpeta (hud.md, sección 3). El número es el que el usuario escribe.
import QtQuick
import ".."
import "../components"

PanelFrame {
    id: panel

    title: "Búsqueda"

    Item {
        id: head

        width: parent.width
        height: 24

        Text {
            width: parent.width - (limitedBadge.visible ? limitedBadge.width + Theme.space8 : 0)
            text: search.total === 1 ? "«" + search.query + "» · 1 resultado"
                                     : "«" + search.query + "» · " + search.total + " resultados"
            color: Theme.textSecondary
            font.family: Theme.fontBody
            font.pixelSize: Theme.sizeSecondary
            elide: Text.ElideRight
            anchors.verticalCenter: parent.verticalCenter
        }

        Badge {
            id: limitedBadge

            x: parent.width - width
            visible: search.limited
            text: "limitada"
            tone: Theme.statusPending
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    ListView {
        id: list

        y: head.height + Theme.space8
        width: parent.width
        height: Math.max(0, parent.height - y)
        clip: true
        model: search.results
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        visible: count > 0

        delegate: NumberedRow {
            required property var modelData

            width: ListView.view.width
            number: modelData.index
            title: modelData.name
            subtitle: modelData.folder
            icon: modelData.isDir === true ? "carpeta" : "archivo"
        }
    }

    EmptyState {
        y: list.y
        width: parent.width
        height: list.height
        visible: list.count === 0
        text: "Sin resultados"
    }
}
