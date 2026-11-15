// Utilidades de los elementos vivos del orbe y del fondo.
.pragma library

// Valor fijo entre 0 y 1 para el elemento `i`. `salt` separa las series entre sí.
function hash(i, salt) {
    var x = Math.sin(i * 127.1 + salt * 311.7) * 43758.5453
    return x - Math.floor(x)
}

// Parejas [a, b] que unen cada punto con sus `k` vecinos más cercanos, sin repetir.
// Los puntos tienen `x`, `y` y, si es una esfera, `z`.
function nearest(points, k) {
    var pairs = []
    var seen = {}
    for (var a = 0; a < points.length; a++) {
        var others = []
        for (var b = 0; b < points.length; b++) {
            if (a === b)
                continue
            var dx = points[a].x - points[b].x
            var dy = points[a].y - points[b].y
            var dz = (points[a].z || 0) - (points[b].z || 0)
            others.push({ index: b, distance: dx * dx + dy * dy + dz * dz })
        }
        others.sort(function (p, q) { return p.distance - q.distance })
        for (var n = 0; n < Math.min(k, others.length); n++) {
            var low = Math.min(a, others[n].index)
            var high = Math.max(a, others[n].index)
            var key = low + "-" + high
            if (!seen[key]) {
                seen[key] = true
                pairs.push([low, high])
            }
        }
    }
    return pairs
}
