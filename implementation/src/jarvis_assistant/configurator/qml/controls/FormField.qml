// Campo de formulario con su etiqueta. Una línea, o varias con `multiline` (una entrada por
// línea: alias, argumentos). `value` es lo guardado. `edited(text)` avisa a cada cambio del
// usuario: así nada se pierde si se pulsa Aceptar o Guardar sin salir antes del campo.
// `committed(text)` avisa al terminar de editar (Enter, Tab o al salir del campo).
import QtQuick
import "../../../ui/qml"

Column {
    id: field

    property string label: ""
    property string value: ""
    property string placeholder: ""
    property string hint: ""          // ayuda bajo el campo
    property bool multiline: false
    property bool mono: false
    readonly property string text: multiline ? area.text : line.text

    signal edited(string text)
    signal committed(string text)

    function setText(value) {
        if (multiline)
            area.text = value
        else
            line.text = value
    }

    spacing: Theme.space4
    opacity: enabled ? 1 : 0.4

    // Solo si es distinto: reescribir el mismo texto movería el cursor mientras se escribe.
    onValueChanged: {
        if (text !== value)
            setText(value)
    }
    Component.onCompleted: setText(value)

    Text {
        text: field.label
        color: Theme.textSecondary
        font.family: Theme.fontBody
        font.pixelSize: Theme.sizeLabel
        visible: text.length > 0
    }

    Rectangle {
        width: field.width
        height: field.multiline ? 72 : 32
        radius: Theme.radiusCard
        color: Theme.bgRaised
        border.width: 1
        border.color: line.activeFocus || area.activeFocus ? Theme.primaryDim : Theme.lineSoft

        TextInput {
            id: line

            objectName: "field-" + field.label
            visible: !field.multiline
            anchors.fill: parent
            anchors.leftMargin: Theme.space8
            anchors.rightMargin: Theme.space8
            verticalAlignment: TextInput.AlignVCenter
            color: Theme.textPrimary
            selectionColor: Theme.primaryDim
            selectedTextColor: Theme.textPrimary
            font.family: field.mono ? Theme.fontMono : Theme.fontBody
            font.pixelSize: Theme.sizeSecondary
            clip: true
            selectByMouse: true
            onTextEdited: field.edited(text)
            onEditingFinished: field.committed(text)
        }

        TextEdit {
            id: area

            visible: field.multiline
            anchors.fill: parent
            anchors.margins: Theme.space8
            color: Theme.textPrimary
            selectionColor: Theme.primaryDim
            selectedTextColor: Theme.textPrimary
            font.family: field.mono ? Theme.fontMono : Theme.fontBody
            font.pixelSize: Theme.sizeSecondary
            clip: true
            selectByMouse: true
            wrapMode: TextEdit.NoWrap
            onTextChanged: {
                if (activeFocus)
                    field.edited(text)
            }
            onActiveFocusChanged: {
                if (!activeFocus)
                    field.committed(text)
            }
        }

        Text {
            anchors.left: parent.left
            anchors.leftMargin: Theme.space8
            y: field.multiline ? Theme.space8 : (parent.height - height) / 2
            text: field.placeholder
            visible: field.text.length === 0
            color: Theme.textMuted
            font.family: Theme.fontBody
            font.pixelSize: Theme.sizeSecondary
        }
    }

    Text {
        width: field.width
        text: field.hint
        visible: text.length > 0
        color: Theme.textMuted
        font.family: Theme.fontBody
        font.pixelSize: Theme.sizeLabel
        wrapMode: Text.WordWrap
    }
}
