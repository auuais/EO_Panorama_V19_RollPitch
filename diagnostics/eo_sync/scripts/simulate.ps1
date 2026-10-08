param([Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
$package=Split-Path -Parent $PSScriptRoot
$simOut=[System.IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $simOut){throw "Refusing existing simulation directory $simOut"}
New-Item -ItemType Directory -Path $simOut | Out-Null
$bin='C:/AMDDesignTools/2025.2/Vivado/bin'
Push-Location -LiteralPath $simOut
try {
    & "$bin/xvlog.bat" --sv "$package/rtl/EoSyncTelemetry.v" "$package/rtl/EoSyncSnapshot.v" "$package/sim/tb_EoSyncTelemetry.sv" "$package/sim/tb_EoSyncSnapshot.sv"
    if($LASTEXITCODE -ne 0){throw 'Compilation failed'}
    foreach($top in @('tb_EoSyncTelemetry','tb_EoSyncSnapshot')) {
        & "$bin/xelab.bat" $top -s $top --debug typical
        if($LASTEXITCODE -ne 0){throw "Elaboration failed $top"}
        & "$bin/xsim.bat" $top -runall -log "$top.log"
        if($LASTEXITCODE -ne 0 -or !(Select-String -LiteralPath "$top.log" -Pattern '^PASS:' -Quiet)){throw "Simulation failed $top"}
    }
} finally {Pop-Location}
