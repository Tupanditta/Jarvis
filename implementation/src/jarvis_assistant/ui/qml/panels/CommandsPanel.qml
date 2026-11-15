// Panel de comandos: el directorio de trabajo y, debajo, el último resultado: listado de
// `ls`, árbol o salida de un binario (hud.md, sección 3). `clear` lo vacía.
import QtQuick
import ".."
import "../components"

PanelFrame {
    id: panel

    readonly property string mode: commands.mode
    readonly property var rows: mode === "listing" ? commands.entries
                              : mode === "tree" ? commands.nodes
                              : mode === "output" ? commands.lines : []
    readonly property string footer: mode === "tree" && commands.truncated
                                     ? "… (árbol recortado)"
                                     : mode === "listing" && commands.hiddenEntries > 0
                                       ? "… y " + commands.hiddenEntries + " más" : ""

    title: "Comandos"

    Column {
        id: head

        width: parent.width
        spacing: Theme.space8

        Row {
            width: parent.width
            height: 20
            spacing: Theme.space8

            Image {
                width: 16
                height: 16
                sourceSize.width: 32
                sourceSize.height: 32
                source: Theme.icon("carpeta")
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                width: parent.width - 16 - Theme.space8
                text: commands.path
                color: Theme.textPrimary
                font.family: Theme.fontMono
                font.pixelSize: Theme.sizeSecondary
                elide: Text.ElideLeft
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.lineSoft
        }

        // Cabecera de la salida: el comando y su estado.
        Row {
            width: parent.width
            height: 20
            spacing: Theme.space8
            visible: panel.mode === "output"

            StatusDot {
                status: commands.commandStatus
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                width: parent.width - 8 - Theme.space8
                text: commands.command
                color: Theme.textSecondary
                font.family: Theme.fontMono
                font.pixelSize: Theme.sizeSecondary
                elide: Text.ElideRight
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
        model: panel.rows
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        onCountChanged: if (panel.mode === "output") positionViewAtEnd()

        delegate: Item {
            id: line

            required property var modelData
            readonly property bool isOutput: panel.mode === "output"
            readonly property int depth: modelData.depth !== undefined ? modelData.depth : 1

            width: ListView.view.width
            height: isOutput ? 18 : 24

            // Líneas guía del árbol: una por nivel.
            Repeater {
                model: line.isOutput ? 0 : line.depth - 1

                Rectangle {
                    required property int index

                    x: index * Theme.space16 + 7
                    width: 1
                    height: line.height
                    color: Theme.lineSoft
                }
            }

            Image {
                id: glyph

                x: (line.depth - 1) * Theme.space16
                width: 16
                height: 16
                sourceSize.width: 32
                sourceSize.height: 32
                visible: !line.isOutput
                source: Theme.icon(line.modelData.isDir === true ? "carpeta" : "archivo")
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                x: line.isOutput ? 0 : glyph.x + 16 + Theme.space8
                width: parent.width - x
                text: line.isOutput ? line.modelData.text : line.modelData.name
                color: line.isOutput && line.modelData.error === true ? Theme.statusError
                                                                      : Theme.textPrimary
                font.family: line.isOutput ? Theme.fontMono : Theme.fontBody
                font.pixelSize: line.isOutput ? Theme.sizeSecondary : Theme.sizeText
                elide: Text.ElideRight
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        footer: Text {
            width: ListView.view ? ListView.view.width : 0
            height: panel.footer.length > 0 ? 24 : 0
            visible: panel.footer.length > 0
            text: panel.footer
            color: Theme.textMuted
            font.family: Theme.fontBody
            font.pixelSize: Theme.sizeSecondary
            verticalAlignment: Text.AlignVCenter
        }
    }

    EmptyState {
        y: list.y
        width: parent.width
        height: list.height
        visible: (panel.mode === "listing" || panel.mode === "tree") && list.count === 0
        text: "Carpeta vacía"
    }
}
