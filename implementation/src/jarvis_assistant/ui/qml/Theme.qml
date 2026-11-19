// Tokens del sistema de diseño (software/Interfaz/README.md, sección 2).
// Ningún componente define colores, tamaños ni duraciones propios: todos salen de aquí.
pragma Singleton
import QtQuick

QtObject {
    // Color
    readonly property color bgBase: "#05070B"
    readonly property color bgPanel: Qt.rgba(12 / 255, 18 / 255, 28 / 255, 0.78)
    readonly property color bgRaised: "#121B28"
    readonly property color bgWindow: Qt.rgba(8 / 255, 13 / 255, 21 / 255, 0.92)
    readonly property color bgHover: Qt.rgba(34 / 255, 211 / 255, 238 / 255, 0.09)
    readonly property color bgSelected: Qt.rgba(34 / 255, 211 / 255, 238 / 255, 0.16)
    readonly property color shadowNear: Qt.rgba(0, 0, 0, 0.30)
    readonly property color shadowFar: Qt.rgba(0, 0, 0, 0.16)
    readonly property color lineSoft: "#1B2A3A"
    readonly property color lineStrong: "#2A4560"
    readonly property color primary: "#22D3EE"
    readonly property color primaryBright: "#7DF3FF"
    readonly property color primaryHot: "#E8FDFF"
    readonly property color primaryDim: "#0E7490"
    readonly property color primaryDeep: "#0B2A4A"
    readonly property color textPrimary: "#E6F1F8"
    readonly property color textSecondary: "#8FA6B8"
    readonly property color textMuted: "#5B7083"
    readonly property color statusPending: "#F5B544"
    readonly property color statusDone: "#34D399"
    readonly property color statusError: "#F2555A"
    readonly property color neonCyan: "#2FDCEB"      // medidores: CPU, RAM y ruido
    readonly property color neonBlue: "#2F7FF2"      // arco secundario del de CPU
    readonly property color neonDim: "#1E4352"       // pistas y segmentos apagados
    readonly property color neonCore: "#071219"      // disco del centro de los medidores
    // Niveles del medidor de ruido (`ui/noise.py`, TIERS).
    readonly property color noiseSilence: statusDone // silencio
    readonly property color noiseFocusHigh: neonBlue // concentración alta
    readonly property color noiseFocusMid: "#FACC15" // concentración media
    readonly property color noiseFocusLow: statusError // concentración baja

    // Tipografía
    readonly property string fontDisplay: "Rajdhani"
    readonly property string fontBody: "Inter"
    readonly property string fontMono: "JetBrains Mono"
    readonly property string fontTech: "Orbitron"    // cifras y rótulos de los medidores
    readonly property real displaySpacing: 0.08  // espaciado de `fontDisplay`, sobre su tamaño
    readonly property int sizeLabel: 11
    readonly property int sizeSecondary: 13
    readonly property int sizeText: 15
    readonly property int sizeTitle: 18
    readonly property int sizeState: 24
    readonly property int sizeClock: 40
    readonly property real lineHeight: 1.4

    // Espaciado, forma
    readonly property int space4: 4
    readonly property int space8: 8
    readonly property int space12: 12
    readonly property int space16: 16
    readonly property int space24: 24
    readonly property int space32: 32
    readonly property int space48: 48
    readonly property int radiusPanel: 10
    readonly property int radiusCard: 6
    readonly property int radiusWindow: 12
    readonly property int windowHeader: 38
    readonly property int windowGrip: 6
    readonly property int windowTab: 184   // ancho de una ventana apartada
    readonly property int cornerMark: 12
    readonly property real iconStroke: 1.5
    readonly property int inputHeight: 40
    readonly property real neonWidth: 1.5    // grosor del neón que recorre los bordes
    readonly property real neonSpeed: 70     // su velocidad, en píxeles por segundo

    // Movimiento (ms)
    readonly property int motionTransition: 2000
    readonly property int motionPanel: 220
    readonly property int motionWindow: 160
    readonly property int motionState: 400
    readonly property int motionLevel: 80
    readonly property int motionEmerge: 520  // una ventana sale del orbe hasta su sitio
    readonly property int motionEmergeGap: 300 // entre una ventana y la siguiente al abrir sesión
    readonly property int motionAside: 440  // una ventana se aparta a un borde o vuelve

    function statusColor(status) {
        if (status === "pendiente")
            return statusPending
        return status === "error" ? statusError : statusDone
    }

    function activityColor(activity) {
        switch (activity) {
        case "escuchando":
        case "hablando":
            return primary
        case "esperando":
            return statusPending
        case "procesando":
            return primaryBright
        default:
            return textSecondary
        }
    }

    function mix(a, b, t) {
        return Qt.rgba(a.r + (b.r - a.r) * t, a.g + (b.g - a.g) * t, a.b + (b.b - a.b) * t,
                       a.a + (b.a - a.a) * t)
    }

    function alpha(c, a) {
        return Qt.rgba(c.r, c.g, c.b, a)
    }

    function icon(name) {
        return Qt.resolvedUrl("../assets/icons/" + name + ".svg")
    }
}
