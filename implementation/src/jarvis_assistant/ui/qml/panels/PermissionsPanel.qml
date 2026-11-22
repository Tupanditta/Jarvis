// Panel Permisos (solo el Acedor): una fila por perfil y una casilla por módulo. Encendida, el
// perfil puede usar el módulo; apagada, lo tiene restringido. Pulsar una casilla pide el
// cambio al módulo Permisos, que responde con la tabla nueva.
// Lee el modelo `admin` (`ui/panel_models.py`, AdminModel).
import QtQuick
import ".."
import "../components"

PanelFrame {
    id: panel

    title: "Permisos"
    summary: admin.matrix.length === 1 ? "1 perfil" : admin.matrix.length + " perfiles"

    Item {
        id: head

        width: parent.width
        height: panel.rich ? 30 : 0
        visible: panel.rich

        Text {
            width: parent.width - refresh.width - Theme.space8
            text: "Encendido: puede usarlo · Apagado: restringido"
            color: Theme.textMuted
            font.family: Theme.fontBody
            font.pixelSize: Theme.sizeLabel
            elide: Text.ElideRight
            anchors.verticalCenter: parent.verticalCenter
        }

        IconButton {
            id: refresh

            x: parent.width - width
            icon: "actualizar"
            enabled: assistant.sessionOpen
            anchors.verticalCenter: parent.verticalCenter
            onClicked: admin.showPermissions()
        }
    }

    Flickable {
        id: table

        y: head.height + (head.height > 0 ? Theme.space8 : 0)
        width: parent.width
        height: Math.max(0, parent.height - y)
        clip: true
        contentWidth: grid.implicitWidth
        contentHeight: grid.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        visible: admin.matrix.length > 0

        Column {
            id: grid

            readonly property int nameWidth: 120
            readonly property int cellWidth: 88

            spacing: Theme.space4

            // Cabecera: un módulo por columna.
            Row {
                Item { width: grid.nameWidth; height: 24 }

                Repeater {
                    model: admin.modules

                    Text {
                        required property var modelData
                        width: grid.cellWidth
                        height: 24
                        text: modelData.name
                        color: Theme.textSecondary
                        font.family: Theme.fontBody
                        font.pixelSize: Theme.sizeLabel
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
                }
            }

            Repeater {
                model: admin.matrix

                Rectangle {
                    id: row

                    required property var modelData

                    width: grid.nameWidth + admin.modules.length * grid.cellWidth
                    height: 36
                    radius: Theme.radiusCard
                    color: Theme.bgRaised

                    Row {
                        anchors.fill: parent

                        Text {
                            width: grid.nameWidth
                            height: parent.height
                            leftPadding: Theme.space8
                            text: row.modelData.name
                            color: Theme.textPrimary
                            font.family: Theme.fontBody
                            font.pixelSize: Theme.sizeSecondary
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }

                        Repeater {
                            model: admin.modules

                            Item {
                                id: cell

                                required property var modelData
                                required property int index
                                readonly property bool allowed: row.modelData.allowed[index]

                                width: grid.cellWidth
                                height: row.height

                                Rectangle {
                                    objectName: "permission-" + row.modelData.id + "-"
                                                + cell.modelData.id
                                    anchors.centerIn: parent
                                    width: 36
                                    height: 20
                                    radius: height / 2
                                    color: cell.allowed ? Theme.alpha(Theme.statusDone, 0.25)
                                                        : Theme.alpha(Theme.statusError, 0.18)
                                    border.width: 1
                                    border.color: cell.allowed ? Theme.statusDone
                                                               : Theme.statusError

                                    Rectangle {
                                        width: 14
                                        height: 14
                                        radius: 7
                                        anchors.verticalCenter: parent.verticalCenter
                                        x: cell.allowed ? parent.width - width - 3 : 3
                                        color: cell.allowed ? Theme.statusDone : Theme.statusError
                                    }

                                    HoverHandler { cursorShape: Qt.PointingHandCursor }

                                    TapHandler {
                                        onTapped: admin.setPermission(
                                            row.modelData.id, cell.modelData.id, !cell.allowed)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    EmptyState {
        y: table.y
        width: parent.width
        height: table.height
        visible: admin.matrix.length === 0
        text: "Sin perfiles"
    }
}
