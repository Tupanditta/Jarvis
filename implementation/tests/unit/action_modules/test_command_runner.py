"""Módulo Comandos (comandos.md) sobre un sistema de archivos temporal y un lanzador falso."""
import asyncio
import sys
from pathlib import Path

import pytest

from fakes.context import ContextRig, settle
from jarvis_assistant.action_modules import command_runner
from jarvis_assistant.action_modules.command_runner import CommandRunner, build_tree
from jarvis_assistant.core import events
from jarvis_assistant.core.action_api import CommandLine, Phrase
from jarvis_assistant.core.content import Entry, TreeNode
from jarvis_assistant.os_adapters import processes

GIT_STATUS = CommandLine("git", "git", ("status",))


class FakeStream:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()

    def feed(self, *lines: bytes) -> None:
        for line in lines:
            self._queue.put_nowait(line)

    async def readline(self) -> bytes:
        return await self._queue.get()


class FakeProcess:
    pid = 4321

    def __init__(self) -> None:
        self.stdout = FakeStream()
        self.stderr = FakeStream()
        self._code: asyncio.Future[int] = asyncio.get_running_loop().create_future()

    def finish(self, code: int) -> None:
        self.stdout.feed(b"")
        self.stderr.feed(b"")
        if not self._code.done():
            self._code.set_result(code)

    async def wait(self) -> int:
        return await self._code


