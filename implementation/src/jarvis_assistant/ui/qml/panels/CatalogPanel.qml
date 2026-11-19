// Panel Catálogo: las aplicaciones y páginas que se abren con «abre {nombre}» y los comandos
// de terminal que se pueden ejecutar. Las aplicaciones del menú Inicio no aparecen aquí.
//
// En su ventana se filtra por tipo, se añade con el formulario y se elimina con el botón de
// cada fila; eliminar lo confirma el asistente con una pregunta. Los cambios se guardan y se
// aplican al momento. Lee el modelo `catalog` (`ui/panel_models.py`, CatalogModel).
import QtQuick
import ".."
import "../components"

PanelFrame {
    id: panel

    property string kind: ""             // filtro: "", "aplicacion", "pagina" o "comando"
    property bool adding: false          // formulario abierto
    property string formKind: "aplicacion"
    readonly property var rows: kind === "" ? catalog.items
                                            : catalog.items.filter((item) => item.kind === kind)
    readonly property bool editable: rich && assistant.sessionOpen

    function countOf(wanted) {
        return catalog.items.filter((item) => item.kind === wanted).length
    }

    function iconOf(itemKind) {
        return itemKind === "aplicacion" ? "aplicacion"
             : itemKind === "pagina" ? "pagina" : "terminal"
    }

    function openForm() {
        formKind = kind === "" ? "aplicacion" : kind
        nameField.clear()
        targetField.clear()
        argsField.clear()
        aliasesField.clear()
        catalog.dismissProblem()
        adding = true
    }

    function submit() {
        catalog.add(formKind, nameField.text, targetField.text, aliasesField.text,
                    formKind === "aplicacion" ? argsField.text : "")
    }

    title: "Catálogo"
    summary: catalog.items.length === 1 ? "1 entrada" : catalog.items.length + " entradas"

    Connections {
        target: catalog

        function onAdded() {
            panel.adding = false
        }
    }

    Column {
        id: top

        width: parent.width
        spacing: Theme.space8

        // --- Filtros y «Añadir» --------------------------------------------------------------

        Item {
            width: parent.width
            height: 28
            visible: panel.rich

            Row {
                spacing: Theme.space4
                anchors.verticalCenter: parent.verticalCenter

                Chip {
                    text: "Todo"
                    count: catalog.items.length
                    selected: panel.kind === ""
                    onClicked: panel.kind = ""
                }

                Chip {
                    icon: "aplicacion"
                    text: "Apps"
                    count: panel.countOf("aplicacion")
                    selected: panel.kind === "aplicacion"
                    onClicked: panel.kind = "aplicacion"
                }

                Chip {
                    icon: "pagina"
                    text: "Páginas"
                    count: panel.countOf("pagina")
                    selected: panel.kind === "pagina"
                    onClicked: panel.kind = "pagina"
                }

                Chip {
                    icon: "terminal"
                    text: "Comandos"
                    count: panel.countOf("comando")
                    selected: panel.kind === "comando"
                    onClicked: panel.kind = "comando"
                }
            }

            Chip {
                objectName: "catalogAdd"
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                icon: "creacion"
                text: "Añadir"
                visible: !panel.adding
                enabled: panel.editable
                opacity: enabled ? 1 : 0.4
                onClicked: panel.openForm()
            }
        }

        // --- Formulario --------------------------------------------------------------------

        Rectangle {
            objectName: "catalogForm"
            width: parent.width
            height: visible ? form.implicitHeight + 2 * Theme.space12 : 0
            visible: panel.adding && panel.editable
            radius: Theme.radiusCard
            color: Theme.bgRaised
            border.width: 1
            border.color: Theme.lineStrong

            Column {
                id: form

                x: Theme.space12
                y: Theme.space12
                width: parent.width - 2 * Theme.space12
                spacing: Theme.space8

                Row {
                    spacing: Theme.space4

                    Chip {
                        objectName: "formKind-aplicacion"
                        icon: "aplicacion"
                        text: "Aplicación"
                        selected: panel.formKind === "aplicacion"
                        onClicked: panel.formKind = "aplicacion"
                    }

                    Chip {
                        objectName: "formKind-pagina"
                        icon: "pagina"
                        text: "Página web"
                        selected: panel.formKind === "pagina"
                        onClicked: panel.formKind = "pagina"
                    }

                    Chip {
                        objectName: "formKind-comando"
                        icon: "terminal"
                        text: "Comando"
                        selected: panel.formKind === "comando"
                        onClicked: panel.formKind = "comando"
                    }
                }

                TextField {
                    id: nameField

                    objectName: "catalogName"
                    width: parent.width
                    placeholder: panel.formKind === "comando"
                                 ? "Nombre que se escribe (git, npm…)"
                                 : "Nombre que se escribe tras «abre»"
                    onAccepted: panel.submit()
                }

                TextField {
                    id: targetField

                    objectName: "catalogTarget"
                    width: parent.width
                    mono: true
                    placeholder: panel.formKind === "aplicacion"
                                 ? "C:/Programas/editor.exe o un nombre del PATH"
                                 : panel.formKind === "pagina" ? "https://example.com"
                                                               : "Ejecutable: nombre del PATH o ruta"
                    onAccepted: panel.submit()
                }

                TextField {
                    id: argsField

                    objectName: "catalogArgs"
                    width: parent.width
                    height: visible ? implicitHeight : 0
                    visible: panel.formKind === "aplicacion"
                    mono: true
                    placeholder: "Argumentos (opcional, separados por comas)"
                    onAccepted: panel.submit()
                }

                TextField {
                    id: aliasesField

                    objectName: "catalogAliases"
                    width: parent.width
                    placeholder: "Otros nombres (opcional, separados por comas)"
                    onAccepted: panel.submit()
                }

                Item {
                    width: parent.width
                    height: 24

                    Row {
                        anchors.right: parent.right
                        spacing: Theme.space8

                        Chip {
                            text: "Cancelar"
                            onClicked: {
                                panel.adding = false
                                catalog.dismissProblem()
                            }
                        }

                        Chip {
                            objectName: "catalogSubmit"
                            icon: "creacion"
                            text: "Añadir"
                            selected: true
                            onClicked: panel.submit()
                        }
                    }
                }
            }
        }

        // Motivo por el que no se ha podido añadir o eliminar.
        Text {
            objectName: "catalogProblem"
            width: parent.width
            height: visible ? implicitHeight : 0
            visible: panel.rich && catalog.problem.length > 0
            text: catalog.problem
            color: Theme.statusError
            font.family: Theme.fontBody
            font.pixelSize: Theme.sizeSecondary
            wrapMode: Text.Wrap
        }
    }

    // --- Lista -------------------------------------------------------------------------------

    ListView {
        id: list

        y: top.height + (panel.rich ? Theme.space8 : 0)
        width: parent.width
        height: Math.max(0, parent.height - y)
        clip: true
        spacing: Theme.space4
        model: panel.rows
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        visible: count > 0

        delegate: Rectangle {
            id: entry

            required property var modelData

            objectName: "catalogItem-" + modelData.id
            width: ListView.view.width
            height: 46
            radius: Theme.radiusCard
            color: Theme.bgRaised

            Image {
                id: glyph

                x: Theme.space12
                width: 16
                height: 16
                sourceSize.width: 32
                sourceSize.height: 32
                source: Theme.icon(panel.iconOf(entry.modelData.kind))
                opacity: 0.85
                anchors.verticalCenter: parent.verticalCenter
            }

            Column {
                anchors.left: glyph.right
                anchors.leftMargin: Theme.space12
                anchors.right: remove.visible ? remove.left : parent.right
                anchors.rightMargin: Theme.space12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2

                Text {
                    width: parent.width
                    text: entry.modelData.name
                          + (entry.modelData.aliases.length > 0
                             ? "  ·  " + entry.modelData.aliases : "")
                    color: Theme.textPrimary
                    font.family: Theme.fontBody
                    font.pixelSize: Theme.sizeSecondary
                    elide: Text.ElideRight
                }

                Text {
                    width: parent.width
                    text: entry.modelData.target
                          + (entry.modelData.args.length > 0 ? " " + entry.modelData.args : "")
                    color: Theme.textMuted
                    font.family: Theme.fontMono
                    font.pixelSize: Theme.sizeLabel
                    elide: Text.ElideMiddle
                }
            }

            Chip {
                id: remove

                objectName: "catalogRemove-" + entry.modelData.id
                x: parent.width - width - Theme.space8
                anchors.verticalCenter: parent.verticalCenter
                visible: panel.rich
                text: "Eliminar"
                tone: Theme.statusError
                enabled: panel.editable
                opacity: enabled ? 1 : 0.4
                onClicked: catalog.remove(entry.modelData.id)
            }
        }
    }

    EmptyState {
        y: list.y
        width: parent.width
        height: list.height
        visible: list.count === 0
        text: panel.kind === "" ? "El catálogo está vacío" : "Nada de este tipo"
    }
}
