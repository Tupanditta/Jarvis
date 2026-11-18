// Medidor de recursos: lo que consume el asistente ahora mismo, CPU y RAM, en dos anillos de
// neón. Forma parte de la pantalla de sesión, fijo en una esquina inferior (`usage.corner`);
// no se mueve ni cambia de tamaño. Un triple clic lo pasa a la otra esquina inferior. Solo se
// oculta con su botón del selector (`usage.toggle`).
//
// Solo se mide mientras está a la vista (`usage.watch`/`unwatch`).
import QtQuick
import ".."

Item {
    id: meter

    property bool watching: false        // a la vista: lo decide la pantalla
    readonly property int ringSize: 120

    implicitWidth: rings.implicitWidth
    implicitHeight: rings.implicitHeight + caption.height + Theme.space4

    onWatchingChanged: watching ? usage.watch() : usage.unwatch()
    Component.onDestruction: {
        if (watching)
            usage.unwatch()
    }

    Row {
        id: rings

        spacing: Theme.space12

        NeonRing {
            objectName: "usage-cpu"
            width: meter.ringSize
            value: usage.cpu
            label: "CPU"
            color: Theme.neonCyan
            animated: !ui.reduceMotion
        }

        NeonRing {
            objectName: "usage-ram"
            width: meter.ringSize
            value: usage.ram
            label: "RAM"
            color: Theme.neonMagenta
            animated: !ui.reduceMotion
        }
    }

    // Debajo, en pequeño: núcleos y memoria en bruto.
    Row {
        id: caption

        y: rings.height + Theme.space4
        height: 14

        Repeater {
            model: [
                usage.cores + (usage.cores === 1 ? " NÚCLEO" : " NÚCLEOS"),
                usage.totalText.length > 0 ? usage.ramText + " / " + usage.totalText : usage.ramText,
            ]

            Text {
                required property string modelData
                required property int index

                width: meter.ringSize + (index === 0 ? Theme.space12 : 0)
                horizontalAlignment: Text.AlignHCenter
                rightPadding: index === 0 ? Theme.space12 : 0
                text: modelData
                color: Theme.textSecondary
                font.family: Theme.fontTech
                font.pixelSize: 9
                font.letterSpacing: 1.2
            }
        }
    }

    TripleTap {
        onTripleTapped: usage.switchCorner()
    }
}
