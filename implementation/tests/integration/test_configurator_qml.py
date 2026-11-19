"""Ventana de configuración y editor de plantillas con QML real (configurador.md)."""
from pathlib import Path

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from jarvis_assistant import config as cfg
from jarvis_assistant.configurator.window import ConfigWindow


@pytest.fixture
def settings(tmp_path, qtbot):
    saved = []
    window = ConfigWindow(tmp_path / "config", on_saved=lambda: saved.append(True))
    window.show()
    yield window, saved, tmp_path / "config"
    if window.window is not None:
        window.window.close()
        window.window.hide()
    window.editor.cancel()


def find(root, name: str) -> QQuickItem:
    """Elemento por su `objectName`, por el árbol visual: los delegados de un `Repeater` no
    cuelgan de la ventana como `QObject`."""
    pending = [root.contentItem()]
    while pending:
        item = pending.pop()
        if item.objectName() == name:
            return item
        pending.extend(item.childItems())
    raise AssertionError(f"No hay ningún elemento «{name}»")


def click(window, item: QQuickItem) -> None:
    center = item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()
    QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, center)


def open_tab(window, section_id: str, qtbot) -> None:
    click(window.window, find(window.window, f"sectionTab-{section_id}"))
    qtbot.wait(50)


def test_la_ventana_y_todos_sus_apartados_cargan_sin_avisos(settings, qtbot):
    window, _saved, _directory = settings
    qtbot.waitUntil(lambda: window.window.isVisible(), timeout=2000)
    for section in ("plantillas", "perfiles", "sonido"):
        open_tab(window, section, qtbot)
    assert window.warnings == []
    assert not find(window.window, "saveButton").isEnabled()


def test_guardar_con_el_boton_escribe_y_avisa(settings, qtbot):
    window, saved, directory = settings
    open_tab(window, "sonido", qtbot)
    click(window.window, find(window.window, "soundToggle"))
    assert window.dirty and window.window.title().endswith("●")
    click(window.window, find(window.window, "saveButton"))
    assert saved == [True]
    assert cfg.load(directory)[0].settings.sound.enabled is False
    assert not window.dirty and window.saved
    assert window.warnings == []


def test_cerrar_con_cambios_pregunta_y_salir_sin_guardar_los_descarta(settings, qtbot):
    window, saved, directory = settings
    open_tab(window, "sonido", qtbot)
    click(window.window, find(window.window, "soundToggle"))
    click(window.window, find(window.window, "cancelButton"))
    dialog = find(window.window, "confirmClose")
    qtbot.waitUntil(lambda: dialog.isVisible(), timeout=2000)
    assert window.window.isVisible()
    click(window.window, find(window.window, "discardButton"))
    qtbot.waitUntil(lambda: not window.window.isVisible(), timeout=2000)
    assert saved == [] and not Path(directory / "settings.toml").exists()
    assert not window.dirty


def test_el_editor_de_plantillas_se_abre_y_acepta(settings, qtbot):
    window, _saved, _directory = settings
    window.sections["plantillas"].create()
    qtbot.waitUntil(lambda: window.editor_window.isVisible(), timeout=2000)
    editor_root = window.editor_window
    find(editor_root, "dockHandle")
    find(editor_root, "inputHandle")
    click(editor_root, find(editor_root, "show-comandos"))
    assert window.editor.workspace.placement("comandos").open
    click(editor_root, find(editor_root, "editorAccept"))
    qtbot.waitUntil(lambda: not window.editor_window.isVisible(), timeout=2000)
    assert [item["name"] for item in window.sections["plantillas"].items] == [
        "Fábrica", "Plantilla nueva"
    ]
    assert window.dirty
    assert window.warnings == []


def test_al_cerrar_avisa_para_que_se_destruya(settings, qtbot):
    window, _saved, _directory = settings
    closed = []
    window.closed.connect(lambda: closed.append(True))
    click(window.window, find(window.window, "cancelButton"))
    qtbot.waitUntil(lambda: closed == [True], timeout=2000)


def test_mostrar_de_nuevo_trae_la_ventana_sin_perder_cambios(settings, qtbot):
    window, _saved, _directory = settings
    window.sections["sonido"].setEnabled(False)
    window.show()
    assert window.dirty


