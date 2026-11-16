// Panel de diálogo (Interfaz, sección 7; hud.md, sección 3): la pregunta en curso, el elemento
// sobre el que se pregunta, las respuestas admitidas y una barra fina que se vacía con el
// tiempo de espera. Se superpone al panel activo mientras dura la pregunta.
// Lee el modelo `dialogue` (`ui/view_models.py`, DialogueModel).
import QtQuick
import ".."

Rectangle {
    id: card

    property bool flat: false            // dentro del HUD: más compacta
    readonly property bool shown: dialogue.active

    implicitHeight: column.implicitHeight + 2 * Theme.space16
    visible: opacity > 0
    opacity: shown ? 1 : 0
    color: Theme.bgPanel
    radius: Theme.radiusPanel
    border.width: 1
    border.color: Theme.statusPending

    Behavior on opacity {
        NumberAnimation { duration: ui.reduceMotion ? 0 : Theme.motionState }
    }

    // Lo que queda del tiempo de espera, de 1 a 0. Cada pregunta (`serial`) la reinicia.
    property real remaining: 1

    NumberAnimation {
        id: countdown

        target: card
        property: "remaining"
        from: 1
        to: 0
        duration: Math.max(1, dialogue.timeoutSeconds * 1000)
    }

    function restart() {
        countdown.stop()
        card.remaining = 1
        if (dialogue.active)
            countdown.start()
    }

    Connections {
        target: dialogue

        function onChanged() {
            card.restart()
        }
    }

    Component.onCompleted: restart()

    Column {
        id: column

        x: Theme.space16
        y: Theme.space16
        width: card.width - 2 * Theme.space16
        spacing: Theme.space12

        Text {
            objectName: "dialogQuestion"
            width: parent.width
            text: dialogue.question
            color: Theme.textPrimary
            font.family: Theme.fontBody
            font.pixelSize: card.flat ? Theme.sizeText : Theme.sizeTitle
            wrapMode: Text.WordWrap
        }

        Text {
            width: parent.width
            visible: text.length > 0
            text: dialogue.subject
            color: Theme.textMuted
            font.family: Theme.fontBody
            font.pixelSize: Theme.sizeSecondary
            elide: Text.ElideMiddle
        }

        Flow {
            width: parent.width
            spacing: Theme.space8

            Repeater {
                model: dialogue.hints

                Badge {
                    required property string modelData

                    text: modelData
                    tone: Theme.statusPending
                }
            }
        }

        // Barra del tiempo de espera.
        Item {
            width: parent.width
            height: 2

            Rectangle {
                anchors.fill: parent
                color: Theme.lineSoft
            }

            Rectangle {
                width: parent.width * card.remaining
                height: parent.height
                color: Theme.statusPending
            }
        }
    }
}
