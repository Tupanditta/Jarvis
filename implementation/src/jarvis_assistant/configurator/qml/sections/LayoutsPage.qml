// Apartado Plantillas: la de fábrica primero; crear abre el editor a pantalla completa.
import QtQuick
import "../../../ui/qml"
import "../../../ui/qml/components"
import "../controls"

Column {
    id: page

    property QtObject section
    readonly property bool editable: section !== null && section.locked.length === 0
    property string removing: ""      // id de la plantilla que se pide eliminar

    spacing: Theme.space16

    PageHeader {
        width: page.width
        title: "Plantillas de pantalla"
        detail: "Dónde van las ventanas, el selector de ventanas y la caja de texto al abrir"
                + " sesión. Cada perfil usa una."
        action: "Nueva plantilla"
        locked: page.section ? page.section.locked : ""
        onTriggered: page.section.create()
    }

    Repeater {
        model: page.section ? page.section.items.length : 0

        Rectangle {
            id: card

            required property int index
            // Al eliminar, la fila puede evaluarse una vez más antes de desaparecer.
            readonly property var item: page.section.items[index]
                                        || ({ id: "", name: "", factory: false, usedBy: "" })
            readonly property bool confirming: page.removing === item.id

            objectName: "layout-" + item.id
            width: page.width
            height: body.implicitHeight + 2 * Theme.space12
            radius: Theme.radiusPanel
            color: Theme.bgPanel
            border.width: 1
            border.color: confirming ? Theme.alpha(Theme.statusError, 0.6) : Theme.lineSoft

            Column {
                id: body

                x: Theme.space16
                y: Theme.space12
                width: parent.width - 2 * Theme.space16
                spacing: Theme.space8

                Item {
                    width: body.width
                    height: Math.max(names.implicitHeight, actions.implicitHeight)

                    Column {
                        id: names

                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2

                        Text {
                            text: card.item.name
                            color: Theme.textPrimary
                            font.family: Theme.fontBody
                            font.pixelSize: Theme.sizeText
                        }

                        Text {
                            text: (card.item.factory ? "De fábrica: no se edita ni se elimina. " : "")
                                  + (card.item.usedBy.length > 0 ? "La usa: " + card.item.usedBy
                                                                 : "Ningún perfil la usa.")
                            color: Theme.textMuted
                            font.family: Theme.fontBody
                            font.pixelSize: Theme.sizeLabel
                        }
                    }

                    Row {
                        id: actions

                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: Theme.space8
                        enabled: page.editable

                        TextButton {
                            objectName: "edit"
                            visible: !card.item.factory
                            text: "Editar"
                            onClicked: page.section.edit(card.item.id)
                        }

                        TextButton {
                            objectName: "duplicate"
                            text: "Duplicar"
                            onClicked: page.section.duplicate(card.item.id)
                        }

                        TextButton {
                            objectName: "remove"
                            visible: !card.item.factory
                            text: "Eliminar"
                            danger: true
                            onClicked: {
                                if (card.item.usedBy.length > 0)
                                    page.removing = card.item.id
                                else
                                    page.section.remove(card.item.id)
                            }
                        }
                    }
                }

                // Eliminar una plantilla en uso: sus perfiles pasan a la de fábrica.
                Row {
                    visible: card.confirming
                    spacing: Theme.space8

                    Text {
                        width: body.width - confirmButtons.width - Theme.space8
                        text: "La usa " + card.item.usedBy + ". Si la elimina, pasará a usar la"
                              + " de fábrica."
                        color: Theme.textSecondary
                        font.family: Theme.fontBody
                        font.pixelSize: Theme.sizeSecondary
                        wrapMode: Text.WordWrap
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Row {
                        id: confirmButtons

                        spacing: Theme.space8

                        TextButton {
                            text: "Cancelar"
                            onClicked: page.removing = ""
                        }

                        TextButton {
                            objectName: "confirmRemove"
                            text: "Eliminar"
                            danger: true
                            onClicked: {
                                page.removing = ""
                                page.section.remove(card.item.id)
                            }
                        }
                    }
                }
            }
        }
    }
}
