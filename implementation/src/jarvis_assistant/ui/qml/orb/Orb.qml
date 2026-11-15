// El orbe (Interfaz, secciones 3 y 4).
//
// No tiene animaciones cerradas: tiene propiedades de control y cada fase fija sus valores
// finales. Toda animación parte de los valores actuales, así que una transición que llega con
// otra en curso continúa desde donde estaba la anterior, sin saltos.
import QtQuick
import QtQuick.Shapes
import ".."

Item {
    id: orb

    // Entradas
    property real d: 400                 // D: 42 % del lado menor de la pantalla
    property string activity: "dormido"
    property real level: 0               // nivel de la voz del asistente, de 0 a 1
    property string quality: "high"
    property bool reduceMotion: false
    property bool running: true          // falso con la ventana oculta: no se anima nada

    // Propiedades de control
    property real brightness: 0
    property real spin1: 0               // °/s de los anillos de datos
    property real spin2: 0
    property real spin3: 0
    property real breath: 0
    property real spectrum: 0
    property real assembly: 0            // 0 colapsado – 1 formado
    property real tint: 1                // 0 cian – 1 marino
    property real arc: 0                 // arco de «procesando»
    property real pending: 0             // anillo 2 en el color de espera
    property real particles: 0
    property real flash: 0               // destello del despertar y chispa del cierre
    property real echo: 1                // anillo de luz del despertar desde reposo (1: no se ve)
    property real coreBounce: 1

    // Aspecto en el que queda el orbe mientras suena una frase: lo fija la última transición.
    property string mode: "dormido"
    readonly property bool inTransition: wake.running || wakeFromRest.running
                                         || sleepRest.running || sleepClose.running
    property var goal: aspect("dormido")

    // Estado derivado
    property real smoothLevel: level
    property real clock: 0               // segundos animados
    property real angle1: 0
    property real angle2: 0
    property real angle3: 0
    readonly property color main: Theme.mix(Theme.primary, Theme.primaryDeep, tint)
    readonly property real breathWave: breath * Math.sin(clock * 2 * Math.PI / 2.4)
    readonly property real restness: Math.max(0, Math.min(1, tint / 0.35)) * assembly
    readonly property real structure: reduceMotion ? 1 : 0.55 + 0.45 * assembly

    width: d * 1.4
    height: width

    Behavior on smoothLevel {
        NumberAnimation { duration: Theme.motionLevel }
    }

    function aspect(name) {
        switch (name) {
        case "dormido":
            return { brightness: 0, spin1: 0, spin2: 0, spin3: 0, breath: 0, spectrum: 0,
                     assembly: 0, tint: 1, arc: 0, pending: 0, particles: 0 }
        case "reposo":
            return { brightness: 0.45, spin1: 3, spin2: -2, spin3: 1, breath: 0, spectrum: 0,
                     assembly: 1, tint: 0.35, arc: 0, pending: 0, particles: 0.4 }
        case "procesando":
            return { brightness: 0.9, spin1: 40, spin2: -30, spin3: 20, breath: 0.1, spectrum: 0,
                     assembly: 1, tint: 0, arc: 1, pending: 0, particles: 1 }
        case "esperando":
            return { brightness: 1, spin1: 18, spin2: -12, spin3: 8, breath: 0.25, spectrum: 1,
                     assembly: 1, tint: 0, arc: 0, pending: 1, particles: 1 }
        default:  // escuchando y hablando
            return { brightness: 1, spin1: 18, spin2: -12, spin3: 8, breath: 0.25, spectrum: 1,
                     assembly: 1, tint: 0, arc: 0, pending: 0, particles: 1 }
        }
    }

    // Factor de escala del anillo `index` (0 interior – 3 exterior): se forman escalonados
    // del interior al exterior y colapsan del exterior al interior.
    function ringScale(index) {
        if (reduceMotion)
            return 1
        var x = Math.max(0, Math.min(1, (assembly - index * 0.076) / (1 - 3 * 0.076)))
        return 1 - Math.pow(1 - x, 3)
    }

    function stopAll() {
        wake.stop()
        wakeFromRest.stop()
        sleepRest.stop()
        sleepClose.stop()
        tween.stop()
    }

    // Lleva las propiedades al aspecto de la actividad actual con un fundido corto.
    function settle() {
        if (activity !== "hablando")
            mode = activity === "reposo" || activity === "dormido" ? activity : "escuchando"
        stopAll()
        goal = aspect(activity === "hablando" ? mode : activity)
        tween.restart()
    }

    // Transición de despertar o de dormirse: "wake", "wake_from_rest", "sleep_rest", "sleep_close".
    function play(kind) {
        mode = kind === "sleep_rest" ? "reposo" : kind === "sleep_close" ? "dormido" : "escuchando"
        stopAll()
        if (reduceMotion) {
            goal = aspect(mode)
            tween.restart()
            return
        }
        if (kind === "wake")
            wake.start()
        else if (kind === "wake_from_rest")
            wakeFromRest.start()
        else if (kind === "sleep_rest")
            sleepRest.start()
        else
            sleepClose.start()
    }

    onActivityChanged: {
        if (!inTransition)
            settle()
    }

    FrameAnimation {
        running: orb.running && !orb.reduceMotion && orb.brightness > 0
        onTriggered: {
            orb.clock += frameTime
            orb.angle1 += orb.spin1 * frameTime
            orb.angle2 += orb.spin2 * frameTime
            orb.angle3 += orb.spin3 * frameTime
        }
    }

    // --- Fundido corto al aspecto de una actividad ------------------------------------------

    ParallelAnimation {
        id: tween

        readonly property int span: Theme.motionState

        NumberAnimation { target: orb; property: "brightness"; to: orb.goal.brightness; duration: tween.span }
        NumberAnimation { target: orb; property: "spin1"; to: orb.goal.spin1; duration: tween.span }
        NumberAnimation { target: orb; property: "spin2"; to: orb.goal.spin2; duration: tween.span }
        NumberAnimation { target: orb; property: "spin3"; to: orb.goal.spin3; duration: tween.span }
        NumberAnimation { target: orb; property: "breath"; to: orb.goal.breath; duration: tween.span }
        NumberAnimation { target: orb; property: "spectrum"; to: orb.goal.spectrum; duration: tween.span }
        NumberAnimation { target: orb; property: "assembly"; to: orb.goal.assembly; duration: tween.span }
        NumberAnimation { target: orb; property: "tint"; to: orb.goal.tint; duration: tween.span }
        NumberAnimation { target: orb; property: "arc"; to: orb.goal.arc; duration: tween.span }
        NumberAnimation { target: orb; property: "pending"; to: orb.goal.pending; duration: tween.span }
        NumberAnimation { target: orb; property: "particles"; to: orb.goal.particles; duration: tween.span }
        NumberAnimation { target: orb; property: "flash"; to: 0; duration: tween.span }
        NumberAnimation { target: orb; property: "echo"; to: 1; duration: tween.span }
        NumberAnimation { target: orb; property: "coreBounce"; to: 1; duration: tween.span }
    }

    // --- Despertar (2 s) --------------------------------------------------------------------

    ParallelAnimation {
        id: wake

        onFinished: orb.settle()

        // 0 – 1,0 s: opacidad global de 0 a 100 %.
        NumberAnimation { target: orb; property: "brightness"; to: 1; duration: 1000 }
        NumberAnimation { target: orb; property: "tint"; to: 0; duration: 1000 }
        // 0 – 0,15 s: punto de luz y destello.
        SequentialAnimation {
            NumberAnimation { target: orb; property: "flash"; to: 1; duration: 150; easing.type: Easing.OutQuad }
            NumberAnimation { target: orb; property: "flash"; to: 0; duration: 650; easing.type: Easing.InQuad }
        }
        // 0,15 – 1,2 s: los anillos se expanden desde el punto.
        SequentialAnimation {
            PauseAnimation { duration: 150 }
            NumberAnimation { target: orb; property: "assembly"; to: 1; duration: 1050 }
        }
        // 1,2 – 2,0 s: estabilización.
        SequentialAnimation {
            PauseAnimation { duration: 1200 }
            ParallelAnimation {
                SequentialAnimation {
                    NumberAnimation { target: orb; property: "coreBounce"; to: 1.06; duration: 200; easing.type: Easing.OutQuad }
                    NumberAnimation { target: orb; property: "coreBounce"; to: 1; duration: 600; easing.type: Easing.OutCubic }
                }
                NumberAnimation { target: orb; property: "spectrum"; to: 1; duration: 800 }
                NumberAnimation { target: orb; property: "particles"; to: 1; duration: 800 }
            }
        }
        NumberAnimation { target: orb; property: "spin1"; to: 18; duration: 2000; easing.type: Easing.OutCubic }
        NumberAnimation { target: orb; property: "spin2"; to: -12; duration: 2000; easing.type: Easing.OutCubic }
        NumberAnimation { target: orb; property: "spin3"; to: 8; duration: 2000; easing.type: Easing.OutCubic }
        NumberAnimation { target: orb; property: "breath"; to: 0.25; duration: 2000 }
        NumberAnimation { target: orb; property: "arc"; to: 0; duration: 400 }
        NumberAnimation { target: orb; property: "pending"; to: 0; duration: 400 }
    }

    // --- Despertar desde reposo (2 s): el orbe ya está formado ------------------------------

    ParallelAnimation {
        id: wakeFromRest

        onFinished: orb.settle()

        NumberAnimation { target: orb; property: "brightness"; to: 1; duration: 2000; easing.type: Easing.InOutQuad }
        NumberAnimation { target: orb; property: "tint"; to: 0; duration: 2000; easing.type: Easing.InOutQuad }
        NumberAnimation { target: orb; property: "assembly"; to: 1; duration: 2000; easing.type: Easing.OutCubic }
        NumberAnimation { target: orb; property: "spin1"; to: 18; duration: 2000; easing.type: Easing.InOutQuad }
        NumberAnimation { target: orb; property: "spin2"; to: -12; duration: 2000; easing.type: Easing.InOutQuad }
        NumberAnimation { target: orb; property: "spin3"; to: 8; duration: 2000; easing.type: Easing.InOutQuad }
        NumberAnimation { target: orb; property: "breath"; to: 0.25; duration: 2000 }
        NumberAnimation { target: orb; property: "spectrum"; to: 1; duration: 2000 }
        NumberAnimation { target: orb; property: "particles"; to: 1; duration: 2000 }
        NumberAnimation { target: orb; property: "flash"; to: 0; duration: 400 }
        NumberAnimation { target: orb; property: "arc"; to: 0; duration: 400 }
        NumberAnimation { target: orb; property: "pending"; to: 0; duration: 400 }
        // Un anillo de luz fino se expande una vez desde el núcleo, como eco del destello.
        SequentialAnimation {
            PropertyAction { target: orb; property: "echo"; value: 0 }
            NumberAnimation { target: orb; property: "echo"; to: 1; duration: 1200; easing.type: Easing.OutCubic }
        }
    }

    // --- Dormirse, variante reposo (2 s): queda formado, tenue y lento ----------------------

    ParallelAnimation {
        id: sleepRest

        onFinished: orb.settle()

        // 0 – 0,8 s: los anillos frenan; el espectro se desvanece.
        NumberAnimation { target: orb; property: "spin1"; to: 3; duration: 800; easing.type: Easing.InQuad }
        NumberAnimation { target: orb; property: "spin2"; to: -2; duration: 800; easing.type: Easing.InQuad }
        NumberAnimation { target: orb; property: "spin3"; to: 1; duration: 800; easing.type: Easing.InQuad }
        NumberAnimation { target: orb; property: "spectrum"; to: 0; duration: 800 }
        NumberAnimation { target: orb; property: "arc"; to: 0; duration: 400 }
        NumberAnimation { target: orb; property: "pending"; to: 0; duration: 400 }
        NumberAnimation { target: orb; property: "flash"; to: 0; duration: 400 }
        // 0,4 – 1,6 s: se contrae hasta 0,8 y vuelve a 1; vira hacia el marino.
        SequentialAnimation {
            PauseAnimation { duration: 400 }
            NumberAnimation { target: orb; property: "assembly"; to: 0.8; duration: 600; easing.type: Easing.InOutQuad }
            NumberAnimation { target: orb; property: "assembly"; to: 1; duration: 600; easing.type: Easing.InOutQuad }
            PauseAnimation { duration: 400 }
        }
        SequentialAnimation {
            PauseAnimation { duration: 400 }
            ParallelAnimation {
                NumberAnimation { target: orb; property: "tint"; to: 0.35; duration: 1200 }
                NumberAnimation { target: orb; property: "brightness"; to: 0.45; duration: 1600 }
            }
        }
        NumberAnimation { target: orb; property: "breath"; to: 0; duration: 2000 }
        NumberAnimation { target: orb; property: "particles"; to: 0.4; duration: 2000 }
    }

    // --- Dormirse, variante cierre (2 s): chispa que desaparece -----------------------------

    ParallelAnimation {
        id: sleepClose

        onFinished: orb.settle()

        NumberAnimation { target: orb; property: "spin1"; to: 0; duration: 800; easing.type: Easing.InQuad }
        NumberAnimation { target: orb; property: "spin2"; to: 0; duration: 800; easing.type: Easing.InQuad }
        NumberAnimation { target: orb; property: "spin3"; to: 0; duration: 800; easing.type: Easing.InQuad }
        NumberAnimation { target: orb; property: "spectrum"; to: 0; duration: 800 }
        NumberAnimation { target: orb; property: "arc"; to: 0; duration: 400 }
        NumberAnimation { target: orb; property: "pending"; to: 0; duration: 400 }
        NumberAnimation { target: orb; property: "breath"; to: 0; duration: 800 }
        // 0,4 – 1,6 s: la estructura colapsa hacia el centro; 1,6 – 2,0 s: chispa.
        SequentialAnimation {
            PauseAnimation { duration: 400 }
            NumberAnimation { target: orb; property: "assembly"; to: 0.12; duration: 1200; easing.type: Easing.InQuad }
            NumberAnimation { target: orb; property: "assembly"; to: 0; duration: 400 }
        }
        SequentialAnimation {
            PauseAnimation { duration: 400 }
            NumberAnimation { target: orb; property: "tint"; to: 1; duration: 1200 }
        }
        SequentialAnimation {
            PauseAnimation { duration: 1500 }
            NumberAnimation { target: orb; property: "flash"; to: 0.8; duration: 150 }
            NumberAnimation { target: orb; property: "flash"; to: 0; duration: 350 }
        }
        SequentialAnimation {
            PauseAnimation { duration: 1600 }
            ParallelAnimation {
                NumberAnimation { target: orb; property: "brightness"; to: 0; duration: 400 }
                NumberAnimation { target: orb; property: "particles"; to: 0; duration: 400 }
            }
        }
    }

    // --- Dibujo -----------------------------------------------------------------------------

    // Orbe apagado del modo dormido: un punto en `primary.deep`.
    Rectangle {
        anchors.centerIn: parent
        width: Math.max(8, orb.d * 0.025)
        height: width
        radius: width / 2
        color: Theme.primaryDeep
        opacity: orb.activity === "dormido" && !orb.inTransition ? 1 : 0

        Behavior on opacity {
            NumberAnimation { duration: Theme.motionState }
        }
    }

    Item {
        id: stage

        anchors.fill: parent
        opacity: Math.min(1, orb.brightness + orb.flash)
        // Flotación muy sutil en reposo: ±4 px, periodo de 6 s.
        transform: Translate { y: orb.restness * 4 * Math.sin(orb.clock * 2 * Math.PI / 6) }

        // Halo: resplandor difuso detrás de todo.
        Shape {
            anchors.centerIn: parent
            width: orb.d * 1.2
            height: width
            visible: orb.quality !== "low"
            opacity: Math.min(1, 0.5 + orb.breathWave + 0.5 * orb.flash + 0.3 * orb.smoothLevel)
            scale: orb.structure

            ShapePath {
                strokeWidth: -1
                fillGradient: RadialGradient {
                    centerX: orb.d * 0.6
                    centerY: orb.d * 0.6
                    focalX: centerX
                    focalY: centerY
                    centerRadius: orb.d * 0.6
                    GradientStop { position: 0.0; color: Theme.alpha(orb.main, 0.32) }
                    GradientStop { position: 0.5; color: Theme.alpha(orb.main, 0.1) }
                    GradientStop { position: 1.0; color: Theme.alpha(orb.main, 0.0) }
                }
                PathAngleArc {
                    centerX: orb.d * 0.6
                    centerY: orb.d * 0.6
                    radiusX: orb.d * 0.6
                    radiusY: radiusX
                    sweepAngle: 360
                }
            }
        }

        Particles {
            anchors.centerIn: parent
            d: orb.d
            count: orb.quality === "high" ? 120 : orb.quality === "medium" ? 60 : 0
            strength: orb.reduceMotion ? 0 : orb.particles
            running: orb.running
            color: orb.main
        }

        DataRing {
            anchors.centerIn: parent
            variant: 3
            diameter: orb.d * 0.86
            color: orb.main
            showText: orb.quality !== "low"
            scale: orb.ringScale(3) * orb.structure
            rotation: orb.angle3 + (1 - orb.ringScale(3)) * 180
        }

        DataRing {
            anchors.centerIn: parent
            variant: 2
            diameter: orb.d * 0.72
            color: Theme.mix(orb.main, Theme.statusPending, orb.pending)
            showText: orb.quality !== "low"
            scale: orb.ringScale(2) * orb.structure
            rotation: orb.angle2 - (1 - orb.ringScale(2)) * 180
        }

        DataRing {
            anchors.centerIn: parent
            variant: 1
            diameter: orb.d * 0.6
            color: orb.main
            scale: orb.ringScale(1) * orb.structure
            rotation: orb.angle1 + (1 - orb.ringScale(1)) * 180
        }

        SpectrumRing {
            anchors.centerIn: parent
            diameter: orb.d * 0.48
            level: orb.smoothLevel
            shift: orb.clock * 3
            maxLength: orb.d * 0.07
            color: orb.main
            // Sigue a la voz aunque el aspecto no muestre espectro (frases de dormirse).
            opacity: Math.max(orb.spectrum, orb.smoothLevel > 0.01 ? 1 : 0) * (1 - orb.arc)
            scale: orb.ringScale(0) * orb.structure
        }

        // Procesando: un arco luminoso recorre el anillo interior, una vuelta cada 1,2 s.
        Shape {
            anchors.centerIn: parent
            width: orb.d * 0.5
            height: width
            opacity: orb.arc
            visible: opacity > 0
            rotation: orb.clock * 300
            scale: orb.structure

            ShapePath {
                strokeColor: Theme.primaryBright
                strokeWidth: 3
                fillColor: "transparent"
                capStyle: ShapePath.RoundCap
                PathAngleArc {
                    centerX: orb.d * 0.25
                    centerY: orb.d * 0.25
                    radiusX: orb.d * 0.25 - 2
                    radiusY: radiusX
                    startAngle: 0
                    sweepAngle: 80
                }
            }
        }

        // Eco del destello al despertar desde reposo.
        Rectangle {
            anchors.centerIn: parent
            width: orb.d * (0.32 + 0.88 * orb.echo)
            height: width
            radius: width / 2
            color: "transparent"
            border.width: 1.5
            border.color: Theme.primaryBright
            opacity: (1 - orb.echo) * 0.8
            visible: opacity > 0
        }

        OrbCore {
            anchors.centerIn: parent
            diameter: orb.d * 0.32
            color: orb.main
            glow: Math.min(1, 0.35 + orb.breathWave + 0.65 * orb.smoothLevel + orb.flash)
            phase: orb.clock * 0.6
            scale: (1 + 0.12 * orb.smoothLevel) * orb.coreBounce
                   * (orb.reduceMotion ? 1 : 0.12 + 0.88 * orb.ringScale(0))
        }
    }
}
