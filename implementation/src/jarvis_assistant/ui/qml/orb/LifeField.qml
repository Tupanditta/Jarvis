// Fondo vivo de la pantalla de sesión: retícula, polvo, constelación de mini orbes y orbes
// satélite. Va por debajo del orbe y de los paneles.
//
// No tiene reloj propio: todo lo mueve el orbe (`conductor`), con sus relojes, su latido y
// su color. En dormido no se ve ni se anima; en reposo queda casi apagado.
import QtQuick
import ".."

Item {
    id: field

    property Item conductor          // el orbe
    property real centerX: width / 2  // centro del orbe, en coordenadas de este elemento
    property real centerY: height / 2
    property string quality: "high"

    readonly property real d: conductor ? conductor.d : 100
    readonly property bool full: quality === "high"
    // El fondo sale del núcleo al despertar y vuelve a él al dormirse, antes que los anillos.
    readonly property real gather: {
        if (!conductor || conductor.reduceMotion)
            return 1
        var x = Math.max(0, Math.min(1, (conductor.assembly - 0.2) / 0.8))
        return 1 - Math.pow(1 - x, 2)
    }

    opacity: conductor ? Math.min(1, conductor.brightness * 1.6 + conductor.flash) : 0
    visible: quality !== "low" && opacity > 0

    Lattice {
        anchors.fill: parent
        conductor: field.conductor
        centerX: field.centerX
        centerY: field.centerY
        d: field.d
        active: field.full
    }

    Dust {
        anchors.fill: parent
        conductor: field.conductor
        count: field.full ? 70 : 35
        fade: field.gather
    }

    Constellation {
        anchors.fill: parent
        conductor: field.conductor
        centerX: field.centerX
        centerY: field.centerY
        d: field.d
        count: field.full ? 45 : 22
        gather: field.gather
    }

    SatelliteOrbs {
        conductor: field.conductor
        x: field.centerX
        y: field.centerY
        d: field.d
        gather: field.gather
    }
}
