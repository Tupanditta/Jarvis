// Panel de aperturas: una tarjeta por elemento abierto, con su estado y el botón «traer al
// frente» (hud.md, sección 3).
//
// En su ventana añade filtros por tipo, el botón que vuelve a abrir una aplicación o una
// página y el acceso rápido: las aplicaciones y páginas del catálogo, que se abren con un clic.
import QtQuick
import ".."
import "../components"

PanelFrame {
    id: panel

    property string kind: ""             // "", "aplicacion", "pagina" o "carpeta"
    readonly property var rows: kind === "" ? opened.items
                                            : opened.items.filter((item) => item.kind === kind)
    readonly property bool quick: rich && opened.targets.length > 0

    function countOf(wanted) {
        return opened.items.filter((item) => item.kind === wanted).length
    }

    title: "Aperturas"
    summary: opened.items.length === 1 ? "1 abierto" : opened.items.length + " abiertos"

    Row {
        id: head

        height: visible ? 28 : 0
        spacing: Theme.space4
        visible: panel.rich

        Chip {
            text: "Todo"
            count: opened.items.length
            selected: panel.kind === ""
            onClicked: panel.kind = ""
            anchors.verticalCenter: parent.verticalCenter
        }

        Chip {
            icon: "aplicacion"
            text: "Apps"
            count: panel.countOf("aplicacion")
            selected: panel.kind === "aplicacion"
            onClicked: panel.kind = "aplicacion"
            anchors.verticalCenter: parent.verticalCenter
        }

        Chip {
            icon: "pagina"
            text: "Páginas"
            count: panel.countOf("pagina")
            selected: panel.kind === "pagina"
            onClicked: panel.kind = "pagina"
            anchors.verticalCenter: parent.verticalCenter
        }

        Chip {
            icon: "carpeta"
            text: "Carpetas"
            count: panel.countOf("carpeta")
            selected: panel.kind === "carpeta"
            onClicked: panel.kind = "carpeta"
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    ListView {
        id: list

        y: head.height + (panel.rich ? Theme.space8 : 0)
        width: parent.width
        height: Math.max(0, parent.height - y - (panel.quick ? shortcuts.height + Theme.space8 : 0))
        clip: true
        model: panel.rows
        spacing: Theme.space4
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        visible: count > 0

        delegate: Rectangle {
            id: card

            required property var modelData
            // Una carpeta no se vuelve a abrir desde aquí: la tarjeta no guarda su ruta.
            readonly property bool relaunches: panel.rich && modelData.kind !== "carpeta"

            width: ListView.view.width
            height: 40
            radius: Theme.radiusCard
            color: Theme.bgRaised
            border.width: 1
            border.color: cardHover.hovered ? Theme.lineStrong : "transparent"

            HoverHandler {
                id: cardHover
            }

            Image {
                id: glyph

                x: Theme.space12
                width: 16
                height: 16
                sourceSize.width: 32
                sourceSize.height: 32
                source: Theme.icon(card.modelData.kind)
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                x: glyph.x + 16 + Theme.space8
                width: Math.max(0, dot.x - x - Theme.space8)
                text: card.modelData.title
                color: Theme.textPrimary
                font.family: Theme.fontBody
                font.pixelSize: Theme.sizeText
                elide: Text.ElideRight
                anchors.verticalCenter: parent.verticalCenter
            }

            StatusDot {
                id: dot

                x: buttons.x - 8 - Theme.space8
                status: card.modelData.status
                anchors.verticalCenter: parent.verticalCenter
            }

            Row {
                id: buttons

                x: parent.width - width - (width > 0 ? Theme.space8 : Theme.space4)
                spacing: 2
                anchors.verticalCenter: parent.verticalCenter

                IconButton {
                    icon: "actualizar"
                    visible: card.relaunches
                    onClicked: opened.launch(card.modelData.title)
                }

                // Desactivado si la ventana ya no existe; ausente si el sistema no lo permite.
                IconButton {
                    icon: "frente"
                    visible: opened.focusSupported
                    enabled: card.modelData.canFocus === true
                    onClicked: opened.focus(card.modelData.id)
                }
            }
        }
    }

    EmptyState {
        y: list.y
        width: parent.width
        height: list.height
        visible: list.count === 0
        text: panel.kind === "" ? "Nada abierto" : "Nada abierto de este tipo"
    }

    // Acceso rápido: el catálogo de aplicaciones y páginas.
    Column {
        id: shortcuts

        y: parent.height - height
        width: parent.width
        spacing: Theme.space8
        visible: panel.quick

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.lineSoft
        }

        DisplayText {
            text: "Acceso rápido"
            size: Theme.sizeLabel
        }

        Flickable {
            width: parent.width
            height: Math.min(flow.implicitHeight, 60)
            contentHeight: flow.implicitHeight
            clip: true
            interactive: contentHeight > height
            boundsBehavior: Flickable.StopAtBounds

            Flow {
                id: flow

                width: parent.width
                spacing: Theme.space4

                Repeater {
                    model: opened.targets

                    Chip {
                        required property var modelData

                        icon: modelData.kind
                        text: modelData.name
                        onClicked: opened.launch(modelData.name)
                    }
                }
            }
        }
    }
}
