// Contorno de un marco: un rectángulo con cada esquina redondeada, en chaflán o recta.
// El mismo contorno sirve para el fondo, el borde, el neón que lo recorre y el recorte de la
// textura, así que todos coinciden aunque la forma cambie.
.pragma library

// Formas de marco: [tipo, tamaño] de cada esquina, en el orden superior izquierda, superior
// derecha, inferior derecha, inferior izquierda. La esquina superior derecha nunca va en
// chaflán: ahí está el botón de cerrar.
var STYLES = {
    "round": [["round", 12], ["round", 12], ["round", 12], ["round", 12]],
    "cut": [["cut", 16], ["round", 4], ["cut", 16], ["round", 4]],
    "leaf": [["round", 16], ["round", 3], ["round", 16], ["round", 3]],
    "bracket": [["round", 2], ["round", 2], ["round", 2], ["round", 2]]
}

function corners(style) {
    return STYLES[style] || STYLES["round"]
}

// Las cuatro esquinas iguales, redondeadas con radio `radius`.
function rounded(radius) {
    return [["round", radius], ["round", radius], ["round", radius], ["round", radius]]
}

function _sizes(width, height, shape, inset) {
    var limit = Math.max(0, Math.min(width, height) / 2 - inset)
    return shape.map(function (corner) { return Math.max(0, Math.min(limit, corner[1])) })
}

function _corner(kind, size, x, y) {
    if (size <= 0)
        return ""
    return kind === "cut" ? " L " + x + " " + y
                          : " A " + size + " " + size + " 0 0 1 " + x + " " + y
}

// Ruta SVG del contorno, en el sentido de las agujas del reloj desde la esquina superior
// izquierda. `inset` lo mete hacia dentro: 0,5 deja un trazo de 1 px sobre píxeles enteros.
function path(width, height, shape, inset) {
    if (width <= 2 * inset || height <= 2 * inset)
        return ""
    var s = _sizes(width, height, shape, inset)
    var x0 = inset
    var y0 = inset
    var x1 = width - inset
    var y1 = height - inset
    return "M " + (x0 + s[0]) + " " + y0
           + " L " + (x1 - s[1]) + " " + y0 + _corner(shape[1][0], s[1], x1, y0 + s[1])
           + " L " + x1 + " " + (y1 - s[2]) + _corner(shape[2][0], s[2], x1 - s[2], y1)
           + " L " + (x0 + s[3]) + " " + y1 + _corner(shape[3][0], s[3], x0, y1 - s[3])
           + " L " + x0 + " " + (y0 + s[0]) + _corner(shape[0][0], s[0], x0 + s[0], y0)
           + " Z"
}

// Longitud del contorno, en píxeles.
function length(width, height, shape, inset) {
    if (width <= 2 * inset || height <= 2 * inset)
        return 0
    var s = _sizes(width, height, shape, inset)
    var total = 2 * (width + height - 4 * inset)
    for (var i = 0; i < 4; i++)
        total += s[i] * ((shape[i][0] === "cut" ? Math.SQRT2 : Math.PI / 2) - 2)
    return total
}

// Traza el contorno en un contexto 2D de `Canvas`, para recortar o rellenar.
function trace(ctx, width, height, shape, inset) {
    var s = _sizes(width, height, shape, inset)
    var x0 = inset
    var y0 = inset
    var x1 = width - inset
    var y1 = height - inset
    var points = [[x1, y0], [x1, y1], [x0, y1], [x0, y0]]          // vértices, desde la sup. dcha.
    var into = [[-1, 0], [0, -1], [1, 0], [0, 1]]                  // de vuelta por el lado de llegada
    var out = [[0, 1], [-1, 0], [0, -1], [1, 0]]                   // hacia el lado de salida
    ctx.beginPath()
    ctx.moveTo(x0 + s[0], y0)
    for (var i = 0; i < 4; i++) {
        var n = (i + 1) % 4                                        // esquina de `shape`
        var p = points[i]
        var size = s[n]
        ctx.lineTo(p[0] + into[i][0] * size, p[1] + into[i][1] * size)
        if (size <= 0)
            continue
        if (shape[n][0] === "cut")
            ctx.lineTo(p[0] + out[i][0] * size, p[1] + out[i][1] * size)
        else
            ctx.arcTo(p[0], p[1], p[0] + out[i][0] * size, p[1] + out[i][1] * size, size)
    }
    ctx.closePath()
}
