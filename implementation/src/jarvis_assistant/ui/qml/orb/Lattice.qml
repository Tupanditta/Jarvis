// Retícula: malla de puntos muy tenue, centrada en el orbe, que se ondula cuando la onda
// del latido pasa por ella.
import QtQuick
import ".."

Item {
    id: lattice

    property Item conductor          // el orbe
    property real centerX: width / 2
    property real centerY: height / 2
    property real d: 100             // D del orbe
    property bool active: true

    readonly property real step: Math.max(48, d * 0.24)
    readonly property int columns: active ? Math.ceil(width / step) + 1 : 0
    readonly property int rows: active ? Math.ceil(height / step) + 1 : 0
    readonly property real startX: centerX - Math.ceil(centerX / step) * step
    readonly property real startY: centerY - Math.ceil(centerY / step) * step
    readonly property real live: conductor ? conductor.live : 0

    visible: active && live > 0.01

    Repeater {
        model: lattice.columns * lattice.rows

        Rectangle {
            id: dot

            required property int index
            readonly property real px: lattice.startX + (index % lattice.columns) * lattice.step
            readonly property real py: lattice.startY + Math.floor(index / lattice.columns) * lattice.step
            readonly property real r: Math.sqrt((px - lattice.centerX) * (px - lattice.centerX)
                                                + (py - lattice.centerY) * (py - lattice.centerY))
                                      / lattice.d
            readonly property real shine: lattice.conductor ? lattice.conductor.wave(r) : 0

            width: 2 + 3 * shine
            height: width
            radius: width / 2
            x: px - width / 2
            y: py - height / 2
            color: lattice.conductor ? lattice.conductor.accent : Theme.primary
            // Dentro del orbe no hay retícula.
            opacity: r < 0.72 ? 0 : lattice.live * (0.1 + 0.6 * shine)
        }
    }
}
