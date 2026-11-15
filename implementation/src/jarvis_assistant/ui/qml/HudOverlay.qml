// HUD flotante (Interfaz, sección 6; hud.md, secciones 1 y 2).
// Siempre encima, sin bordes y translúcido. No toma el foco por su cuenta: solo lo recibe con
// un clic en su caja de texto. En reposo no tiene ninguna animación continua.
import QtQuick
import QtQuick.Window
import "orb"
import "components"
import "panels"

Window {
    id: hudWindow

    objectName: "hudOverlay"
    title: "Jarvis HUD"
    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
    color: "transparent"
    width: 380

    readonly property int gap: Theme.space16
    readonly property int collapsedHeight: 104
    readonly property real maxHeight: Screen.desktopAvailableHeight * 0.6
    readonly property bool atRight: ui.hudCorner.indexOf("right") >= 0
    readonly property bool atBottom: ui.hudCorner.indexOf("bottom") >= 0
    readonly property real bodyHeight: assistant.activePanel.length > 0 ? 260
                                       : activity.contentHeight
    readonly property real wanted: hud.expanded
                                   ? Math.min(maxHeight, collapsedHeight + Theme.space8 + bodyHeight)
                                   : collapsedHeight

    height: wanted
    x: Screen.virtualX + (atRight ? Screen.desktopAvailableWidth - width - gap : gap)
    y: Screen.virtualY + (atBottom ? Screen.desktopAvailableHeight - height - gap : gap)

    Behavior on height {
        enabled: !ui.reduceMotion
        NumberAnimation { duration: Theme.motionPanel; easing.type: Easing.OutCubic }
    }

    onVisibleChanged: {
        if (visible)
            frame.opacity = 1
    }

    Connections {
        target: windows

        function onHudAnimation(kind) {
            mini.play(kind)
            fade.stop()
            if (kind === "wake" || kind === "wake_from_rest") {
                frame.opacity = ui.reduceMotion ? 1 : 0.4
                fade.to = 1
            } else if (kind === "sleep_close") {
                fade.to = 0
            } else {
                return
            }
            fade.start()
        }
    }

    NumberAnimation {
        id: fade

        target: frame
        property: "opacity"
        duration: ui.reduceMotion ? Theme.motionState : Theme.motionTransition
    }

    Rectangle {
        id: frame

        anchors.fill: parent
        color: Theme.bgPanel
        radius: Theme.radiusPanel
        border.width: 1
        border.color: Theme.lineSoft
        clip: true

        // --- Cabecera ------------------------------------------------------------------------

        MiniOrb {
            id: mini

            x: Theme.space12
            y: Theme.space8
            activity: assistant.activity
            level: assistant.level
            reduceMotion: ui.reduceMotion
            running: hudWindow.visible
        }

        Column {
            x: mini.x + mini.width + Theme.space12
            y: Theme.space8
            width: frame.width - x - buttons.width - Theme.space12 - Theme.space8
            spacing: Theme.space4

            StateLabel {
                activity: assistant.activity
                text: assistant.stateText
                size: Theme.sizeTitle
            }

            Subtitles {
                width: parent.width
                compact: true
            }
        }

        Row {
            id: buttons

            anchors.right: parent.right
            anchors.rightMargin: Theme.space8
            y: Theme.space8
            spacing: Theme.space4

            IconButton {
                icon: "silencio"
                visible: assistant.canSilence
                onClicked: assistant.silence()
            }

            IconButton {
                icon: hud.expanded ? "contraer" : "expandir"
                onClicked: hud.toggle()
            }
        }

        CommandInput {
            id: input

            x: Theme.space12
            y: hudWindow.collapsedHeight - height - Theme.space8
            width: frame.width - 2 * Theme.space12
            onPressed: windows.hudInputPressed()
        }

        // --- Cuerpo: el panel activo ---------------------------------------------------------

        Rectangle {
            x: 0
            y: hudWindow.collapsedHeight
            width: frame.width
            height: 1
            color: Theme.lineSoft
            visible: hud.expanded
        }

        Item {
            x: 0
            y: hudWindow.collapsedHeight + Theme.space8
            width: frame.width
            height: frame.height - y - Theme.space8
            visible: hud.expanded

            ActivityPanel {
                id: activity

                anchors.fill: parent
                flat: true
                limit: 6
                visible: assistant.activePanel.length === 0
            }

            PanelHost {
                anchors.fill: parent
                flat: true
                panel: assistant.activePanel
            }
        }
    }
}
