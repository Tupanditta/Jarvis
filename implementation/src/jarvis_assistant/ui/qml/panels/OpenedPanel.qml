// Panel de aperturas: una tarjeta por elemento abierto, con su estado y el botón «traer al
// frente» (hud.md, sección 3). El botón es uno de los tres únicos controles de ratón.
import QtQuick
import ".."
import "../components"

PanelFrame {
    id: panel

    title: "Aperturas"

    ListView {
        id: list

        anchors.fill: parent
        clip: true
        model: opened.items
        spacing: Theme.space4
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        visible: count > 0

        delegate: Rectangle {
            id: card

            required property var modelData

            width: ListView.view.width
            height: 40
            radius: Theme.radiusCard
            color: Theme.bgRaised

            Image {
                id: glyph

                x: Theme.space12
                width: 16
                height: 16
                sourceSize.width: 32
                sourceSize.height: 32
                source: Theme.icon(card.modelData.kind)
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                x: glyph.x + 16 + Theme.space8
                width: Math.max(0, dot.x - x - Theme.space8)
                text: card.modelData.title
                color: Theme.textPrimary
                font.family: Theme.fontBody
                font.pixelSize: Theme.sizeText
                elide: Text.ElideRight
                anchors.verticalCenter: parent.verticalCenter
            }

            StatusDot {
                id: dot

                x: (front.visible ? front.x : parent.width - Theme.space4) - 8 - Theme.space8
                status: card.modelData.status
                anchors.verticalCenter: parent.verticalCenter
            }

            // Desactivado si la ventana ya no existe; ausente si el sistema no lo permite.
            IconButton {
                id: front

                x: parent.width - width - Theme.space8
                icon: "frente"
                visible: opened.focusSupported
                enabled: card.modelData.canFocus === true
                opacity: enabled ? 1 : 0.3
                anchors.verticalCenter: parent.verticalCenter
                onClicked: opened.focus(card.modelData.id)
            }
        }
    }

    EmptyState {
        anchors.fill: parent
        visible: list.count === 0
        text: "Nada abierto"
    }
}
