// Apartado Aplicaciones: las aplicaciones y páginas añadidas a mano. Añadir pide primero el
// tipo; después, el formulario de ese tipo. Aceptar guarda en el borrador; el archivo solo se
// escribe al pulsar Guardar.
import QtQuick
import QtQuick.Dialogs
import "../../../ui/qml"
import "../../../ui/qml/components"
import "../controls"

Column {
    id: page

    property QtObject section
    readonly property bool editable: section !== null && section.locked.length === 0

    // Formulario: "" (cerrado), "choose" (elegir tipo), "app" o "page".
    property string mode: ""
    property int row: -1              // fila que se edita; -1: entrada nueva
    property string error: ""

    function openForm(kind, index) {
        row = index
        mode = kind
        error = ""
        var entry = index >= 0 ? section.entry(index) : ({})
        nameField.setText(entry.name || "")
        targetField.setText(entry.target || "")
        argsField.setText(entry.args || "")
        aliasesField.setText(entry.aliases || "")
    }

    function accept() {
        error = section.submit(row, mode, nameField.text, targetField.text, argsField.text,
                               aliasesField.text)
        if (error.length === 0)
            mode = ""
    }

    spacing: Theme.space16

    PageHeader {
        width: page.width
        title: "Aplicaciones y páginas"
        detail: "Lo que se abre con «abre {nombre}». Las aplicaciones del menú Inicio se añaden"
                + " solas y no aparecen aquí."
        action: "Añadir"
        locked: page.section ? page.section.locked : ""
        onTriggered: page.openForm("choose", -1)
    }

    // --- Elegir tipo -------------------------------------------------------------------------

    Rectangle {
        objectName: "chooseKind"
        visible: page.mode === "choose"
        width: page.width
        height: chooseColumn.implicitHeight + 2 * Theme.space16
        radius: Theme.radiusPanel
        color: Theme.bgPanel
        border.width: 1
        border.color: Theme.lineStrong

        Column {
            id: chooseColumn

            x: Theme.space16
            y: Theme.space16
            spacing: Theme.space12

            Text {
                text: "¿Qué quiere añadir?"
                color: Theme.textPrimary
                font.family: Theme.fontBody
                font.pixelSize: Theme.sizeText
            }

            Row {
                spacing: Theme.space8

                TextButton {
                    objectName: "kindApp"
                    text: "Aplicación"
                    icon: "aplicacion"
                    onClicked: page.openForm("app", -1)
                }

                TextButton {
                    objectName: "kindPage"
                    text: "Página web"
                    icon: "pagina"
                    onClicked: page.openForm("page", -1)
                }

                TextButton {
                    text: "Cancelar"
                    onClicked: page.mode = ""
                }
            }
        }
    }

    // --- Formulario --------------------------------------------------------------------------

    Rectangle {
        objectName: "entryForm"
        visible: page.mode === "app" || page.mode === "page"
        width: page.width
        height: form.implicitHeight + 2 * Theme.space16
        radius: Theme.radiusPanel
        color: Theme.bgPanel
        border.width: 1
        border.color: Theme.lineStrong

        Column {
            id: form

            x: Theme.space16
            y: Theme.space16
            width: parent.width - 2 * Theme.space16
            spacing: Theme.space12

            DisplayText {
                text: (page.row >= 0 ? "Editar " : "Nueva ")
                      + (page.mode === "app" ? "aplicación" : "página web")
                size: Theme.sizeSecondary
                color: Theme.textPrimary
            }

            FormField {
                id: nameField

                objectName: "entryName"
                width: form.width
                label: "Nombre"
                placeholder: page.mode === "app" ? "Visual Studio Code" : "Documentación"
                hint: "Lo que se escribe tras «abre»."
            }

            Item {
                width: form.width
                height: targetField.height

                FormField {
                    id: targetField

                    objectName: "entryTarget"
                    width: parent.width - (browse.visible ? browse.width + Theme.space8 : 0)
                    label: page.mode === "app" ? "Programa" : "Dirección"
                    placeholder: page.mode === "app" ? "C:/Programas/editor.exe o un nombre del PATH"
                                                     : "https://example.com"
                    mono: true
                    hint: page.section ? page.section.warning(page.mode, text) : ""
                }

                TextButton {
                    id: browse

                    visible: page.mode === "app"
                    y: targetField.children[1].y
                    anchors.right: parent.right
                    text: "Examinar…"
                    onClicked: picker.open()
                }
            }

            FormField {
                id: argsField

                visible: page.mode === "app"
                width: form.width
                label: "Argumentos (opcional, uno por línea)"
                multiline: true
                mono: true
            }

            FormField {
                id: aliasesField

                width: form.width
                label: "Otros nombres (opcional, uno por línea)"
                placeholder: page.mode === "app" ? "code\nel editor" : "docs"
                multiline: true
            }

            Notice {
                objectName: "entryError"
                width: form.width
                text: page.error
            }

            Row {
                anchors.right: parent.right
                spacing: Theme.space8

                TextButton {
                    text: "Cancelar"
                    onClicked: page.mode = ""
                }

                TextButton {
                    objectName: "entryAccept"
                    text: "Aceptar"
                    primary: true
                    onClicked: page.accept()
                }
            }
        }
    }

    FileDialog {
        id: picker

        title: "Elegir programa"
        nameFilters: ["Programas y accesos directos (*.exe *.lnk *.bat *.cmd)", "Todos (*)"]
        onAccepted: {
            var path = decodeURIComponent(selectedFile.toString().replace(/^file:\/{2,3}/, ""))
            targetField.setText(path)
        }
    }

    // --- Lista -------------------------------------------------------------------------------

    Text {
        visible: page.section !== null && page.section.items.length === 0 && page.mode === ""
        text: "Todavía no ha añadido ninguna aplicación ni página."
        color: Theme.textMuted
        font.family: Theme.fontBody
        font.pixelSize: Theme.sizeSecondary
    }

    Repeater {
        model: page.section ? page.section.items.length : 0

        Rectangle {
            id: card

            required property int index
            // Al eliminar, la fila puede evaluarse una vez más antes de desaparecer.
            readonly property var item: page.section.items[index]
                                        || ({ kind: "app", name: "", target: "", aliases: "" })

            objectName: "entry-" + index
            width: page.width
            height: Math.max(48, info.implicitHeight + 2 * Theme.space12)
            radius: Theme.radiusPanel
            color: Theme.bgPanel
            border.width: 1
            border.color: Theme.lineSoft

            Image {
                id: kindIcon

                x: Theme.space16
                width: 18
                height: 18
                sourceSize.width: 36
                sourceSize.height: 36
                source: Theme.icon(card.item.kind === "app" ? "aplicacion" : "pagina")
                anchors.verticalCenter: parent.verticalCenter
            }

            Column {
                id: info

                anchors.left: kindIcon.right
                anchors.leftMargin: Theme.space12
                anchors.right: rowActions.left
                anchors.rightMargin: Theme.space12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2

                Text {
                    width: parent.width
                    text: card.item.name
                          + (card.item.aliases.length > 0
                             ? "  ·  " + card.item.aliases.split("\n").join(", ") : "")
                    color: Theme.textPrimary
                    font.family: Theme.fontBody
                    font.pixelSize: Theme.sizeSecondary
                    elide: Text.ElideRight
                }

                Text {
                    width: parent.width
                    text: card.item.target
                    color: Theme.textMuted
                    font.family: Theme.fontMono
                    font.pixelSize: Theme.sizeLabel
                    elide: Text.ElideMiddle
                }
            }

            Row {
                id: rowActions

                anchors.right: parent.right
                anchors.rightMargin: Theme.space16
                anchors.verticalCenter: parent.verticalCenter
                spacing: Theme.space8
                enabled: page.editable

                TextButton {
                    text: "Editar"
                    onClicked: page.openForm(card.item.kind, card.index)
                }

                TextButton {
                    text: "Eliminar"
                    danger: true
                    onClicked: page.section.remove(card.index)
                }
            }
        }
    }
}
