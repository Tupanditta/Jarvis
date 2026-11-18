// Pantalla de sesión (Interfaz, sección 5; hud.md, sección 1).
// Pantalla completa en el monitor principal. Visible también en dormido: fondo oscuro, orbe
// apagado, la caja de texto y, encima, el selector de perfiles. Con la sesión abierta muestra
// las ventanas flotantes de los módulos y su selector. Dónde van las ventanas y las dos barras
// lo dice la plantilla del perfil (`workspace`). Cerrarla solo la oculta: el proceso sigue en
// la bandeja.
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
    readonly property bool asleep: assistant.activity === "dormido"
    // Dormido y ya en calma: sin sesión y sin la animación de cierre en curso. Lo propio de la
    // pantalla dormida (perfiles, configuración) espera a que el orbe termine de colapsar.
    readonly property bool dormant: asleep && !assistant.sessionOpen && !orb.inTransition
    // La caja de texto está en la mitad de abajo: subtítulos y perfiles van encima de ella.
    readonly property bool inputLow: input.y + input.height / 2 >= height / 2
    property real panels: 0              // opacidad de paneles y subtítulos
    property bool cursorHidden: false

    function focusInput() {
        if (access.gateOpen)
            gate.focusInput()
        else
            input.focusInput()
    }

    onActiveChanged: {
        if (active)
            screen.focusInput()
    }

    onClosing: (close) => {
        close.accepted = windows.acceptClose()
    }

    // --- Transiciones ------------------------------------------------------------------------

    Connections {
        target: windows

        function onScreenAnimation(kind) {
            // Al abrir sesión las ventanas esperan al orbe y salen de él al acabar el despertar.
            if (kind === "wake")
                desk.hold()
            else
                desk.cancel()
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

        onAwake: desk.release()
    }

    // --- Medidores ----------------------------------------------------------------------------

    // Separación entre dos medidores en la misma esquina.
    readonly property real meterGap: Theme.space24
    // El de ruido se pone al lado del de recursos si comparten esquina: hacia dentro.
    readonly property bool metersJoined: usage.shown && noise.shown
                                         && usage.corner === noise.corner

    // Ancho que ocupan los medidores en una esquina inferior, desde el borde de la pantalla
    // (margen incluido); 0 si no hay ninguno. Con las posiciones finales, no las animadas.
    function cornerSpan(side) {
        var span = 0
        if (meter.visible && usage.corner === side)
            span += meter.width
        if (noiseMeter.visible && noise.corner === side)
            span += (span > 0 ? meterGap : 0) + noiseMeter.width
        return span > 0 ? span + margin : 0
    }

    function cornerHeight(side) {
        var tall = 0
        if (meter.visible && usage.corner === side)
            tall = meter.height
        if (noiseMeter.visible && noise.corner === side)
            tall = Math.max(tall, noiseMeter.height)
        return tall > 0 ? tall + margin : 0
    }

    // CPU y RAM del asistente, fijo en una esquina inferior y por debajo de las ventanas.
    ResourceMeter {
        id: meter

        objectName: "resourceMeter"
        width: implicitWidth
        height: implicitHeight
        x: usage.corner === "left" ? screen.margin : screen.width - width - screen.margin
        y: screen.height - height - screen.margin
        opacity: screen.panels
        visible: usage.shown && opacity > 0
        watching: visible && screen.drawing

        Behavior on x {
            NumberAnimation {
                duration: ui.reduceMotion ? 0 : Theme.motionAside
                easing.type: Easing.InOutCubic
            }
        }
    }

    // Ruido alrededor, en decibelios. Junto al de recursos si están en la misma esquina; si
    // no, en la suya.
    NoiseMeter {
        id: noiseMeter

        readonly property real inset: screen.metersJoined ? meter.width + screen.meterGap : 0

        objectName: "noiseMeter"
        width: implicitWidth
        height: implicitHeight
        x: noise.corner === "left" ? screen.margin + inset
                                   : screen.width - width - screen.margin - inset
        y: screen.height - height - screen.margin
        opacity: screen.panels
        visible: noise.shown && opacity > 0
        watching: visible && screen.drawing

        Behavior on x {
            NumberAnimation {
                duration: ui.reduceMotion ? 0 : Theme.motionAside
                easing.type: Easing.InOutCubic
            }
        }
    }

    // --- Ventanas flotantes -----------------------------------------------------------------

    // Una ventana por módulo. Se abren solas cuando su módulo muestra algo y a mano desde el
    // selector; se mueven, cambian de tamaño y se cierran con el ratón.
    Workspace {
        id: desk

        x: Theme.space8
        y: Theme.space8
        width: screen.width - 2 * Theme.space8
        height: Math.max(0, screen.height - 2 * Theme.space8)
        opacity: screen.panels
        visible: opacity > 0
        conductor: orb
        centerX: orb.x + orb.width / 2 - x
        centerY: orb.y + orb.height / 2 - y
        // Las pestañas de las ventanas apartadas no tapan el selector si está arriba.
        readonly property bool dockOnTop: dock.y < Theme.space48
        reserveLeft: dockOnTop ? dock.x - x : 0
        reserveRight: dockOnTop ? dock.x + dock.width - x : 0
        // Ni los medidores de las esquinas inferiores.
        reserveBottomLeft: Qt.size(Math.max(0, screen.cornerSpan("left") - x),
                                   Math.max(0, screen.cornerHeight("left") - y))
        reserveBottomRight: Qt.size(Math.max(0, screen.cornerSpan("right") - x),
                                    Math.max(0, screen.cornerHeight("right") - y))
    }

    Dock {
        id: dock

        // Centro en las fracciones de la plantilla, sin salirse de la pantalla.
        x: Math.round(Math.max(0, Math.min(screen.width - width,
                                           workspace.dockX * screen.width - width / 2)))
        y: Math.round(Math.max(0, Math.min(screen.height - height,
                                           workspace.dockY * screen.height - height / 2)))
        z: 1
        opacity: screen.panels
        visible: opacity > 0
    }

    // --- Diálogo ------------------------------------------------------------------------------

    // La pregunta en curso, sobre el lateral derecho y por encima de las ventanas.
    DialogCard {
        objectName: "dialogCard"
        width: Math.min(420, screen.width - 2 * screen.margin)
        anchors.right: parent.right
        anchors.rightMargin: screen.margin
        anchors.verticalCenter: orb.verticalCenter
        z: 2
    }

    // --- Subtítulos y caja de texto ----------------------------------------------------------

    Subtitles {
        id: subtitles

        width: Math.min(900, screen.width - 2 * screen.margin)
        x: Math.round(Math.max(0, Math.min(screen.width - width,
                                           input.x + input.width / 2 - width / 2)))
        y: screen.inputLow ? input.y - height - Theme.space16
                           : input.y + input.height + Theme.space16
        visible: screen.panels > 0
        opacity: shown ? screen.panels : 0
    }

    // Solo en dormido, en el centro bajo el orbe: el perfil con el que se abrirá la sesión.
    ProfilePicker {
        objectName: "profilePicker"
        shown: screen.dormant && !access.gateOpen
        anchors.horizontalCenter: parent.horizontalCenter
        y: Math.round(orb.y + orb.height / 2 + Theme.space48)
    }

    // Solo en dormido, junto a la caja: la entrada a la configuración. Es el único sitio desde
    // el que se configura el asistente.
    Chip {
        objectName: "settingsButton"
        visible: screen.dormant && windows.settingsAvailable && !access.gateOpen
        icon: "ajustes"
        text: windows.configuring ? "Configuración abierta" : "Configuración"
        selected: windows.configuring
        x: Math.round(Math.max(0, Math.min(screen.width - width,
                                           input.x + input.width / 2 - width / 2)))
        y: screen.inputLow ? input.y - height - Theme.space16
                           : input.y + input.height + Theme.space16
        onClicked: windows.openSettings()
    }

    CommandInput {
        id: input

        width: Math.round(Math.min(screen.width - 2 * Theme.space8,
                                   Math.max(300, workspace.inputWidth * screen.width)))
        x: Math.round(Math.max(Theme.space8, Math.min(screen.width - width - Theme.space8,
                                                      workspace.inputX * screen.width - width / 2)))
        y: Math.round(Math.max(Theme.space8, Math.min(screen.height - height - Theme.space8,
                                                      workspace.inputY * screen.height - height / 2)))
        focus: true
        // Con la configuración abierta no se puede iniciar sesión; con la caja de la contraseña
        // abierta, se escribe en ella.
        enabled: !windows.configuring && !access.gateOpen
        onBrowse: (delta) => {
            if (profiles.count > 1)
                profiles.step(delta)
        }
    }

    // Perfil protegido: la contraseña, en el centro y por encima de todo.
    AccessGate {
        id: gate

        anchors.fill: parent
        z: 10
        onClosed: input.focusInput()
    }

    // Aviso crítico de intrusión, en el centro, hasta que se confirma.
    IntrusionCard {
        width: Math.min(560, screen.width - 2 * screen.margin)
        anchors.centerIn: parent
        z: 9
    }

    FrameCounter {
        visible: ui.debug
        x: Theme.space8
        y: Theme.space8
    }
}
