// Selector de ventanas: un botón por ventana flotante. Abre la ventana, la trae al frente o,
// si ya está encima, la cierra. El punto bajo el icono marca las abiertas. Tras ellos, los de
// los medidores de recursos y de ruido, que no son ventanas: los muestran u ocultan
// (`usage.toggle`, `noise.toggle`). Luego, un
// botón aparta a los bordes las ventanas a la vista o, si hay más apartadas que a la vista,
// devuelve las apartadas. El último devuelve todas a su disposición inicial.
import QtQuick
import ".."

Rectangle {
    id: dock

    property string hint: ""             // nombre del botón bajo el cursor

    implicitWidth: row.implicitWidth + 2 * Theme.space8
    implicitHeight: 44
    width: implicitWidth
    height: implicitHeight
    radius: height / 2
    color: Theme.bgWindow
    border.width: 1
    border.color: Theme.lineSoft

    // Botón de un medidor de la pantalla de sesión (`meter`: su modelo, con `shown`, `allowed`
    // y `toggle`). El punto bajo el icono marca que está a la vista. Sin permiso, no se ofrece.
    component MeterButton: Item {
        id: button

        property QtObject meter
        property string what: ""         // para el rótulo: «Mostrar <what>»
        property string icon: ""
        readonly property bool active: meter ? meter.shown : false
        readonly property string label: (active ? "Ocultar " : "Mostrar ") + what
        readonly property bool allowed: meter ? meter.allowed : true

        onLabelChanged: {
            if (buttonHover.hovered)
                dock.hint = label
        }

        visible: allowed
        width: allowed ? 40 : 0
        height: 36

        Rectangle {
            anchors.fill: parent
            anchors.margins: 2
            radius: Theme.radiusCard + 2
            color: buttonHover.hovered ? Theme.bgHover : "transparent"
        }

        Image {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -2
            width: 18
            height: 18
            sourceSize.width: 36
            sourceSize.height: 36
            source: Theme.icon(button.icon)
            opacity: button.active ? 1 : 0.5
        }

        Rectangle {
            width: 4
            height: 2
            radius: 1
            color: Theme.primary
            visible: button.active
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 5
        }

        HoverHandler {
            id: buttonHover
            cursorShape: Qt.PointingHandCursor
            onHoveredChanged: {
                if (hovered)
                    dock.hint = button.label
                else if (dock.hint === button.label)
                    dock.hint = ""
            }
        }

        TapHandler {
            onTapped: button.meter.toggle()
        }
    }

    Row {
        id: row

        anchors.centerIn: parent
        spacing: 2

        Repeater {
            model: workspace

            Item {
                id: entry

                required property string windowId
                required property string title
                required property string icon
                required property bool open
                required property bool focused
                required property bool available  // sin permiso, el módulo no se ofrece

                objectName: "dock-" + windowId
                visible: available
                width: available ? 40 : 0
                height: 36

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 2
                    radius: Theme.radiusCard + 2
                    color: hover.hovered ? Theme.bgHover
                                         : entry.focused ? Theme.bgSelected : "transparent"
                    border.width: entry.focused ? 1 : 0
                    border.color: Theme.primaryDim
                }

                Image {
                    anchors.centerIn: parent
                    anchors.verticalCenterOffset: -2
                    width: 18
                    height: 18
                    sourceSize.width: 36
                    sourceSize.height: 36
                    source: Theme.icon(entry.icon)
                    opacity: entry.open ? 1 : 0.5
                }

                Rectangle {
                    width: entry.focused ? 10 : 4
                    height: 2
                    radius: 1
                    color: Theme.primary
                    visible: entry.open
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 5

                    Behavior on width {
                        NumberAnimation { duration: Theme.motionWindow }
                    }
                }

                HoverHandler {
                    id: hover
                    cursorShape: Qt.PointingHandCursor
                    onHoveredChanged: {
                        if (hovered)
                            dock.hint = entry.title
                        else if (dock.hint === entry.title)
                            dock.hint = ""
                    }
                }

                TapHandler {
                    onTapped: workspace.toggle(entry.windowId)
                }
            }
        }

        MeterButton {
            objectName: "dock-recursos"
            meter: usage
            what: "recursos"
            icon: "recursos"
        }

        MeterButton {
            objectName: "dock-ruido"
            meter: noise
            what: "ruido"
            icon: "ruido"
        }

        Item {
            width: Theme.space12
            height: 36

            Rectangle {
                anchors.centerIn: parent
                width: 1
                height: 18
                color: Theme.lineSoft
            }
        }

        Item {
            id: setAside

            // A la par, aparta (`workspace.toggle_aside_all`).
            readonly property bool restoring: workspace.asideCount > workspace.spreadCount
            readonly property string label: restoring ? "Devolver ventanas" : "Apartar ventanas"
            readonly property bool usable: workspace.openCount > 0

            onLabelChanged: {
                if (asideHover.hovered)
                    dock.hint = label
            }

            objectName: "dock-apartar"
            width: 40
            height: 36

            Rectangle {
                anchors.fill: parent
                anchors.margins: 2
                radius: Theme.radiusCard + 2
                color: asideHover.hovered && setAside.usable ? Theme.bgHover : "transparent"
            }

            Image {
                anchors.centerIn: parent
                width: 18
                height: 18
                sourceSize.width: 36
                sourceSize.height: 36
                source: Theme.icon("apartar")
                opacity: setAside.usable ? 0.7 : 0.3
                // Devolver es el gesto inverso: la misma flecha, de vuelta.
                rotation: setAside.restoring ? 180 : 0

                Behavior on rotation {
                    NumberAnimation {
                        duration: ui.reduceMotion ? 0 : Theme.motionPanel
                        easing.type: Easing.OutCubic
                    }
                }
            }

            HoverHandler {
                id: asideHover
                cursorShape: setAside.usable ? Qt.PointingHandCursor : Qt.ArrowCursor
                onHoveredChanged: {
                    if (hovered)
                        dock.hint = setAside.label
                    else if (dock.hint === setAside.label)
                        dock.hint = ""
                }
            }

            TapHandler {
                onTapped: workspace.toggle_aside_all()
            }
        }

        Item {
            id: reset

            readonly property string label: "Restablecer disposición"

            width: 40
            height: 36

            Rectangle {
                anchors.fill: parent
                anchors.margins: 2
                radius: Theme.radiusCard + 2
                color: resetHover.hovered ? Theme.bgHover : "transparent"
            }

            Image {
                anchors.centerIn: parent
                width: 18
                height: 18
                sourceSize.width: 36
                sourceSize.height: 36
                source: Theme.icon("restablecer")
                opacity: 0.7
            }

            HoverHandler {
                id: resetHover
                cursorShape: Qt.PointingHandCursor
                onHoveredChanged: {
                    if (hovered)
                        dock.hint = reset.label
                    else if (dock.hint === reset.label)
                        dock.hint = ""
                }
            }

            TapHandler {
                onTapped: workspace.reset()
            }
        }
    }

    DisplayText {
        anchors.top: parent.bottom
        anchors.topMargin: Theme.space4
        anchors.horizontalCenter: parent.horizontalCenter
        text: dock.hint
        size: Theme.sizeLabel
        opacity: dock.hint.length > 0 ? 1 : 0

        Behavior on opacity {
            NumberAnimation { duration: Theme.motionWindow }
        }
    }
}
