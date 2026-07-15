Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Resolve the project root from the script location so the command works
# regardless of the shell's current directory.
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

# Read the application version directly from source to keep the executable
# name synchronized with the code and git tag.
$version = @'
from applecalls import __version__
print(__version__)
'@ | python -

$exeName = "AppleCalls-$version"
$iconPath = (Resolve-Path ".\iphone_apple_mac_171.ico").Path

# Remove stale build outputs so each build starts cleanly.
Remove-Item -Recurse -Force ".\build\pyinstaller" -ErrorAction SilentlyContinue
Remove-Item -Force ".\$exeName.exe" -ErrorAction SilentlyContinue

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --icon $iconPath `
  --name $exeName `
  --distpath "." `
  --workpath ".\build\pyinstaller" `
  --specpath ".\build" `
  ".\main.py"

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller failed with exit code $LASTEXITCODE."
}
