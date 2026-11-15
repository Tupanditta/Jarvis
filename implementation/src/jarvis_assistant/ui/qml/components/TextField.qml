// Campo de texto de una línea para las ventanas: filtros, búsquedas y la línea de programas.
// Enter envía (`accepted`); Escape lo vacía. Teclear en él cuenta como actividad del usuario.
import QtQuick
import ".."

Rectangle {
    id: field

    property alias text: input.text
    property string placeholder: ""
    property string icon: ""
    property bool mono: false
    readonly property bool editing: input.activeFocus

    signal accepted(string text)
    signal edited(string text)

    function clear() {
        input.clear()
        field.edited("")
    }

    implicitHeight: 30
    height: implicitHeight
    radius: Theme.radiusCard
    color: Theme.bgRaised
    border.width: 1
    border.color: input.activeFocus ? Theme.primaryDim : Theme.lineSoft

    Image {
        id: glyph

        x: Theme.space8
        width: 14
        height: 14
        sourceSize.width: 28
        sourceSize.height: 28
        visible: field.icon.length > 0
        source: field.icon.length > 0 ? Theme.icon(field.icon) : ""
        opacity: 0.8
        anchors.verticalCenter: parent.verticalCenter
    }

    TextInput {
        id: input

        anchors.fill: parent
        anchors.leftMargin: glyph.visible ? glyph.x + glyph.width + Theme.space8 : Theme.space8
        anchors.rightMargin: Theme.space8
        verticalAlignment: TextInput.AlignVCenter
        color: Theme.textPrimary
        selectionColor: Theme.primaryDim
        selectedTextColor: Theme.textPrimary
        font.family: field.mono ? Theme.fontMono : Theme.fontBody
        font.pixelSize: Theme.sizeSecondary
        clip: true
        selectByMouse: true

        onAccepted: field.accepted(text)
        onTextEdited: {
            assistant.typing()
            field.edited(text)
        }
        Keys.onEscapePressed: field.clear()
    }

    Text {
        anchors.fill: input
        verticalAlignment: Text.AlignVCenter
        text: field.placeholder
        visible: input.text.length === 0 && input.preeditText.length === 0
        color: Theme.textMuted
        font: input.font
        elide: Text.ElideRight
    }
}
