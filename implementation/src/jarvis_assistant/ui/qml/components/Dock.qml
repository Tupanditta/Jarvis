// Selector de ventanas: un botón por ventana flotante. Abre la ventana, la trae al frente o,
// si ya está encima, la cierra. El punto bajo el icono marca las abiertas. Tras ellos, un
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

                objectName: "dock-" + windowId
                width: 40
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
