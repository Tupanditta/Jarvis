// Medidor de recursos: lo que consume el asistente ahora mismo, CPU y RAM, en dos esferas
// (`CpuGauge`, `RamGauge`). Forma parte de la pantalla de sesión, fijo en una esquina inferior
// (`usage.corner`), siempre la opuesta a la del de ruido; no se mueve ni cambia de tamaño. Un
// triple clic lo pasa a la otra esquina inferior y el de ruido cambia también. Solo se oculta
// con su botón del selector (`usage.toggle`).
//
// Solo se mide mientras está a la vista (`usage.watch`/`unwatch`).
import QtQuick
import ".."

Item {
    id: meter

    property bool watching: false        // a la vista: lo decide la pantalla
    readonly property int ringSize: 150

    implicitWidth: rings.implicitWidth
    implicitHeight: rings.implicitHeight

    onWatchingChanged: watching ? usage.watch() : usage.unwatch()
    Component.onDestruction: {
        if (watching)
            usage.unwatch()
    }

    // Debajo de cada esfera, en pequeño: núcleos y memoria en bruto.
    component Caption: Text {
        width: meter.ringSize
        height: 14
        horizontalAlignment: Text.AlignHCenter
        color: Theme.textSecondary
        font.family: Theme.fontTech
        font.pixelSize: 10
        font.letterSpacing: 1.4
        fontSizeMode: Text.HorizontalFit
        minimumPixelSize: 7
    }

    Row {
        id: rings

        spacing: Theme.space24

        Column {
            spacing: Theme.space4

            CpuGauge {
                objectName: "usage-cpu"
                width: meter.ringSize
                value: usage.cpu
                animated: !ui.reduceMotion
            }

            Caption {
                text: usage.cores + (usage.cores === 1 ? " NÚCLEO" : " NÚCLEOS")
            }
        }

        Column {
            spacing: Theme.space4

            RamGauge {
                objectName: "usage-ram"
                width: meter.ringSize
                value: usage.ram
                animated: !ui.reduceMotion
            }

            Caption {
                text: usage.totalText.length > 0 ? usage.ramText + " / " + usage.totalText
                                                 : usage.ramText
            }
        }
    }

    TripleTap {
        onTripleTapped: usage.switchCorner()
    }
}
