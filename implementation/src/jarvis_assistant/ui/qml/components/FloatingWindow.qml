// Ventana flotante de la pantalla de sesión: cabecera con icono, título y estado, y el panel
// de un módulo como contenido. Se mueve arrastrando la cabecera, cambia de tamaño desde
// cualquier borde o esquina, pasa al frente al pulsarla y se cierra con su botón.
//
// `frameStyle` elige la forma del marco y la textura del fondo (`outline.js`): «round»,
// «cut» (chaflanes y líneas de barrido), «leaf» (esquinas alternas y retícula de puntos) o
// «bracket» (recto, con las esquinas marcadas por fuera). Un trazo de neón recorre el borde;
// corre más en la ventana que está encima, se enciende al paso del latido del orbe (`beat`)
// y se apaga en reposo.
//
// Apartada (`aside`), sale lanzada hacia su pestaña (`tabX`, `tabY`), en un borde o una
// esquina, y se encoge por el camino hasta quedar en la cabecera: icono, título y cerrar. Se
// aparta con un triple clic en la cabecera; un clic en la pestaña la devuelve a su sitio y a
// su tamaño. Apartada no se mueve ni cambia de tamaño.
//
// No guarda su disposición: la recibe en fracciones del área de trabajo (`fx`, `fy`, `fw`,
// `fh`) y pide los cambios con sus señales. El dueño es `workspace` (`ui/workspace.py`).
import QtQuick
import QtQuick.Shapes
import ".."
import "outline.js" as Outline

