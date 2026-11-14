<#
.SYNOPSIS
Lanza el asistente Jarvis desde el venv del proyecto.
.PARAMETER Console
Usa python.exe y mantiene la salida en la consola (para ver errores).
.PARAMETER VenvDir
Directorio del venv. Por defecto implementation\.venv relativo a este script.
#>
[CmdletBinding()]
param(
    [switch]$Console,
    [string]$VenvDir
)

$ErrorActionPreference = 'Stop'

if (-not $VenvDir) {
    $VenvDir = Join-Path $PSScriptRoot '..\.venv'
}

$implementationDir = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$exeName = if ($Console) { 'python.exe' } else { 'pythonw.exe' }
$exe = Join-Path ([System.IO.Path]::GetFullPath($VenvDir)) "Scripts\$exeName"

if (-not (Test-Path -LiteralPath $exe)) {
    Write-Error "No existe el ejecutable: $exe"
}

$argumentos = @('-I', '-m', 'jarvis_assistant')
$logPath = Join-Path $env:LOCALAPPDATA 'Jarvis\logs\jarvis.log'

if ($Console) {
    Write-Output "Log: $logPath"
    Push-Location -LiteralPath $implementationDir
    try {
        & $exe @argumentos
    }
    finally {
        Pop-Location
    }
}
else {
    Start-Process -FilePath $exe -ArgumentList $argumentos -WorkingDirectory $implementationDir -WindowStyle Hidden
    Write-Output "Asistente lanzado sin consola. Log: $logPath"
}
