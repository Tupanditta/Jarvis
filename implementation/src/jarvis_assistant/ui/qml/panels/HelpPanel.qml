// Panel de ayuda: las órdenes disponibles agrupadas por módulo, cada una con su descripción y
// un ejemplo entre comillas (hud.md, sección 3). Sale del registro de intenciones.
//
// En su ventana se filtra por texto y un clic en una orden escribe su ejemplo en la caja de
// órdenes, lista para enviar o cambiar. Al abrirse carga las órdenes.
import QtQuick
import ".."
import "../components"

PanelFrame {
    id: panel

    property string needle: ""           // filtro, en minúsculas
    // Con filtro se muestran solo las órdenes que coinciden, sin las cabeceras de grupo.
    readonly property var rows: needle.length === 0
        ? help.rows
        : help.rows.filter((row) => row.header !== true
                           && (row.title.toLowerCase().indexOf(needle) >= 0
                               || row.example.toLowerCase().indexOf(needle) >= 0))

    title: "Ayuda"
    summary: needle.length > 0 ? rows.length + " coincidencias" : ""

    // Carga las órdenes al abrir la ventana a mano, si aún no se han pedido.
    Timer {
        interval: 400
        running: panel.rich
        onTriggered: {
            if (help.rows.length === 0 && assistant.sessionOpen)
                help.load()
        }
    }

    TextField {
        id: filter

        width: parent.width
        height: visible ? implicitHeight : 0
        visible: panel.rich
        icon: "filtro"
        placeholder: "Filtrar órdenes"
        onEdited: (text) => panel.needle = text.trim().toLowerCase()
    }

    ListView {
        id: list

        y: filter.height + (panel.rich ? Theme.space8 : 0)
        width: parent.width
        height: Math.max(0, parent.height - y)
        clip: true
        model: panel.rows
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        visible: count > 0

        delegate: Item {
            id: entry

            required property var modelData
            readonly property bool isHeader: modelData.header === true
            readonly property bool usable: panel.rich && !isHeader

            width: ListView.view.width
            height: isHeader ? 32 : 42

            Rectangle {
                anchors.fill: parent
                radius: Theme.radiusCard
                color: Theme.bgHover
                visible: entry.usable && entryHover.hovered
            }

            HoverHandler {
                id: entryHover
                enabled: entry.usable
                cursorShape: Qt.PointingHandCursor
            }

            TapHandler {
                enabled: entry.usable
                onTapped: assistant.suggest(entry.modelData.example)
            }

            DisplayText {
                width: parent.width
                visible: entry.isHeader
                text: entry.modelData.title
                color: Theme.primary
                anchors.bottom: parent.bottom
                anchors.bottomMargin: Theme.space4
            }

            Column {
                x: entry.usable ? Theme.space8 : 0
                width: parent.width - 2 * x
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
                    color: entryHover.hovered ? Theme.primaryBright : Theme.textSecondary
                    font.family: Theme.fontBody
                    font.pixelSize: Theme.sizeSecondary
                    elide: Text.ElideRight
                }
            }
        }
    }

    EmptyState {
        y: list.y
        width: parent.width
        height: list.height
        visible: list.count === 0
        text: panel.needle.length > 0 ? "Ninguna orden coincide" : "Sin órdenes"
    }
}
