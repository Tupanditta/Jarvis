// Aviso dentro de una página: error (rojo), aviso (ámbar) o correcto (verde).
import QtQuick
import "../../../ui/qml"

Rectangle {
    id: notice

    property string text: ""
    property string kind: "error"     // "error", "warning" u "ok"
    readonly property color tone: kind === "ok" ? Theme.statusDone
                                  : kind === "warning" ? Theme.statusPending : Theme.statusError

    visible: text.length > 0
    implicitHeight: label.implicitHeight + 2 * Theme.space8
    radius: Theme.radiusCard
    color: Theme.alpha(tone, 0.10)
    border.width: 1
    border.color: Theme.alpha(tone, 0.5)

    Text {
        id: label

        anchors.fill: parent
        anchors.margins: Theme.space8
        text: notice.text
        color: Theme.textPrimary
        font.family: Theme.fontBody
        font.pixelSize: Theme.sizeSecondary
        wrapMode: Text.WordWrap
        verticalAlignment: Text.AlignVCenter
    }
}
