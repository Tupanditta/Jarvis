// El orbe (Interfaz, secciones 3 y 4).
//
// No tiene animaciones cerradas: tiene propiedades de control y cada fase fija sus valores
// finales. Toda animación parte de los valores actuales, así que una transición que llega con
// otra en curso continúa desde donde estaba la anterior, sin saltos.
//
// El orbe es también el director de todos los elementos vivos, los suyos y los del fondo
// (`LifeField`): comparten sus relojes (`flow`, `mind`), su latido (`wave`), el nivel de la
// voz y el color. Por eso se mueven a la vez aunque sean distintos entre sí.
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

    // El despertar ("wake") ha terminado entero; no se emite si otra transición lo corta.
    signal awake()

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
    property real particles: 0           // capas vivas: partículas, red, satélites, glifos y fondo
    property real energy: 0              // 0–1: velocidad y brillo de los elementos vivos
    property real chaos: 0               // 0–1: irregularidad (deformación, parpadeo, sinapsis)
    property real beatRate: 0            // latidos por segundo
    property real mass: 0                // masa viva que se concentra en el núcleo al despertar
    property real inflow: 0              // materia que cae en espiral hacia el núcleo
    property real intake: 0              // avance de esa caída
    property real horizon: 0             // horizonte del agujero negro del cierre
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
    property real flow: 0                // segundos ponderados por `energy`
    property real mind: 0                // segundos ponderados por `chaos`
    property real beatPhase: 0           // 0–1: avance de la onda del latido
    property real voicePhase: 0          // 0–1: avance de las ondas de la voz
    readonly property real voiceRate: 1.3    // ondas de voz por segundo
    readonly property real reach: 2.5    // alcance de la onda, en unidades de D: toda la pantalla
    readonly property real pulse: reduceMotion ? 0 : Math.min(1, beatRate / 0.4)
    readonly property real live: particles
    // Escala común de lo que rodea al núcleo: se forma y colapsa con él.
    readonly property real coreScale: (reduceMotion ? 1 : 0.12 + 0.88 * ringScale(0)) * structure
    readonly property color accent: Theme.mix(main, Theme.statusPending, pending)
    readonly property color main: Theme.mix(Theme.primary, Theme.primaryDeep, tint)
    readonly property real breathWave: breath * Math.sin(clock * 2 * Math.PI / 2.4)
    readonly property real restness: Math.max(0, Math.min(1, tint / 0.35)) * assembly
    readonly property real structure: reduceMotion ? 1 : 0.55 + 0.45 * assembly

    width: d * 1.4
    height: width

    Behavior on smoothLevel {
        NumberAnimation { duration: Theme.motionLevel }
    }

    // Brillo que el latido añade a un elemento situado a `r` (en unidades de D) del centro:
    // una onda que nace en el núcleo y se atenúa al alejarse. Mientras el asistente habla se
    // suman las ondas de la voz, más anchas y seguidas: toda la pantalla vibra con la frase.
    function wave(r) {
        var x = (r - beatPhase * reach) / 0.16
        var glow = pulse * (1 - 0.6 * beatPhase) * Math.exp(-x * x)
        if (reduceMotion || smoothLevel <= 0.01)
            return glow
        var v = (r - voicePhase * reach) / 0.3
        return Math.min(1, glow + smoothLevel * (1 - 0.5 * voicePhase) * Math.exp(-v * v))
    }

    function aspect(name) {
        switch (name) {
        case "dormido":
            return { brightness: 0, spin1: 0, spin2: 0, spin3: 0, breath: 0, spectrum: 0,
                     assembly: 0, tint: 1, arc: 0, pending: 0, particles: 0,
                     energy: 0, chaos: 0, beatRate: 0 }
        case "reposo":
            return { brightness: 0.22, spin1: 3, spin2: -2, spin3: 1, breath: 0, spectrum: 0,
                     assembly: 1, tint: 0.6, arc: 0, pending: 0, particles: 0,
                     energy: 0.08, chaos: 0, beatRate: 0 }
        case "procesando":
            return { brightness: 1, spin1: 40, spin2: -30, spin3: 20, breath: 0.1, spectrum: 0,
                     assembly: 1, tint: 0, arc: 1, pending: 0, particles: 1,
                     energy: 1, chaos: 1, beatRate: 1 / 0.9 }
        case "esperando":
            return { brightness: 1, spin1: 18, spin2: -12, spin3: 8, breath: 0.25, spectrum: 1,
                     assembly: 1, tint: 0, arc: 0, pending: 1, particles: 1,
                     energy: 0.45, chaos: 0.2, beatRate: 1 / 1.8 }
        default:  // escuchando y hablando
            return { brightness: 1, spin1: 18, spin2: -12, spin3: 8, breath: 0.25, spectrum: 1,
                     assembly: 1, tint: 0, arc: 0, pending: 0, particles: 1,
                     energy: 0.6, chaos: 0.35, beatRate: 1 / 2.4 }
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
            if (kind === "wake")
                awake()
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
            orb.flow += orb.energy * frameTime
            // En reposo el pensamiento casi se detiene: el núcleo queda quieto.
            orb.mind += (0.25 + 1.75 * orb.chaos) * Math.min(1, orb.energy * 4) * frameTime
            orb.beatPhase = (orb.beatPhase + orb.beatRate * frameTime) % 1
            if (orb.smoothLevel > 0.01)
                orb.voicePhase = (orb.voicePhase + orb.voiceRate * frameTime) % 1
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
        NumberAnimation { target: orb; property: "energy"; to: orb.goal.energy; duration: tween.span }
        NumberAnimation { target: orb; property: "chaos"; to: orb.goal.chaos; duration: tween.span }
        NumberAnimation { target: orb; property: "beatRate"; to: orb.goal.beatRate; duration: tween.span }
        NumberAnimation { target: orb; property: "flash"; to: 0; duration: tween.span }
        NumberAnimation { target: orb; property: "mass"; to: 0; duration: tween.span }
        NumberAnimation { target: orb; property: "inflow"; to: 0; duration: tween.span }
        NumberAnimation { target: orb; property: "horizon"; to: 0; duration: tween.span }
        NumberAnimation { target: orb; property: "echo"; to: 1; duration: tween.span }
        NumberAnimation { target: orb; property: "coreBounce"; to: 1; duration: tween.span }
    }

    // --- Despertar (2 s): la masa se concentra, estalla y se asienta -------------------------

    ParallelAnimation {
        id: wake

        onFinished: {
            orb.settle()
            orb.awake()
        }

        // 0 – 1,0 s: concentración. El punto del modo dormido se vuelve una masa viva: materia
        // que cae en espiral hacia el centro, el núcleo crece y se agita, y vira al cian.
        NumberAnimation { target: orb; property: "brightness"; to: 1; duration: 900; easing.type: Easing.OutQuad }
        NumberAnimation { target: orb; property: "tint"; to: 0; duration: 950; easing.type: Easing.InQuad }
        SequentialAnimation {
            NumberAnimation { target: orb; property: "inflow"; to: 1; duration: 200 }
            PauseAnimation { duration: 700 }
            NumberAnimation { target: orb; property: "inflow"; to: 0; duration: 150 }
        }
        SequentialAnimation {
            PropertyAction { target: orb; property: "intake"; value: 0 }
            NumberAnimation { target: orb; property: "intake"; to: 2.2; duration: 1050; easing.type: Easing.InQuad }
        }
        SequentialAnimation {
            NumberAnimation { target: orb; property: "mass"; to: 1; duration: 950; easing.type: Easing.InOutQuad }
            NumberAnimation { target: orb; property: "mass"; to: 0; duration: 500 }
        }
        // Si interrumpe un cierre, lo que quede formado termina de caer antes del estallido.
        SequentialAnimation {
            NumberAnimation { target: orb; property: "assembly"; to: 0; duration: 200 }
            PauseAnimation { duration: 800 }
            NumberAnimation { target: orb; property: "assembly"; to: 1; duration: 500; easing.type: Easing.OutBack }
        }
        SequentialAnimation {
            NumberAnimation { target: orb; property: "chaos"; to: 0.95; duration: 600; easing.type: Easing.OutQuad }
            PauseAnimation { duration: 400 }
            NumberAnimation { target: orb; property: "chaos"; to: 0.35; duration: 1000; easing.type: Easing.InOutQuad }
        }
        SequentialAnimation {
            NumberAnimation { target: orb; property: "energy"; to: 0.7; duration: 500 }
            PauseAnimation { duration: 500 }
            NumberAnimation { target: orb; property: "energy"; to: 1; duration: 100 }
            NumberAnimation { target: orb; property: "energy"; to: 0.6; duration: 900; easing.type: Easing.InOutQuad }
        }
        // 0,8 – 1,0 s: el núcleo se comprime. 1,0 s: estalla.
        SequentialAnimation {
            PauseAnimation { duration: 800 }
            NumberAnimation { target: orb; property: "coreBounce"; to: 0.72; duration: 200; easing.type: Easing.InQuad }
            NumberAnimation { target: orb; property: "coreBounce"; to: 1.35; duration: 120; easing.type: Easing.OutQuad }
            NumberAnimation { target: orb; property: "coreBounce"; to: 1; duration: 700; easing.type: Easing.OutCubic }
        }
        SequentialAnimation {
            PauseAnimation { duration: 950 }
            NumberAnimation { target: orb; property: "flash"; to: 1; duration: 80; easing.type: Easing.OutQuad }
            NumberAnimation { target: orb; property: "flash"; to: 0; duration: 650; easing.type: Easing.InQuad }
        }
        // La onda del estallido: un anillo de luz y el primer latido, que cruza la pantalla.
        SequentialAnimation {
            PauseAnimation { duration: 1000 }
            PropertyAction { target: orb; property: "echo"; value: 0 }
            NumberAnimation { target: orb; property: "echo"; to: 1; duration: 700; easing.type: Easing.OutCubic }
        }
        SequentialAnimation {
            NumberAnimation { target: orb; property: "beatRate"; to: 0; duration: 200 }
            PauseAnimation { duration: 800 }
            PropertyAction { target: orb; property: "beatPhase"; value: 0 }
            PropertyAction { target: orb; property: "beatRate"; value: 1 / 0.9 }
            NumberAnimation { target: orb; property: "beatRate"; to: 1 / 2.4; duration: 1000 }
        }
        // 1,0 – 2,0 s: las capas vivas salen despedidas y todo converge a los valores de escucha.
        SequentialAnimation {
            PauseAnimation { duration: 1000 }
            NumberAnimation { target: orb; property: "particles"; to: 1; duration: 450; easing.type: Easing.OutQuad }
        }
        SequentialAnimation {
            PauseAnimation { duration: 1200 }
            NumberAnimation { target: orb; property: "spectrum"; to: 1; duration: 800 }
        }
        SequentialAnimation {
            PauseAnimation { duration: 1000 }
            NumberAnimation { target: orb; property: "spin1"; to: 70; duration: 150 }
            NumberAnimation { target: orb; property: "spin1"; to: 18; duration: 850; easing.type: Easing.OutCubic }
        }
        SequentialAnimation {
            PauseAnimation { duration: 1000 }
            NumberAnimation { target: orb; property: "spin2"; to: -55; duration: 150 }
            NumberAnimation { target: orb; property: "spin2"; to: -12; duration: 850; easing.type: Easing.OutCubic }
        }
        SequentialAnimation {
            PauseAnimation { duration: 1000 }
            NumberAnimation { target: orb; property: "spin3"; to: 40; duration: 150 }
            NumberAnimation { target: orb; property: "spin3"; to: 8; duration: 850; easing.type: Easing.OutCubic }
        }
        NumberAnimation { target: orb; property: "breath"; to: 0.25; duration: 2000 }
        NumberAnimation { target: orb; property: "arc"; to: 0; duration: 400 }
        NumberAnimation { target: orb; property: "pending"; to: 0; duration: 400 }
        NumberAnimation { target: orb; property: "horizon"; to: 0; duration: 300 }
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
        SequentialAnimation {
            NumberAnimation { target: orb; property: "energy"; to: 1; duration: 900; easing.type: Easing.OutQuad }
            NumberAnimation { target: orb; property: "energy"; to: 0.6; duration: 1100; easing.type: Easing.InOutQuad }
        }
        SequentialAnimation {
            NumberAnimation { target: orb; property: "chaos"; to: 0.8; duration: 900; easing.type: Easing.OutQuad }
            NumberAnimation { target: orb; property: "chaos"; to: 0.35; duration: 1100; easing.type: Easing.InOutQuad }
        }
        NumberAnimation { target: orb; property: "beatRate"; to: 1 / 2.4; duration: 2000 }
        NumberAnimation { target: orb; property: "flash"; to: 0; duration: 400 }
        NumberAnimation { target: orb; property: "mass"; to: 0; duration: 400 }
        NumberAnimation { target: orb; property: "inflow"; to: 0; duration: 400 }
        NumberAnimation { target: orb; property: "horizon"; to: 0; duration: 400 }
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
        NumberAnimation { target: orb; property: "mass"; to: 0; duration: 400 }
        NumberAnimation { target: orb; property: "inflow"; to: 0; duration: 400 }
        NumberAnimation { target: orb; property: "horizon"; to: 0; duration: 400 }
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
                NumberAnimation { target: orb; property: "tint"; to: 0.6; duration: 1200 }
                NumberAnimation { target: orb; property: "brightness"; to: 0.22; duration: 1600 }
            }
        }
        NumberAnimation { target: orb; property: "breath"; to: 0; duration: 2000 }
        // Lo vivo se apaga antes que la estructura.
        NumberAnimation { target: orb; property: "particles"; to: 0; duration: 1400 }
        NumberAnimation { target: orb; property: "energy"; to: 0.08; duration: 1400; easing.type: Easing.OutQuad }
        NumberAnimation { target: orb; property: "chaos"; to: 0; duration: 1000 }
        NumberAnimation { target: orb; property: "beatRate"; to: 0; duration: 800 }
    }

    // --- Dormirse, variante cierre (2 s): chispa que desaparece -----------------------------

    ParallelAnimation {
        id: sleepClose

        onFinished: orb.settle()

        // Colapso: el núcleo se vuelve un agujero negro y lo atrae todo.
        // 0 – 0,5 s: se abre el horizonte en el centro y la materia empieza a caer en espiral.
        SequentialAnimation {
            NumberAnimation { target: orb; property: "horizon"; to: 1; duration: 500; easing.type: Easing.OutQuad }
            PauseAnimation { duration: 700 }
            NumberAnimation { target: orb; property: "horizon"; to: 0; duration: 400; easing.type: Easing.InQuad }
        }
        SequentialAnimation {
            NumberAnimation { target: orb; property: "inflow"; to: 1; duration: 300 }
            PauseAnimation { duration: 1100 }
            NumberAnimation { target: orb; property: "inflow"; to: 0; duration: 250 }
        }
        SequentialAnimation {
            PropertyAction { target: orb; property: "intake"; value: 0 }
            NumberAnimation { target: orb; property: "intake"; to: 3.6; duration: 1650; easing.type: Easing.InQuad }
        }
        // Los anillos no frenan: giran cada vez más deprisa mientras caen.
        NumberAnimation { target: orb; property: "spin1"; to: 110; duration: 1500; easing.type: Easing.InQuad }
        NumberAnimation { target: orb; property: "spin2"; to: -85; duration: 1500; easing.type: Easing.InQuad }
        NumberAnimation { target: orb; property: "spin3"; to: 60; duration: 1500; easing.type: Easing.InQuad }
        NumberAnimation { target: orb; property: "energy"; to: 1; duration: 1200; easing.type: Easing.InQuad }
        NumberAnimation { target: orb; property: "chaos"; to: 0.8; duration: 800 }
        NumberAnimation { target: orb; property: "spectrum"; to: 0; duration: 500 }
        NumberAnimation { target: orb; property: "arc"; to: 0; duration: 400 }
        NumberAnimation { target: orb; property: "pending"; to: 0; duration: 400 }
        NumberAnimation { target: orb; property: "breath"; to: 0; duration: 800 }
        NumberAnimation { target: orb; property: "beatRate"; to: 0; duration: 400 }
        NumberAnimation { target: orb; property: "mass"; to: 0; duration: 400 }
        // 0,25 – 1,6 s: toda la estructura cae hacia el centro, cada vez más deprisa, y el
        // fondo con ella. El cian vira al marino.
        SequentialAnimation {
            PauseAnimation { duration: 250 }
            NumberAnimation { target: orb; property: "assembly"; to: 0; duration: 1350; easing.type: Easing.InCubic }
        }
        SequentialAnimation {
            PauseAnimation { duration: 400 }
            NumberAnimation { target: orb; property: "tint"; to: 1; duration: 1200 }
        }
        SequentialAnimation {
            PauseAnimation { duration: 1300 }
            NumberAnimation { target: orb; property: "particles"; to: 0; duration: 300 }
        }
        // 1,6 – 2,0 s: la singularidad: una chispa que se apaga.
        SequentialAnimation {
            PauseAnimation { duration: 1550 }
            NumberAnimation { target: orb; property: "flash"; to: 0.8; duration: 100 }
            NumberAnimation { target: orb; property: "flash"; to: 0; duration: 350 }
        }
        SequentialAnimation {
            PauseAnimation { duration: 1600 }
            NumberAnimation { target: orb; property: "brightness"; to: 0; duration: 400 }
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
            opacity: Math.min(1, 0.35 + 0.6 * orb.energy + orb.breathWave + 0.5 * orb.flash
                                 + 0.6 * orb.smoothLevel)
            // Al concentrarse la masa, la luz se recoge hacia el núcleo. La voz lo hincha.
            scale: orb.structure * (1 + 0.3 * orb.energy) * (1 - 0.3 * orb.mass)
                   * (1 + 0.12 * orb.smoothLevel)

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

        // Onda del latido: nace en el núcleo y cruza toda la pantalla. Los elementos vivos
        // se iluminan a su paso (`wave`).
        Rectangle {
            anchors.centerIn: parent
            width: orb.d * 2 * orb.reach * orb.beatPhase
            height: width
            radius: width / 2
            color: "transparent"
            border.width: 1.5
            border.color: orb.accent
            opacity: orb.pulse * 0.45 * Math.pow(1 - orb.beatPhase, 2)
            visible: opacity > 0.005
        }

        // Ondas de la voz: dos anillos seguidos salen del núcleo mientras suena una frase y
        // cruzan la pantalla. Su grosor y su brillo siguen al nivel de la voz.
        Repeater {
            model: orb.reduceMotion ? 0 : 2

            Rectangle {
                required property int index
                readonly property real travel: (orb.voicePhase + index * 0.5) % 1

                anchors.centerIn: parent
                width: orb.d * (0.3 + 2 * orb.reach * travel)
                height: width
                radius: width / 2
                color: "transparent"
                border.width: 1 + 2 * orb.smoothLevel
                border.color: Theme.mix(orb.main, Theme.primaryBright, 0.5)
                opacity: orb.smoothLevel * 0.7 * Math.pow(1 - travel, 2)
                visible: opacity > 0.005
            }
        }

        Accretion {
            anchors.centerIn: parent
            d: orb.d
            count: orb.quality === "high" ? 36 : orb.quality === "medium" ? 18 : 0
            color: orb.main
            phase: orb.intake
            strength: orb.inflow
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
            sparks: orb.live
            time: orb.mind
            scale: orb.ringScale(3) * orb.structure
            rotation: orb.angle3 + (1 - orb.ringScale(3)) * 180
        }

        DataRing {
            anchors.centerIn: parent
            variant: 2
            diameter: orb.d * 0.72
            color: Theme.mix(orb.main, Theme.statusPending, orb.pending)
            showText: orb.quality !== "low"
            sparks: orb.live
            time: orb.mind
            scale: orb.ringScale(2) * orb.structure
            rotation: orb.angle2 - (1 - orb.ringScale(2)) * 180
        }

        DataRing {
            anchors.centerIn: parent
            variant: 1
            diameter: orb.d * 0.6
            color: orb.main
            sparks: orb.live
            time: orb.mind
            scale: orb.ringScale(1) * orb.structure
            rotation: orb.angle1 + (1 - orb.ringScale(1)) * 180
        }

        Glyphs {
            anchors.centerIn: parent
            d: orb.d
            count: orb.quality === "high" ? 10 : orb.quality === "medium" ? 5 : 0
            color: orb.main
            time: orb.mind
            chaos: orb.chaos
            strength: orb.live
            scale: orb.ringScale(2) * orb.structure
        }

        Satellites {
            anchors.centerIn: parent
            d: orb.d
            trails: orb.quality === "high"
            color: orb.main
            spin: orb.flow
            strength: orb.live
            conductor: orb
            scale: orb.ringScale(2) * orb.structure
        }

        GyroArcs {
            anchors.centerIn: parent
            diameter: orb.d * 0.54
            color: orb.main
            spin: orb.flow
            time: orb.mind
            chaos: orb.chaos
            strength: orb.live
            scale: orb.coreScale
        }

        SpectrumRing {
            anchors.centerIn: parent
            diameter: orb.d * 0.48
            level: orb.smoothLevel
            shift: orb.clock * 3
            maxLength: orb.d * (0.07 + 0.05 * orb.smoothLevel)
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
            border.width: 1.5 + 3 * (1 - orb.echo)
            border.color: Theme.primaryBright
            opacity: (1 - orb.echo) * 0.8
            visible: opacity > 0
        }

        OrbCore {
            anchors.centerIn: parent
            diameter: orb.d * 0.32
            color: orb.main
            glow: Math.min(1, 0.2 + 0.4 * orb.energy + orb.breathWave + 0.65 * orb.smoothLevel
                              + orb.flash)
            time: orb.mind
            chaos: orb.chaos
            level: orb.smoothLevel
            fluid: orb.quality !== "low" && !orb.reduceMotion
            // Crece con la masa antes del estallido y con la estructura después.
            scale: (1 + 0.2 * orb.smoothLevel) * orb.coreBounce
                   * (orb.reduceMotion ? 1 : Math.max(0.12 + 0.88 * orb.ringScale(0),
                                                      0.12 + 0.55 * orb.mass))
        }

        NeuralNet {
            anchors.centerIn: parent
            radius: orb.d * 0.2
            count: orb.quality === "high" ? 28 : orb.quality === "medium" ? 14 : 0
            color: orb.main
            spin: orb.flow * 0.7
            time: orb.mind
            chaos: orb.chaos
            strength: orb.live
            scale: orb.coreScale * orb.coreBounce
        }

        // Horizonte del cierre: un disco negro con un filo de luz que se traga el núcleo.
        Rectangle {
            anchors.centerIn: parent
            width: orb.d * 0.26 * orb.horizon
            height: width
            radius: width / 2
            color: Theme.bgBase
            border.width: 1.5
            border.color: Theme.primaryBright
            visible: orb.horizon > 0.01
        }
    }
}
