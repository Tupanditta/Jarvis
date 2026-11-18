// Medidor de ruido: el ruido que hay alrededor ahora mismo, en decibelios aproximados, en un
// anillo de neón para medir la concentración. Forma parte de la pantalla de sesión, fijo en
// una esquina inferior (`noise.corner`); si el de recursos está en la misma esquina, se pone a
// su lado. No se mueve ni cambia de tamaño. Un triple clic lo pasa a la otra esquina inferior.
// Solo se muestra u oculta con su botón del selector (`noise.toggle`).
//
// Solo se abre el micrófono mientras está a la vista (`noise.watch`/`unwatch`).
import QtQuick
import ".."

Item {
    id: meter

    property bool watching: false        // a la vista: lo decide la pantalla
    readonly property int ringSize: 120

    implicitWidth: ring.width
    implicitHeight: ring.height + caption.height + Theme.space4

    onWatchingChanged: watching ? noise.watch() : noise.unwatch()
    Component.onDestruction: {
        if (watching)
            noise.unwatch()
    }

    NeonRing {
        id: ring

        objectName: "noise-db"
        width: meter.ringSize
        value: noise.level
        maximum: 100
        alert: 65                        // ruido que ya no deja concentrarse
        unit: "dB"
        label: "RUIDO"
        color: Theme.neonLime
        animated: !ui.reduceMotion
    }

    // Debajo, en pequeño: lo que el ruido deja concentrarse.
    Text {
        id: caption

        objectName: "noise-focus"
        y: ring.height + Theme.space4
        width: meter.ringSize
        height: 14
        horizontalAlignment: Text.AlignHCenter
        text: noise.focusText
        color: noise.available ? Theme.textSecondary : Theme.statusError
        font.family: Theme.fontTech
        font.pixelSize: 9
        font.letterSpacing: 1.2
        fontSizeMode: Text.HorizontalFit
        minimumPixelSize: 7
    }

    TripleTap {
        onTripleTapped: noise.switchCorner()
    }
}
