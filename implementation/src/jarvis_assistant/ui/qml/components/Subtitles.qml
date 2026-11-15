// Subtítulos (RF-89): la última orden entre comillas y, debajo, la última respuesta.
// Se desvanecen a los 6 s. En modo compacto (HUD), una sola línea: la respuesta si la hay;
// si no, la orden.
import QtQuick
import ".."

Item {
    id: subtitles

    property bool compact: false
    property bool shown: false
    readonly property string command: assistant.commandText.length > 0
                                      ? "«" + assistant.commandText + "»" : ""

    implicitHeight: compact ? single.implicitHeight : lines.implicitHeight
    opacity: shown ? 1 : 0

    Behavior on opacity {
        NumberAnimation { duration: Theme.motionState }
    }

    Connections {
        target: assistant

        function onSubtitlesChanged() {
            subtitles.shown = true
            fade.restart()
        }
    }

    Timer {
        id: fade
        interval: 6000
        onTriggered: subtitles.shown = false
    }

    Column {
        id: lines

        visible: !subtitles.compact
        width: parent.width
        spacing: Theme.space4

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Theme.space8

            Text {
                text: subtitles.command
                width: Math.min(implicitWidth,
                                lines.width - (mark.visible ? mark.width + Theme.space8 : 0))
                color: assistant.commandRecognized ? Theme.textSecondary : Theme.textMuted
                font.family: Theme.fontBody
                font.pixelSize: Theme.sizeText
                elide: Text.ElideRight
            }

            Badge {
                id: mark
                text: "no reconocido"
                visible: !assistant.commandRecognized && subtitles.command.length > 0
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Text {
            width: parent.width
            text: assistant.responseText
            color: Theme.textPrimary
            font.family: Theme.fontBody
            font.pixelSize: Theme.sizeTitle
            lineHeight: Theme.lineHeight
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            maximumLineCount: 2
            elide: Text.ElideRight
        }
    }

    Text {
        id: single

        visible: subtitles.compact
        width: parent.width
        text: assistant.responseText.length > 0 ? assistant.responseText : subtitles.command
        color: assistant.responseText.length > 0 ? Theme.textPrimary
               : assistant.commandRecognized ? Theme.textSecondary : Theme.textMuted
        font.family: Theme.fontBody
        font.pixelSize: Theme.sizeSecondary
        elide: Text.ElideRight
    }
}
