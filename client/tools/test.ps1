# 铁轨快递 · RAIL 测试：玩法断言 + 存档两遍 + 无头冒烟。
#
# 三段（缺一不可）：
#   1. rail_test_OK            —— 玩法断言用例（轨道连通 / 机车前进 /
#                                 分岔选路 / 货物匹配 / 超时失败 / 关卡推进）
#   2. rail_SAVE_OK runs=1 -> runs=2
#                              —— 存档写两遍读得到（第一遍写局数 1，
#                                 第二遍是新进程，必须读回局数 2）
#   3. rail_SMOKE_OK           —— 无头冒烟跑满帧自行退出
#
# 存档落在临时目录里，不碰玩家机器上的 %LOCALAPPDATA%/Rail。
param(
    [string]$Compiler = $env:ZANC,
    [string]$PackageProject = '',
    [int]$TimeoutSeconds = 120
)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$repo = Split-Path -Parent $project
if (-not $Compiler) {
    $local = if ($env:ZAN_HOME) { Join-Path $env:ZAN_HOME 'build/zanc.exe' } else { '' }
    if ($local -and (Test-Path $local)) { $Compiler = $local } else { $Compiler = (Get-Command zanc -ErrorAction Stop).Source }
}
if (-not $PackageProject) { if ($env:ZAN_HOME) { $PackageProject = $env:ZAN_HOME } else { throw '需要 $env:ZAN_HOME 指向 zan-lang 仓库（公共包在它的 packages/ 下）' } }
$out = Join-Path $repo 'build/rail'
& (Join-Path $PSScriptRoot 'build.ps1') -Compiler $Compiler -PackageProject $PackageProject -Output $out
$exe = Join-Path $out 'Rail.exe'
if (-not (Test-Path $exe)) { throw "缺少可执行文件：$exe" }

# --- 第 1 段：玩法断言 -------------------------------------------------
# 源码要排除 main.zan（它带 Main()，用例自己的 Main 才是入口）。
$caseSources = @(Get-ChildItem (Join-Path $project 'src') -Recurse -File -Filter *.zan |
    Where-Object { $_.Name -ne 'main.zan' } |
    Sort-Object FullName | ForEach-Object { $_.FullName })
$case = 'rail_test.zan'
$stem = [IO.Path]::GetFileNameWithoutExtension($case)
$caseExe = Join-Path $out "$stem.exe"
& $Compiler (@((Join-Path $project "tests/$case")) + $caseSources +
    @('--auto-stdlib', '--package-project', $PackageProject, '-o', $caseExe))
if ($LASTEXITCODE -ne 0) { throw "玩法用例编译失败：$case (zanc=$LASTEXITCODE)" }
# 用例自己也会建 GameShell（读存档），给它一个干净的临时目录。
$ruleSave = Join-Path $out 'savetest_rules'
if (Test-Path $ruleSave) { Remove-Item $ruleSave -Recurse -Force }
New-Item -ItemType Directory -Force $ruleSave | Out-Null
$env:RAIL_SAVE = $ruleSave
$caseOut = & $caseExe 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) { throw "玩法用例失败：$case`n$caseOut" }
if ($caseOut -notmatch "$stem OK") { throw "玩法用例输出不对：$case`n$caseOut" }
Write-Host $caseOut.Trim()
Write-Host "${stem}_OK"

# --- 第 2 段：存档两遍 -------------------------------------------------
$saveDir = Join-Path $out 'savetest'
if (Test-Path $saveDir) { Remove-Item $saveDir -Recurse -Force }
New-Item -ItemType Directory -Force $saveDir | Out-Null
$env:RAIL_SAVE = $saveDir
# 冒烟标记：跑满 N 帧后程序自行退出（不走 UiDriver 脚本，避免桌面事件污染）
$env:RAIL_SMOKE = '1'
$env:RAIL_FRAMES = '420'
$log = Join-Path $out 'rail_smoke.log'
if (Test-Path $log) { Remove-Item $log -Force }
$proc = Start-Process -FilePath $exe -WorkingDirectory $out -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $log -RedirectStandardError (Join-Path $out 'rail_smoke.err')
if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
    $proc.Kill()
    throw "无头冒烟超时：应用没在 $TimeoutSeconds 秒内退出"
}
if ($proc.ExitCode -ne 0) { throw "无头冒烟失败：exit=$($proc.ExitCode)" }
if (-not (Select-String -Path $log -Pattern 'RAIL_SMOKE_OK' -Quiet)) {
    throw "无头冒烟未收尾（缺 RAIL_SMOKE_OK）：$log"
}
# 存档落盘 + 读回：第二遍是新进程，必须读回第一遍写的档（局数 1 -> 2）。
$saveLine = Select-String -Path $log -Pattern 'RAIL_SAVE' | Select-Object -First 1
if (-not $saveLine) { throw "没有存档输出行（RAIL_SAVE）：$log" }
if ($saveLine.Line -notmatch 'runs=1') {
    throw "第一遍存档没写成局数 1：$($saveLine.Line)"
}
if (-not (Test-Path (Join-Path $saveDir 'rail_slot0.json'))) {
    throw "存档文件没落盘：$saveDir"
}
$log2 = Join-Path $out 'rail_smoke2.log'
if (Test-Path $log2) { Remove-Item $log2 -Force }
$proc2 = Start-Process -FilePath $exe -WorkingDirectory $out -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $log2 -RedirectStandardError (Join-Path $out 'rail_smoke2.err')
if (-not $proc2.WaitForExit($TimeoutSeconds * 1000)) {
    $proc2.Kill()
    throw "第二遍无头冒烟超时"
}
if ($proc2.ExitCode -ne 0) { throw "第二遍无头冒烟失败：exit=$($proc2.ExitCode)" }
if (-not (Select-String -Path $log2 -Pattern 'RAIL_SMOKE_OK' -Quiet)) {
    throw "第二遍无头冒烟未收尾（缺 RAIL_SMOKE_OK）：$log2"
}
$saveLine2 = Select-String -Path $log2 -Pattern 'RAIL_SAVE' | Select-Object -First 1
if (-not $saveLine2 -or $saveLine2.Line -notmatch 'runs=2') {
    throw "第二遍没读回上一遍的存档（期望 runs=2）：$($saveLine2.Line)"
}
Write-Host "rail_SAVE_OK runs=1 -> runs=2"
Write-Host "rail_SMOKE_OK"
