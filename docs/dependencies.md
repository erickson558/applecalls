# Dependencies

## Resumen

AppleCalls usa principalmente la libreria estandar de Python. Las dependencias
externas actuales se reservan para build y automatizacion del repositorio.

## Dependencias de runtime

No hay dependencias externas obligatorias para ejecutar la aplicacion desde
codigo fuente. La app usa modulos de la libreria estandar como:

- `tkinter`
- `threading`
- `subprocess`
- `queue`
- `json`
- `pathlib`

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
- `netsh`
- adaptador `Bluetooth` funcional

## Politica de cambios

- Mantener runtime sin dependencias externas salvo que haya una necesidad clara.
- Declarar en `requirements.txt` solo dependencias necesarias para build o tooling.
- Documentar cualquier nueva dependencia en este archivo y en `README.md`.
