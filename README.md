# Jarvis: asistente personal local

Asistente para Windows que funciona al 100 % en su equipo. Usted **escribe** una orden y Jarvis la ejecuta y le **responde con voz** y en pantalla. Sin internet, sin IA generativa y sin servicios de pago.

## Empiece aquí

| Quiero… | Lea |
|---|---|
| Instalarlo | [INSTALAR.md](INSTALAR.md). También puede pedírselo a un agente de IA (Claude Code, Codex, Copilot…): «Instala Jarvis en este equipo siguiendo INSTALAR.md». |
| Aprender a usarlo | [MANUAL.md](MANUAL.md) |
| Añadir mis aplicaciones, páginas, carpetas, protocolos, perfiles o plantillas | [PERSONALIZAR.md](PERSONALIZAR.md) |
| Ver qué ha cambiado en cada versión, o actualizar desde la 1.0 | [CHANGELOG.md](CHANGELOG.md) |

## Ideas clave

- **Órdenes fijas, no conversación.** Jarvis reconoce un catálogo cerrado de frases («abre {aplicación}», «busca {archivo}», «recuérdame {algo}»), con tolerancia a erratas. Una frase fuera del catálogo se ignora. La misma orden da siempre el mismo resultado. Escriba «ayuda» para ver todas.
- **Tres frases controlan todo.** «Hey Jarvis» lo despierta, «Gracias Jarvis» lo deja en reposo y «Buenas noches Jarvis» cierra la sesión. «Cancelar» detiene lo que esté haciendo.
- **Perfiles.** Cada perfil tiene su nombre, su disposición de pantalla y sus recordatorios, y puede protegerse con contraseña. Se elige en la pantalla dormida, antes de «Hey Jarvis».
- **Todo se queda en su equipo.** No envía datos. El micrófono solo se usa para el medidor de ruido, si usted lo muestra, y nunca graba. Solo la instalación usa la red, una vez, para descargar la voz.
- **Su configuración es suya.** Sus aplicaciones, páginas, protocolos y perfiles se guardan en `%APPDATA%\Jarvis\config\`, fuera de este repositorio. Se editan a mano, desde la ventana de configuración o con el módulo Catálogo.

## Qué sabe hacer

| Módulo | Para qué sirve |
|---|---|
| Apertura | Abrir aplicaciones, páginas web (en Microsoft Edge) y carpetas. |
| Búsqueda | Encontrar archivos y carpetas en el disco. |
| Creación | Crear archivos y carpetas sin sobrescribir nunca nada. |
| Comandos | Moverse por carpetas y ejecutar programas permitidos (`git`, `gcc`, `python`…). |
| Recordatorio | Avisos con fecha, fecha límite y posposición. |
| Protocolos | Ejecutar varias tareas con una sola orden («protocolo modo trabajo»). |
| Sesión e Historial | Nombrar la sesión, marcarla como importante, consultar sesiones anteriores y eliminarlas. |
| Catálogo | Ver, añadir y eliminar aplicaciones, páginas y comandos sin editar archivos. |
| Medidores | Consumo de CPU y RAM del asistente, y ruido de fondo con el nivel de concentración que permite. |
| Permisos, Credenciales y Perfiles | Solo para el Acedor, el perfil administrador opcional: decidir qué usa cada perfil, ver sus contraseñas y eliminar perfiles. |

## Limitaciones

- Solo Windows 10 y 11.
- Las órdenes se escriben; no hay entrada por voz.
- No entiende frases libres, solo las del catálogo.
- Las páginas web se abren solo en Microsoft Edge y solo si están en su catálogo.
- La voz (`piper-tts`) tiene licencia GPL-3.0: revísela antes de un uso comercial.

## Para desarrolladores

- [implementation/README.md](implementation/README.md): código, pruebas, diagnóstico y medidas.
- [software/README.md](software/README.md): especificación completa (requisitos, reglas, módulos, interfaz). Es la fuente de verdad; el código cita sus identificadores (RN-xx, RF-xx).
- [software/arquitectura.md](software/arquitectura.md): diseño técnico. Python 3.11, `asyncio`, PySide6 (QML), SQLite, `rapidfuzz`, `APScheduler`, `piper-tts`, `tomlkit` y `cryptography`.
- [software/plan-implementacion.md](software/plan-implementacion.md): fases. La versión 1 abarca las fases 0 a 7.
- Comprobaciones manuales en el equipo: [implementation/tests/manual/fase-7.md](implementation/tests/manual/fase-7.md) (versión 1) y [implementation/tests/manual/version-2.md](implementation/tests/manual/version-2.md) (versión 2).
- [CHANGELOG.md](CHANGELOG.md): cambios de cada versión.
