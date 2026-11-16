"""Comunes a las pruebas de integración."""
import pytest


@pytest.fixture(autouse=True)
def _frases_sin_rotacion(monkeypatch):
    """Cada frase se dice siempre en su primera variante: las pruebas comparan lo dicho con
    `render`, que da la variante vigente. La rotación se prueba en las pruebas del Sintetizador."""
    from jarvis_assistant.speaker import speaker

    monkeypatch.setattr(speaker, "advance", lambda _phrase_id: None)
