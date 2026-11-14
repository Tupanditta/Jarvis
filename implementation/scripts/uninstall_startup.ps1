<#
.SYNOPSIS
Elimina el arranque automatico de Jarvis (Jarvis.lnk de la carpeta Inicio).
.DESCRIPTION
Termina con codigo 0 aunque el acceso directo no exista.
.PARAMETER StartupDir
Carpeta donde esta Jarvis.lnk. Por defecto la carpeta Inicio del usuario.
#>
[CmdletBinding()]
param(
    [string]$StartupDir
)

$ErrorActionPreference = 'Stop'

if (-not $StartupDir) {
    $StartupDir = (New-Object -ComObject WScript.Shell).SpecialFolders('Startup')
}

$shortcutPath = Join-Path ([System.IO.Path]::GetFullPath($StartupDir)) 'Jarvis.lnk'

if (Test-Path -LiteralPath $shortcutPath) {
    Remove-Item -LiteralPath $shortcutPath
    Write-Output "Acceso directo eliminado: $shortcutPath"
}
else {
    Write-Output "No hay acceso directo que eliminar: $shortcutPath"
}
