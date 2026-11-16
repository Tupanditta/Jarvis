// HUD flotante (Interfaz, sección 6; hud.md, secciones 1 y 2).
// Siempre encima, sin bordes y translúcido. No toma el foco por su cuenta: solo lo recibe con
// un clic en su caja de texto. En reposo no tiene ninguna animación continua.
// Se mueve arrastrando la cabecera, cambia de tamaño con el asa de la esquina libre y se oculta
// con su botón de ocultar (vuelve con «Mostrar HUD» en la bandeja o al pasar por la pantalla de
// sesión). La posición se guarda como el borde anclado más cercano: al crecer, crece hacia el
// otro lado.
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

    readonly property int gap: Theme.space16
    readonly property int collapsedHeight: 104
    readonly property int defaultWidth: 380
    readonly property int minWidth: 300
    readonly property real maxWidth: Math.max(minWidth, Screen.desktopAvailableWidth * 0.8)
    readonly property real minExpandedHeight: collapsedHeight + 120
    readonly property real maxHeight: Screen.desktopAvailableHeight * 0.6
    readonly property real maxUserHeight: Math.max(minExpandedHeight,
                                                   Screen.desktopAvailableHeight * 0.9)
    readonly property bool atRight: ui.hudCorner.indexOf("right") >= 0
    readonly property bool atBottom: ui.hudCorner.indexOf("bottom") >= 0
    readonly property real bodyHeight: assistant.activePanel.length > 0 ? 260
                                       : activity.contentHeight
    readonly property real autoHeight: Math.min(maxHeight,
                                                collapsedHeight + Theme.space8 + bodyHeight)
    readonly property real wanted: !hud.expanded ? collapsedHeight
                                   : userHeight > 0 ? userHeight : autoHeight

    // Tamaño y posición elegidos por el usuario (solo mientras la aplicación está abierta).
    property real userWidth: defaultWidth
    property real userHeight: -1  // altura desplegado; -1: la calcula el contenido
    property bool placed: false  // false: la esquina de `ui.hudCorner`
    property bool placedRight: false
    property bool placedBottom: false
    property real placedEdgeX: 0  // borde anclado: el derecho si `placedRight`, si no el izquierdo
    property real placedEdgeY: 0  // borde anclado: el inferior si `placedBottom`, si no el superior
    property bool resizing: false

    readonly property bool anchorRight: placed ? placedRight : atRight
    readonly property bool anchorBottom: placed ? placedBottom : atBottom
    readonly property real edgeX: placed ? placedEdgeX
                                  : Screen.virtualX + (atRight ? Screen.desktopAvailableWidth - gap
                                                               : gap)
    readonly property real edgeY: placed ? placedEdgeY
                                  : Screen.virtualY + (atBottom ? Screen.desktopAvailableHeight - gap
                                                                : gap)

    width: userWidth
    height: wanted
    x: anchorRight ? edgeX - width : edgeX
    y: anchorBottom ? edgeY - height : edgeY

    Behavior on height {
        enabled: !ui.reduceMotion && !hudWindow.resizing
        NumberAnimation { duration: Theme.motionPanel; easing.type: Easing.OutCubic }
    }

    // Fija la posición dada como colocada por el usuario, anclada al borde más cercano.
    function place(left, top) {
        var middleX = Screen.virtualX + Screen.width / 2
        var middleY = Screen.virtualY + Screen.height / 2
        placedRight = left + width / 2 > middleX
        placedBottom = top + height / 2 > middleY
        placedEdgeX = placedRight ? left + width : left
        placedEdgeY = placedBottom ? top + height : top
        placed = true
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

        // Arrastrar la cabecera mueve la ventana. No cubre los botones ni la caja de texto.
        MouseArea {
            id: mover

            property point pressGlobal
            property point pressWindow

            x: 0
            y: 0
            width: buttons.x - Theme.space4
            height: input.y
            cursorShape: pressed ? Qt.ClosedHandCursor : Qt.ArrowCursor

            onPressed: function (mouse) {
                pressGlobal = mapToGlobal(mouse.x, mouse.y)
                pressWindow = Qt.point(hudWindow.x, hudWindow.y)
                hudWindow.place(hudWindow.x, hudWindow.y)
            }
            onPositionChanged: function (mouse) {
                if (!pressed)
                    return
                var now = mapToGlobal(mouse.x, mouse.y)
                hudWindow.place(pressWindow.x + now.x - pressGlobal.x,
                                pressWindow.y + now.y - pressGlobal.y)
            }
        }

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

            IconButton {
                objectName: "hudOpenScreen"
                icon: "pantalla"
                onClicked: windows.hudOpenScreen()
            }

            IconButton {
                icon: "ocultar"
                onClicked: windows.hudDismissed()
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
                visible: assistant.activePanel.length === 0 && !dialog.shown
            }

            PanelHost {
                anchors.fill: parent
                flat: true
                panel: assistant.activePanel
                visible: panel.length > 0 && !dialog.shown
            }

            // Mientras hay una pregunta, se superpone al panel activo.
            DialogCard {
                id: dialog

                objectName: "hudDialogCard"
                width: parent.width
                flat: true
            }
        }

        // --- Asa de tamaño: en la esquina contraria a la anclada -----------------------------

        MouseArea {
            id: grip

            readonly property bool atLeft: hudWindow.anchorRight
            readonly property bool atTop: hudWindow.anchorBottom
            property point pressGlobal
            property real pressWidth
            property real pressHeight

            width: 16
            height: 16
            x: atLeft ? 0 : frame.width - width
            y: atTop ? 0 : frame.height - height
            z: 10
            hoverEnabled: true
            cursorShape: atLeft === atTop ? Qt.SizeFDiagCursor : Qt.SizeBDiagCursor

            onPressed: function (mouse) {
                pressGlobal = mapToGlobal(mouse.x, mouse.y)
                pressWidth = hudWindow.width
                pressHeight = hudWindow.height
                hudWindow.place(hudWindow.x, hudWindow.y)
                hudWindow.resizing = true
            }
            onReleased: hudWindow.resizing = false
            onCanceled: hudWindow.resizing = false
            onPositionChanged: function (mouse) {
                if (!pressed)
                    return
                var now = mapToGlobal(mouse.x, mouse.y)
                var dx = (now.x - pressGlobal.x) * (atLeft ? -1 : 1)
                var dy = (now.y - pressGlobal.y) * (atTop ? -1 : 1)
                hudWindow.userWidth = Math.max(hudWindow.minWidth,
                                               Math.min(hudWindow.maxWidth, pressWidth + dx))
                if (hud.expanded)  // plegado, la altura es fija
                    hudWindow.userHeight = Math.max(hudWindow.minExpandedHeight,
                                                    Math.min(hudWindow.maxUserHeight,
                                                             pressHeight + dy))
            }
            onDoubleClicked: {  // vuelve al tamaño por defecto
                hudWindow.userWidth = hudWindow.defaultWidth
                hudWindow.userHeight = -1
            }

            // Dos trazos diagonales que apuntan a la esquina del asa.
            Canvas {
                anchors.fill: parent
                anchors.margins: 3
                opacity: grip.containsMouse || grip.pressed ? 1 : 0.5
                rotation: grip.atTop ? (grip.atLeft ? 180 : 270) : (grip.atLeft ? 90 : 0)
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    ctx.strokeStyle = Theme.textSecondary
                    ctx.lineWidth = Theme.iconStroke
                    ctx.lineCap = "round"
                    ctx.beginPath()
                    ctx.moveTo(width, 0)
                    ctx.lineTo(0, height)
                    ctx.moveTo(width, height / 2)
                    ctx.lineTo(width / 2, height)
                    ctx.stroke()
                }
            }
        }
    }
}
