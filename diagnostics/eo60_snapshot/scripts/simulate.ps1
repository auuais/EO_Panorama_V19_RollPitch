param([Parameter(Mandatory=$true)][string]$OutputDirectory,
      [string[]]$Tops=@('tb_Eo60RasterMonitor','tb_Eo60FullRaster','tb_Eo60Telemetry','tb_Eo60InputSampler'))
$ErrorActionPreference='Stop'
$package=Split-Path -Parent $PSScriptRoot
$simOut=[System.IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $simOut){throw "Refusing existing simulation directory $simOut"}
New-Item -ItemType Directory -Path $simOut | Out-Null
$bin='C:/AMDDesignTools/2025.2/Vivado/bin'
Push-Location -LiteralPath $simOut
try {
    & "$bin/xvlog.bat" --sv "$package/rtl/Eo60RasterMonitor.v" "$package/rtl/Eo60Telemetry.v" "$package/rtl/Eo60InputSampler.v" "$package/sim/tb_Eo60RasterMonitor.sv" "$package/sim/tb_Eo60FullRaster.sv" "$package/sim/tb_Eo60Telemetry.sv" "$package/sim/tb_Eo60InputSampler.sv" "$bin/../data/verilog/src/glbl.v"
    if($LASTEXITCODE -ne 0){throw 'Compilation failed'}
    foreach($top in $Tops) {
        & "$bin/xelab.bat" $top glbl -L unisims_ver -s $top --debug typical
        if($LASTEXITCODE -ne 0){throw "Elaboration failed $top"}
        & "$bin/xsim.bat" $top -runall -log "$top.log"
        if($LASTEXITCODE -ne 0 -or !(Select-String -LiteralPath "$top.log" -Pattern '^PASS:' -Quiet)){throw "Simulation failed $top"}
    }
} finally {Pop-Location}
