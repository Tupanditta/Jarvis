// Interruptor con su texto: sí o no. `toggled(checked)` con el valor nuevo; el dueño decide
// si lo acepta y lo devuelve por `checked`.
import QtQuick
import "../../../ui/qml"

Item {
    id: toggle

    property bool checked: false
    property string text: ""
    property string detail: ""        // explicación debajo del texto

    signal toggled(bool checked)

    implicitWidth: track.width + Theme.space12 + Math.max(label.implicitWidth, info.implicitWidth)
    implicitHeight: Math.max(track.height, label.implicitHeight + (info.visible ? info.implicitHeight + 2 : 0))
    opacity: enabled ? 1 : 0.4

    Rectangle {
        id: track

        width: 34
        height: 18
        radius: height / 2
        anchors.verticalCenter: label.verticalCenter
        color: toggle.checked ? Theme.alpha(Theme.primary, 0.35) : Theme.bgRaised
        border.width: 1
        border.color: toggle.checked ? Theme.primary : Theme.lineStrong

        Rectangle {
            width: 12
            height: 12
            radius: 6
            y: 3
            x: toggle.checked ? parent.width - width - 3 : 3
            color: toggle.checked ? Theme.primaryBright : Theme.textMuted

            Behavior on x {
                NumberAnimation { duration: Theme.motionWindow }
            }
        }
    }

    Text {
        id: label

        x: track.width + Theme.space12
        text: toggle.text
        color: Theme.textPrimary
        font.family: Theme.fontBody
        font.pixelSize: Theme.sizeSecondary
    }

    Text {
        id: info

        x: label.x
        anchors.top: label.bottom
        anchors.topMargin: 2
        width: Math.max(0, toggle.width - x)
        visible: toggle.detail.length > 0
        text: toggle.detail
        color: Theme.textMuted
        font.family: Theme.fontBody
        font.pixelSize: Theme.sizeLabel
        wrapMode: Text.WordWrap
    }

    HoverHandler {
        cursorShape: Qt.PointingHandCursor
    }

    TapHandler {
        enabled: toggle.enabled
        onTapped: toggle.toggled(!toggle.checked)
    }
}
