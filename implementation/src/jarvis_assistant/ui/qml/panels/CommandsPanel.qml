// Panel de comandos: el directorio de trabajo y, debajo, el último resultado: listado de
// `ls`, árbol o salida de un binario (hud.md, sección 3). `clear` lo vacía.
//
// En su ventana es un explorador: barra de herramientas (subir, inicio, actualizar, árbol,
// terminal, gestor de archivos, limpiar), ruta navegable carpeta a carpeta, filtro del
// listado, carpetas que se abren con un clic, copia de la salida de un programa y una línea
// para ejecutar programas permitidos.
//
// Cada ventana de Comandos muestra su propia consola (`windowId`): la principal o una copia
// abierta por un protocolo o por el botón «Nueva ventana de Comandos».
import QtQuick
import ".."
import "../components"

PanelFrame {
    id: panel

    // El panel de su consola (`ui/panel_models.py`, `ConsolesModel`).
    readonly property var commands: consoles.get(windowId.length > 0 ? windowId : "comandos")
    readonly property string mode: commands.mode
    readonly property bool isOutput: mode === "output"
    readonly property bool browsing: mode === "listing" || mode === "tree"
    property string needle: ""           // filtro del listado, en minúsculas
    readonly property var source: mode === "listing" ? commands.entries
                                  : mode === "tree" ? commands.nodes
                                  : isOutput ? commands.lines : []
    readonly property var rows: !browsing || needle.length === 0
                                ? source
                                : source.filter((row) => row.name.toLowerCase().indexOf(needle) >= 0)
    readonly property string footer: mode === "tree" && commands.truncated
                                     ? "… (árbol recortado)"
                                     : mode === "listing" && commands.hiddenEntries > 0
                                       ? "… y " + commands.hiddenEntries + " más" : ""

    title: "Comandos"
    summary: isOutput ? commands.lines.length + " líneas"
             : browsing ? rows.length + (rows.length === 1 ? " elemento" : " elementos") : ""

    Column {
        id: head

        width: parent.width
        spacing: Theme.space8

        ToolBar {
            width: parent.width
            visible: panel.rich
            actions: [
                { icon: "subir", hint: "Carpeta superior", enabled: commands.canGoUp,
                  run: () => commands.up() },
                { icon: "inicio", hint: "Carpeta personal", run: () => commands.home() },
                { icon: "actualizar", hint: "Listar la carpeta", run: () => commands.refresh() },
                { icon: "arbol", hint: "Árbol de la carpeta", run: () => commands.tree() },
                { icon: "terminal", hint: "Abrir una terminal aquí",
                  run: () => commands.terminal() },
                { icon: "carpeta", hint: "Abrir en el gestor de archivos",
                  run: () => commands.reveal() },
                { icon: "limpiar", hint: "Limpiar el panel", enabled: panel.mode.length > 0,
                  run: () => commands.clear() },
                { icon: "nueva_ventana", hint: "Nueva ventana de Comandos en esta carpeta",
                  run: () => commands.duplicate() }
            ]
        }

        // Ruta navegable: cada carpeta lleva a ella.
        ListView {
            id: crumbs

            width: parent.width
            height: 22
            visible: panel.rich
            orientation: ListView.Horizontal
            clip: true
            model: commands.crumbs
            boundsBehavior: Flickable.StopAtBounds
            onCountChanged: positionViewAtEnd()

            delegate: Row {
                id: crumb

                required property var modelData
                required property int index
                readonly property bool last: index === crumbs.count - 1

                height: crumbs.height
                spacing: Theme.space4

                Text {
                    text: crumb.modelData.name
                    color: crumb.last ? Theme.textPrimary
                                      : crumbHover.hovered ? Theme.primaryBright
                                                           : Theme.textSecondary
                    font.family: Theme.fontMono
                    font.pixelSize: Theme.sizeSecondary
                    anchors.verticalCenter: parent.verticalCenter

                    HoverHandler {
                        id: crumbHover
                        enabled: !crumb.last
                        cursorShape: Qt.PointingHandCursor
                    }

                    TapHandler {
                        enabled: !crumb.last
                        onTapped: commands.goTo(crumb.modelData.path)
                    }
                }

                Text {
                    text: "›"
                    visible: !crumb.last
                    color: Theme.textMuted
                    font.family: Theme.fontMono
                    font.pixelSize: Theme.sizeSecondary
                    rightPadding: Theme.space4
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }

        // En el HUD, la ruta en una línea.
        Row {
            width: parent.width
            height: 20
            spacing: Theme.space8
            visible: !panel.rich

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

        // Cabecera de la salida: el comando, su estado y el botón de copiar.
        Item {
            width: parent.width
            height: 28
            visible: panel.isOutput

            StatusDot {
                id: outputDot

                status: commands.commandStatus
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                x: outputDot.width + Theme.space8
                width: Math.max(0, copy.x - x - Theme.space8)
                text: commands.command
                color: Theme.textSecondary
                font.family: Theme.fontMono
                font.pixelSize: Theme.sizeSecondary
                elide: Text.ElideRight
                anchors.verticalCenter: parent.verticalCenter
            }

            IconButton {
                id: copy

                x: parent.width - (visible ? width : 0)
                icon: "copiar"
                visible: panel.rich
                enabled: commands.lines.length > 0
                anchors.verticalCenter: parent.verticalCenter
                onClicked: windows.copyText(commands.outputText())
            }
        }

        TextField {
            width: parent.width
            visible: panel.rich && panel.browsing
            icon: "filtro"
            placeholder: "Filtrar por nombre"
            onEdited: (text) => panel.needle = text.trim().toLowerCase()
        }
    }

    ListView {
        id: list

        y: head.height + Theme.space8
        width: parent.width
        height: Math.max(0, parent.height - y - (prompt.visible ? prompt.height + Theme.space8 : 0))
        clip: true
        model: panel.rows
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        onCountChanged: if (panel.isOutput) positionViewAtEnd()

        delegate: Item {
            id: line

            required property var modelData
            readonly property int depth: modelData.depth !== undefined ? modelData.depth : 1
            // Una carpeta del listado se abre con un clic.
            readonly property bool opens: panel.rich && panel.mode === "listing"
                                          && modelData.isDir === true

            width: ListView.view.width
            height: panel.isOutput ? 18 : 24

            Rectangle {
                anchors.fill: parent
                radius: Theme.radiusCard
                color: Theme.bgHover
                visible: line.opens && lineHover.hovered
            }

            // Líneas guía del árbol: una por nivel.
            Repeater {
                model: panel.isOutput ? 0 : line.depth - 1

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
                visible: !panel.isOutput
                source: Theme.icon(line.modelData.isDir === true ? "carpeta" : "archivo")
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                x: panel.isOutput ? 0 : glyph.x + 16 + Theme.space8
                width: parent.width - x
                text: panel.isOutput ? line.modelData.text : line.modelData.name
                color: panel.isOutput && line.modelData.error === true ? Theme.statusError
                                                                       : Theme.textPrimary
                font.family: panel.isOutput ? Theme.fontMono : Theme.fontBody
                font.pixelSize: panel.isOutput ? Theme.sizeSecondary : Theme.sizeText
                elide: Text.ElideRight
                anchors.verticalCenter: parent.verticalCenter
            }

            HoverHandler {
                id: lineHover
                enabled: line.opens
                cursorShape: Qt.PointingHandCursor
            }

            TapHandler {
                enabled: line.opens
                onTapped: commands.enter(line.modelData.name)
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
        visible: list.count === 0 && (panel.browsing || panel.rich)
        text: !panel.browsing ? "Liste la carpeta o ejecute un programa"
              : panel.needle.length > 0 ? "Ningún nombre coincide" : "Carpeta vacía"
    }

    // Línea de programas: lo escrito se envía como la orden «ejecuta …».
    TextField {
        id: prompt

        y: parent.height - height
        width: parent.width
        visible: panel.rich
        mono: true
        icon: "ejecutar"
        placeholder: "Ejecutar un programa permitido: git status"
        onAccepted: (text) => {
            if (text.trim().length > 0) {
                assistant.submit("ejecuta " + text.trim())
                prompt.text = ""
            }
        }
    }
}
