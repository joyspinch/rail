# 铁轨快递 · RAIL

> 铁路调度：机车自动前进，玩家在分岔处选路，把车上的货运到同色站台得分。

用 [Zan](https://github.com/joyspinch/zan-lang) 语言写的独立游戏项目（仓库根自带 git 仓库）。完整设计与实现说明见 [`PROJECT.md`](PROJECT.md)。

## 玩法

- **地图**是 ASCII 网格（`RailNetwork` 解析）：

  | 字符 | 含义 |
  |---|---|
  | `#` | 空地 |
  | `-` `|` | 东西 / 南北向直轨 |
  | `*` `x` | 分岔（东西直通 + 南向 / 北向岔道），3 个接头 |
  | `C` | 货场，机车出发点 |
  | `S` `A` `V` `B` | 站台（只接西 / 东 / 北 / 南），尽头 |

  两格相邻**不等于**相连，必须互相声明了对方方向才算连上。于是铁路网是一棵
  **树**（每个分岔 3 个接头，每个站台/货场 1 个接头），任意两点之间路径唯一
  ——「该往哪边走」是确定答案，不是猜谜（断言里用「边数 = 点数 - 1」守着）。

- **一局**：机车每 tick 走一格（380 ms）；到分岔**停下等调度**，玩家按
  `A` / `D` 或点击「A 北轨（左转）」「D 东轨（直行）」两个按钮选路，
  鼠标悬停按钮会**点亮整条支线**预览。
- **得分**：送到同色站台 +100 并卸货（卸完换下一件货）；送到异色站台 -15；
  走进没有轨道的格子 = 脱轨 -25 分、-5 秒，机车退回上一个分岔重新选路。
- **时限**：每关倒计时（70 / 90 / 110 秒），归零即本关失败。
- **关卡**：3 关递进——第 1 关 1 个分岔 2 座站台，第 2 关 3 个分岔 3 座站台
  并有撞车死路，第 3 关 5 个分岔 5 座站台（含同色诱饵站台）。
- **结算**：送达数 / 得分 / 用时 / 脱轨次数 + 累计数据（最高得分、累计送达、
  通关次数），存档落盘，菜单与结算面板都能看到。

### 设置（Esc）

| 项 | 说明 |
|---|---|
| 音效 | 关/开全部音效事件 |
| 自动调度 | 由调度员代选分岔（看目标站台、避死路），演示/新手用 |
| 调度建议 | 在分岔处标出通往目标站台的方向（关掉就是纯手眼调度） |
| 严格时限 | 倒计时打八折 |

## 构建

需要 [zan-lang](https://github.com/joyspinch/zan-lang) 仓库（`zanc` 编译器、公共包与 stdlib 都在里面）：

```powershell
git clone https://github.com/joyspinch/zan-lang.git
$env:ZAN_HOME = 'D:/path/to/zan-lang'   # 指到刚克隆的 zan-lang 仓库根

pwsh -File client/tools/build.ps1
```

产物：`build/rail/Rail.exe`（运行目录要带上它旁边的 `assets/` 与 `skins/`）。

## 运行

```powershell
cd build/rail
.\Rail.exe
```

## 测试

```powershell
pwsh -File client/tools/test.ps1
```

## 目录结构

```
rail/
client/
  src/      # 游戏源码（.zan 源码 + HTML 界面设计稿）
  assets/   # 位图 / 音频素材
  data/     # 数值表与数据文件
  tests/    # 玩法断言用例
  tools/    # 构建与测试脚本
PROJECT.md
```

## 素材与授权

- 素材清单与授权说明见 [`client/ASSETS.md`](client/ASSETS.md)。

## 许可

本仓库暂未附带 `LICENSE` 文件，开源许可待作者选定后补充。依赖的 zan-lang 仓库采用 ZCSL（Zan Community Source License 1.0）。

## 更多文档

- [`PROJECT.md`](PROJECT.md) —— 完整设计与实现说明
- [`client/ASSETS.md`](client/ASSETS.md) —— 素材清单
