// Caja de texto: la única entrada de órdenes (entrada-texto.md). Una línea; Enter envía el
// texto tal cual y vacía la caja; el foco se queda en ella. No interpreta el texto.
//
// Es una cápsula con una marca de entrada a la izquierda. Dos trazos de neón recorren su
// borde: despacio y tenues en dormido y en reposo, vivos con la sesión despierta y más
// rápidos y brillantes mientras el asistente habla.
import QtQuick
import ".."
import "outline.js" as Outline

Rectangle {
    id: box

    property alias text: input.text
    readonly property bool inputFocus: input.activeFocus
    signal pressed()

    function focusInput() {
        input.forceActiveFocus()
    }

    readonly property bool asleep: assistant.activity === "dormido"
    readonly property bool resting: assistant.activity === "reposo"
    readonly property var outline: Outline.rounded(height / 2)

    implicitHeight: Theme.inputHeight
    radius: height / 2
    color: Theme.bgPanel
    border.width: 1
    border.color: input.activeFocus ? Theme.lineStrong : Theme.lineSoft

    Behavior on border.color {
        ColorAnimation { duration: Theme.motionWindow }
    }

    // Brillo interior con el foco: la caja se enciende al ir a escribir.
    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: height / 2
        opacity: input.activeFocus ? 1 : 0

        gradient: Gradient {
            GradientStop { position: 0; color: Theme.alpha(Theme.primary, 0.0) }
            GradientStop { position: 1; color: Theme.alpha(Theme.primary, 0.07) }
        }

        Behavior on opacity {
            NumberAnimation { duration: Theme.motionWindow }
        }
    }

    NeonTrace {
        anchors.fill: parent
        path: Outline.path(box.width, box.height, box.outline, 0.5)
        length: Outline.length(box.width, box.height, box.outline, 0.5)
        count: 2
        speed: Theme.neonSpeed * (box.asleep ? 0.3 : box.resting ? 0.5 : 1)
        strength: (box.asleep ? 0.3 : box.resting ? 0.45 : 0.75) + (input.activeFocus ? 0.25 : 0)
        running: box.visible
    }

    // Marca de entrada.
    Text {
        id: prompt

        x: Theme.space16
        text: "›"
        color: input.activeFocus ? Theme.primary : Theme.primaryDim
        font.family: Theme.fontMono
        font.pixelSize: Theme.sizeTitle
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: -1

        Behavior on color {
            ColorAnimation { duration: Theme.motionWindow }
        }
    }

    TextInput {
        id: input

        objectName: "commandInput"
        anchors.fill: parent
        anchors.leftMargin: prompt.x + prompt.width + Theme.space8
        anchors.rightMargin: Theme.space16
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

    // Una ventana propone una orden (un ejemplo de la ayuda): se escribe, sin enviarla.
    Connections {
        target: assistant

        function onSuggested(text) {
            input.text = text
            input.cursorPosition = text.length
            input.forceActiveFocus()
        }
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