def type_into(window, field: QQuickItem, text: str, qtbot) -> None:
    """Clic en el campo, borra lo que haya y escribe, sin pulsar Enter ni salir del campo."""
    click(window, field)
    qtbot.waitUntil(field.hasActiveFocus, timeout=2000)
    QTest.keyClick(window, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    QTest.keyClick(window, Qt.Key.Key_Backspace)
    for char in text:  # `keyClicks` no admite ventanas QML
        QTest.keyClick(window, char)


def test_el_nombre_escrito_en_el_editor_vale_al_pulsar_aceptar_sin_salir_del_campo(
    settings, qtbot
):
    window, _saved, directory = settings
    window.sections["plantillas"].create()
    editor_root = window.editor_window
    qtbot.waitUntil(editor_root.isVisible, timeout=2000)
    type_into(editor_root, find(editor_root, "field-Nombre"), "Estudio con espacios", qtbot)
    click(editor_root, find(editor_root, "editorAccept"))
    qtbot.waitUntil(lambda: not editor_root.isVisible(), timeout=2000)
    assert [item["name"] for item in window.sections["plantillas"].items][1] == (
        "Estudio con espacios"
    )
    assert window.save()
    assert [layout.name for layout in cfg.load(directory)[0].layouts] == ["Estudio con espacios"]


def test_el_nombre_de_usuario_escrito_vale_al_pulsar_guardar_sin_salir_del_campo(
    settings, qtbot
):
    window, _saved, directory = settings
    open_tab(window, "perfiles", qtbot)
    type_into(window.window, find(window.window, "field-Nombre del usuario"), "Jane Doe", qtbot)
    assert window.dirty
    click(window.window, find(window.window, "saveButton"))
    profile = cfg.load(directory)[0].profiles[0]
    assert profile.user_name == "Jane Doe"
    assert window.warnings == []


# --- Perfiles protegidos -----------------------------------------------------------------------


@pytest.fixture
def protected(tmp_path, qtbot):
    from jarvis_assistant.core.database import Database
    from jarvis_assistant.core.security import ProfileVault, hash_password

    directory = tmp_path / "config"
    directory.mkdir()
    (directory / "profiles.toml").write_text(
        '[[profiles]]\nid = "secreto"\nname = "Confidencial"\n', encoding="utf-8"
    )
    db = Database(":memory:")
    db.migrate()
    vault = ProfileVault(db)
    vault.set_password_hash("secreto", hash_password("clave-1234"))
    window = ConfigWindow(directory, vault=vault)
    window.show()
    yield window
    if window.window is not None:
        window.window.close()
        window.window.hide()
    window.editor.cancel()
    db.close()


def test_un_perfil_protegido_se_desbloquea_con_su_contrasena_en_la_pagina(protected, qtbot):
    window = protected
    open_tab(window, "perfiles", qtbot)
    lock = find(window.window, "profileLock")
    assert lock.isVisible()
    field = find(window.window, "unlockField")
    click(window.window, field)
    for char in "mala":
        QTest.keyClick(window.window, char)
    click(window.window, find(window.window, "unlockProfile"))
    qtbot.wait(50)
    assert find(window.window, "unlockMessage").property("text") != ""
    assert lock.isVisible()
    click(window.window, field)
    for char in "clave-1234":
        QTest.keyClick(window.window, char)
    QTest.keyClick(window.window, Qt.Key.Key_Return)
    qtbot.waitUntil(lambda: not lock.isVisible(), timeout=2000)
    assert find(window.window, "setPassword").property("text") == "Cambiar contraseña"
    assert window.warnings == []


def test_el_acedor_se_activa_desde_su_tarjeta_y_no_hay_boton_de_eliminar(protected, qtbot):
    window = protected
    open_tab(window, "perfiles", qtbot)
    with pytest.raises(AssertionError):
        find(window.window, "removeProfile")
    click(window.window, find(window.window, "adminPasswordButton"))
    qtbot.wait(50)
    for name in ("adminNew", "adminRepeated"):
        click(window.window, find(window.window, name))
        for char in "maestra-1234":
            QTest.keyClick(window.window, char)
    click(window.window, find(window.window, "adminAccept"))
    qtbot.waitUntil(lambda: window.sections["perfiles"].adminActive, timeout=2000)
    assert find(window.window, "adminMessage").property("text") == ""
    assert find(window.window, "adminPasswordButton").property("text") == "Cambiar contraseña"
    assert window.warnings == []
