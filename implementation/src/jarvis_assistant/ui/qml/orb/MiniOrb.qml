// Mini orbe del HUD (44 px): núcleo, un anillo y el espectro simplificado. Reacciona al nivel
// de la voz del asistente. En reposo no tiene ninguna animación continua.
import QtQuick
import ".."

Item {
    id: mini

    property real size: 44
    property string activity: "dormido"
    property real level: 0
    property bool reduceMotion: false
    property bool running: true

    property string mode: "dormido"      // aspecto mientras suena una frase
    readonly property string look: activity === "hablando" ? mode : activity
    readonly property bool awake: look !== "reposo" && look !== "dormido"
    property real smoothLevel: level
    property real pulse: 1
    readonly property color main: look === "esperando" ? Theme.statusPending
                                  : awake ? Theme.primary : Theme.primaryDim

    width: size
    height: size
    opacity: look === "dormido" ? 0.25 : awake ? 1 : 0.45

    Behavior on opacity {
        NumberAnimation { duration: mini.reduceMotion ? Theme.motionState : Theme.motionTransition }
    }
    Behavior on smoothLevel {
        NumberAnimation { duration: Theme.motionLevel }
    }

    onActivityChanged: {
        if (activity !== "hablando")
            mode = activity === "reposo" || activity === "dormido" ? activity : "escuchando"
    }

    // Despertar: un pulso. Dormirse: se atenúa (lo hace la opacidad).
    function play(kind) {
        mode = kind === "sleep_rest" ? "reposo" : kind === "sleep_close" ? "dormido" : "escuchando"
        if ((kind === "wake" || kind === "wake_from_rest") && !reduceMotion)
            beat.restart()
    }

    SequentialAnimation {
        id: beat

        NumberAnimation { target: mini; property: "pulse"; to: 1.25; duration: 300; easing.type: Easing.OutQuad }
        NumberAnimation { target: mini; property: "pulse"; to: 1; duration: 1700; easing.type: Easing.OutCubic }
    }

    Rectangle {
        id: ring

        anchors.centerIn: parent
        width: mini.size * 0.86
        height: width
        radius: width / 2
        color: "transparent"
        border.width: 1
        border.color: Theme.alpha(mini.main, 0.6)
        scale: mini.pulse

        // Una marca que hace visible el giro.
        Rectangle {
            width: 3
            height: 3
            radius: 1.5
            color: mini.main
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.top
        }

        RotationAnimation on rotation {
            from: 0
            to: 360
            duration: mini.look === "procesando" ? 3000 : 9000
            loops: Animation.Infinite
            running: mini.running && mini.awake && !mini.reduceMotion
        }
    }

    SpectrumRing {
        anchors.centerIn: parent
        diameter: mini.size * 0.5
        bars: 16
        level: mini.smoothLevel
        maxLength: mini.size * 0.14
        color: mini.main
    }

    Rectangle {
        anchors.centerIn: parent
        width: mini.size * 0.36
        height: width
        radius: width / 2
        color: mini.main
        scale: (1 + 0.12 * mini.smoothLevel) * mini.pulse

        Rectangle {
            anchors.centerIn: parent
            width: parent.width * 0.45
            height: width
            radius: width / 2
            color: Theme.primaryBright
            opacity: mini.awake ? 1 : 0.4
        }
    }
}
