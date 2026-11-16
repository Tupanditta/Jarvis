// Panel de protocolo (Interfaz, sección 8): el nombre del protocolo, una barra de progreso
// fina en `primary` (tareas terminadas / total) y la lista de sus tareas como `TaskCard`. El
// estado de cada tarea cambia en cuanto cambia (RF-57, RNF-14). «Qué protocolos hay» muestra
// en su lugar el listado de los protocolos de la configuración (RF-99).
//
// En su ventana, el botón de actualizar pide el listado; un clic en un protocolo del listado
// lo ejecuta, y el botón de volver regresa al protocolo en curso o al último.
import QtQuick
import ".."
import "../components"

PanelFrame {
    id: panel

    readonly property bool showsList: protocols.mode === "list"

    title: "Protocolo"
    summary: showsList
             ? protocols.protocols.length + (protocols.protocols.length === 1 ? " protocolo"
                                                                              : " protocolos")
             : protocols.hasRun ? protocols.doneCount + " de " + protocols.steps.length
                                  + (protocols.running ? " · en curso" : "")
             : ""

    // Al abrir la ventana a mano sin nada que mostrar, pide el listado. Espera un momento: si
    // la ha abierto una orden, su contenido está a punto de llegar.
    Timer {
        interval: 400
        running: panel.rich
        onTriggered: {
            if (protocols.mode === "" && assistant.sessionOpen)
                protocols.refresh()
        }
    }

    Item {
        id: head

        width: parent.width
        height: panel.rich || (!panel.showsList && protocols.hasRun) ? 30 : 0

        IconButton {
            id: back

            icon: "atras"
            visible: panel.rich && panel.showsList && protocols.hasRun
            anchors.verticalCenter: parent.verticalCenter
            onClicked: protocols.showRun()
        }

        // Nombre del protocolo y recuento de errores.
        Text {
            x: back.visible ? back.width + Theme.space4 : 0
            width: Math.max(0, parent.width - x - (refresh.visible ? refresh.width : 0)
                                - Theme.space8)
            visible: !panel.showsList && protocols.hasRun
            text: protocols.name + (protocols.errorCount === 0 ? ""
                  : protocols.errorCount === 1 ? " · 1 error"
                  : " · " + protocols.errorCount + " errores")
            color: Theme.textPrimary
            font.family: Theme.fontBody
            font.pixelSize: Theme.sizeText
            elide: Text.ElideRight
            anchors.verticalCenter: parent.verticalCenter
        }

        IconButton {
            id: refresh

            x: parent.width - width
            icon: "actualizar"
            visible: panel.rich
            enabled: assistant.sessionOpen
            anchors.verticalCenter: parent.verticalCenter
            onClicked: protocols.refresh()
        }
    }

    // Progreso: tareas terminadas / total.
    Rectangle {
        id: track

        y: head.height + Theme.space4
        width: parent.width
        height: visible ? 3 : 0
        radius: 1.5
        color: Theme.lineSoft
        visible: !panel.showsList && protocols.hasRun

        Rectangle {
            width: parent.width * protocols.progress
            height: parent.height
            radius: parent.radius
            color: protocols.errorCount > 0 && !protocols.running ? Theme.statusError
                                                                   : Theme.primary

            Behavior on width {
                enabled: !ui.reduceMotion
                NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
            }
        }
    }

    ListView {
        id: steps

        y: track.y + track.height + Theme.space8
        width: parent.width
        height: Math.max(0, parent.height - y)
        clip: true
        model: protocols.steps
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        visible: !panel.showsList && count > 0

        delegate: TaskCard {
            required property var modelData

            width: ListView.view.width
            module: modelData.module
            description: modelData.description
            status: modelData.status
            detail: modelData.detail
            time: modelData.time
        }
    }

    ListView {
        id: available

        y: head.height + (head.height > 0 ? Theme.space8 : 0)
        width: parent.width
        height: Math.max(0, parent.height - y)
        clip: true
        spacing: Theme.space4
        model: protocols.protocols
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        visible: panel.showsList && count > 0

        delegate: Item {
            id: entry

            required property var modelData
            required property int index

            width: ListView.view.width
            height: 48

            Rectangle {
                anchors.fill: parent
                radius: Theme.radiusCard
                color: Theme.bgHover
                visible: entryHover.hovered
            }

            HoverHandler {
                id: entryHover
                enabled: panel.rich && assistant.sessionOpen
                cursorShape: Qt.PointingHandCursor
            }

            TapHandler {
                enabled: panel.rich && assistant.sessionOpen
                onTapped: protocols.run(entry.modelData.name)
            }

            NumberedRow {
                x: Theme.space4
                width: parent.width - x - (star.visible ? star.width + Theme.space12 : 0)
                height: parent.height
                number: entry.index + 1
                title: entry.modelData.name
                subtitle: (entry.modelData.steps === 1 ? "1 tarea"
                           : entry.modelData.steps + " tareas")
                          + (entry.modelData.aliases.length > 0
                             ? " · " + entry.modelData.aliases : "")
            }

            Image {
                id: star

                x: parent.width - width - Theme.space8
                width: 14
                height: 14
                sourceSize.width: 28
                sourceSize.height: 28
                visible: entry.modelData.important === true
                source: Theme.icon("estrella")
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    EmptyState {
        y: head.height
        width: parent.width
        height: Math.max(0, parent.height - y)
        visible: panel.showsList ? available.count === 0 : steps.count === 0
        text: panel.showsList ? "Sin protocolos" : "Ningún protocolo en curso"
    }
}
