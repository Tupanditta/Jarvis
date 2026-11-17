// Apartado Perfiles: una tarjeta por perfil con su nombre, el nombre del usuario, la
// plantilla que usa y su contraseña. Siempre queda al menos uno. Un perfil protegido aparece
// bloqueado: se desbloquea con su contraseña y queda editable hasta cerrar la ventana. Los
// perfiles solo los elimina el Acedor, desde su sesión. Arriba, la tarjeta del Acedor.
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
                + " escribir «Hey Jarvis». Con un solo perfil no se muestra el selector. Solo el"
                + " Acedor elimina perfiles, desde su sesión."
        action: "Nuevo perfil"
        locked: page.section ? page.section.locked : ""
        onTriggered: page.section.add()
    }

    // El Acedor: máxima autoridad. Se activa una vez poniéndole contraseña; después solo se le
    // cambia dando la actual. Se aplica al guardar.
    Rectangle {
        id: adminCard

        property bool editing: false

        objectName: "adminCard"
        width: page.width
        height: adminBody.implicitHeight + 2 * Theme.space16
        visible: page.section !== null && page.section.canProtect
        radius: Theme.radiusPanel
        color: Theme.bgPanel
        border.width: 1
        border.color: Theme.primaryDim

        Column {
            id: adminBody

            x: Theme.space16
            y: Theme.space16
            width: parent.width - 2 * Theme.space16
            spacing: Theme.space8
            enabled: page.editable

            Row {
                spacing: Theme.space8

                Image {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 16
                    height: 16
                    sourceSize: Qt.size(32, 32)
                    source: Theme.icon("candado")
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Acedor"
                    color: Theme.textPrimary
                    font.family: Theme.fontBody
                    font.pixelSize: Theme.sizeText
                }
            }

            Text {
                width: parent.width
                text: page.section && page.section.adminActive
                      ? "Activado. Desde su sesión da y quita permisos, ve las contraseñas y"
                        + " elimina perfiles."
                      : "Sin activar. Póngale contraseña para administrar permisos, ver las"
                        + " contraseñas y eliminar perfiles. Guárdela bien: si la olvida, hay"
                        + " que reiniciarlo y las contraseñas dejan de poder verse."
                color: Theme.textSecondary
                font.family: Theme.fontBody
                font.pixelSize: Theme.sizeSecondary
                wrapMode: Text.WordWrap
            }

            TextButton {
                objectName: "adminPasswordButton"
                visible: !adminCard.editing
                text: page.section && page.section.adminActive ? "Cambiar contraseña"
                                                               : "Activar el Acedor"
                primary: !(page.section && page.section.adminActive)
                onClicked: {
                    adminMessage.text = ""
                    adminCard.editing = true
                }
            }

            Row {
                spacing: Theme.space8
                visible: adminCard.editing

                SecretField {
                    id: adminCurrent

                    objectName: "adminCurrent"
                    visible: page.section !== null && page.section.adminActive
                    hidden: true
                    width: 160
                    placeholder: "Contraseña actual"
                }

                SecretField {
                    id: adminNew

                    objectName: "adminNew"
                    width: 160
                    placeholder: "Contraseña nueva"
                    onAccepted: adminRepeated.focusInput()
                }

                SecretField {
                    id: adminRepeated

                    objectName: "adminRepeated"
                    width: 160
                    placeholder: "Repítala"
                    onAccepted: adminAccept.clicked()
                }

                TextButton {
                    id: adminAccept

                    objectName: "adminAccept"
                    text: "Aceptar"
                    primary: true
                    onClicked: {
                        const problem = page.section.adminActive
                            ? page.section.changeAdminPassword(
                                  adminCurrent.text, adminNew.text, adminRepeated.text)
                            : page.section.activateAdmin(adminNew.text, adminRepeated.text)
                        adminCurrent.clear()
                        adminNew.clear()
                        adminRepeated.clear()
                        adminMessage.text = problem
                        if (problem.length === 0)
                            adminCard.editing = false
                    }
                }

                TextButton {
                    text: "Cancelar"
                    onClicked: {
                        adminCurrent.clear()
                        adminNew.clear()
                        adminRepeated.clear()
                        adminMessage.text = ""
                        adminCard.editing = false
                    }
                }
            }

            Text {
                id: adminMessage

                objectName: "adminMessage"
                visible: text.length > 0
                color: Theme.statusError
                font.family: Theme.fontBody
                font.pixelSize: Theme.sizeSecondary
            }
        }
    }

    Repeater {
        model: page.section ? page.section.items.length : 0

        Rectangle {
            id: card

            required property int index
            // Al eliminar, la fila puede evaluarse una vez más antes de desaparecer.
            readonly property var item: page.section.items[index]
                                        || ({ id: "", name: "", userName: "", layout: "",
                                              protected: false, unlocked: true })
            property bool settingPassword: false

            objectName: "profile-" + item.id
            width: page.width
            height: lockBar.height + body.implicitHeight + 2 * Theme.space16
                    + (lockBar.visible ? Theme.space12 : 0)
            radius: Theme.radiusPanel
            color: Theme.bgPanel
            border.width: 1
            border.color: card.item.protected ? Theme.lineStrong : Theme.lineSoft

            // Perfil protegido y bloqueado: la contraseña, sin mostrar nada de lo que se
            // escribe. El tercer fallo seguido registra un aviso de intrusión.
            Column {
                id: lockBar

                objectName: "profileLock"
                x: Theme.space16
                y: Theme.space16
                width: parent.width - 2 * Theme.space16
                height: visible ? implicitHeight : 0
                visible: card.item.protected && !card.item.unlocked
                spacing: Theme.space8

                Row {
                    width: lockBar.width
                    spacing: Theme.space8

                    Image {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 16
                        height: 16
                        sourceSize: Qt.size(32, 32)
                        source: Theme.icon("candado")
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Perfil protegido. Introduzca su contraseña para editarlo."
                        color: Theme.textSecondary
                        font.family: Theme.fontBody
                        font.pixelSize: Theme.sizeSecondary
                    }
                }

                Row {
                    spacing: Theme.space8

                    SecretField {
                        id: unlockField

                        objectName: "unlockField"
                        hidden: true
                        width: 240
                        placeholder: "Contraseña"
                        onAccepted: unlockButton.clicked()
                    }

                    TextButton {
                        id: unlockButton

                        objectName: "unlockProfile"
                        text: "Desbloquear"
                        primary: true
                        onClicked: {
                            const password = unlockField.text
                            unlockField.clear()
                            if (password.length === 0)
                                return
                            const outcome = page.section.unlock(card.index, password)
                            unlockMessage.text = outcome === "concedido"
                                ? "" : "Clave incorrecta. Acceso denegado."
                        }
                    }
                }

                Text {
                    id: unlockMessage

                    objectName: "unlockMessage"
                    visible: text.length > 0
                    color: Theme.statusError
                    font.family: Theme.fontBody
                    font.pixelSize: Theme.sizeSecondary
                }
            }

            Column {
                id: body

                x: Theme.space16
                y: lockBar.visible ? lockBar.y + lockBar.height + Theme.space12 : Theme.space16
                width: parent.width - 2 * Theme.space16
                spacing: Theme.space12
                enabled: page.editable && card.item.unlocked
                opacity: card.item.unlocked ? 1 : 0.5

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

                // Contraseña: se aplica al guardar.
                Column {
                    objectName: "profilePassword"
                    width: body.width
                    spacing: Theme.space8
                    visible: page.section.canProtect

                    Text {
                        text: "Contraseña"
                        color: Theme.textSecondary
                        font.family: Theme.fontBody
                        font.pixelSize: Theme.sizeLabel
                    }

                    Row {
                        spacing: Theme.space8
                        visible: !card.settingPassword

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: card.item.protected
                                  ? "Protegido: pide contraseña al iniciar sesión y al editarlo."
                                  : "Sin contraseña."
                            color: Theme.textPrimary
                            font.family: Theme.fontBody
                            font.pixelSize: Theme.sizeSecondary
                        }

                        TextButton {
                            objectName: "setPassword"
                            text: card.item.protected ? "Cambiar contraseña" : "Poner contraseña"
                            onClicked: {
                                passwordMessage.text = ""
                                card.settingPassword = true
                                newPassword.focusInput()
                            }
                        }

                        TextButton {
                            objectName: "clearPassword"
                            visible: card.item.protected
                            text: "Quitar contraseña"
                            danger: true
                            onClicked: page.section.clearPassword(card.index)
                        }
                    }

                    Row {
                        spacing: Theme.space8
                        visible: card.settingPassword

                        SecretField {
                            id: newPassword

                            objectName: "newPassword"
                            width: 200
                            placeholder: "Contraseña nueva"
                            onAccepted: repeatedPassword.focusInput()
                        }

                        SecretField {
                            id: repeatedPassword

                            objectName: "repeatedPassword"
                            width: 200
                            placeholder: "Repítala"
                            onAccepted: acceptPassword.clicked()
                        }

                        TextButton {
                            id: acceptPassword

                            objectName: "acceptPassword"
                            text: "Aceptar"
                            primary: true
                            onClicked: {
                                const problem = page.section.setPassword(
                                    card.index, newPassword.text, repeatedPassword.text)
                                newPassword.clear()
                                repeatedPassword.clear()
                                passwordMessage.text = problem
                                if (problem.length === 0)
                                    card.settingPassword = false
                            }
                        }

                        TextButton {
                            text: "Cancelar"
                            onClicked: {
                                newPassword.clear()
                                repeatedPassword.clear()
                                passwordMessage.text = ""
                                card.settingPassword = false
                            }
                        }
                    }

                    Text {
                        id: passwordMessage

                        objectName: "passwordMessage"
                        visible: text.length > 0
                        color: Theme.statusError
                        font.family: Theme.fontBody
                        font.pixelSize: Theme.sizeSecondary
                    }
                }

                Row {
                    anchors.right: parent.right
                    spacing: Theme.space8

                    TextButton {
                        text: "Duplicar"
                        onClicked: page.section.duplicate(card.index)
                    }
                }
            }
        }
    }
}
