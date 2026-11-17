// Caja de la contraseña de un perfil protegido, en el centro de la pantalla dormida. Aparece
// tras «Hey Jarvis» (o «Abrir sesión») en un perfil con contraseña (`access.gateOpen`).
//
// No muestra nada de lo que se escribe, ni puntos: cada tecla solo hace brillar el borde un
// instante. Enter envía la clave y vacía la caja; Esc la cierra. Con la clave incorrecta la
// caja se sacude y se pone roja; nunca dice cuántos intentos quedan.
// Lee el modelo `access` (`ui/view_models.py`, AccessModel).
import QtQuick
import ".."
import "outline.js" as Outline

Item {
    id: gate

    readonly property bool shown: access.gateOpen || lingering.running
    property real pulse: 0      // brillo de una tecla, de 1 a 0
    property real alarm: 0      // rojo de una clave incorrecta, de 1 a 0
    property real shake: 0      // desplazamiento de la sacudida, en píxeles

    signal closed()

    visible: opacity > 0
    opacity: shown ? 1 : 0

    Behavior on opacity {
        NumberAnimation { duration: ui.reduceMotion ? 0 : Theme.motionState }
    }

    function focusInput() {
        field.forceActiveFocus()
    }

    onShownChanged: {
        if (shown) {
            field.text = ""
            message.text = ""
            field.forceActiveFocus()
        } else {
            field.text = ""
            gate.closed()
        }
    }

    Connections {
        target: access

        function onDenied() {
            message.text = "Clave incorrecta. Acceso denegado."
            denial.restart()
            // Tras el tercer fallo la caja se cierra: antes se deja ver la sacudida.
            lingering.restart()
        }
    }

    // Mantiene la caja visible un instante tras cerrarse con una clave incorrecta.
    Timer {
        id: lingering

        interval: 900
    }

    ParallelAnimation {
        id: denial

        NumberAnimation {
            target: gate
            property: "alarm"
            from: 1
            to: 0
            duration: ui.reduceMotion ? 0 : 1200
            easing.type: Easing.InQuad
        }

        SequentialAnimation {
            NumberAnimation { target: gate; property: "shake"; to: 14; duration: ui.reduceMotion ? 0 : 50 }
            NumberAnimation { target: gate; property: "shake"; to: -12; duration: ui.reduceMotion ? 0 : 70 }
            NumberAnimation { target: gate; property: "shake"; to: 9; duration: ui.reduceMotion ? 0 : 70 }
            NumberAnimation { target: gate; property: "shake"; to: -6; duration: ui.reduceMotion ? 0 : 70 }
            NumberAnimation { target: gate; property: "shake"; to: 0; duration: ui.reduceMotion ? 0 : 60 }
        }
    }

    NumberAnimation {
        id: keyPulse

        target: gate
        property: "pulse"
        from: 1
        to: 0
        duration: ui.reduceMotion ? 0 : 320
        easing.type: Easing.OutCubic
    }

    // Velo: la caja manda mientras está abierta.
    Rectangle {
        anchors.fill: parent
        color: Theme.alpha(Theme.bgBase, 0.72)

        TapHandler {
            onTapped: field.forceActiveFocus()
        }
    }

    Rectangle {
        id: card

        objectName: "accessGate"
        width: Math.min(460, gate.width - 2 * Theme.space24)
        height: column.implicitHeight + 2 * Theme.space24
        anchors.centerIn: parent
        anchors.horizontalCenterOffset: gate.shake
        radius: Theme.radiusPanel
        color: Theme.bgWindow
        border.width: 1
        border.color: Theme.mix(Theme.lineStrong, Theme.statusError, gate.alarm)

        Column {
            id: column

            x: Theme.space24
            y: Theme.space24
            width: card.width - 2 * Theme.space24
            spacing: Theme.space16

            Row {
                spacing: Theme.space8

                Image {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 18
                    height: 18
                    sourceSize: Qt.size(36, 36)
                    source: Theme.icon("candado")
                }

                DisplayText {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Acceso restringido"
                    size: Theme.sizeTitle
                    color: Theme.mix(Theme.primary, Theme.statusError, gate.alarm)
                }
            }

            Text {
                width: parent.width
                text: "Entorno: " + access.profileName
                color: Theme.textSecondary
                font.family: Theme.fontBody
                font.pixelSize: Theme.sizeText
                elide: Text.ElideRight
            }

            // La caja: sin caracteres, sin cursor. El borde brilla con cada tecla.
            Rectangle {
                id: box

                readonly property var outline: Outline.rounded(height / 2)

                width: parent.width
                height: Theme.inputHeight
                radius: height / 2
                color: Theme.bgPanel
                border.width: 1
                border.color: Theme.mix(
                    Theme.mix(field.activeFocus ? Theme.lineStrong : Theme.lineSoft,
                              Theme.primaryBright, gate.pulse),
                    Theme.statusError, gate.alarm)

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 1
                    radius: height / 2
                    color: Theme.alpha(Theme.primary, 0.12 * gate.pulse)
                }

                NeonTrace {
                    anchors.fill: parent
                    path: Outline.path(box.width, box.height, box.outline, 0.5)
                    length: Outline.length(box.width, box.height, box.outline, 0.5)
                    count: 2
                    speed: Theme.neonSpeed * (0.6 + gate.pulse)
                    strength: 0.45 + 0.5 * gate.pulse
                    running: gate.visible
                }

                TextInput {
                    id: field

                    objectName: "accessInput"
                    anchors.fill: parent
                    anchors.leftMargin: Theme.space16
                    anchors.rightMargin: Theme.space16
                    verticalAlignment: TextInput.AlignVCenter
                    echoMode: TextInput.NoEcho
                    cursorVisible: false
                    cursorDelegate: Item {}
                    color: "transparent"
                    selectByMouse: false
                    inputMethodHints: Qt.ImhSensitiveData | Qt.ImhNoPredictiveText
                        | Qt.ImhNoAutoUppercase
                    enabled: access.gateOpen
                    font.family: Theme.fontBody
                    font.pixelSize: Theme.sizeText

                    onTextEdited: keyPulse.restart()
                    onAccepted: {
                        const password = text
                        text = ""
                        access.unlock(password)
                    }
                    Keys.onEscapePressed: (event) => {
                        text = ""
                        access.cancel()
                        event.accepted = true
                    }
                }

                Text {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.space16
                    verticalAlignment: Text.AlignVCenter
                    visible: field.length === 0 && gate.pulse === 0
                    text: "Introduzca la clave de acceso"
                    color: Theme.textMuted
                    font.family: Theme.fontBody
                    font.pixelSize: Theme.sizeText
                }
            }

            Text {
                id: message

                objectName: "accessMessage"
                width: parent.width
                visible: text.length > 0
                color: Theme.statusError
                font.family: Theme.fontBody
                font.pixelSize: Theme.sizeSecondary
                wrapMode: Text.WordWrap
            }

            Text {
                width: parent.width
                text: "Enter para entrar · Esc para cancelar"
                color: Theme.textMuted
                font.family: Theme.fontBody
                font.pixelSize: Theme.sizeLabel
                horizontalAlignment: Text.AlignRight
            }
        }
    }
}
