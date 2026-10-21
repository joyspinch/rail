$ErrorActionPreference = 'Stop'
# 原始生成图落 build/raw/（git-ignored），后处理后入库 client/assets/。
#
# 用法：pwsh -File client/tools/gen_images.ps1
# 后处理：python client/tools/postprocess.py（抠 alpha → 裁边 → 入库）
# 方向精灵表：python client/tools/bake_facing.py（从入库图旋出 16 方向）
# UI 底板：python client/tools/bake_ui.py（程序化九宫格/按钮/表盘）
# 背景层次：python client/tools/bake_bg.py（程序化云影 + 暗角）
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$raw = Join-Path $root 'build/raw'
New-Item -ItemType Directory -Force $raw | Out-Null
$script = "$HOME\.codex\skills\local-image2\scripts\image2.ps1"

$jobs = @(
    @{ name = 'bg_land';   size = '1536x1024'; prompt = 'Top-down aerial view of a stylized countryside railway region, patchwork green farm fields, small forest clusters, a winding river, dirt roads, painterly game art, even soft lighting, no text, no people, no trains' },
    @{ name = 'track_h';   size = '1024x1024'; prompt = 'Top-down orthographic view of one straight railway track segment running horizontally, two steel rails on wooden sleepers on grey ballast bed, perfectly centered, isolated on pure black background, crisp game asset, high detail, no text' },
    @{ name = 'train';     size = '1024x1024'; prompt = 'Top-down orthographic view of a small vintage steam locomotive seen from directly above, symmetrical boiler and cab, chimney in the middle, isolated on pure black background, crisp game asset, high detail, no text' },
    @{ name = 'cargo';     size = '1024x1024'; prompt = 'Top-down orthographic view of a wooden shipping crate with iron metal bands, perfectly centered, isolated on pure black background, crisp game asset, high detail, no text' },
    @{ name = 'station';   size = '1024x1024'; prompt = 'Top-down orthographic view of a small rural railway station platform with a wooden shelter, small roof and awning, perfectly centered, isolated on pure black background, crisp game asset, high detail, no text' }
)

foreach ($j in $jobs) {
    $out = Join-Path $raw ($j.name + '.png')
    if (Test-Path $out) { Write-Host "skip $($j.name) (exists)"; continue }
    $ok = $false
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        Write-Host "generate $($j.name) attempt $attempt"
        & $script generate --model gpt-image-2.5 --prompt $j.prompt --size $j.size --quality high --output-format png --out $out --force 2>&1 | Out-String | Write-Host
        if (Test-Path $out) { $ok = $true; break }
        Write-Host "retry in 60s ($($j.name))"
        Start-Sleep -Seconds 60
    }
    if (-not $ok) { Write-Host "FAILED $($j.name)" }
}
Write-Host 'GEN_DONE'
