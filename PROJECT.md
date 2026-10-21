# 铁脉物流 —— 2D 等轴测物流经营（OpenTTD 式）

> 本文件是 rail 项目的落地说明。**素材清单见 `client/ASSETS.md`**，全局规格见工作区根的 `ASSET-PIPELINE.md`。

## 参考源与授权边界

- **参考**：OpenTTD（`media/baseset/openttd/`，GPL-2.0 自制重绘路线）
- **抄什么**：抄产业需求链、路网连通、车流调度、地形改造、经济与信号机制。素材按 baseset 路线自制重绘。

**红线与差异**：

- OpenTTD 同目录 `orig_*.obg` / `orig_extra` 是 **TTD 原版衍生件，不可再用**。
- baseset 路线意味着**像素全部重画**，不做原样移植。
- 若用 `IsoTileMap` + `YSortLayer`，`GridToWorld` 与贴图菱形必须是同一套 2:1 比例，否则会出现半像素错位。

## 渲染路线

2D 贴图批 + **等轴测预切菱形（2:1）** 图块。地形 32×32 菱形，车辆 64×32，建筑 64×64。

## 目录

    rail/
      client/       src/ 源码、assets/ 素材、data/ 数据、skins/ 皮肤、tools/ 脚本、tests/ 用例
      build/        编译产物（不入库）

所有命令都在**项目根**下执行（路径相对项目根）。

## 编译

```powershell
$env:ZAN_HOME = 'D:/project/zan-lang'   # 编译器与 stdlib 同源；公共包在它的 packages/ 下
pwsh -File client/tools/build.ps1
```

ZAN_HOME 指向 zan-lang 仓库时用它的 `build/zanc.exe` 与 `stdlib/`；不设则用 PATH 上的 `zanc`。
编译时加 `--package-project $env:ZAN_HOME` 可直接吃仓库里的 `packages/`。

## 测试

```powershell
pwsh -File client/tools/test.ps1     # 无头冒烟：跑满 90 帧后自行退出
```

工作区批量冒烟：在 zan-lang 仓库侧跑 `pwsh -File scripts/smoke_all_game_projects.ps1`（一次跑完仓库外全部游戏项目）。

## 当前状态

骨架可编译可运行（90 帧无头冒烟通过）：等轴测网格、路网铺设、货车沿轨道行驶。

## 后续（按优先级）

1. 接入真实位图 sprite 与音效（素材见 `client/ASSETS.md`）。
2. 补玩法深度：参照源的关卡/数值/AI 三个维度逐项对齐。
3. 需要时再评估联网（`legend` 有服务端可参考）。