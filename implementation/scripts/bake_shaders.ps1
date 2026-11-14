<#
.SYNOPSIS
Compila los shaders .frag del tema holo_core a .qsb con la herramienta qsb.
.DESCRIPTION
Recorre shaders\*.frag y genera <nombre>.frag.qsb junto al fuente. Idempotente:
los .qsb existentes se sobrescriben. No toca nada fuera de shaders\. Falla con
un mensaje claro si falta qsb. Si shaders\ no existe, avisa y termina sin error.
qsb se busca en: -QsbPath, PATH, el venv (PySide6 lo incluye; PyQt6 no) y las
instalaciones de Qt (QTDIR o C:\Qt).
.PARAMETER ShadersDir
Carpeta con los .frag. Por defecto la de holo_core relativa a este script.
.PARAMETER VenvDir
Directorio del venv. Por defecto implementation\.venv relativo a este script.
.PARAMETER QsbPath
Ruta explicita a qsb.exe. Si se omite se autodetecta.
#>
[CmdletBinding()]
param(
    [string]$ShadersDir,
    [string]$VenvDir,
    [string]$QsbPath
)

$ErrorActionPreference = 'Stop'

# $PSScriptRoot puede estar vacio en los valores por defecto de param segun como
# se invoque (p. ej. powershell -File); se resuelve aqui con MyInvocation de respaldo.
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $ShadersDir) {
    $ShadersDir = Join-Path $scriptDir '..\src\jarvis_assistant\ui\themes\holo_core\shaders'
}
if (-not $VenvDir) { $VenvDir = Join-Path $scriptDir '..\.venv' }

# Perfil apto para Qt Quick; incluye HLSL para D3D11 en Windows.
$qsbProfileArgs = @('--glsl', '100es,120,150', '--hlsl', '50', '--msl', '12')

function Find-Qsb {
    param([string]$ExplicitPath, [string]$Venv)

    if ($ExplicitPath) {
        if (Test-Path -LiteralPath $ExplicitPath) { return (Resolve-Path -LiteralPath $ExplicitPath).Path }
        return $null
    }

    $inPath = Get-Command qsb -ErrorAction SilentlyContinue
    if ($inPath) { return $inPath.Source }

    $venvRoot = [System.IO.Path]::GetFullPath($Venv)
    $candidates = @(
        (Join-Path $venvRoot 'Lib\site-packages\PySide6\qsb.exe'),
        (Join-Path $venvRoot 'Lib\site-packages\PySide6\Qt\bin\qsb.exe')
    )
    foreach ($qtRoot in @($env:QTDIR, 'C:\Qt')) {
        if ($qtRoot -and (Test-Path -LiteralPath $qtRoot)) {
            $candidates += Get-ChildItem -LiteralPath $qtRoot -Recurse -Filter qsb.exe -ErrorAction SilentlyContinue |
                Select-Object -ExpandProperty FullName
        }
    }
    return $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}

$shadersFull = [System.IO.Path]::GetFullPath($ShadersDir)
if (-not (Test-Path -LiteralPath $shadersFull -PathType Container)) {
    Write-Warning "No existe la carpeta de shaders, nada que compilar: $shadersFull"
    return
}

$sources = @(Get-ChildItem -LiteralPath $shadersFull -Filter '*.frag' -File)
if ($sources.Count -eq 0) {
    Write-Warning "No hay archivos .frag en: $shadersFull"
    return
}

$qsb = Find-Qsb -ExplicitPath $QsbPath -Venv $VenvDir
if (-not $qsb) {
    Write-Error ("No se encontro la herramienta qsb (Qt Shader Tools). " +
        "Instala PySide6 en el venv (PyQt6 no incluye qsb), anade qsb al PATH " +
        "o pasa -QsbPath con la ruta a qsb.exe.")
}

foreach ($source in $sources) {
    $output = "$($source.FullName).qsb"
    & $qsb @qsbProfileArgs -o $output $source.FullName
    if ($LASTEXITCODE -ne 0) {
        Write-Error "qsb fallo con codigo $LASTEXITCODE compilando: $($source.FullName)"
    }
    Write-Output "Generado: $output"
}
