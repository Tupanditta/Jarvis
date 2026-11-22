// Ventana de configuración (configurador.md): apartados a la izquierda, el apartado elegido a
// la derecha y, abajo, Cancelar y Guardar. Nada se registra hasta pulsar Guardar; cerrar con
// cambios pendientes pregunta antes de descartarlos.
import QtQuick
import QtQuick.Window
import "../../ui/qml"
import "../../ui/qml/components"
import "controls"

Window {
    id: root

    objectName: "configWindow"
    title: "Configuración de Jarvis" + (settingsWindow.dirty ? " ●" : "")
    width: 960
    height: 640
    minimumWidth: 760
    minimumHeight: 480
    color: Theme.bgBase

    property string current: settingsWindow.sectionList.length > 0
                             ? settingsWindow.sectionList[0].id : ""
    property bool confirming: false   // «Hay cambios sin guardar»

    function pageOf(sectionId) {
        var list = settingsWindow.sectionList
        for (var i = 0; i < list.length; ++i)
            if (list[i].id === sectionId)
                return list[i].page
        return ""
    }

    function openPage() {
        if (current.length === 0)
            return
        page.setSource(Qt.resolvedUrl("sections/" + pageOf(current)),
                       { section: settingsWindow.section(current) })
    }

    function requestClose() {
        if (settingsWindow.canClose())
            root.hide()
        else
            root.confirming = true
    }

    onCurrentChanged: openPage()
    Component.onCompleted: openPage()

    onClosing: (close) => {
        if (!settingsWindow.canClose()) {
            close.accepted = false
            root.confirming = true
        }
    }

    Shortcut {
        sequence: "Esc"
        enabled: !editor.active
        onActivated: root.confirming ? root.confirming = false : root.requestClose()
    }

    // --- Apartados ---------------------------------------------------------------------------

    Rectangle {
        id: side

        width: 210
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        color: Theme.bgWindow

        Rectangle {
            width: 1
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            color: Theme.lineSoft
        }

        Column {
            anchors.fill: parent
            anchors.margins: Theme.space16
            spacing: Theme.space4

            DisplayText {
                text: "Configuración"
                size: Theme.sizeTitle
                color: Theme.textPrimary
                bottomPadding: Theme.space16
            }

            Repeater {
                model: settingsWindow.sectionList

                Rectangle {
                    id: entry

                    required property var modelData
                    readonly property bool selected: root.current === modelData.id
                    readonly property var section: settingsWindow.section(modelData.id)

                    objectName: "sectionTab-" + modelData.id
                    width: parent.width
                    height: 36
                    radius: Theme.radiusCard
                    color: selected ? Theme.bgSelected : tabHover.hovered ? Theme.bgHover : "transparent"
                    border.width: selected ? 1 : 0
                    border.color: Theme.alpha(Theme.primary, 0.5)

                    Image {
                        id: tabIcon

                        x: Theme.space8
                        width: 16
                        height: 16
                        sourceSize.width: 32
                        sourceSize.height: 32
                        source: Theme.icon(entry.modelData.icon)
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Text {
                        anchors.left: tabIcon.right
                        anchors.leftMargin: Theme.space8
                        anchors.verticalCenter: parent.verticalCenter
                        text: entry.modelData.title
                        color: entry.selected ? Theme.textPrimary : Theme.textSecondary
                        font.family: Theme.fontBody
                        font.pixelSize: Theme.sizeSecondary
                    }

                    // Punto: el apartado tiene cambios sin guardar.
                    Rectangle {
                        width: 6
                        height: 6
                        radius: 3
                        anchors.right: parent.right
                        anchors.rightMargin: Theme.space8
                        anchors.verticalCenter: parent.verticalCenter
                        color: Theme.statusPending
                        visible: entry.section !== null && entry.section.dirty
                    }

                    HoverHandler {
                        id: tabHover
                        cursorShape: Qt.PointingHandCursor
                    }

                    TapHandler {
                        onTapped: root.current = entry.modelData.id
                    }
                }
            }
        }
    }

    // --- Apartado elegido --------------------------------------------------------------------

    Flickable {
        id: scroller

        anchors.left: side.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: footer.top
        contentWidth: width
        contentHeight: page.height + 2 * Theme.space24
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Loader {
            id: page

            x: Theme.space24
            y: Theme.space24
            width: scroller.width - 2 * Theme.space24
        }
    }

    // --- Guardar y cancelar ------------------------------------------------------------------

    Rectangle {
        id: footer

        anchors.left: side.right
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: Math.max(56, messages.implicitHeight + 2 * Theme.space12)
        color: Theme.bgWindow

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.lineSoft
        }

        Column {
            id: messages

            anchors.left: parent.left
            anchors.leftMargin: Theme.space24
            anchors.right: buttons.left
            anchors.rightMargin: Theme.space16
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.space4

            Repeater {
                model: settingsWindow.problems

                Text {
                    required property string modelData
                    width: messages.width
                    text: "• " + modelData
                    color: Theme.statusError
                    font.family: Theme.fontBody
                    font.pixelSize: Theme.sizeSecondary
                    wrapMode: Text.WordWrap
                }
            }

            Text {
                objectName: "statusText"
                width: messages.width
                visible: settingsWindow.problems.length === 0
                text: settingsWindow.dirty ? "Hay cambios sin guardar."
                      : settingsWindow.saved ? "Guardado. Se aplicará al abrir la próxima sesión."
                      : ""
                color: settingsWindow.dirty ? Theme.statusPending : Theme.statusDone
                font.family: Theme.fontBody
                font.pixelSize: Theme.sizeSecondary
                wrapMode: Text.WordWrap
            }
        }

        Row {
            id: buttons

            anchors.right: parent.right
            anchors.rightMargin: Theme.space24
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.space8

            TextButton {
                objectName: "cancelButton"
                text: "Cancelar"
                onClicked: root.requestClose()
            }

            TextButton {
                objectName: "saveButton"
                text: "Guardar"
                primary: true
                enabled: settingsWindow.dirty
                onClicked: settingsWindow.save()
            }
        }
    }

    // --- Confirmación al salir con cambios ---------------------------------------------------

    Rectangle {
        anchors.fill: parent
        visible: root.confirming
        color: Theme.alpha(Theme.bgBase, 0.8)
        z: 10

        TapHandler {}  // nada debajo responde mientras se pregunta

        Rectangle {
            objectName: "confirmClose"
            anchors.centerIn: parent
            width: 420
            height: dialogColumn.implicitHeight + 2 * Theme.space24
            radius: Theme.radiusPanel
            color: Theme.bgWindow
            border.width: 1
            border.color: Theme.lineStrong

            Column {
                id: dialogColumn

                anchors.fill: parent
                anchors.margins: Theme.space24
                spacing: Theme.space16

                DisplayText {
                    text: "Hay cambios sin guardar"
                    size: Theme.sizeTitle
                    color: Theme.textPrimary
                }

                Text {
                    width: parent.width
                    text: "Si sale ahora, se descartan todos los cambios desde el último guardado."
                    color: Theme.textSecondary
                    font.family: Theme.fontBody
                    font.pixelSize: Theme.sizeSecondary
                    wrapMode: Text.WordWrap
                }

                Row {
                    anchors.right: parent.right
                    spacing: Theme.space8

                    TextButton {
                        objectName: "keepEditing"
                        text: "Seguir editando"
                        onClicked: root.confirming = false
                    }

                    TextButton {
                        objectName: "discardButton"
                        text: "Salir sin guardar"
                        danger: true
                        onClicked: {
                            root.confirming = false
                            settingsWindow.discard()
                        }
                    }
                }
            }
        }
    }
}
