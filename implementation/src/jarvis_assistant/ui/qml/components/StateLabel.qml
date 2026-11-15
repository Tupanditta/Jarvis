// Punto y texto del estado del asistente.
import QtQuick
import ".."

Row {
    id: label

    property string activity: "dormido"
    property string text: ""
    property int size: Theme.sizeState
    readonly property color tone: Theme.activityColor(activity)

    spacing: Theme.space8

    Rectangle {
        width: 8
        height: 8
        radius: 4
        color: label.tone
        anchors.verticalCenter: parent.verticalCenter

        Behavior on color {
            ColorAnimation { duration: Theme.motionState }
        }

        // Procesando: latido.
        SequentialAnimation on opacity {
            running: label.activity === "procesando" && label.visible
            loops: Animation.Infinite
            alwaysRunToEnd: true
            NumberAnimation { to: 0.4; duration: 400 }
            NumberAnimation { to: 1; duration: 400 }
        }
    }

    DisplayText {
        text: label.text
        size: label.size
        color: label.tone
        anchors.verticalCenter: parent.verticalCenter

        Behavior on color {
            ColorAnimation { duration: Theme.motionState }
        }
    }
}
