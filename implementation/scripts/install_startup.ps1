<#
.SYNOPSIS
Registra el arranque automatico de Jarvis creando Jarvis.lnk en la carpeta Inicio.
.DESCRIPTION
Idempotente: si el acceso directo existe se sobrescribe. Falla sin crear nada
si falta pythonw.exe en el venv.
.PARAMETER StartupDir
Carpeta donde crear Jarvis.lnk. Por defecto la carpeta Inicio del usuario.
.PARAMETER VenvDir
Directorio del venv. Por defecto implementation\.venv relativo a este script.
#>
[CmdletBinding()]
param(
    [string]$StartupDir,
    [string]$VenvDir
)

$ErrorActionPreference = 'Stop'

if (-not $VenvDir) {
    $VenvDir = Join-Path $PSScriptRoot '..\.venv'
}

$windowStyleMinimized = 7
$shell = New-Object -ComObject WScript.Shell

if (-not $StartupDir) {
    $StartupDir = $shell.SpecialFolders('Startup')
}

$implementationDir = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$pythonw = Join-Path ([System.IO.Path]::GetFullPath($VenvDir)) 'Scripts\pythonw.exe'

if (-not (Test-Path -LiteralPath $pythonw)) {
    Write-Error "No existe pythonw.exe: $pythonw"
}

$shortcutPath = Join-Path ([System.IO.Path]::GetFullPath($StartupDir)) 'Jarvis.lnk'

$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = '-I -m jarvis_assistant'
$shortcut.WorkingDirectory = $implementationDir
$shortcut.WindowStyle = $windowStyleMinimized
$shortcut.Save()

Write-Output "Acceso directo creado: $shortcutPath"
