"""`catalog.toml`: aplicaciones y páginas que se abren por su nombre."""
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from jarvis_assistant.config.reader import InvalidError, Reader

URL_SCHEMES = ("http://", "https://")


@dataclass(frozen=True)
class AppEntry:
    name: str
    path: str  # ejecutable, acceso directo o nombre en el PATH
    aliases: tuple[str, ...] = ()
    args: tuple[str, ...] = ()


@dataclass(frozen=True)
class PageEntry:
    name: str
    url: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Catalog:
    discover_installed_apps: bool = True
    apps: tuple[AppEntry, ...] = ()
    pages: tuple[PageEntry, ...] = ()


def parse_catalog(reader: Reader) -> Catalog:
    discover = reader.boolean("discover_installed_apps", True)
    apps = []
    for item in reader.tables("apps") or []:
        apps.append(
            AppEntry(
                name=item.text("name", non_empty=True),
                path=item.text("path", non_empty=True),
                aliases=item.texts("aliases"),
                args=item.texts("args"),
            )
        )
        item.close()
    pages = []
    for item in reader.tables("pages") or []:
        name = item.text("name", non_empty=True)
        url = item.text("url")
        if not url.startswith(URL_SCHEMES):
            raise InvalidError(item.key("url"), "debe empezar por http:// o https://")
        pages.append(PageEntry(name=name, url=url, aliases=item.texts("aliases")))
        item.close()
    return Catalog(discover_installed_apps=discover, apps=tuple(apps), pages=tuple(pages))


def dump_catalog(document: Any, apps: Sequence[AppEntry], pages: Sequence[PageEntry]) -> None:
    """Sustituye las listas `[[apps]]` y `[[pages]]` de un documento `tomlkit`. Los
    comentarios y el resto de claves se conservan."""
    import tomlkit

    for key in ("apps", "pages"):
        if key in document:
            del document[key]
    if apps:
        array = tomlkit.aot()
        for app in apps:
            table = tomlkit.table()
            table["name"] = app.name
            if app.aliases:
                table["aliases"] = list(app.aliases)
            table["path"] = app.path
            if app.args:
                table["args"] = list(app.args)
            array.append(table)
        document["apps"] = array
    if pages:
        array = tomlkit.aot()
        for page in pages:
            table = tomlkit.table()
            table["name"] = page.name
            if page.aliases:
                table["aliases"] = list(page.aliases)
            table["url"] = page.url
            array.append(table)
        document["pages"] = array
