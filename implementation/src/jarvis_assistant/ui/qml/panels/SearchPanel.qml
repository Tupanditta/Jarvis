// Panel de búsqueda: cabecera con la consulta y el total, y los resultados numerados con su
// nombre y su carpeta (hud.md, sección 3). El número es el que el usuario escribe.
//
// En su ventana se busca sin escribir la orden: campo de búsqueda, tipo (todo, archivos o
// carpetas) y, en cada resultado, abrirlo, abrir su carpeta y copiar su ruta.
import QtQuick
import ".."
import "../components"

PanelFrame {
    id: panel

    property string kind: "ambos"        // 'ambos', 'archivos' o 'carpetas'

    function run() {
        search.run(query.text, panel.kind)
    }

    title: "Búsqueda"
    summary: !search.active ? ""
             : search.total === 1 ? "1 resultado" : search.total + " resultados"

    Column {
        id: head

        width: parent.width
        spacing: Theme.space8

        TextField {
            id: query

            width: parent.width
            visible: panel.rich
            icon: "busqueda"
            placeholder: "Buscar archivos y carpetas"
            onAccepted: panel.run()
        }

        Row {
            height: 24
            spacing: Theme.space4
            visible: panel.rich

            Repeater {
                model: [
                    { kind: "ambos", text: "Todo", icon: "" },
                    { kind: "archivos", text: "Archivos", icon: "archivo" },
                    { kind: "carpetas", text: "Carpetas", icon: "carpeta" }
                ]

                Chip {
                    required property var modelData

                    text: modelData.text
                    icon: modelData.icon
                    selected: panel.kind === modelData.kind
                    onClicked: {
                        panel.kind = modelData.kind
                        if (query.text.trim().length > 0)
                            panel.run()
                    }
                }
            }
        }

        Item {
            width: parent.width
            height: 24
            visible: search.active

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

        delegate: Item {
            id: result

            required property var modelData
            readonly property bool acting: panel.rich && resultHover.hovered

            width: ListView.view.width
            height: 44

            Rectangle {
                anchors.fill: parent
                radius: Theme.radiusCard
                color: Theme.bgHover
                visible: result.acting
            }

            HoverHandler {
                id: resultHover
            }

            NumberedRow {
                width: parent.width - (result.acting ? buttons.width + Theme.space8 : 0)
                height: parent.height
                number: result.modelData.index
                title: result.modelData.name
                subtitle: result.modelData.folder
                icon: result.modelData.isDir === true ? "carpeta" : "archivo"
            }

            Row {
                id: buttons

                x: parent.width - width - Theme.space4
                spacing: 2
                visible: result.acting
                anchors.verticalCenter: parent.verticalCenter

                IconButton {
                    icon: "apertura"
                    onClicked: search.open(result.modelData.index)
                }

                IconButton {
                    icon: "ubicacion"
                    onClicked: search.reveal(result.modelData.index)
                }

                IconButton {
                    icon: "copiar"
                    onClicked: windows.copyText(result.modelData.path)
                }
            }
        }
    }

    EmptyState {
        y: list.y
        width: parent.width
        height: list.height
        visible: list.count === 0
        text: search.active ? "Sin resultados" : panel.rich ? "Escriba qué buscar" : "Sin resultados"
    }
}
