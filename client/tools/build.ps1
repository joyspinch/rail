# 铁脉物流 构建：编译 client/src/ 下全部 .zan → 可执行文件。
#
# 公共包（Gui / Game.Kit / Game.Foundation / Game.Tactics …）住在 zan-lang
# 仓库的 packages/ 下，编译要带 --package-project 指向包根：仓库内 = 仓库根；
# 项目搬到仓库外后 = zan-lang 仓库，由 $ZAN_HOME 或 -PackageProject 指定。
# assets/ 由 zanc 自动内嵌进 exe（入口源文件带目录前缀时才会定位到），
# 这里再在 exe 旁留一份磁盘副本——运行时磁盘优先，换图即生效。
param(
    [string]$Compiler = $env:ZANC,
    [string]$Stdlib = $env:ZAN_STDLIB,
    [string]$Output = '',
    [string]$PackageProject = '',
    # 透传给 zanc 的额外参数（如 --publish --target android-arm64 ...）
    [string[]]$ZancArgs = @()
)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$repo = Split-Path -Parent $project
# 编译器查找顺序：-Compiler → $env:ZANC → $env:ZAN_HOME\build → PATH →
# 包工程旁边的 zan-lang 仓库（仓库外的独立项目常用 worktree 做包源，
# 编译器只在主仓库里编译过）。
function Resolve-Zanc([string]$explicit, [string]$packageProject) {
    if ($explicit) { return $explicit }
    if ($env:ZANC) { return $env:ZANC }
    if ($env:ZAN_HOME) {
        $p = Join-Path $env:ZAN_HOME 'build/zanc.exe'
        if (Test-Path $p) { return $p }
    }
    $onPath = Get-Command zanc -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    $candidates = @()
    if ($packageProject) {
        $parent = Split-Path -Parent $packageProject
        if ($parent) { $candidates += (Join-Path $parent 'zan-lang/build/zanc.exe') }
    }
    $candidates += (Join-Path $repo 'build/zanc.exe')
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    throw '找不到 zanc 编译器：请用 -Compiler 指定，或设置 $env:ZANC / $env:ZAN_HOME'
}
function Resolve-PackageProject([string]$projectRoot) {
    if ($env:ZAN_HOME -and (Test-Path (Join-Path $env:ZAN_HOME 'packages'))) { return $env:ZAN_HOME }
    $dir = Split-Path -Parent $projectRoot
    for ($i = 0; $i -lt 4 -and $dir; $i = $i + 1) {
        foreach ($name in @('zan-lang', 'zan-head')) {
            $c = Join-Path $dir $name
            if (Test-Path (Join-Path $c 'packages')) { return $c }
        }
        $dir = Split-Path -Parent $dir
    }
    return ''
}
$Compiler = Resolve-Zanc $Compiler $PackageProject
if (-not $PackageProject) { $PackageProject = Resolve-PackageProject $repo }
if (-not $Stdlib -and $env:ZAN_HOME) { $Stdlib = Join-Path $env:ZAN_HOME 'stdlib' }
if (-not $PackageProject) { if ($env:ZAN_HOME) { $PackageProject = $env:ZAN_HOME } else { throw '需要 $env:ZAN_HOME 指向 zan-lang 仓库（公共包在它的 packages/ 下）' } }
if (-not $Output) { $Output = Join-Path $repo 'build/rail' }
$Output = [IO.Path]::GetFullPath($Output)
New-Item -ItemType Directory -Force -Path $Output | Out-Null
# 入口 main.zan 必须排第一：zanc 只把 Main() 给第一个编译输入
# （genrun.c 的 emitMain=paths[0]）。其余 .zan 递归枚举——zanc 不会自动
# 带上同目录的其它文件，少传一个就是 "undefined type"。
$entry = Join-Path $project 'src/main.zan'
$sources = @()
if (Test-Path $entry) { $sources += $entry }
$sources += @(Get-ChildItem (Join-Path $project 'src') -Recurse -File -Filter *.zan |
    Where-Object { $_.FullName -ne $entry } | Sort-Object FullName | ForEach-Object { $_.FullName })
$zargs = @($sources) + @('--auto-stdlib', '--package-project', $PackageProject)
if ($Stdlib) { $zargs += @('--stdlib-path', $Stdlib) }
if ($ZancArgs) { $zargs += $ZancArgs }
$exe = Join-Path $Output 'Rail.exe'
$zargs += @('-o', $exe)
& $Compiler @zargs
if ($LASTEXITCODE -ne 0) { throw "zanc failed ($LASTEXITCODE)" }
$assets = Join-Path $project 'assets'
if (Test-Path $assets) { Copy-Item $assets $Output -Recurse -Force }
# 皮肤包必须与 exe 同级：build/rail/skins/rail/skin.css
# （Gui.Styling.Skin.Roots 查的是 exe 同级 skins/ 与 assets/skins/）。
$skinSrc = Join-Path $assets 'skins/rail'
if (Test-Path $skinSrc) {
    $skinDst = Join-Path $Output 'skins/rail'
    New-Item -ItemType Directory -Force -Path $skinDst | Out-Null
    Copy-Item (Join-Path $skinSrc '*') $skinDst -Recurse -Force
}
# 控件基线 base.css 跟皮肤包放在一起：Gui 只在磁盘上找它（没有内嵌
# 兜底），缺了它整层组件基线就没了，控件会退回硬编码的系统外观。
$baseCss = Join-Path $PackageProject 'packages/Zan.Gui/src/Gui/skins/base.css'
if (Test-Path $baseCss) {
    $skinsDir = Join-Path $Output 'skins'
    New-Item -ItemType Directory -Force -Path $skinsDir | Out-Null
    Copy-Item $baseCss (Join-Path $skinsDir 'base.css') -Force
}
Write-Host "Built $exe"