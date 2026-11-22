// Triple clic: tres pulsaciones seguidas en el mismo sitio, como en la cabecera de una
// ventana. Se cuentan a mano: `tapCount` depende de las marcas de tiempo del evento.
import QtQuick

TapHandler {
    id: handler

    property int clicks: 0
    property double lastTap: 0
    property point lastPoint

    signal tripleTapped()

    onTapped: (point) => {
        var now = Date.now()
        var near = Math.abs(point.position.x - lastPoint.x) < 8
                   && Math.abs(point.position.y - lastPoint.y) < 8
        clicks = near && now - lastTap <= Qt.styleHints.mouseDoubleClickInterval
                 ? clicks + 1 : 1
        lastTap = now
        lastPoint = point.position
        if (clicks >= 3) {
            clicks = 0
            handler.tripleTapped()
        }
    }
}
