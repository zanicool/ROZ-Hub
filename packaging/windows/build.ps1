# Builds ROZ-Hub.exe and adds a Start Menu shortcut. Run from anywhere in PowerShell.
# Pinning to the taskbar is manual on Windows 10/11 (right-click the Start entry > Pin to taskbar).
$ErrorActionPreference = 'Stop'
$root = Resolve-Path "$PSScriptRoot\..\.."
Set-Location $root

python -m venv .build-venv
.\.build-venv\Scripts\pip install -q -r packaging\requirements-build.txt

# PyInstaller and Windows shortcuts both need a multi-size .ico, not PNG
New-Item -ItemType Directory -Force .build | Out-Null
.\.build-venv\Scripts\python -c "from PIL import Image; Image.open('logo/roz-256.png').save('.build/roz.ico', sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])"

# --add-data uses ';' as the separator on Windows
.\.build-venv\Scripts\pyinstaller --noconfirm --windowed --onefile --name ROZ-Hub `
    --icon .build\roz.ico `
    --add-data "logo;logo" --add-data "keyboard.json;." `
    --distpath dist --workpath .build\work --specpath .build `
    roz_he_configurator.py

$lnk = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\ROZ Hub.lnk'
$shell = New-Object -ComObject WScript.Shell
$s = $shell.CreateShortcut($lnk)
$s.TargetPath = Join-Path $root 'dist\ROZ-Hub.exe'
$s.WorkingDirectory = Join-Path $root 'dist'
$s.IconLocation = Join-Path $root '.build\roz.ico'
$s.Description = 'ROZ HE keyboard configurator'
$s.Save()

Write-Host "Installed. Open 'ROZ Hub' from the Start menu and pin it to the taskbar."
