// Ventana flotante de la pantalla de sesión: cabecera con icono, título y estado, y el panel
// de un módulo como contenido. Se mueve arrastrando la cabecera, cambia de tamaño desde
// cualquier borde o esquina, pasa al frente al pulsarla y se cierra con su botón.
//
// No guarda su disposición: la recibe en fracciones del área de trabajo (`fx`, `fy`, `fw`,
// `fh`) y pide los cambios con sus señales. El dueño es `workspace` (`ui/workspace.py`).
import QtQuick
import ".."

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
    default property alias content: body.data

    objectName: "window-" + windowId

    signal moved(real fx, real fy)
    signal resized(real fx, real fy, real fw, real fh)
    signal closed()
    signal activated()

    width: Math.min(areaWidth, Math.max(minWidth, Math.round(fw * areaWidth)))
    height: Math.min(areaHeight, Math.max(minHeight, Math.round(fh * areaHeight)))
    x: Math.max(0, Math.min(areaWidth - width, Math.round(fx * areaWidth)))
    y: Math.max(0, Math.min(areaHeight - height, Math.round(fy * areaHeight)))

    visible: opacity > 0
    opacity: open ? 1 : 0
    scale: open ? 1 : 0.97

    Behavior on opacity {
        NumberAnimation { duration: ui.reduceMotion ? 0 : Theme.motionWindow }
    }
    Behavior on scale {
        NumberAnimation {
            duration: ui.reduceMotion ? 0 : Theme.motionWindow
            easing.type: Easing.OutCubic
        }
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

    Rectangle {
        id: frame

        anchors.fill: parent
        radius: Theme.radiusWindow
        color: Theme.bgWindow
        border.width: 1
        border.color: win.focused ? Theme.lineStrong : Theme.lineSoft

        Behavior on border.color {
            ColorAnimation { duration: Theme.motionWindow }
        }
    }

    // --- Cabecera ----------------------------------------------------------------------------

    Item {
        id: header

        x: 1
        y: 1
        width: parent.width - 2
        height: Theme.windowHeader
        clip: true

        // Más alto que la cabecera: sus esquinas inferiores quedan fuera y no se ven.
        Rectangle {
            width: parent.width
            height: parent.height + Theme.radiusWindow
            radius: Theme.radiusWindow - 1
            opacity: win.focused ? 1 : 0.45

            gradient: Gradient {
                GradientStop { position: 0; color: Theme.alpha(Theme.primaryDeep, 0.85) }
                GradientStop { position: 1; color: Theme.alpha(Theme.primaryDeep, 0.20) }
            }

            Behavior on opacity {
                NumberAnimation { duration: Theme.motionWindow }
            }
        }

        MouseArea {
            id: mover

            property real offsetX: 0
            property real offsetY: 0

            anchors.fill: parent
            cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor

            onPressed: (mouse) => {
                var point = mapToItem(win.parent, mouse.x, mouse.y)
                offsetX = point.x - win.x
                offsetY = point.y - win.y
            }
            onPositionChanged: (mouse) => {
                if (!pressed || win.areaWidth <= 0 || win.areaHeight <= 0)
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
    }

    // Trazo de acento bajo el título: marca la ventana que está encima.
    Rectangle {
        x: Theme.space12
        y: header.y + header.height
        width: 40
        height: 1
        color: Theme.primary
        opacity: win.focused ? 1 : 0

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

    // Marca del asa de la esquina inferior derecha.
    Canvas {
        x: win.width - width - 4
        y: win.height - height - 4
        width: 9
        height: 9
        opacity: win.focused ? 0.8 : 0.35

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

    // Cualquier pulsación trae la ventana al frente. No consume el evento: sigue hacia el
    // control que haya debajo.
    MouseArea {
        anchors.fill: parent
        onPressed: (mouse) => {
            win.activated()
            mouse.accepted = false
        }
    }
}
