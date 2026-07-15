# Contributing

Gracias por contribuir a AppleCalls.

## Alcance del proyecto

AppleCalls diagnostica la ruta soportada para llamadas de iPhone en Windows
mediante `Microsoft Phone Link` y `Bluetooth`. El proyecto no busca reimplementar
la funcion privada de `Continuity` de Apple fuera de su ecosistema.

## Flujo recomendado

1. Abre un issue si el cambio corrige un bug real, cambia comportamiento o agrega una mejora relevante.
2. Trabaja en una rama corta y con un objetivo concreto.
3. Mantiene compatibilidad con el comportamiento soportado actual.
4. Incluye validacion local antes de abrir el PR.

## Preparacion local

Instalar dependencias de build y automatizacion:

```powershell
python -m pip install -r requirements.txt
```

Ejecutar la app:

```powershell
python main.py
```

## Validaciones minimas

Ejecuta esto antes de proponer cambios:

```powershell
python -m unittest discover -s tests
python -m compileall .
```

Si el cambio afecta el empaquetado:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

## Criterios de cambio

- No hagas fixes a ciegas.
- Explica la causa raiz cuando corrijas un bug.
- No rompas funcionalidades existentes.
- Mantiene la GUI responsiva.
- Si actualizas comportamiento, actualiza tambien pruebas o documentacion.

## Convenciones utiles

- Versiones visibles: `Vx.x.x`
- Commits sugeridos: `fix: ...`, `feat: ...`, `docs: ...`, `chore: ...`
- Cuando agregues comentarios de codigo, prefiere docstrings y comentarios cortos sobre bloques importantes.

## Pull requests

Incluye en el PR:

- que cambia
- por que cambia
- como se valido
- riesgos o limitaciones residuales
