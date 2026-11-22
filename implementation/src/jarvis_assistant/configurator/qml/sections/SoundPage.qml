// Apartado Sonido.
import QtQuick
import "../../../ui/qml"
import "../controls"

Column {
    id: page

    property QtObject section

    spacing: Theme.space24

    PageHeader {
        width: page.width
        title: "Sonido"
        detail: "Sin sonido, el asistente no habla ni suena al abrir ventanas. Sus respuestas se"
                + " siguen viendo en los subtítulos."
        locked: page.section ? page.section.locked : ""
    }

    Toggle {
        objectName: "soundToggle"
        width: page.width
        enabled: page.section !== null && page.section.locked.length === 0
        text: "Sonido del asistente"
        detail: checked ? "Activado: el asistente habla." : "Desactivado: el asistente no habla."
        checked: page.section ? page.section.enabled : true
        onToggled: (value) => page.section.setEnabled(value)
    }
}
