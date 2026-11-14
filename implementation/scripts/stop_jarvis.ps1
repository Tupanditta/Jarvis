<#
.SYNOPSIS
Termina el proceso del asistente Jarvis lanzado desde el venv del proyecto.
.PARAMETER VenvDir
Directorio del venv. Por defecto implementation\.venv relativo a este script.
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$VenvDir
)

$ErrorActionPreference = 'Stop'

if (-not $VenvDir) {
    $VenvDir = Join-Path $PSScriptRoot '..\.venv'
}

$venvFull = [System.IO.Path]::GetFullPath($VenvDir).TrimEnd('\') + '\'

# La consulta es de solo lectura: -WhatIf no debe afectar a la carga del modulo CIM.
$whatIfOriginal = $WhatIfPreference
$WhatIfPreference = $false
try {
    $procesos = @(Get-CimInstance -ClassName Win32_Process -Filter "Name = 'pythonw.exe' OR Name = 'python.exe'" |
        Where-Object {
            $_.CommandLine -like '*jarvis_assistant*' -and
            $_.ExecutablePath -and
            $_.ExecutablePath.StartsWith($venvFull, [System.StringComparison]::OrdinalIgnoreCase)
        })
}
finally {
    $WhatIfPreference = $whatIfOriginal
}

if ($procesos.Count -eq 0) {
    Write-Output 'No hay procesos del asistente en ejecucion.'
    exit 0
}

$terminados = 0
foreach ($proceso in $procesos) {
    if ($PSCmdlet.ShouldProcess("PID $($proceso.ProcessId) ($($proceso.ExecutablePath))", 'Stop-Process')) {
        Stop-Process -Id $proceso.ProcessId -Force
        $terminados++
    }
}

Write-Output "Procesos terminados: $terminados"
exit 0
