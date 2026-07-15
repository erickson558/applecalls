# AppleCalls

AppleCalls es una utilidad de escritorio en Python para Windows que responde una
pregunta concreta: `esta PC puede usar las llamadas de mi iPhone por la ruta
soportada, o no?`

Version actual: `V0.2.2`

## Resumen

AppleCalls no intenta clonar la funcion privada de `Continuity` de macOS.
Apple mantiene ese relay de llamadas dentro de su propio ecosistema. En Windows,
la ruta practica y soportada es `Microsoft Phone Link` + `Bluetooth`.

El programa existe para:

- inspeccionar el estado real de Windows, Bluetooth, red local y Phone Link
- decir con claridad si la ruta soportada esta lista, incompleta o bloqueada
- abrir Phone Link y, cuando existe, su vista de `Llamadas`
- ayudar a corregir instalaciones o asociaciones rotas sin congelar la GUI

## Que hace el programa

- Detecta version de Windows, build y version de Python.
- Revisa si `Microsoft Phone Link` esta instalado.
- Lee el estado local de Phone Link para saber si el iPhone aparece conectado.
- Detecta si la vista de `Llamadas` ya esta expuesta por Phone Link.
- Enumera adaptadores Bluetooth.
- Verifica si Windows expone perfiles de llamada como `Hands-Free HF`.
- Detecta perfil de red, conectividad Wi-Fi, SSID e IPs IPv4 locales.
- Genera un reporte tecnico copiable.
- Ejecuta el diagnostico en segundo plano para no congelar la interfaz.
- Abre Phone Link por el ejecutable real, URI o shell target, segun disponibilidad.
- Intenta instalar o actualizar Phone Link en modo silencioso con `winget`.
- Incluye interfaz `es` y `en`.

## Que no hace

- No implementa el relay privado de llamadas de Apple para Windows.
- No reemplaza Phone Link con una pila propia de telefonia.
- No convierte por si solo una red Wi-Fi compartida en equivalente de una Mac.

## Requisitos

- Windows 10 May 2019 Update o superior
- Python 3.12 o compatible
- iPhone con iOS 15 o superior para la ruta de Phone Link
- Bluetooth funcional en la PC

## Dependencias

En tiempo de ejecucion, la app usa solo la libreria estandar de Python.

Para build y automatizacion se usan dependencias declaradas en `requirements.txt`.
El detalle completo esta en [docs/dependencies.md](docs/dependencies.md).

Instalacion de dependencias de build:

```powershell
python -m pip install -r requirements.txt
```

## Uso local

Ejecutar la app:

```powershell
python main.py
```

Ejecutar pruebas:

```powershell
python -m unittest discover -s tests
```

Validar compilacion de modulos:

```powershell
python -m compileall .
```

## Compilacion a EXE

Compilar el ejecutable en la raiz del proyecto:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

Resultado esperado:

- `AppleCalls-V0.2.2.exe` en la carpeta raiz del proyecto

## Estructura del proyecto

```text
main.py
requirements.txt
applecalls/
  __init__.py
  app.py
  diagnostics.py
  i18n.py
  logic.py
docs/
  agents.md
  dependencies.md
  spec-driven-development.md
scripts/
  build_exe.ps1
tests/
  test_diagnostics.py
  test_logic.py
  test_report_format.py
.github/
  dependabot.yml
  pull_request_template.md
  workflows/ci.yml
```

## Buenas practicas de GitHub incluidas

Este repo queda preparado con:

- workflow de CI para pruebas y `compileall`
- `dependabot` para dependencias de `pip` y GitHub Actions
- templates de issues para bugs y mejoras
- template de pull request
- guia de contribucion
- licencia Apache License 2.0

## Contribucion

La guia para contribuir esta en [CONTRIBUTING.md](CONTRIBUTING.md).

## Licencia

Este proyecto se distribuye bajo [Apache License 2.0](LICENSE).

## Fuentes tecnicas usadas para el criterio funcional

- Microsoft: https://support.microsoft.com/en-us/windows/apps/make-and-receive-phone-calls-from-your-pc
- Microsoft: https://support.microsoft.com/en-us/windows/apps/phonelink/setting-up-calls-in-the-phone-link
- Apple: https://support.apple.com/en-us/102405
