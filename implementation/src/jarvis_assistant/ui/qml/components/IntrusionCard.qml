// Aviso crítico de intrusión: al entrar en un perfil protegido en el que alguien falló la
// contraseña tres veces. Sale con la frase de alerta, tras la de apertura, por encima de todo
// lo demás, y sigue hasta pulsar «Entendido». Si la sesión se cierra sin confirmarlo, vuelve a
// salir en la próxima.
// Lee el modelo `access` (`ui/view_models.py`, AccessModel).
import QtQuick
import ".."

Rectangle {
    id: card

    readonly property bool shown: access.alertsOpen

    objectName: "intrusionCard"
    implicitHeight: column.implicitHeight + 2 * Theme.space24
    visible: opacity > 0
    opacity: shown ? 1 : 0
    color: Theme.bgWindow
    radius: Theme.radiusPanel
    border.width: 2
    border.color: Theme.statusError

    Behavior on opacity {
        NumberAnimation { duration: ui.reduceMotion ? 0 : Theme.motionState }
    }

    // Halo rojo que late mientras el aviso está sin confirmar.
    Rectangle {
        anchors.fill: parent
        anchors.margins: -6
        radius: card.radius + 6
        color: "transparent"
        border.width: 6
        border.color: Theme.alpha(Theme.statusError, 0.25)
        z: -1

        SequentialAnimation on opacity {
            running: card.visible && !ui.reduceMotion
            loops: Animation.Infinite
            NumberAnimation { from: 0.2; to: 1; duration: 700; easing.type: Easing.InOutSine }
            NumberAnimation { from: 1; to: 0.2; duration: 700; easing.type: Easing.InOutSine }
        }
    }

    Column {
        id: column

        x: Theme.space24
        y: Theme.space24
        width: card.width - 2 * Theme.space24
        spacing: Theme.space16

        DisplayText {
            text: "Alerta de seguridad"
            size: Theme.sizeState
            color: Theme.statusError
        }

        Text {
            width: parent.width
            text: access.alerts.length === 1
                  ? "Alguien intentó acceder a este entorno sin autorización."
                  : "Ha habido " + access.alerts.length
                    + " intentos de acceso no autorizado a este entorno desde su última visita."
            color: Theme.textPrimary
            font.family: Theme.fontBody
            font.pixelSize: Theme.sizeText
            wrapMode: Text.WordWrap
        }

        Column {
            width: parent.width
            spacing: Theme.space8

            Repeater {
                model: access.alerts

                Rectangle {
                    required property var modelData

                    width: parent.width
                    height: row.implicitHeight + 2 * Theme.space8
                    radius: Theme.radiusCard
                    color: Theme.alpha(Theme.statusError, 0.08)
                    border.width: 1
                    border.color: Theme.alpha(Theme.statusError, 0.35)

                    Row {
                        id: row

                        x: Theme.space12
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: Theme.space16

                        Text {
                            text: modelData.date + "  " + modelData.time
                            color: Theme.textPrimary
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.sizeSecondary
                        }

                        Text {
                            text: modelData.attempts + " intentos fallidos"
                            color: Theme.textSecondary
                            font.family: Theme.fontBody
                            font.pixelSize: Theme.sizeSecondary
                        }

                        Text {
                            text: modelData.origin
                            color: Theme.textMuted
                            font.family: Theme.fontBody
                            font.pixelSize: Theme.sizeSecondary
                        }
                    }
                }
            }
        }

        Rectangle {
            objectName: "intrusionAcknowledge"
            anchors.right: parent.right
            width: label.implicitWidth + 2 * Theme.space24
            height: 36
            radius: height / 2
            color: hover.hovered ? Theme.alpha(Theme.statusError, 0.25)
                                 : Theme.alpha(Theme.statusError, 0.12)
            border.width: 1
            border.color: Theme.statusError

            DisplayText {
                id: label

                anchors.centerIn: parent
                text: "Entendido"
                size: Theme.sizeSecondary
                color: Theme.textPrimary
            }

            HoverHandler {
                id: hover
                cursorShape: Qt.PointingHandCursor
            }

            TapHandler {
                onTapped: access.acknowledge()
            }
        }
    }
}
