// Campo de contraseña. `hidden`: no muestra nada de lo que se escribe, ni puntos (como la caja
// de la pantalla dormida); si no, puntos. La contraseña no se guarda en ninguna propiedad
// enlazada: se lee con `text` al aceptar y se borra con `clear()`.
import QtQuick
import "../../../ui/qml"

Rectangle {
    id: field

    property string placeholder: ""
    property bool hidden: false
    readonly property alias text: input.text
    property real pulse: 0

    signal accepted()

    function clear() {
        input.text = ""
    }

    function focusInput() {
        input.forceActiveFocus()
    }

    implicitWidth: 220
    implicitHeight: 32
    radius: Theme.radiusCard
    color: Theme.bgRaised
    border.width: 1
    border.color: Theme.mix(input.activeFocus ? Theme.primaryDim : Theme.lineSoft,
                            Theme.primaryBright, pulse)

    NumberAnimation {
        id: keyPulse

        target: field
        property: "pulse"
        from: 1
        to: 0
        duration: 320
        easing.type: Easing.OutCubic
    }

    TextInput {
        id: input

        objectName: "secret-" + field.placeholder
        anchors.fill: parent
        anchors.leftMargin: Theme.space8
        anchors.rightMargin: Theme.space8
        verticalAlignment: TextInput.AlignVCenter
        echoMode: field.hidden ? TextInput.NoEcho : TextInput.Password
        cursorVisible: !field.hidden && activeFocus
        color: Theme.textPrimary
        selectByMouse: false
        inputMethodHints: Qt.ImhSensitiveData | Qt.ImhNoPredictiveText | Qt.ImhNoAutoUppercase
        font.family: Theme.fontBody
        font.pixelSize: Theme.sizeSecondary
        clip: true

        onTextEdited: {
            if (field.hidden)
                keyPulse.restart()
        }
        onAccepted: field.accepted()
    }

    Text {
        anchors.fill: input
        verticalAlignment: Text.AlignVCenter
        visible: input.length === 0 && field.pulse === 0
        text: field.placeholder
        color: Theme.textMuted
        font: input.font
        elide: Text.ElideRight
    }
}
