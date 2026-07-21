# AppleCalls

AppleCalls es una utilidad de escritorio en Python para Windows que responde una
pregunta concreta: `esta PC puede usar las llamadas de mi iPhone, y puede hacerlo
sin depender de Microsoft Phone Link?`

Version actual: `V0.3.0`

## Resumen

AppleCalls no intenta clonar la funcion privada de `Continuity` de macOS: se
investigo a fondo (ver [docs/spec-driven-development.md](docs/spec-driven-development.md))
y se confirmo que no es viable para un tercero, porque la senalizacion de
Continuity Calls depende de la infraestructura de push privada de Apple
(APNs/IDS), autenticada con Apple ID. Tampoco depende de `Microsoft Phone
Link`: se probo en hardware real que Windows reserva para su propio uso tanto
el canal Bluetooth Hands-Free como el canal BLE ANCS, sin exponerlos a
aplicaciones de terceros.

El camino real e independiente que SI es viable es un softphone SIP/VoIP
(RFC 3261 + RTP/G.711) estandar: el usuario desvia su numero real de iPhone a
un numero VoIP/SIP (por su operador o un proveedor VoIP de su eleccion), y
AppleCalls se registra directamente contra esa cuenta SIP para recibir y
hacer llamadas desde la PC, sin Bluetooth, sin Phone Link y sin infraestructura
de Apple involucrada.

El programa existe para:

- ofrecer un softphone SIP real e independiente para recibir y hacer llamadas
  desde la PC (cuenta SIP propia, sin Phone Link)
- inspeccionar el estado real de Windows, Bluetooth, red local y Phone Link
  (diagnostico heredado, sigue disponible para quien todavia use esa ruta)
- decir con claridad si la ruta soportada por Phone Link esta lista, incompleta
  o bloqueada
- abrir Phone Link y, cuando existe, su vista de `Llamadas`
- ayudar a corregir instalaciones o asociaciones rotas sin congelar la GUI

## Que hace el programa

### Softphone SIP/VoIP (independiente de Phone Link)

- Se registra contra cualquier cuenta SIP/VoIP estandar (servidor, puerto,
  usuario, contrasena, numero visible).
- Guarda la configuracion de cuenta en disco (sin la contrasena) y la
  contrasena por separado en el Administrador de credenciales de Windows via
  `keyring` -- nunca en texto plano.
- Muestra el estado de registro (`Registrando`, `Registrado`, `Fallo`, etc.).
- Avisa una llamada entrante con el numero del remitente, y permite
  contestar o rechazar.
- Permite marcar y colgar llamadas salientes.
- Puentea audio real (microfono/altavoces) usando G.711 (PCMU/PCMA) a 8kHz.
- Abre reglas de Firewall de Windows en modo silencioso para el puerto SIP y
  el rango RTP usado.
- Limitacion conocida: la libreria SIP usada solo puede *recibir* tonos DTMF,
  no enviarlos durante una llamada (sin teclado numerico en vivo).

### Diagnostico de Phone Link (funcion heredada, sigue disponible)

- Detecta version de Windows, build y version de Python.
- Revisa si `Microsoft Phone Link` esta instalado.
- Lee el estado local de Phone Link para saber si el iPhone aparece conectado.
- Detecta si la vista de `Llamadas` ya esta expuesta por Phone Link.
- Enumera adaptadores Bluetooth.
- Verifica si Windows expone perfiles de llamada como `Hands-Free HF`.
- Detecta audifonos o endpoints Bluetooth externos que pueden bloquear el popup
  para contestar llamadas desde Phone Link.
- Detecta perfil de red, conectividad Wi-Fi, SSID e IPs IPv4 locales.
- Genera un reporte tecnico copiable.
- Ejecuta el diagnostico en segundo plano para no congelar la interfaz.
- Ejecuta `PowerShell`, `netsh` y `winget` en segundo plano sin abrir ventanas de `CMD` o `PowerShell`.
- Abre Phone Link por el ejecutable real, URI o shell target, segun disponibilidad.
- Intenta instalar o actualizar Phone Link en modo silencioso con `winget`.
- Incluye interfaz `es` y `en`.

## Que no hace

- No implementa el relay privado de `Continuity Calls` de Apple (requiere
  credenciales de Apple ID que un tercero no puede emitir; investigado y
  descartado, ver SDD).
- No usa ni requiere Microsoft Phone Link para el softphone SIP -- Phone Link
  queda como funcion de diagnostico heredada e independiente.
- No envia tonos DTMF durante una llamada activa (limitacion de la libreria
  SIP usada).

## Requisitos

- Windows 10 May 2019 Update o superior
- Python 3.12 o compatible
- Para el softphone SIP: una cuenta SIP/VoIP propia y, para recibir las
  llamadas del iPhone en ella, desvio de llamadas configurado con tu operador
- Para el diagnostico heredado de Phone Link: iPhone con iOS 15 o superior y
  Bluetooth funcional en la PC

## Dependencias

El softphone SIP necesita tres dependencias de tiempo de ejecucion (protocolo
SIP/RTP, audio y almacenamiento seguro de credenciales); el resto de la app
sigue usando solo la libreria estandar de Python. El detalle completo,
incluyendo el porque de cada una, esta en
[docs/dependencies.md](docs/dependencies.md).

Instalacion de dependencias (runtime + build):

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

- `AppleCalls-V0.3.0.exe` en la carpeta raiz del proyecto

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
  process_utils.py
  voip.py
docs/
  agents.md
  dependencies.md
  spec-driven-development.md
scripts/
  build_exe.ps1
tests/
  test_diagnostics.py
  test_logic.py
  test_process_utils.py
  test_report_format.py
  test_voip.py
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
