"""Ventana de configuración (configurador.md).

Edita la configuración con el ratón, sin el asistente: no se le dan órdenes ni responde.
Todo lo que se cambia queda en un borrador; solo al pulsar Guardar se escribe en los archivos
TOML, y el asistente lo aplica al abrir la siguiente sesión.

Cada apartado (plantillas, perfiles, sonido…) es una clase de `sections/` con su
página QML, registrada en `registry.SECTIONS`. Añadir un apartado es añadir su clase, su página
y su fila en el registro.

Depende de `config` y de componentes de `ui`; ni el núcleo ni la interfaz del asistente
dependen de este paquete.
"""
