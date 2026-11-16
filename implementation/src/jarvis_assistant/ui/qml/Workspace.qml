// Área de trabajo de la pantalla de sesión: las ventanas flotantes de los módulos.
// Una por fila de `workspace` (`ui/workspace.py`). El panel de cada ventana solo se carga
// mientras la ventana está abierta.
//
// Al abrir sesión (`hold`, luego `release`) las ventanas esperan ocultas a que termine el
// despertar del orbe y salen de él una a una, de la de abajo a la de arriba. Las que se abren
// mientras tanto se suman a la cola.
//
// Cada ventana que aparece suena con un aviso corto. Si aparecen varias a la vez (sin
// animaciones), suena una sola vez.
//
// Una ventana apartada queda como pestaña en el borde o la esquina más cercanos a su centro:
// en el tercio de una esquina, en esa esquina; si no, en el borde más próximo, a su altura.
// Las esquinas son de las filas de arriba y de abajo; las columnas de los lados empiezan
// debajo de ellas. Las pestañas de un mismo borde se ponen en fila sin taparse, y en la fila
// de arriba dejan libre el hueco del selector (`reserveLeft`, `reserveRight`). Las que no
// caben en su fila pasan a otra, más hacia dentro.
import QtQuick
import QtMultimedia
import "components"

