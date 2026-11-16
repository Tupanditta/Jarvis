// Fila de tarea: estado, icono del módulo, descripción (una línea, con elipsis) y hora.
// Una tarea en `error` muestra debajo su motivo. Las de un protocolo se sangran.
import QtQuick
import ".."

Item {
    id: card

    property string module: ""
    property string description: ""
    property string status: "completado"
    property string detail: ""
    property string time: ""
    property bool child: false

    readonly property var moduleIcons: ["comandos", "apertura", "busqueda", "creacion",
                                        "recordatorio", "protocolo", "historial", "sesion",
                                        "nucleo"]
    // El módulo se llama `protocolos`; su icono, `protocolo`.
    readonly property string iconName: module === "protocolos" ? "protocolo" : module
    readonly property bool failed: status === "error" && detail.length > 0

    implicitHeight: row.height + (failed ? reason.implicitHeight + Theme.space4 : 0)
                    + Theme.space8

    Row {
        id: row

        x: card.child ? Theme.space16 : 0
        width: parent.width - x
        height: 24
        spacing: Theme.space8

        StatusDot {
            status: card.status
            anchors.verticalCenter: parent.verticalCenter
        }

        Image {
            width: 16
            height: 16
            sourceSize.width: 32
            sourceSize.height: 32
            source: Theme.icon(card.moduleIcons.indexOf(card.iconName) >= 0 ? card.iconName
                                                                              : "tarea")
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            width: Math.max(0, parent.width - 8 - 16 - clock.width - 3 * Theme.space8)
            text: card.description
            color: Theme.textPrimary
            font.family: Theme.fontBody
            font.pixelSize: Theme.sizeText
            elide: Text.ElideRight
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            id: clock

            text: card.time
            color: Theme.textMuted
            font.family: Theme.fontBody
            font.pixelSize: Theme.sizeSecondary
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    Text {
        id: reason

        visible: card.failed
        x: row.x + 8 + Theme.space8
        y: row.height + Theme.space4
        width: parent.width - x
        text: card.detail
        color: Theme.statusError
        font.family: Theme.fontBody
        font.pixelSize: Theme.sizeSecondary
        elide: Text.ElideRight
    }
}
