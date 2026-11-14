# Matriz de trazabilidad

Relación entre los requisitos funcionales, el módulo que los implementa, los casos de uso que los cubren y la fase del [plan](../plan-implementacion.md) en la que se construyen. Un requisito sin caso de uso propio se verifica con los criterios de aceptación de su módulo.

Abreviaturas de módulos: **FSM** máquina de estados y orquestador · **AUD** captura de audio · **STT** transcriptor · **ENR** enrutador · **TTS** sintetizador · **UI** interfaz · **BD** persistencia · **CFG** configuración · **PRO** proceso · **PLA** plataforma · **SES** Sesión · **HIS** Historial · **COM** Comandos · **APE** Apertura · **BUS** Búsqueda · **CRE** Creación · **REC** Recordatorio · **PRT** Protocolos.

## Requisitos funcionales

| Requisito | Módulos | Casos de uso | Fase |
|---|---|---|---|
| RF-01 | FSM, SES | CU-03 | 1 |
| RF-02 | FSM, AUD, ENR, SES | CU-05 | 1 |
| RF-03, RF-04, RF-05 | SES | CU-10 | 4 |
| RF-06, RF-07 | SES | CU-10, CU-05 | 4 |
| RF-08, RF-09 | HIS | CU-10 | 3 |
| RF-10 | FSM, BD | todos | 3 |
| RF-11 a RF-14 | HIS, FSM | CU-10 | 4 |
| RF-15, RF-16 | COM, ENR | CU-06 | 3 |
| RF-17, RF-18, RF-98 | COM | — | 3 |
| RF-19, RF-20 | COM | CU-06 | 3 |
| RF-21 | COM, PLA | — | 3 |
| RF-59, RF-73, RF-74 | COM | CU-02 | 3 |
| RF-22, RF-23, RF-24, RF-25 | APE, PLA, UI | CU-07 | 3 |
| RF-58 | APE, PLA | CU-01 | 3 |
| RF-26, RF-27, RF-28, RF-90 | BUS, PLA | CU-08 | 3 |
| RF-29 a RF-34, RF-97 | CRE, FSM | CU-09 | 4 |
| RF-35 a RF-38 | REC, ENR | CU-11 | 5 |
| RF-39 a RF-51 | REC, FSM, TTS, UI | CU-12 | 5 |
| RF-52 a RF-57, RF-99 | PRT, SES | CU-13 | 6 |
| RF-60, RF-61 | AUD | CU-03 | 1 |
| RF-62 | STT | CU-04 | 1 |
| RF-63, RF-65 | ENR | CU-04 | 1 |
| RF-64, RF-69 | FSM, TTS | CU-01, CU-02, CU-06 a CU-08 | 3 |
| RF-66, RF-67, RF-68, RF-84 | FSM, ENR, UI | CU-09, CU-10, CU-11 | 4 |
| RF-70, RF-85 | TTS, AUD | CU-12 | 3 |
| RF-71, RF-87, RF-89 | UI | CU-07 | 2 |
| RF-72 | BD | CU-10, CU-11 | 3 |
| RF-75, RF-86, RF-95 | PRO, AUD | CU-03 | 1 |
| RF-76, RF-78 | FSM, ENR | CU-04 | 1 |
| RF-77 | FSM, PRO | CU-05 | 1 |
| RF-79 | TTS | CU-03, CU-04, CU-05 | 1 |
| RF-80, RF-81, RF-82, RF-83 | UI | CU-03, CU-04, CU-05 | 2 |
| RF-88 | UI, FSM | — | 2 |
| RF-92, RF-94 | FSM, ENR, TTS | — | 3 |
| RF-93 | SES, PRO | CU-05 | 4 |
| RF-96 | CFG | CU-03 | 3 |

## Requisitos no funcionales

| Requisito | Dónde se garantiza | Cómo se verifica |
|---|---|---|
| RNF-01, RNF-02 | Todo el código; `scripts/fetch_models.py` es la única excepción y no forma parte del asistente. | Bloqueo de sockets en las pruebas; lista manual con la red desactivada. |
| RNF-03, RNF-25 | STT, TTS, FSM, PRO | `scripts/measure.py` en el equipo de referencia. |
| RNF-04, RNF-05, RNF-06 | AUD, STT, UI | `scripts/measure.py`. |
| RNF-30 | AUD | `scripts/calibrate_wakeword.py` y lista manual de la fase 1. |
| RNF-31 | STT, ENR | Lista manual de órdenes habladas (T-7.2). |
| RNF-07 | AUD, TTS, FSM | Pruebas de integración y lista manual. |
| RNF-08, RNF-12 | BD | Pruebas automáticas. |
| RNF-09 | BUS, PLA | Prueba con marcador `hardware`. |
| RNF-10, RNF-11, RNF-15 | ENR | Juego de frases de prueba. |
| RNF-13, RNF-14, RNF-21, RNF-22, RNF-29 | UI, TTS | Listas manuales de las fases 2 y 7. |
| RNF-16, RNF-17 | PLA | Lista manual por sistema. |
| RNF-18, RNF-19, RNF-20, RNF-24, RNF-26 | Arquitectura | Pruebas automáticas de importaciones, de registro y de cobertura. |
| RNF-23 | FSM | Prueba con un módulo que falla. |
| RNF-27 | COM, APE, CRE | Pruebas automáticas e inspección del código. |
| RNF-28 | Dependencias | Revisión de licencias de [arquitectura.md](../arquitectura.md), sección 9. |
