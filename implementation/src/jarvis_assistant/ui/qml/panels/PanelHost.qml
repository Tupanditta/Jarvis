// El panel activo (hud.md, sección 3): el último que recibió `PanelActivated`. Los paneles de
// cada módulo llegan con sus módulos; uno sin componente propio se muestra vacío.
import QtQuick
import ".."
import "../components"

Item {
    id: host

    property string panel: ""
    property bool flat: false
    property bool active: true

    // Nombre del panel → archivo QML de `panels/`. Se amplía con cada módulo.
    readonly property var components: ({})
    readonly property url source: components[panel] !== undefined
                                  ? Qt.resolvedUrl(components[panel]) : ""

    visible: panel.length > 0

    Loader {
        anchors.fill: parent
        active: host.visible && host.source.toString().length > 0
        source: host.source
    }

    PanelFrame {
        anchors.fill: parent
        visible: host.visible && host.source.toString().length === 0
        title: host.panel
        active: host.active
        flat: host.flat

        EmptyState {
            anchors.fill: parent
            text: "Sin contenido"
        }
    }
}
