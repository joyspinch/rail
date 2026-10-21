# 铁轨快递 · RAIL —— 铁路调度

俯视网格铁路调度游戏：机车自动前进，玩家在**分岔处选路**，把车上的货运到
**同色站台**得分；送错站台扣分，走进死路支线脱轨。每关限时，3 关递进，
结算面板给出送达数 / 得分 / 用时，累计数据进存档。

> 素材清单见 [`client/ASSETS.md`](client/ASSETS.md)；交付标准见
> zan-lang 仓库 `docs/REAL_GAME_STANDARD.md`。

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

## 怎么跑

```powershell
$env:ZAN_HOME = 'D:/project/zan-lang'      # 编译器与 stdlib 同源；公共包在它 packages/ 下
pwsh -File client/tools/build.ps1           # → build/rail/Rail.exe
pwsh -File client/tools/test.ps1            # 三段：玩法断言 / 存档两遍 / 无头冒烟
```

项目在仓库外，编译时 `--package-project` 指向 zan-lang 仓库（公共包在它的
`packages/` 下；一律用主仓，不再用 worktree 副本——副本停在旧 commit，
公共包一改就追不上）：

```powershell
pwsh -File client/tools/build.ps1 -Compiler D:/project/zan-lang/build/zanc.exe `
    -PackageProject D:/project/zan-lang
```

### 环境变量

| 变量 | 作用 |
|---|---|
| `RAIL_SMOKE=1` | 无头冒烟：跑满 `RAIL_FRAMES` 帧后自行退出 |
| `RAIL_FRAMES=n` | 冒烟帧数（默认 300） |
| `RAIL_DEMO=1` | 演示：直接进第 1 关并开自动调度（截图用） |
| `RAIL_RESULT=1` | 直接摆出结算画面（截图用） |
| `RAIL_FACE=up\|right\|down\|left` | 把机车摆到该朝向并冻结（截"朝向一眼可辨"的对比图） |
| `RAIL_SETTINGS=1` | 直接弹出设置浮层（截皮肤用；Esc 键同样能弹） |
| `RAIL_TIME=n` | 把本关剩余秒数改成 n（截倒计时变红闪烁用） |
| `RAIL_SAVE=dir` | 覆盖存档目录（测试脚本用） |
| `RAIL_CAPTURE=path.zpx` | 抓画布像素（调试用） |

## 源码结构

```
client/
  src/
    main.zan        GuiHost 入口（建宿主 → 跑主循环）
    RailGame.zan    状态机（菜单/游戏中/结算）+ 关卡数据 + 输入
    RailNetwork.zan ASCII 地图 → 连接掩码 / 路径查询（树，唯一路径）
    RailTrain.zan   机车前进、分岔决策、脱轨回退
    RailCargo.zan   货物与站台类型规则、得分与罚分
    RailView.zan    渲染层：地图、机车、站台、HUD、菜单、结算面板
    RailPaint.zan   逻辑坐标绘制原语（CDraw 视口映射 + 裁源贴图 + 九宫格）
    RailFacing.zan  朝向 → 精灵表帧号（纯函数，16 方向）
    RailPalette.zan 色板（整个项目唯一一处颜色定义）
    RailPuff.zan    一缕蒸汽（格坐标）
    GameShell.zan   存档（最高得分/累计送达/通关次数/出场）+ 设置 + 设置浮层
  assets/           16 张位图 + assets/sfx/ 8 个 WAV + assets/skins/rail/skin.css
  tests/rail_test.zan  164 条玩法断言
  tools/build.ps1   编译（顺带把皮肤包拷到 exe 同级；控件基线 base.css 由编译器内嵌）
  tools/test.ps1    三段测试
  tools/bake_facing.py / bake_ui.py / bake_bg.py / postprocess.py
                    素材生成脚本（方向精灵表 / UI 底板 / 背景层次 / AI 原图后处理）
  tools/gen_images.ps1 / gen_sfx.py  AI 原图与音效的生成脚本
```

公共件全部来自 `packages/Zan.Game`：`Game.Kit.CDraw`（视口映射 + 贴图）、
`Game.Foundation.SfxBank`（音效库）、`Game.Foundation.GameSaveStore` /
`GameSettings` / `SettingsOverlay`（存档与设置）、`Game.Foundation.Gui.GuiHost`
（宿主与 `IGuiHostLoop`）。

## 观感（第二轮：UI 图形化 + 机车朝向）

- **机车朝向**：引擎运行时转不了图，方向帧由 `client/tools/bake_facing.py`
  离线旋成 **16 方向精灵表**（帧 0 = 车头朝上，之后每帧顺时针 22.5°），
  运行时按行进方向取帧（`RailFacing.FrameForDirection`）。车头 = 底部红色
  排障器 + 一枚暖色前照灯，货箱挂在**车尾**、朝向与车一致。
- **UI 图形化**：自带皮肤包 `client/assets/skins/rail/skin.css`（机油黑 +
  黄铜 + 信号灯红/绿），设置浮层不再是系统默认黑卡片；画布上的面板/按钮走
  **美术底板九宫格**（`ui_panel.png` / `ui_btn_sheet.png`，按钮三态），
  文字带阴影/描边。
- **倒计时**：压力表表盘 + 指针（剩余时间占比）+ 信号灯（<10 秒转红闪烁）。
- **画面细节**：背景加低频层次（云影 + 薄雾带 + 暗角）、站台/货箱/机车加接触
  阴影、行进时冒蒸汽并轻微摇摆、送错/脱轨时红色警示闪烁。

## 测试

`client/tools/test.ps1` 三段：

1. `rail_test_OK` —— 玩法断言用例（164 条）：地图解析、轨道连通性与树性质、
   机车逐格前进不脱轨、分岔选择决定下一节点、脱轨回退、货物类型匹配才得分、
   送错扣分、倒计时归零判失败、关卡依次推进、3 个种子随机调度跑完不崩且
   得分与送达数自洽、**朝向映射（0/90/180/270 度、±π 等价、帧界单调、
   精灵表源矩形）**、**送错/脱轨触发红色警示**。
2. `rail_SAVE_OK runs=1 -> runs=2` —— 存档写两遍读得到（第二遍是新进程）。
3. `rail_SMOKE_OK` —— 无头冒烟跑满帧自行退出。

## 当前状态

三关可玩闭环已通：真实位图渲染（轨道/机车/货箱/站台/背景/HUD 面板）、8 个
音效事件、存档与累计数据、164 条玩法断言全绿。第二轮补上了**机车朝向**
（16 方向精灵表）与**UI 图形化**（皮肤包 + 美术底板 + 压力表倒计时 +
画面细节）。截图见 `build/rail/ui_run.png`（游戏画面）、
`build/rail/ui_face_up.png` / `ui_face_right.png`（朝向对比）、
`build/rail/ui_settings.png`（皮肤化设置面板）。
