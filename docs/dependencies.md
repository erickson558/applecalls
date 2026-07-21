# Dependencies

## Resumen

AppleCalls usa principalmente la libreria estandar de Python. Las dependencias
externas historicas se reservaban para build y automatizacion del
repositorio. A partir de la funcion de telefono SIP/VoIP (V0.3.0), la app
tambien depende de tres paquetes de runtime, agregados porque el diagnostico
de Phone Link dejo de ser la unica via de llamadas soportada: `applecalls`
ahora puede actuar como un softphone SIP (RFC 3261) real e independiente de
Microsoft Phone Link y de Apple Continuity.

## Dependencias de runtime

La app usa modulos de la libreria estandar como:

- `tkinter`
- `threading`
- `subprocess`
- `queue`
- `json`
- `pathlib`

Ademas, `requirements.txt` declara tres dependencias de runtime nuevas,
exclusivamente para el telefono SIP/VoIP (`applecalls/voip.py`):

| Dependencia | Uso |
| --- | --- |
| `pyVoIP` | Implementa la pila de protocolos SIP (registro, invite, respuestas) y RTP/G.711 necesaria para registrar una cuenta SIP real y para hacer/recibir llamadas VoIP, sin ninguna dependencia de Phone Link o de APIs privadas de Apple. |
| `sounddevice` | Provee acceso a los dispositivos de audio (microfono/altavoces) de Windows via PortAudio, para capturar y reproducir el audio de la llamada en tiempo real. |
| `keyring` | Guarda la contrasena de la cuenta SIP en el almacen de credenciales del sistema operativo (Windows Credential Manager) en lugar de en un archivo de texto plano. |

Nota tecnica: el audio que intercambia `pyVoIP` es PCM lineal de 8 bits (no
16 bits), asi que `applecalls/voip.py` usa `audioop.lin2lin` (libreria
estandar) para convertir entre el PCM de 16 bits que produce/consume
`sounddevice` y el PCM de 8 bits que espera `pyVoIP`. `audioop` esta
deprecado para su eliminacion a partir de Python 3.13+; es un riesgo
conocido para una futura migracion de version de Python, no resuelto en esta
entrega porque el proyecto todavia usa Python 3.12.

Limitacion conocida de `pyVoIP` 1.6.8: solo puede **recibir** tonos DTMF, no
enviarlos durante una llamada en curso. Por eso la UI no ofrece un teclado de
tonos en vivo; el teclado numerico solo sirve para componer el numero antes
de llamar.

Nota de empaquetado (PyInstaller): se verifico compilando el `.exe` real que
`sounddevice` (via el hook `hook-sounddevice.py` de `pyinstaller-hooks-contrib`)
y el backend de `keyring` para Windows (`keyring.backends.Windows`, resuelto
junto con los hooks de `pywintypes`/`win32ctypes`) quedan incluidos sin
configuracion adicional en `scripts/build_exe.ps1`. No se requirio agregar
`--hidden-import` ni `--collect-data` manualmente.

## Dependencias de build y automatizacion

Estas dependencias viven en `requirements.txt`:

| Dependencia | Uso |
| --- | --- |
| `pyinstaller` | Generar el ejecutable `.exe` para Windows |
| `pyyaml` | Soporte para automatizacion y validacion de skills/configuracion YAML |

## Dependencias externas del entorno Windows

Aunque no forman parte de `pip`, el comportamiento de la app depende de
componentes del sistema:

- `Microsoft Phone Link`
- `winget` para instalar o actualizar Phone Link en silencio
- `PowerShell`
- `netsh` (diagnostico de Wi-Fi y, desde V0.3.0, tambien para abrir de forma
  idempotente y best-effort las reglas de entrada UDP del telefono SIP)
- adaptador `Bluetooth` funcional
- Una cuenta SIP/VoIP real de un proveedor a eleccion del usuario, con desvio
  de llamadas configurado desde el iPhone (requerida solo para usar el
  telefono SIP, no para el diagnostico de Phone Link)

## Politica de cambios

- Mantener runtime sin dependencias externas salvo que haya una necesidad clara.
- Declarar en `requirements.txt` solo dependencias necesarias para build o tooling.
- Documentar cualquier nueva dependencia en este archivo y en `README.md`.
- Excepcion aplicada en V0.3.0: `pyVoIP`, `sounddevice` y `keyring` se
  agregaron como dependencias de runtime porque implementan un protocolo
  (SIP/RTP), acceso a hardware (audio) y almacenamiento seguro de secretos
  (credential store) que la libreria estandar de Python no cubre; no hay
  alternativa razonable dentro de stdlib para esta funcion.
