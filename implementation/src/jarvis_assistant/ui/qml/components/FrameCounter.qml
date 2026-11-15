// Contador de frames del modo de diagnóstico (`--ui-debug`, RNF-21).
import QtQuick
import ".."

Text {
    id: counter

    property real lowest: 0

    color: Theme.textMuted
    font.family: Theme.fontMono
    font.pixelSize: Theme.sizeLabel
    text: "-- fps"

    FrameAnimation {
        id: frames
        running: counter.visible
    }

    Timer {
        interval: 500
        repeat: true
        running: counter.visible
        onTriggered: {
            if (frames.smoothFrameTime <= 0)
                return
            var fps = 1 / frames.smoothFrameTime
            counter.lowest = counter.lowest > 0 ? Math.min(counter.lowest, fps) : fps
            counter.text = Math.round(fps) + " fps · mín " + Math.round(counter.lowest)
        }
    }
}
