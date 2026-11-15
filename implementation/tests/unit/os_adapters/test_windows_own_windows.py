"""Ventanas propias en Windows (plataforma.md): pasar al frente y ventana que no se activa."""
from jarvis_assistant.os_adapters import windows
from jarvis_assistant.os_adapters.windows import WindowsAdapter


class FakeUser32:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.ex_style = 0x100

    def SetWindowPos(self, hwnd, after, x, y, cx, cy, flags):
        self.calls.append(("SetWindowPos", hwnd, after, flags))
        return 1

    def GetWindowLongW(self, hwnd, index):
        self.calls.append(("GetWindowLongW", hwnd, index))
        return self.ex_style

    def SetWindowLongW(self, hwnd, index, value):
        self.calls.append(("SetWindowLongW", hwnd, index, value))
        self.ex_style = value
        return 1


def make(user32):
    later = []
    adapter = WindowsAdapter({}, user32=user32, call_later=lambda s, f: later.append((s, f)))
    return adapter, later


def test_pasar_al_frente_marca_superior_y_quita_la_marca_un_segundo_despues():
    user32 = FakeUser32()
    adapter, later = make(user32)
    adapter.bring_own_window_to_front(42)
    flags = windows.SWP_NOMOVE | windows.SWP_NOSIZE | windows.SWP_SHOWWINDOW
    assert user32.calls == [("SetWindowPos", 42, windows.HWND_TOPMOST, flags)]
    ((seconds, callback),) = later
    assert seconds == 1.0
    callback()
    assert user32.calls[-1] == (
        "SetWindowPos", 42, windows.HWND_NOTOPMOST, windows.SWP_NOMOVE | windows.SWP_NOSIZE
        | windows.SWP_NOACTIVATE,
    )  # fmt: skip


def test_ventana_que_no_se_activa_anade_ws_ex_noactivate_y_conserva_el_resto():
    user32 = FakeUser32()
    adapter, _ = make(user32)
    adapter.make_non_activating(7)
    assert user32.ex_style == 0x100 | windows.WS_EX_NOACTIVATE
    assert ("GetWindowLongW", 7, windows.GWL_EXSTYLE) in user32.calls
    adapter.make_non_activating(7, enabled=False)  # al hacer clic en su caja de texto
    assert user32.ex_style == 0x100


def test_sin_user32_no_hace_nada():
    adapter = WindowsAdapter({}, user32=None)
    adapter.bring_own_window_to_front(1)
    adapter.make_non_activating(1)
