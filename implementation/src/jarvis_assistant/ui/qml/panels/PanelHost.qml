// El panel activo (hud.md, sección 3): el último que recibió `PanelActivated`. Los paneles de
// cada módulo llegan con sus módulos; uno sin componente propio se muestra vacío.
// El mismo componente se usa en la pantalla de sesión y en el HUD (AD-08).
import QtQuick
import ".."
import "../components"

Item {
    id: host

    property string panel: ""
    property bool flat: false
    property bool active: true

    // Nombre del panel → archivo QML de `panels/`: sale del registro de ventanas
    // (`ui/workspace.py`), el único sitio donde se declara el panel de un módulo.
    readonly property string component: workspace.component(panel)
    readonly property url source: component.length > 0 ? Qt.resolvedUrl(component) : ""

    visible: panel.length > 0

    Loader {
        id: loader

        anchors.fill: parent
        active: host.visible && host.source.toString().length > 0
        source: host.source
    }

    Binding {
        target: loader.item
        property: "flat"
        value: host.flat
        when: loader.status === Loader.Ready
    }

    Binding {
        target: loader.item
        property: "active"
        value: host.active
        when: loader.status === Loader.Ready
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
