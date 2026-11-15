// Caja de texto: la única entrada de órdenes (entrada-texto.md). Una línea; Enter envía el
// texto tal cual y vacía la caja; el foco se queda en ella. No interpreta el texto.
import QtQuick
import ".."

Rectangle {
    id: box

    property alias text: input.text
    readonly property bool inputFocus: input.activeFocus
    signal pressed()

    function focusInput() {
        input.forceActiveFocus()
    }

    implicitHeight: 36
    radius: Theme.radiusCard
    color: Theme.bgPanel
    border.width: 1
    border.color: input.activeFocus ? Theme.lineStrong : Theme.lineSoft

    TextInput {
        id: input

        objectName: "commandInput"
        anchors.fill: parent
        anchors.leftMargin: Theme.space12
        anchors.rightMargin: Theme.space12
        verticalAlignment: TextInput.AlignVCenter
        color: Theme.textPrimary
        selectionColor: Theme.primaryDim
        selectedTextColor: Theme.textPrimary
        font.family: Theme.fontBody
        font.pixelSize: Theme.sizeText
        clip: true
        selectByMouse: true

        onAccepted: {
            assistant.submit(text)
            clear()
        }
        // Solo las ediciones del usuario: cambiar el texto por código no cuenta como teclear.
        onTextEdited: assistant.typing()
    }

    Text {
        anchors.fill: input
        verticalAlignment: Text.AlignVCenter
        text: assistant.placeholder
        visible: input.text.length === 0 && input.preeditText.length === 0
        color: Theme.textMuted
        font: input.font
        elide: Text.ElideRight
    }

    // Avisa del clic antes de que la caja lo reciba (el HUD necesita aceptar el foco).
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.IBeamCursor
        onPressed: (mouse) => {
            box.pressed()
            input.forceActiveFocus()
            mouse.accepted = false
        }
    }
}