class Launches:
    """Lanzador falso: guarda lo lanzado y devuelve procesos que la prueba controla."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...], Path]] = []
        self.processes: list[FakeProcess] = []
        self.killed: list[int] = []
        self.error: Exception | None = None

    async def launch(self, executable, args, cwd):
        self.calls.append((executable, tuple(args), cwd))
        if self.error is not None:
            raise self.error
        self.processes.append(FakeProcess())
        return self.processes[-1]

    def kill(self, pid: int) -> None:
        self.killed.append(pid)
        for process in self.processes:
            process.finish(-9)


@pytest.fixture
def rig(tmp_path):
    rig = ContextRig(tmp_path)
    rig.home.mkdir(parents=True, exist_ok=True)
    yield rig
    rig.close()


@pytest.fixture
def launches():
    return Launches()


@pytest.fixture
def module(launches):
    return CommandRunner(launcher=launches.launch, kill_tree=launches.kill)


# --- cd, ls, pwd, clear ----------------------------------------------------------------------


async def test_cd_a_una_carpeta_valida(rig, module):
    target = rig.home / "Proyectos"
    target.mkdir()
    result = await module.execute("cd", {"ruta": target}, rig.ctx)
    assert result.status == "completado"
    assert result.speech == Phrase("comandos.cd", {"carpeta": "Proyectos"})
    assert rig.workdir.path == target
    assert rig.events == [events.WorkdirChanged(str(target))]


async def test_cd_relativo_se_resuelve_respecto_al_directorio_de_trabajo(rig, module):
    (rig.home / "a" / "b").mkdir(parents=True)
    rig.workdir.change(rig.home / "a")
    await module.execute("cd", {"ruta": Path("b")}, rig.ctx)
    assert rig.workdir.path == rig.home / "a" / "b"


async def test_cd_a_una_carpeta_inexistente_o_a_un_archivo_no_cambia_nada(rig, module):
    (rig.home / "notas.txt").write_text("x")
    missing = await module.execute("cd", {"ruta": rig.home / "nada"}, rig.ctx)
    assert (missing.status, missing.speech) == (
        "error", Phrase("ruta.no_existe", {"nombre": "nada"}),
    )  # fmt: skip
    a_file = await module.execute("cd", {"ruta": rig.home / "notas.txt"}, rig.ctx)
    assert (a_file.status, a_file.speech) == (
        "error", Phrase("ruta.no_es_carpeta", {"nombre": "notas.txt"}),
    )  # fmt: skip
    assert rig.workdir.path == rig.home
    assert rig.events == []


async def test_ls_ordena_carpetas_primero_y_cuenta(rig, module):
    for folder in ("zeta", "Alfa"):
        (rig.home / folder).mkdir()
    for name in ("b.txt", "A.txt", "c.txt"):
        (rig.home / name).write_text("x")
    result = await module.execute("ls", {}, rig.ctx)
    listed = rig.last(events.DirectoryListed)
    assert listed.path == str(rig.home)
    assert listed.entries == (
        Entry("Alfa", True), Entry("zeta", True),
        Entry("A.txt", False), Entry("b.txt", False), Entry("c.txt", False),
    )  # fmt: skip
    assert listed.total == 5
    assert result.speech == Phrase(
        "comandos.ls",
        {"carpeta": rig.home.name, "carpetas": "2 carpetas", "archivos": "3 archivos"},
    )


async def test_ls_dice_el_singular(rig, module):
    (rig.home / "una").mkdir()
    (rig.home / "uno.txt").write_text("x")
    result = await module.execute("ls", {}, rig.ctx)
    assert result.speech.params == {
        "carpeta": rig.home.name, "carpetas": "1 carpeta", "archivos": "1 archivo"
    }


async def test_ls_muestra_como_maximo_500_entradas(rig, module, monkeypatch):
    monkeypatch.setattr(command_runner, "MAX_LISTED", 3)
    for index in range(5):
        (rig.home / f"f{index}.txt").write_text("x")
    await module.execute("ls", {}, rig.ctx)
    listed = rig.last(events.DirectoryListed)
    assert len(listed.entries) == 3 and listed.total == 5


async def test_pwd_dice_y_muestra_el_directorio(rig, module):
    result = await module.execute("pwd", {}, rig.ctx)
    assert result.speech == Phrase("comandos.pwd", {"ruta": str(rig.home)})
    assert rig.events == [events.WorkdirChanged(str(rig.home))]


async def test_clear_vacia_el_panel_sin_voz(rig, module):
    result = await module.execute("clear", {}, rig.ctx)
    assert (result.status, result.speech) == ("completado", None)
    assert rig.events == [events.CommandPanelCleared()]


async def test_al_abrir_la_sesion_el_panel_empieza_vacio_en_la_carpeta_del_usuario(rig, module):
    await module.on_session_opened(rig.ctx)
    assert rig.events == [events.CommandPanelCleared(), events.WorkdirChanged(str(rig.home))]


# --- Árbol (RN-40) ---------------------------------------------------------------------------


def test_arbol_la_raiz_no_cuenta_y_baja_tres_niveles(tmp_path):
    (tmp_path / "a" / "b" / "c" / "d").mkdir(parents=True)
    (tmp_path / "a" / "b" / "c" / "d" / "hondo.txt").write_text("x")
    (tmp_path / "a" / "uno.txt").write_text("x")
    (tmp_path / "z.txt").write_text("x")
    tree = build_tree(tmp_path)
    assert tree.nodes == (
        TreeNode("a", 1, True),
        TreeNode("b", 2, True),
        TreeNode("c", 3, True),  # nivel 3: aparece, sin hijos
        TreeNode("uno.txt", 2, False),
        TreeNode("z.txt", 1, False),
    )
    assert (tree.dirs, tree.files, tree.truncated) == (3, 2, False)


def test_arbol_se_corta_a_las_200_entradas(tmp_path):
    for index in range(150):
        (tmp_path / f"f{index:03}.txt").write_text("x")
    (tmp_path / "carpeta").mkdir()
    for index in range(100):
        (tmp_path / "carpeta" / f"g{index:03}.txt").write_text("x")
    tree = build_tree(tmp_path)
    assert len(tree.nodes) == 200
    assert tree.truncated
    assert (tree.dirs, tree.files) == (1, 199)
    # En anchura: el nivel 1 entra entero y el corte cae en el nivel 2.
    assert sum(node.depth == 1 for node in tree.nodes) == 151


def test_arbol_con_exactamente_200_entradas_no_esta_recortado(tmp_path):
    for index in range(200):
        (tmp_path / f"f{index:03}.txt").write_text("x")
    tree = build_tree(tmp_path)
    assert (len(tree.nodes), tree.truncated) == (200, False)


def test_arbol_de_una_carpeta_vacia(tmp_path):
    assert build_tree(tmp_path).nodes == ()


async def test_arbol_del_directorio_de_trabajo_o_de_la_ruta_indicada(rig, module):
    (rig.home / "docs" / "sub").mkdir(parents=True)
    (rig.home / "docs" / "a.txt").write_text("x")
    here = await module.execute("arbol", {}, rig.ctx)
    assert rig.last(events.DirectoryTreeBuilt).root == str(rig.home)
    assert here.speech == Phrase(
        "comandos.arbol",
        {"carpeta": rig.home.name, "carpetas": "2 carpetas", "archivos": "1 archivo"},
    )
    there = await module.execute("arbol", {"ruta": rig.home / "docs"}, rig.ctx)
    built = rig.last(events.DirectoryTreeBuilt)
    assert (built.root, built.dirs, built.files, built.truncated) == (
        str(rig.home / "docs"), 1, 1, False,
    )  # fmt: skip
    assert there.speech.params == {
        "carpeta": "docs", "carpetas": "1 carpeta", "archivos": "1 archivo"
    }
    assert rig.workdir.path == rig.home


async def test_arbol_recortado_lo_dice(rig, module, monkeypatch):
    monkeypatch.setattr(command_runner, "TREE_MAX_ENTRIES", 2)
    monkeypatch.setattr(command_runner.build_tree, "__defaults__", (3, 2))
    for index in range(4):
        (rig.home / f"f{index}.txt").write_text("x")
    result = await module.execute("arbol", {}, rig.ctx)
    assert result.speech.id == "comandos.arbol_recortado"
    assert rig.last(events.DirectoryTreeBuilt).truncated


async def test_arbol_de_una_ruta_invalida(rig, module):
    result = await module.execute("arbol", {"ruta": rig.home / "nada"}, rig.ctx)
    assert (result.status, result.speech.id) == ("error", "ruta.no_existe")
    assert rig.events == []


# --- Binarios externos -----------------------------------------------------------------------


async def test_ejecutar_con_una_orden_queda_en_segundo_plano(rig, module, launches):
    result = await module.execute("ejecutar", {"comando": GIT_STATUS}, rig.ctx)
    assert result.background and result.status == "completado"
    assert result.speech == Phrase("comandos.ejecutando", {"comando": "git status"})
    assert launches.calls == [("git", ("status",), rig.home)]
    process = launches.processes[0]
    process.stdout.feed(b"On branch main\n", b"nothing to commit\r\n")
    process.stderr.feed(b"aviso \xff\n")
    await settle()
    process.finish(0)
    final = await rig.job()
    assert (final.status, final.speech) == (
        "completado", Phrase("comandos.ok", {"comando": "git status"}),
    )  # fmt: skip
    output = rig.of(events.CommandOutputAppended)
    assert output[0] == events.CommandOutputAppended(7, "git status", (), "out")
    assert [(e.stream, e.lines) for e in output[1:]] == [
        ("out", ("On branch main", "nothing to commit")),
        ("err", ("aviso �",)),  # bytes inválidos: no falla
    ]


async def test_la_salida_se_publica_por_lotes_cada_200_ms(rig, module, launches):
    await module.execute("ejecutar", {"comando": GIT_STATUS}, rig.ctx)
    process = launches.processes[0]
    process.stdout.feed(b"uno\n", b"dos\n")
    await settle()
    assert len(rig.of(events.CommandOutputAppended)) == 1  # solo la cabecera
    rig.clock.advance(0.2)
    await settle()
    assert rig.last(events.CommandOutputAppended).lines == ("uno", "dos")
    process.finish(0)
    await rig.job()


async def test_ejecutar_codigo_distinto_de_cero(rig, module, launches):
    await module.execute("ejecutar", {"comando": GIT_STATUS}, rig.ctx)
    launches.processes[0].finish(1)
    final = await rig.job()
    assert (final.status, final.speech) == (
        "error", Phrase("comandos.fallo", {"comando": "git status"}),
    )  # fmt: skip


async def test_ejecutar_un_programa_que_no_existe(rig, module, launches):
    launches.error = FileNotFoundError("git")
    result = await module.execute("ejecutar", {"comando": GIT_STATUS}, rig.ctx)
    assert (result.status, result.background) == ("error", False)
    assert result.speech == Phrase("comandos.no_encontrado", {"nombre": "git"})
    assert rig.jobs == []


async def test_ejecutar_tiempo_agotado_termina_el_arbol_de_procesos(rig, module, launches):
    await module.execute("ejecutar", {"comando": GIT_STATUS}, rig.ctx)
    await settle()
    rig.clock.advance(119)
    await settle()
    assert launches.killed == []
    rig.clock.advance(1)
    final = await rig.job()
    assert launches.killed == [4321]
    assert (final.status, final.speech) == ("error", Phrase("comandos.tiempo"))


async def test_ejecutar_usa_el_tiempo_maximo_del_binario(rig, module, launches):
    command = CommandLine("gcc", "gcc", ("main.c",), timeout_seconds=10)
    await module.execute("ejecutar", {"comando": command}, rig.ctx)
    await settle()
    rig.clock.advance(10)
    assert (await rig.job()).speech == Phrase("comandos.tiempo")


async def test_un_segundo_binario_simultaneo_se_rechaza(rig, module, launches):
    await module.execute("ejecutar", {"comando": GIT_STATUS}, rig.ctx)
    second = await module.execute("ejecutar", {"comando": GIT_STATUS}, rig.ctx)
    assert (second.status, second.speech) == ("error", Phrase("comandos.ocupado"))
    assert len(launches.calls) == 1
    launches.processes[0].finish(0)
    await rig.job()
    third = await module.execute("ejecutar", {"comando": GIT_STATUS}, rig.ctx)
    assert third.background  # al terminar el primero, se puede lanzar otro
    launches.processes[1].finish(0)
    await rig.job()


async def test_cancelar_termina_el_arbol_de_procesos(rig, module, launches):
    await module.execute("ejecutar", {"comando": GIT_STATUS}, rig.ctx)
    await settle()
    rig.jobs[0].cancel()
    with pytest.raises(asyncio.CancelledError):
        await rig.jobs[0]
    assert launches.killed == [4321]
    again = await module.execute("ejecutar", {"comando": GIT_STATUS}, rig.ctx)
    assert again.background  # el módulo queda libre
    launches.processes[1].finish(0)
    await rig.job()


async def test_en_un_protocolo_el_binario_se_espera_en_linea(tmp_path, module, launches):
    rig = ContextRig(tmp_path, origin="protocolo")
    rig.home.mkdir(parents=True, exist_ok=True)
    running = asyncio.ensure_future(module.execute("ejecutar", {"comando": GIT_STATUS}, rig.ctx))
    await settle()
    assert not running.done() and rig.jobs == []
    launches.processes[0].finish(0)
    result = await running
    assert (result.status, result.background) == ("completado", False)
    assert result.speech == Phrase("comandos.ok", {"comando": "git status"})
    rig.close()


async def test_ejecutar_real_python_version(rig):
    """Integración: un binario real, sin intérprete de órdenes."""
    module = CommandRunner()
    command = CommandLine("python", sys.executable, ("--version",))
    result = await module.execute("ejecutar", {"comando": command}, rig.ctx)
    assert result.background
    final = await asyncio.wait_for(rig.job(), 20)
    assert final.status == "completado"
    lines = [line for event in rig.of(events.CommandOutputAppended) for line in event.lines]
    assert any(line.startswith("Python 3") for line in lines)


async def test_el_lanzador_real_no_encuentra_un_programa_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        await processes.launch_process("no-existe-este-programa-jarvis", (), tmp_path)


async def test_el_lanzador_real_no_abre_ventana_de_consola_en_windows(tmp_path, monkeypatch):
    """En Windows, un binario de consola lanzado desde la interfaz no muestra su ventana."""
    seen: dict[str, object] = {}

    async def fake_exec(*args, **kwargs):
        seen.update(kwargs)
        return object()

    monkeypatch.setattr(processes.sys, "platform", "win32")
    monkeypatch.setattr(processes.asyncio, "create_subprocess_exec", fake_exec)
    await processes.launch_process(sys.executable, ("--version",), tmp_path)
    assert seen["creationflags"] == processes.CREATE_NO_WINDOW


# --- Consola ---------------------------------------------------------------------------------


async def test_abrir_consola_en_el_directorio_de_trabajo(rig, module):
    result = await module.execute("abrir_consola", {}, rig.ctx)
    assert (result.status, result.speech) == ("completado", Phrase("comandos.consola"))
    assert rig.platform.calls == [("open_terminal", (rig.home,))]


async def test_abrir_consola_fallo(rig, module):
    rig.platform.launch_error = OSError("sin terminal")
    result = await module.execute("abrir_consola", {}, rig.ctx)
    assert result.status == "error"


def test_solo_abrir_consola_no_activa_el_panel_de_comandos(module):
    panels = {spec.action: spec.panel for spec in module.intents()}
    assert panels.pop("abrir_consola") is None
    assert set(panels.values()) == {"comandos"}
    assert all(spec.in_protocols for spec in module.intents())
