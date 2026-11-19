// Editor de plantillas (configurador.md): la pantalla de sesión, inerte y a pantalla completa.
// Las ventanas que la plantilla muestra se mueven y se redimensionan como en la sesión; las
// dos barras se arrastran y la caja de texto cambia de ancho desde sus extremos. Nada más
// responde: no hay asistente, la caja no admite texto y el selector no abre ventanas. Una
// paleta flotante reúne el nombre, qué ventanas y medidores se muestran y Aceptar o Cancelar.
//
// Usa el mismo modelo (`workspace`) y los mismos componentes que la pantalla de sesión, con la
// misma área de trabajo: lo que se ve aquí es lo que se verá al abrir sesión.
import QtQuick
import QtQuick.Window
import "../../ui/qml"
import "../../ui/qml/components"
import "controls"

Window {
    id: screen

    objectName: "layoutEditor"
    title: "Editor de plantilla"
    color: Theme.bgBase
    width: 1366
    height: 768
    visibility: editor.active ? Window.FullScreen : Window.Hidden
    flags: Qt.Window | Qt.FramelessWindowHint

    onVisibilityChanged: {
        if (visibility !== Window.Hidden) {
            raise()
            requestActivate()
        }
    }

    onClosing: (close) => {
        close.accepted = false
        editor.cancel()
    }

    Shortcut {
        sequence: "Esc"
        enabled: editor.active
        onActivated: editor.cancel()
    }

    // ¿Se tocan dos rectángulos?
    function overlaps(a, b) {
        return a.x < b.x + b.width && b.x < a.x + a.width
            && a.y < b.y + b.height && b.y < a.y + a.height
    }

    // --- Referencia: el orbe, quieto ---------------------------------------------------------

    Rectangle {
        readonly property real d: Math.min(screen.width, screen.height) * 0.42

        width: d
        height: d
        radius: d / 2
        anchors.centerIn: parent
        anchors.verticalCenterOffset: -screen.height * 0.04
        color: "transparent"
        border.width: 1
        border.color: Theme.alpha(Theme.primaryDim, 0.5)

        DisplayText {
            anchors.centerIn: parent
            text: "Orbe"
            color: Theme.textMuted
        }
    }

    // --- Medidores: donde estarán al abrir sesión, sin medir -------------------------------

    // El margen de la pantalla de sesión (`SessionScreen.qml`).
    readonly property real meterMargin: Math.round(
        Theme.space48 * Math.min(1, Math.min(width / 1920, height / 1080)))

    ResourceMeter {
        objectName: "resourceMeterPreview"
        width: implicitWidth
        height: implicitHeight
        x: usage.corner === "left" ? screen.meterMargin : screen.width - width - screen.meterMargin
        y: screen.height - height - screen.meterMargin
        visible: usage.shown
    }

    NoiseMeter {
        objectName: "noiseMeterPreview"
        width: implicitWidth
        height: implicitHeight
        x: noise.corner === "left" ? screen.meterMargin : screen.width - width - screen.meterMargin
        y: screen.height - height - screen.meterMargin
        visible: noise.shown
    }

    // --- Ventanas: la misma área de trabajo que la pantalla de sesión -----------------------

    Item {
        id: area

        x: Theme.space8
        y: Theme.space8
        width: screen.width - 2 * Theme.space8
        height: Math.max(0, screen.height - 2 * Theme.space8)

        Repeater {
            model: workspace

            FloatingWindow {
                required property string style
                required property int order
                required windowId
                required title
                required icon
                required open
                required focused
                required fx
                required fy
                required fw
                required fh
                required minWidth
                required minHeight

                areaWidth: area.width
                areaHeight: area.height
                frameStyle: style
                subtitle: "vista previa"
                z: order

                onMoved: (left, top) => workspace.move(windowId, left, top)
                onResized: (left, top, wide, tall) => workspace.resize(windowId, left, top, wide, tall)
                onClosed: workspace.set_open(windowId, false)
                onActivated: workspace.raise_window(windowId)

                EmptyState {
                    anchors.fill: parent
                    text: "Contenido de la ventana"
                }
            }
        }
    }

    // --- Barra superior: selector de ventanas ------------------------------------------------

    Dock {
        id: dock

        x: Math.round(Math.max(0, Math.min(screen.width - width,
                                           workspace.dockX * screen.width - width / 2)))
        y: Math.round(Math.max(0, Math.min(screen.height - height,
                                           workspace.dockY * screen.height - height / 2)))
        z: 2000

        BarHandle {
            objectName: "dockHandle"
            anchors.fill: parent
            hint: "Selector de ventanas: arrástrelo"
            onDragged: (dx, dy) => workspace.moveDock(
                (dock.x + dock.width / 2 + dx) / screen.width,
                (dock.y + dock.height / 2 + dy) / screen.height)
            onReleased: (startX, startY) => {
                if (screen.overlaps(dock, input))
                    workspace.moveDock(startX, startY)
            }
            startX: workspace.dockX
            startY: workspace.dockY
        }
    }

    // --- Barra inferior: caja de texto -------------------------------------------------------

    CommandInput {
        id: input

        width: Math.round(Math.min(screen.width - 2 * Theme.space8,
                                   Math.max(300, workspace.inputWidth * screen.width)))
        x: Math.round(Math.max(Theme.space8, Math.min(screen.width - width - Theme.space8,
                                                      workspace.inputX * screen.width - width / 2)))
        y: Math.round(Math.max(Theme.space8, Math.min(screen.height - height - Theme.space8,
                                                      workspace.inputY * screen.height - height / 2)))
        z: 2000

        BarHandle {
            objectName: "inputHandle"
            anchors.fill: parent
            hint: "Caja de texto: arrástrela; los extremos cambian su ancho"
            startX: workspace.inputX
            startY: workspace.inputY
            onDragged: (dx, dy) => workspace.placeInput(
                (input.x + input.width / 2 + dx) / screen.width,
                (input.y + input.height / 2 + dy) / screen.height,
                workspace.inputWidth)
            onReleased: (startX, startY) => {
                if (screen.overlaps(dock, input))
                    workspace.placeInput(startX, startY, workspace.inputWidth)
            }
        }

        // Extremos: cambian el ancho sin mover el centro.
        Repeater {
            model: [-1, 1]

            Rectangle {
                required property int modelData

                width: 10
                height: parent.height - 8
                radius: 3
                y: 4
                x: modelData < 0 ? -width / 2 : parent.width - width / 2
                color: Theme.alpha(Theme.primary, grip.containsMouse || grip.pressed ? 0.7 : 0.35)

                MouseArea {
                    id: grip

                    anchors.fill: parent
                    anchors.margins: -4
                    hoverEnabled: true
                    cursorShape: Qt.SizeHorCursor
                    preventStealing: true
                    onPositionChanged: (mouse) => {
                        if (!pressed)
                            return
                        var point = mapToItem(null, mouse.x, mouse.y)
                        var center = input.x + input.width / 2
                        workspace.placeInput(workspace.inputX, workspace.inputY,
                                             2 * Math.abs(point.x - center) / screen.width)
                    }
                }
            }
        }
    }

    // --- Paleta ------------------------------------------------------------------------------

    Rectangle {
        id: palette

        objectName: "editorPalette"
        x: Math.round(screen.width * 0.30)
        y: Math.round(screen.height * 0.22)
        width: 340
        height: paletteColumn.implicitHeight + 2 * Theme.space16
        z: 3000
        radius: Theme.radiusPanel
        color: Theme.bgWindow
        border.width: 1
        border.color: Theme.lineStrong

        Column {
            id: paletteColumn

            x: Theme.space16
            y: Theme.space16
            width: palette.width - 2 * Theme.space16
            spacing: Theme.space12

            // Cabecera: se arrastra la paleta desde aquí.
            Item {
                width: parent.width
                height: titleText.implicitHeight

                DisplayText {
                    id: titleText
                    text: "Editor de plantilla"
                    color: Theme.textPrimary
                }

                DragHandler {
                    target: palette
                    cursorShape: Qt.SizeAllCursor
                }
            }

            FormField {
                objectName: "layoutName"
                width: parent.width
                label: "Nombre"
                value: editor.name
                onEdited: (text) => editor.setName(text)
            }

            Text {
                width: parent.width
                text: "Ventanas al abrir sesión"
                color: Theme.textSecondary
                font.family: Theme.fontBody
                font.pixelSize: Theme.sizeLabel
            }

            Column {
                width: parent.width
                spacing: Theme.space8

                Repeater {
                    model: workspace

                    Toggle {
                        required property string windowId
                        required property string title
                        required property bool open
                        required property bool available  // las del Acedor no van en plantillas

                        objectName: "show-" + windowId
                        visible: available
                        height: available ? implicitHeight : 0
                        width: parent.width
                        text: title
                        checked: open
                        onToggled: (value) => workspace.set_open(windowId, value)
                    }
                }
            }

            Text {
                width: parent.width
                text: "Medidores al abrir sesión"
                color: Theme.textSecondary
                font.family: Theme.fontBody
                font.pixelSize: Theme.sizeLabel
            }

            Column {
                width: parent.width
                spacing: Theme.space8

                Toggle {
                    objectName: "show-recursos"
                    width: parent.width
                    text: "Recursos (CPU y RAM)"
                    checked: usage.shown
                    onToggled: (value) => { if (value !== usage.shown) usage.toggle() }
                }

                Toggle {
                    objectName: "show-ruido"
                    width: parent.width
                    text: "Ruido (decibelios)"
                    checked: noise.shown
                    onToggled: (value) => { if (value !== noise.shown) noise.toggle() }
                }
            }

            Text {
                width: parent.width
                text: "Las ventanas ocultas conservan su sitio: si un módulo la abre durante la"
                      + " sesión, aparece ahí."
                color: Theme.textMuted
                font.family: Theme.fontBody
                font.pixelSize: Theme.sizeLabel
                wrapMode: Text.WordWrap
            }

            Notice {
                objectName: "editorError"
                width: parent.width
                text: editor.error
            }

            Row {
                spacing: Theme.space8

                TextButton {
                    text: "Restablecer"
                    onClicked: editor.restoreFactory()
                }

                TextButton {
                    objectName: "editorCancel"
                    text: "Cancelar"
                    onClicked: editor.cancel()
                }

                TextButton {
                    objectName: "editorAccept"
                    text: "Aceptar"
                    primary: true
                    onClicked: editor.accept()
                }
            }
        }
    }
}
