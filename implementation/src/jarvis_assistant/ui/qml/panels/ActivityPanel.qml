// Panel de actividad: las tareas de la sesión, la más reciente arriba (hud.md, sección 3).
import QtQuick
import ".."
import "../components"

PanelFrame {
    id: panel

    property int limit: -1               // en el HUD, las 6 últimas
    readonly property real contentHeight: headerHeight
                                          + (tasks.count > 0 ? list.contentHeight : 48)

    title: "Actividad"

    ListView {
        id: list

        anchors.fill: parent
        model: tasks
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        visible: tasks.count > 0

        delegate: TaskCard {
            required property int index
            required module
            required description
            required status
            required detail
            required time
            required child
            readonly property bool shown: panel.limit < 0 || index < panel.limit

            width: ListView.view.width
            height: shown ? implicitHeight : 0
            visible: shown
        }
    }

    EmptyState {
        anchors.fill: parent
        visible: tasks.count === 0
        text: "Sin actividad"
    }
}
