// Apartado Perfiles: una tarjeta por perfil con su nombre, el nombre del usuario y la
// plantilla que usa. Siempre queda al menos uno.
import QtQuick
import "../../../ui/qml"
import "../../../ui/qml/components"
import "../controls"

Column {
    id: page

    property QtObject section
    readonly property bool editable: section !== null && section.locked.length === 0

    spacing: Theme.space16

    PageHeader {
        width: page.width
        title: "Perfiles"
        detail: "El perfil se elige en la pantalla dormida, encima de la caja de texto, antes de"
                + " escribir «Hey Jarvis». Con un solo perfil no se muestra el selector."
        action: "Nuevo perfil"
        locked: page.section ? page.section.locked : ""
        onTriggered: page.section.add()
    }

    Repeater {
        model: page.section ? page.section.items.length : 0

        Rectangle {
            id: card

            required property int index
            // Al eliminar, la fila puede evaluarse una vez más antes de desaparecer.
            readonly property var item: page.section.items[index]
                                        || ({ id: "", name: "", userName: "", layout: "" })

            objectName: "profile-" + item.id
            width: page.width
            height: body.implicitHeight + 2 * Theme.space16
            radius: Theme.radiusPanel
            color: Theme.bgPanel
            border.width: 1
            border.color: Theme.lineSoft

            Column {
                id: body

                x: Theme.space16
                y: Theme.space16
                width: parent.width - 2 * Theme.space16
                spacing: Theme.space12
                enabled: page.editable

                Row {
                    width: body.width
                    spacing: Theme.space16

                    FormField {
                        objectName: "profileName"
                        width: (body.width - Theme.space16) / 2
                        label: "Nombre del perfil"
                        placeholder: "Trabajo, Casa…"
                        value: card.item.name
                        onEdited: (text) => page.section.setName(card.index, text)
                    }

                    FormField {
                        objectName: "profileUser"
                        width: (body.width - Theme.space16) / 2
                        label: "Nombre del usuario"
                        placeholder: "Opcional"
                        hint: "El que dice el asistente al presentarse («preséntate»)."
                        value: card.item.userName
                        onEdited: (text) => page.section.setUserName(card.index, text)
                    }
                }

                Column {
                    width: body.width
                    spacing: Theme.space4

                    Text {
                        text: "Plantilla de pantalla"
                        color: Theme.textSecondary
                        font.family: Theme.fontBody
                        font.pixelSize: Theme.sizeLabel
                    }

                    Flow {
                        width: body.width
                        spacing: Theme.space8

                        Repeater {
                            model: page.section ? page.section.layouts : []

                            Chip {
                                required property var modelData
                                text: modelData.name
                                selected: card.item.layout === modelData.id
                                onClicked: page.section.setLayout(card.index, modelData.id)
                            }
                        }
                    }
                }

                Row {
                    anchors.right: parent.right
                    spacing: Theme.space8

                    TextButton {
                        text: "Duplicar"
                        onClicked: page.section.duplicate(card.index)
                    }

                    TextButton {
                        objectName: "removeProfile"
                        text: "Eliminar"
                        danger: true
                        enabled: page.section.items.length > 1
                        onClicked: page.section.remove(card.index)
                    }
                }
            }
        }
    }
}