Item {
    id: area

    property Item conductor              // el orbe: su latido enciende el borde de las ventanas
    property real centerX: width / 2     // centro del orbe, en coordenadas de esta área
    property real centerY: height / 2
    property bool staging: false         // abriendo sesión: las ventanas esperan al orbe
    property real reserveLeft: 0         // hueco del selector en el borde de arriba, en x
    property real reserveRight: 0

    onWidthChanged: placeTabs()
    onHeightChanged: placeTabs()
    onReserveLeftChanged: placeTabs()
    onReserveRightChanged: placeTabs()

    // Recoloca las pestañas de las ventanas apartadas, una vez por vuelta del bucle de eventos.
    function placeTabs() {
        Qt.callLater(area.layoutTabs)
    }

    // Pone en fila, dentro de [lo, hi], piezas de tamaño `size` que quieren empezar en `want`:
    // cada una lo más cerca de donde quiere sin pisar a las demás. Las que no caben pasan a la
    // fila siguiente (`line`).
    function pack(items, lo, hi, size) {
        var gap = Theme.space8
        var fits = Math.max(1, Math.floor((hi - lo + gap) / (size + gap)))
        items.sort((a, b) => a.want - b.want)
        for (var first = 0; first < items.length; first += fits) {
            var line = items.slice(first, first + fits)
            var end = lo - gap
            for (var i = 0; i < line.length; ++i) {
                line[i].line = first / fits
                line[i].at = Math.max(line[i].want, end + gap)
                end = line[i].at + size
            }
            var start = hi + gap
            for (var j = line.length - 1; j >= 0; --j) {
                line[j].at = Math.max(lo, Math.min(line[j].at, start - gap - size))
                start = line[j].at
            }
        }
    }

    function layoutTabs() {
        var w = width
        var h = height
        if (w <= 0 || h <= 0)
            return
        var margin = Theme.space8
        var gap = Theme.space8
        var tabW = Theme.windowTab
        var tabH = Theme.windowHeader + 2
        var edges = { top: [], bottom: [], left: [], right: [] }
        for (var i = 0; i < stack.count; ++i) {
            var win = stack.itemAt(i)
            if (!win || !win.open || !win.aside)
                continue
            var cx = (win.fullX + win.fullWidth / 2) / w
            var cy = (win.fullY + win.fullHeight / 2) / h
            var hz = cx < 1 / 3 ? -1 : cx > 2 / 3 ? 1 : 0
            var vz = cy < 1 / 3 ? -1 : cy > 2 / 3 ? 1 : 0
            var edge
            if (vz !== 0)
                edge = vz < 0 ? "top" : "bottom"
            else if (hz !== 0)
                edge = hz < 0 ? "left" : "right"
            else {
                var nearest = Math.min(cx, 1 - cx, cy, 1 - cy)
                edge = nearest === cy ? "top" : nearest === 1 - cy ? "bottom"
                     : nearest === cx ? "left" : "right"
            }
            var want
            if (edge === "top" || edge === "bottom")
                want = hz < 0 ? margin : hz > 0 ? w - margin - tabW : cx * w - tabW / 2
            else
                want = cy * h - tabH / 2
            edges[edge].push({ win: win, want: want, at: 0, line: 0 })
        }

        // Fila de arriba: a los lados del selector, si lo hay.
        var top = [{ lo: margin, hi: w - margin, items: [] }]
        if (reserveRight > reserveLeft)
            top = [{ lo: margin, hi: reserveLeft - gap, items: [] },
                   { lo: reserveRight + gap, hi: w - margin, items: [] }]
        for (var t = 0; t < edges.top.length; ++t) {
            var item = edges.top[t]
            var middle = item.want + tabW / 2
            var side = top.length > 1 && middle > (reserveLeft + reserveRight) / 2 ? 1 : 0
            top[side].items.push(item)
        }
        var topLines = 1
        for (var s = 0; s < top.length; ++s) {
            pack(top[s].items, top[s].lo, Math.max(top[s].lo + tabW, top[s].hi), tabW)
            for (var a = 0; a < top[s].items.length; ++a) {
                var up = top[s].items[a]
                up.win.tabX = up.at
                up.win.tabY = margin + up.line * (tabH + gap)
                topLines = Math.max(topLines, up.line + 1)
            }
        }

        var bottomLines = 1
        pack(edges.bottom, margin, w - margin, tabW)
        for (var b = 0; b < edges.bottom.length; ++b) {
            var down = edges.bottom[b]
            down.win.tabX = down.at
            down.win.tabY = h - margin - tabH - down.line * (tabH + gap)
            bottomLines = Math.max(bottomLines, down.line + 1)
        }

        // Columnas de los lados, entre las filas de arriba y de abajo.
        var columnTop = margin + topLines * (tabH + gap)
        var columnBottom = h - margin - bottomLines * (tabH + gap)
        pack(edges.left, columnTop, columnBottom, tabH)
        for (var l = 0; l < edges.left.length; ++l) {
            edges.left[l].win.tabX = margin + edges.left[l].line * (tabW + gap)
            edges.left[l].win.tabY = edges.left[l].at
        }
        pack(edges.right, columnTop, columnBottom, tabH)
        for (var r = 0; r < edges.right.length; ++r) {
            edges.right[r].win.tabX = w - margin - tabW - edges.right[r].line * (tabW + gap)
            edges.right[r].win.tabY = edges.right[r].at
        }
    }

    // Empieza el despertar: ninguna ventana se ve hasta `release`.
    function hold() {
        launches.stop()
        if (ui.reduceMotion) {
            staging = false
            return
        }
        staging = true
        for (var i = 0; i < stack.count; ++i)
            stack.itemAt(i).held = true
    }

    // El orbe ya ha despertado: lanza las ventanas abiertas, una a una.
    function release() {
        if (!staging)
            return
        launchNext()
        launches.start()
    }

    // Deja de esperar sin animación: otra transición ha cortado el despertar.
    function cancel() {
        launches.stop()
        staging = false
        for (var i = 0; i < stack.count; ++i)
            stack.itemAt(i).held = false
    }

    // Lanza la ventana abierta que queda más abajo; si no queda ninguna, termina.
    function launchNext() {
        var next = null
        for (var i = 0; i < stack.count; ++i) {
            var win = stack.itemAt(i)
            if (win.held && win.open && (next === null || win.order < next.order))
                next = win
        }
        if (next !== null) {
            next.emerge()
            return
        }
        cancel()
    }

    SoundEffect {
        id: chime

        property double lastPlayed: 0

        source: Qt.resolvedUrl("../assets/sounds/window_open.wav")
        volume: 0.6

        function ring() {
            var now = Date.now()
            if (now - lastPlayed < 120)
                return
            lastPlayed = now
            play()
        }
    }

    Timer {
        id: launches

        interval: Theme.motionEmergeGap
        repeat: true
        onTriggered: area.launchNext()
    }

    Repeater {
        id: stack

        model: workspace
        onItemAdded: area.placeTabs()

        FloatingWindow {
            id: win

            required property string component
            required property string style
            required property int order
            required windowId
            required title
            required icon
            required open
            required focused
            required aside
            required fx
            required fy
            required fw
            required fh
            required minWidth
            required minHeight

            areaWidth: area.width
            areaHeight: area.height
            originX: area.centerX
            originY: area.centerY
            frameStyle: style
            beat: {
                if (!area.conductor || !open)
                    return 0
                var dx = x + width / 2 - area.centerX
                var dy = y + height / 2 - area.centerY
                return area.conductor.wave(Math.sqrt(dx * dx + dy * dy) / area.conductor.d)
            }
            // Las pestañas, por encima de las ventanas sin apartar.
            z: aside ? order + 1000 : order
            subtitle: loader.item ? loader.item.summary : ""

            onMoved: (left, top) => workspace.move(windowId, left, top)
            onResized: (left, top, wide, tall) => workspace.resize(windowId, left, top, wide, tall)
            onClosed: workspace.close(windowId)
            onActivated: workspace.raise_window(windowId)
            onAppeared: chime.ring()
            onAsideRequested: workspace.set_aside(windowId)
            onRestored: workspace.restore(windowId)
            onAsideChanged: area.placeTabs()
            onOpenChanged: area.placeTabs()

            Loader {
                id: loader

                anchors.fill: parent
                active: win.open
                source: Qt.resolvedUrl("panels/" + win.component)
                onLoaded: {
                    item.embedded = true
                    item.active = Qt.binding(() => win.focused)
                }
            }
        }
    }
}