Item {
    id: win

    property string windowId: ""
    property string title: ""
    property string icon: "tarea"
    property string subtitle: ""         // estado del panel, a la derecha del título
    property bool open: false
    property bool focused: false         // es la ventana que queda encima
    property real fx: 0
    property real fy: 0
    property real fw: 0.2
    property real fh: 0.4
    property int minWidth: 300
    property int minHeight: 220
    property real areaWidth: 0           // área de trabajo, en píxeles
    property real areaHeight: 0
    property string frameStyle: "round"
    property real beat: 0                // brillo del latido del orbe a la altura de la ventana
    property bool held: false            // abierta pero oculta: espera a que el orbe la lance
    property real originX: 0             // centro del orbe, en coordenadas del área de trabajo
    property real originY: 0
    property real launch: 1              // salida desde el orbe: 0 en su centro, 1 en su sitio
    property bool aside: false           // apartada a un borde: solo se ve la cabecera
    property real tabX: 0                // sitio de la pestaña al estar apartada
    property real tabY: 0
    default property alias content: body.data

    readonly property var outline: Outline.corners(frameStyle)
    readonly property string outlinePath: Outline.path(width, height, outline, 0.5)
    // En reposo no queda movimiento llamativo: el neón se apaga.
    readonly property real live: assistant.activity === "reposo" ? 0 : 1
    readonly property bool accelerated: GraphicsInfo.api !== GraphicsInfo.Software
    property real headerTone: focused ? 1 : 0.45

    Behavior on headerTone {
        NumberAnimation { duration: Theme.motionWindow }
    }

    objectName: "window-" + windowId

    signal moved(real fx, real fy)
    signal resized(real fx, real fy, real fw, real fh)
    signal closed()
    signal activated()
    signal appeared()                    // ha pasado de oculta a visible
    signal asideRequested()              // triple clic en la cabecera
    signal restored()                    // clic en la pestaña de una ventana apartada

    // Su rectángulo sin apartar. Al apartarla se conserva: es adonde vuelve.
    readonly property real fullWidth:
        Math.min(areaWidth, Math.max(minWidth, Math.round(fw * areaWidth)))
    readonly property real fullHeight:
        Math.min(areaHeight, Math.max(minHeight, Math.round(fh * areaHeight)))
    readonly property real fullX:
        Math.max(0, Math.min(areaWidth - fullWidth, Math.round(fx * areaWidth)))
    readonly property real fullY:
        Math.max(0, Math.min(areaHeight - fullHeight, Math.round(fy * areaHeight)))
    readonly property int tabWidth: Theme.windowTab
    readonly property int tabHeight: Theme.windowHeader + 2

    // Avance del apartado: 0 en su sitio, 1 en su pestaña. Al apartarse pasa un poco de 1 al
    // llegar, como si chocara con el borde. Oculta no se anima: se abre ya en su forma.
    property real tuck: aside ? 1 : 0
    // El contenido se apaga en el primer tramo del viaje y se enciende en el último.
    readonly property real fold: Math.max(0, Math.min(1, tuck * 2.2))

    Behavior on tuck {
        enabled: win.visible && !ui.reduceMotion
        NumberAnimation {
            duration: Theme.motionAside
            easing.type: win.aside ? Easing.OutBack : Easing.OutCubic
            easing.overshoot: 0.9
        }
    }
    // Una pestaña ya apartada se desliza si las de su borde se recolocan.
    Behavior on tabX {
        enabled: win.aside && win.tuck >= 1 && !ui.reduceMotion
        NumberAnimation { duration: Theme.motionPanel; easing.type: Easing.OutCubic }
    }
    Behavior on tabY {
        enabled: win.aside && win.tuck >= 1 && !ui.reduceMotion
        NumberAnimation { duration: Theme.motionPanel; easing.type: Easing.OutCubic }
    }

    width: Math.round(fullWidth + (tabWidth - fullWidth) * tuck)
    height: Math.round(fullHeight + (tabHeight - fullHeight) * tuck)
    x: Math.round(fullX + (tabX - fullX) * tuck)
    y: Math.round(fullY + (tabY - fullY) * tuck)
    // Un leve giro hacia donde va mientras viaja: se lanza, no se desliza.
    rotation: ui.reduceMotion || tuck <= 0 || tuck >= 1 ? 0
              : 3 * Math.sin(Math.PI * tuck) * (tabX >= fullX ? 1 : -1)

    readonly property bool shown: open && !held
    property real pop: shown ? 1 : 0.97  // escala al abrir y cerrar a mano

    onShownChanged: {
        if (shown)
            appeared()
    }

    visible: opacity > 0
    opacity: shown ? 1 : 0
    scale: pop * (0.06 + 0.94 * launch)
    // `scale` crece desde el centro de la ventana; esto la lleva del orbe a su sitio.
    transform: Translate {
        x: (1 - win.launch) * (win.originX - win.x - win.width / 2)
        y: (1 - win.launch) * (win.originY - win.y - win.height / 2)
    }

    Behavior on opacity {
        NumberAnimation { duration: ui.reduceMotion ? 0 : Theme.motionWindow }
    }
    Behavior on pop {
        NumberAnimation {
            duration: ui.reduceMotion ? 0 : Theme.motionWindow
            easing.type: Easing.OutCubic
        }
    }

    // Deja de esperar y sale del centro del orbe hasta su sitio.
    function emerge() {
        if (ui.reduceMotion) {
            held = false
            return
        }
        launch = 0
        held = false
        launcher.restart()
    }

    NumberAnimation {
        id: launcher

        target: win
        property: "launch"
        from: 0
        to: 1
        duration: Theme.motionEmerge
        easing.type: Easing.OutCubic
    }

    // Nuevo rectángulo al tirar de un borde: `hx`, `hy` dicen qué bordes se mueven.
    function stretch(start, hx, hy, dx, dy) {
        if (areaWidth <= 0 || areaHeight <= 0)
            return
        var left = start.x
        var top = start.y
        var right = start.x + start.width
        var bottom = start.y + start.height
        if (hx < 0)
            left = Math.max(0, Math.min(right - minWidth, left + dx))
        else if (hx > 0)
            right = Math.min(areaWidth, Math.max(left + minWidth, right + dx))
        if (hy < 0)
            top = Math.max(0, Math.min(bottom - minHeight, top + dy))
        else if (hy > 0)
            bottom = Math.min(areaHeight, Math.max(top + minHeight, bottom + dy))
        win.resized(left / areaWidth, top / areaHeight,
                    (right - left) / areaWidth, (bottom - top) / areaHeight)
    }

    // --- Sombra ------------------------------------------------------------------------------

    Rectangle {
        anchors.fill: parent
        anchors.margins: -10
        anchors.topMargin: -4
        radius: Theme.radiusWindow + 10
        color: Theme.shadowFar
        visible: win.focused
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: -3
        anchors.topMargin: 0
        radius: Theme.radiusWindow + 3
        color: Theme.shadowNear
    }

    // --- Marco -------------------------------------------------------------------------------

    // Sin aceleración gráfica las formas no se rellenan: el marco es un rectángulo liso.
    Rectangle {
        anchors.fill: parent
        visible: !win.accelerated
        radius: Theme.radiusCard
        color: Theme.bgWindow
        border.width: 1
        border.color: win.focused ? Theme.lineStrong : Theme.lineSoft
    }

    // Fondo y borde con la forma del marco y, encima, el degradado de la cabecera. Solo se
    // recalculan al cambiar el tamaño o el foco, nunca en cada fotograma.
    Shape {
        id: frame

        anchors.fill: parent
        visible: win.accelerated
        preferredRendererType: Shape.CurveRenderer

        ShapePath {
            strokeWidth: 1
            strokeColor: win.focused ? Theme.lineStrong : Theme.lineSoft
            fillColor: Theme.bgWindow
            PathSvg { path: win.outlinePath }
        }

        ShapePath {
            strokeWidth: -1
            fillGradient: LinearGradient {
                x1: 0
                y1: 0
                x2: 0
                y2: Theme.windowHeader + 1
                GradientStop {
                    position: 0
                    color: Theme.alpha(Theme.primaryDeep, 0.85 * win.headerTone)
                }
                GradientStop {
                    position: 0.999
                    color: Theme.alpha(Theme.primaryDeep, 0.20 * win.headerTone)
                }
                GradientStop { position: 1; color: Theme.alpha(Theme.primaryDeep, 0) }
            }
            PathSvg { path: win.outlinePath }
        }
    }

    // Textura del fondo, propia de cada forma de marco. Se pinta una vez; al cambiar el
    // tamaño de la ventana espera a que el arrastre se detenga para repintarse.
    Canvas {
        id: texture

        readonly property string kind: win.frameStyle

        anchors.fill: parent
        visible: win.accelerated && ui.quality !== "low"
        opacity: win.focused ? 1 : 0.6

        onKindChanged: repaint.restart()
        onWidthChanged: repaint.restart()
        onHeightChanged: repaint.restart()

        Timer {
            id: repaint
            interval: 120
            onTriggered: texture.requestPaint()
        }

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            if (width <= 0 || height <= 0)
                return
            Outline.trace(ctx, width, height, win.outline, 1)
            ctx.clip()
            var top = Theme.windowHeader + 2
            if (kind === "cut") {
                // Líneas de barrido, como una terminal.
                ctx.fillStyle = Theme.alpha(Theme.primary, 0.035)
                for (var y = top; y < height; y += 4)
                    ctx.fillRect(0, y, width, 1)
            } else if (kind === "leaf") {
                // Retícula de puntos.
                ctx.fillStyle = Theme.alpha(Theme.primary, 0.13)
                for (var py = top + 8; py < height; py += 18)
                    for (var px = 10; px < width; px += 18)
                        ctx.fillRect(px, py, 1, 1)
            } else if (kind === "bracket") {
                // Trama diagonal en la esquina inferior izquierda.
                ctx.strokeStyle = Theme.alpha(Theme.primary, 0.07)
                ctx.lineWidth = 1
                ctx.beginPath()
                for (var d = 8; d <= 96; d += 8) {
                    ctx.moveTo(0, height - d)
                    ctx.lineTo(d, height)
                }
                ctx.stroke()
            } else {
                // Resplandor suave que cae desde la cabecera.
                var glow = ctx.createLinearGradient(0, top, 0, Math.min(height, top + 140))
                glow.addColorStop(0, Theme.alpha(Theme.primary, 0.06))
                glow.addColorStop(1, Theme.alpha(Theme.primary, 0))
                ctx.fillStyle = glow
                ctx.fillRect(0, top, width, 140)
            }
        }
    }

    // El neón que recorre el borde.
    NeonTrace {
        anchors.fill: parent
        visible: drawn && win.accelerated
        path: win.outlinePath
        length: Outline.length(win.width, win.height, win.outline, 0.5)
        count: win.frameStyle === "leaf" ? 2 : 1
        tail: win.frameStyle === "leaf" ? 56 : 80
        speed: Theme.neonSpeed * (win.focused ? 1 : 0.55)
        strength: win.live * (win.focused ? 0.85 : 0.35)
        boost: win.beat * win.live
        running: win.open
    }

    // Marco «bracket»: cuatro esquinas marcadas por fuera, que se abren con el latido.
    Repeater {
        model: win.frameStyle === "bracket" && win.accelerated ? 4 : 0

        Item {
            id: mark

            required property int index
            readonly property bool atRight: index % 2 === 1
            readonly property bool atBottom: index >= 2
            readonly property real gap: 4 + 3 * win.beat * win.live

            x: atRight ? win.width + gap - width : -gap
            y: atBottom ? win.height + gap - height : -gap
            width: Theme.cornerMark
            height: Theme.cornerMark
            opacity: win.focused ? 0.9 : 0.4

            Behavior on opacity {
                NumberAnimation { duration: Theme.motionWindow }
            }

            Rectangle {
                width: parent.width
                height: 1
                y: mark.atBottom ? parent.height - 1 : 0
                color: Theme.primary
            }

            Rectangle {
                width: 1
                height: parent.height
                x: mark.atRight ? parent.width - 1 : 0
                color: Theme.primary
            }
        }
    }

    // --- Cabecera ----------------------------------------------------------------------------

    Item {
        id: header

        x: 1
        y: 1
        width: parent.width - 2
        height: Theme.windowHeader

        MouseArea {
            id: mover

            property real offsetX: 0
            property real offsetY: 0

            anchors.fill: parent
            property int clicks: 0           // pulsaciones seguidas, para el triple clic
            property double lastPress: 0
            property point lastPoint
            property bool thrown: false      // esta pulsación ha apartado la ventana

            cursorShape: win.aside ? Qt.PointingHandCursor
                                   : pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor

            onPressed: (mouse) => {
                var point = mapToItem(win.parent, mouse.x, mouse.y)
                offsetX = point.x - win.x
                offsetY = point.y - win.y
                thrown = false
                if (win.aside) {
                    clicks = 0
                    return
                }
                var now = Date.now()
                var near = Math.abs(mouse.x - lastPoint.x) < 8
                           && Math.abs(mouse.y - lastPoint.y) < 8
                clicks = near && now - lastPress <= Qt.styleHints.mouseDoubleClickInterval
                         ? clicks + 1 : 1
                lastPress = now
                lastPoint = Qt.point(mouse.x, mouse.y)
                if (clicks >= 3) {
                    clicks = 0
                    thrown = true
                    win.asideRequested()
                }
            }
            onClicked: {
                // El clic que la aparta no la recupera.
                if (win.aside && !thrown)
                    win.restored()
            }
            onPositionChanged: (mouse) => {
                if (!pressed || win.aside || win.areaWidth <= 0 || win.areaHeight <= 0)
                    return
                var point = mapToItem(win.parent, mouse.x, mouse.y)
                var left = Math.max(0, Math.min(win.areaWidth - win.width, point.x - offsetX))
                var top = Math.max(0, Math.min(win.areaHeight - win.height, point.y - offsetY))
                win.moved(left / win.areaWidth, top / win.areaHeight)
            }
        }

        Image {
            id: glyph

            x: Theme.space12
            width: 16
            height: 16
            sourceSize.width: 32
            sourceSize.height: 32
            source: Theme.icon(win.icon)
            opacity: win.focused ? 1 : 0.7
            anchors.verticalCenter: parent.verticalCenter
        }

        DisplayText {
            id: caption

            x: glyph.x + glyph.width + Theme.space8
            width: Math.min(implicitWidth, close.x - x - Theme.space8)
            text: win.title
            size: Theme.sizeSecondary
            color: win.focused ? Theme.textPrimary : Theme.textSecondary
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            x: caption.x + caption.width + Theme.space12
            width: Math.max(0, close.x - x - Theme.space8)
            opacity: 1 - win.fold
            text: win.subtitle
            color: Theme.textMuted
            font.family: Theme.fontBody
            font.pixelSize: Theme.sizeLabel
            horizontalAlignment: Text.AlignRight
            elide: Text.ElideRight
            anchors.verticalCenter: parent.verticalCenter
        }

        IconButton {
            id: close

            x: parent.width - width - Theme.space4
            icon: "ocultar"
            anchors.verticalCenter: parent.verticalCenter
            onClicked: win.closed()
        }
    }

    Rectangle {
        x: 1
        y: header.y + header.height
        width: parent.width - 2
        height: 1
        color: Theme.lineSoft
        opacity: 1 - win.fold
    }

    // Trazo de acento bajo el título: marca la ventana que está encima.
    Rectangle {
        x: Theme.space12
        y: header.y + header.height
        width: 40
        height: 1
        color: Theme.primary
        opacity: win.focused ? 1 - win.fold : 0

        Behavior on opacity {
            NumberAnimation { duration: Theme.motionWindow }
        }
    }

    // --- Contenido ---------------------------------------------------------------------------

    Item {
        id: body

        anchors.fill: parent
        anchors.topMargin: header.y + header.height + 1 + Theme.space12
        anchors.leftMargin: Theme.space12
        anchors.rightMargin: Theme.space12
        anchors.bottomMargin: Theme.space12
        clip: true
        opacity: 1 - win.fold
        visible: opacity > 0
    }

    // --- Asas de tamaño: cuatro bordes y cuatro esquinas -------------------------------------

    Repeater {
        model: [[-1, -1], [0, -1], [1, -1], [-1, 0], [1, 0], [-1, 1], [0, 1], [1, 1]]

        MouseArea {
            id: grip

            required property var modelData
            readonly property int hx: modelData[0]
            readonly property int hy: modelData[1]
            readonly property int corner: 14
            property point origin
            property rect start

            enabled: !win.aside
            width: hx === 0 ? win.width - 2 * corner : hy === 0 ? Theme.windowGrip : corner
            height: hy === 0 ? win.height - 2 * corner : hx === 0 ? Theme.windowGrip : corner
            x: hx < 0 ? 0 : hx === 0 ? corner : win.width - width
            y: hy < 0 ? 0 : hy === 0 ? corner : win.height - height
            cursorShape: hx === 0 ? Qt.SizeVerCursor
                         : hy === 0 ? Qt.SizeHorCursor
                         : hx === hy ? Qt.SizeFDiagCursor : Qt.SizeBDiagCursor

            onPressed: (mouse) => {
                origin = mapToItem(win.parent, mouse.x, mouse.y)
                start = Qt.rect(win.x, win.y, win.width, win.height)
            }
            onPositionChanged: (mouse) => {
                if (!pressed)
                    return
                var point = mapToItem(win.parent, mouse.x, mouse.y)
                win.stretch(start, hx, hy, point.x - origin.x, point.y - origin.y)
            }
        }
    }

    // Marca del asa de la esquina inferior derecha. Con chaflán, el propio corte hace de asa.
    Canvas {
        visible: win.outline[2][0] !== "cut" && !win.aside
        x: win.width - width - 4
        y: win.height - height - 4
        width: 9
        height: 9
        opacity: (win.focused ? 0.8 : 0.35) * (1 - win.fold)

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.strokeStyle = Theme.textMuted
            ctx.lineWidth = 1
            ctx.lineCap = "round"
            ctx.beginPath()
            ctx.moveTo(width, 1)
            ctx.lineTo(1, height)
            ctx.moveTo(width, height / 2 + 1)
            ctx.lineTo(width / 2 + 1, height)
            ctx.stroke()
        }
    }

    // Cualquier pulsación trae la ventana al frente y, en reposo, despierta al asistente. No
    // consume el evento: sigue hacia el control que haya debajo.
    MouseArea {
        anchors.fill: parent
        onPressed: (mouse) => {
            win.activated()
            assistant.windowPressed()
            mouse.accepted = false
        }
    }
}
