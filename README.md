# AppleCalls

AppleCalls es una app de escritorio en Python para Windows que te dice si tu
equipo esta listo para usar las llamadas de tu iPhone por la ruta soportada:
`Microsoft Phone Link`.

Version actual: `V0.2.0`

Importante:

- No intenta clonar la funcion privada de `Continuity` de macOS.
- Apple mantiene esa integracion nativa dentro de su propio ecosistema.
- En Windows, la via practica y soportada hoy es `Phone Link` + `Bluetooth`.
- Estar en la misma red Wi-Fi no habilita en Windows el mismo relay de llamadas
  que Apple ofrece en Mac.

## Que hace

- Detecta la version de Windows y el build actual.
- Revisa si `Microsoft Phone Link` esta instalado.
- Enumera adaptadores Bluetooth y cuantos estan activos.
- Detecta el perfil de red, el SSID Wi-Fi y las IPs locales de la PC.
- Ejecuta el diagnostico sin congelar la interfaz.
- Muestra un veredicto claro:
  - `Ruta soportada disponible`
  - `Posible, pero falta configuracion`
  - `No esta listo`
- Abre accesos directos a:
  - `Phone Link`
  - configuracion de `Bluetooth`
  - guia oficial de Microsoft
  - guia oficial de Apple
- Incluye interfaz en espanol e ingles.
- Incluye boton `Comprame una cerveza`.

## Requisitos

- Windows 10 May 2019 Update o mas reciente
- Python 3.12 o compatible
- iPhone con iOS 15 o superior para la ruta de `Phone Link`
- Bluetooth funcional en la PC

## Ejecutar

```powershell
python main.py
```

## Compilar a EXE

Instala la dependencia de build:

```powershell
python -m pip install -r requirements.txt
```

Compila el ejecutable en la misma carpeta del proyecto:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

Resultado esperado:

- `AppleCalls-V0.2.0.exe` en la carpeta raiz del proyecto

## Estructura

```text
main.py
applecalls/
  __init__.py
  app.py
  diagnostics.py
  i18n.py
  logic.py
docs/
  agents.md
  spec-driven-development.md
scripts/
  build_exe.ps1
tests/
  test_logic.py
```

## Pruebas

```powershell
python -m unittest discover -s tests
```

## Fuentes oficiales usadas para el criterio tecnico

- Microsoft: https://support.microsoft.com/en-us/windows/apps/make-and-receive-phone-calls-from-your-pc
- Microsoft: https://support.microsoft.com/en-us/windows/apps/phonelink/setting-up-calls-in-the-phone-link
- Apple: https://support.apple.com/en-us/108046
