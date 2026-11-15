// Pantalla de sesión (Interfaz, sección 5; hud.md, sección 1).
// Pantalla completa en el monitor principal. Visible también en dormido: fondo oscuro, orbe
// apagado y la caja de texto. Cerrarla solo la oculta: el proceso sigue en la bandeja.
import QtQuick
import QtQuick.Window
import "orb"
import "components"
import "panels"

Window {
    id: screen

    objectName: "sessionScreen"
    title: "Jarvis"
    color: Theme.bgBase
    width: 1366
    height: 768
    minimumWidth: 640
    minimumHeight: 480

    // Referencia 1920 × 1080: márgenes y columnas se reducen en pantallas menores.
    readonly property real k: Math.min(1, Math.min(width / 1920, height / 1080))
    readonly property real margin: Math.round(Theme.space48 * k)
    readonly property bool drawing: visible && visibility !== Window.Minimized
    readonly property bool resting: assistant.activity === "reposo"
    property real panels: 0              // opacidad de paneles y subtítulos
    property bool cursorHidden: false
    property string now: Qt.formatTime(new Date(), "HH:mm")

    function focusInput() {
        input.focusInput()
    }

    onActiveChanged: {
        if (active)
            input.focusInput()
    }

    onClosing: (close) => {
        close.accepted = windows.acceptClose()
    }

    // --- Transiciones ------------------------------------------------------------------------

    Connections {
        target: windows

        function onScreenAnimation(kind) {
            orb.play(kind)
            panelFade.stop()
            if (kind === "wake") {
                // Los paneles aparecen con el estallido, entre 1,0 y 1,8 s (solo al abrir).
                panelFade.target = 1
                panelFade.delay = 1000
                panelFade.span = 800
            } else if (kind === "wake_from_rest") {
                panelFade.target = 1
                panelFade.delay = 0
                panelFade.span = Theme.motionTransition
            } else if (kind === "sleep_rest") {
                panelFade.target = 0.5
                panelFade.delay = 400
                panelFade.span = 1200
            } else {
                // Cierre: los paneles se apagan mientras el orbe colapsa.
                panelFade.target = 0
                panelFade.delay = 200
                panelFade.span = 1100
            }
            if (ui.reduceMotion) {
                panelFade.delay = 0
                panelFade.span = Theme.motionState
            }
            panelFade.start()
        }
    }

    SequentialAnimation {
        id: panelFade

        property real target: 1
        property int delay: 0
        property int span: 1000

        PauseAnimation { duration: panelFade.delay }
        NumberAnimation {
            target: screen
            property: "panels"
            to: panelFade.target
            duration: panelFade.span
            easing.type: Easing.OutCubic
        }
    }

    Timer {
        interval: 1000
        repeat: true
        running: screen.drawing
        onTriggered: screen.now = Qt.formatTime(new Date(), "HH:mm")
    }

    // --- Cursor: se oculta tras 2 s sin moverse ----------------------------------------------

    HoverHandler {
        cursorShape: screen.cursorHidden ? Qt.BlankCursor : Qt.ArrowCursor
        onPointChanged: {
            screen.cursorHidden = false
            cursorTimer.restart()
        }
    }

    Timer {
        id: cursorTimer
        interval: 2000
        running: screen.drawing
        onTriggered: screen.cursorHidden = true
    }

    // --- Fondo vivo y orbe -------------------------------------------------------------------

    LifeField {
        anchors.fill: parent
        conductor: orb
        centerX: orb.x + orb.width / 2
        centerY: orb.y + orb.height / 2
        quality: ui.quality
    }

    Orb {
        id: orb

        objectName: "orb"
        anchors.centerIn: parent
        anchors.verticalCenterOffset: -screen.height * 0.04
        d: Math.min(screen.width, screen.height) * 0.42
        activity: assistant.activity
        level: assistant.level
        quality: ui.quality
        reduceMotion: ui.reduceMotion
        running: screen.drawing
    }

    // --- Barra superior ----------------------------------------------------------------------

    Item {
        id: topBar

        x: screen.margin
        y: screen.margin
        width: screen.width - 2 * screen.margin
        height: 44
        opacity: screen.panels

        Row {
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.space12

            DisplayText {
                text: "Jarvis"
                size: Theme.sizeTitle
                color: Theme.primary
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: assistant.sessionName.length > 0 ? "· " + assistant.sessionName : ""
                width: Math.min(implicitWidth, topBar.width * 0.4)
                color: Theme.textSecondary
                font.family: Theme.fontBody
                font.pixelSize: Theme.sizeText
                elide: Text.ElideRight
                anchors.verticalCenter: parent.verticalCenter
            }

            Image {
                visible: assistant.sessionImportant
                width: 16
                height: 16
                sourceSize.width: 32
                sourceSize.height: 32
                source: Theme.icon("estrella")
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Row {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.space24

            StateLabel {
                activity: assistant.activity
                text: assistant.stateText
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: screen.now
                color: Theme.textSecondary
                font.family: Theme.fontBody
                font.pixelSize: Theme.sizeClock
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    // --- Columnas ----------------------------------------------------------------------------

    ActivityPanel {
        id: activityPanel

        x: screen.margin
        y: topBar.y + topBar.height + screen.margin
        width: Math.round(360 * screen.k)
        height: Math.max(160, subtitles.y - y - screen.margin)
        opacity: screen.panels
        visible: opacity > 0
    }

    PanelHost {
        x: screen.width - screen.margin - width
        y: activityPanel.y
        width: Math.round(420 * screen.k)
        height: activityPanel.height
        panel: assistant.activePanel
        opacity: screen.panels
    }

    // --- Subtítulos y caja de texto ----------------------------------------------------------

    Subtitles {
        id: subtitles

        width: Math.min(900, screen.width - 2 * screen.margin)
        anchors.horizontalCenter: parent.horizontalCenter
        y: input.y - height - Theme.space16
        visible: screen.panels > 0
        opacity: shown ? screen.panels : 0
    }

    CommandInput {
        id: input

        width: Math.min(900, screen.width - 2 * screen.margin)
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: screen.margin
        focus: true
    }

    FrameCounter {
        visible: ui.debug
        x: Theme.space8
        y: Theme.space8
    }
}
