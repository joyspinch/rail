# 铁轨快递 · RAIL —— 素材清单

俯视铁路调度游戏。素材全部自制：位图由 AI 生成（gpt-image-2.5）后经
Python/PIL 抠 alpha、裁边、按显示尺寸 2 倍入库；方向帧、UI 底板与背景层次
由**程序化脚本**生成（可复现，见 §二）；音效由 Python/numpy 合成。

**入库总量**：位图 16 张 + 音效 8 个 ≈ **1.2 MB**（口径 0.3–1.5 MB，达标）。
原始生成图不入库，落在 `build/raw/`。

## 一、位图（client/assets/）

### 1. AI 生成 + 后处理（原始素材）

| 文件 | 尺寸 | 显示尺寸 | 用途 | 来源 |
|---|---|---|---|---|
| `bg_land.png` | 1024×640 | 1280×848 满铺 | 俯视乡村背景大图（田地/河/林/农舍） | AI 生成 → 缩放 + 128 色调色板 |
| `track_h.png` | 128×128 | 48–64 px/格 | 东西向直轨 | AI 生成 → 抠黑底 + 裁边 |
| `track_v.png` | 128×128 | 48–64 px/格 | 南北向直轨 | `track_h.png` 旋转 90° 派生 |
| `switch_n.png` | 128×128 | 48–64 px/格 | 分岔（东西直通 + 北向岔道） | `track_h` + `track_v` 上半拼合 |
| `switch_s.png` | 128×128 | 48–64 px/格 | 分岔（东西直通 + 南向岔道） | `track_h` + `track_v` 下半拼合 |
| `train.png` | 128×128 | 1.35 格 | 俯视蒸汽机车（车头有红色排障器）**——方向精灵表的源图** | AI 生成 → 抠黑底 + 裁边 |
| `cargo.png` | 64×64 | 0.44 格 | 车载木货箱 **——方向精灵表的源图** | AI 生成 → 抠黑底 + 裁边 |
| `station.png` | 160×160 | 1.35 格 | 乡村站台（雨棚 + 站台板） | AI 生成 → 抠黑底 + 裁边 |

**为什么直轨只有一张原图**：竖轨与两种分岔由横轨图旋转/拼合派生，
轨道接缝才对得上——AI 各画一张必然对不齐。

**生成提示词**（`gpt-image-2.5`，`--size 1024x1024` 或 `1536x1024`）：

- bg_land：`Top-down aerial view of a stylized countryside railway region,
  patchwork green farm fields, small forest clusters, a winding river, dirt
  roads, painterly game art, even soft lighting, no text, no people, no trains`
- track_h：`Top-down orthographic view of one straight railway track segment
  running horizontally, two steel rails on wooden sleepers on grey ballast bed,
  perfectly centered, isolated on pure black background, crisp game asset`
- train：`Top-down orthographic view of a small vintage steam locomotive seen
  from directly above, symmetrical boiler and cab, chimney in the middle,
  isolated on pure black background, crisp game asset`
- cargo：`Top-down orthographic view of a wooden shipping crate with iron metal
  bands, perfectly centered, isolated on pure black background, crisp game asset`
- station：`Top-down orthographic view of a small rural railway station
  platform with a wooden shelter, small roof and awning, perfectly centered,
  isolated on pure black background, crisp game asset`

### 2. 方向精灵表（离线旋帧烘焙）

引擎运行时转不了图（`Canvas.BlitImage` 只有源矩形，无旋转/无水平翻转），
所以方向帧只能在素材阶段烘好，运行时按角度取帧。

| 文件 | 尺寸 | 帧数 | 帧宽 | 显示 | 用途 |
|---|---|---|---|---|---|
| `train_sheet.png` | 2048×128 | **16** | 128×128 | 1.35 格 | 机车 16 方向（22.5°/帧） |
| `cargo_sheet.png` | 768×48 | **16** | 48×48 | 0.44 格 | 货箱 16 方向（朝向与车一致） |

**映射规则（三处必须一致）**：

- 精灵表**帧 0 = 车头朝上**，之后每帧**顺时针**转 `360/16 = 22.5°`；
- 角度用屏幕坐标（x 向右 = 0°，y 向下 = +90°），与 `atan2(dy, dx)` 一致；
- 帧号 = 角度换算成"自上起顺时针"后四舍五入到最近帧：
  `idx = (int)((deg + 11.25) / 22.5)`；
- 网格方向 → 帧号：北 0 / 东 4 / 南 8 / 西 12。

运行时取帧 = `RailFacing.FrameForDirection(train.dir)`，
映射是**纯函数**（`client/src/RailFacing.zan`），用例钉住
（0/90/180/270 度、±π 等价、帧界单调）。

**烘焙脚本**：`client/tools/bake_facing.py`

- 输入：`client/assets/train.png` / `cargo.png`（**入库图**，不是 AI 原图——
  入库图才是运行时真正贴的那张）；
- 旋转轴 = 贴图中心（= 机车中心）；
- 旋转用"**预乘 alpha → 旋转 → 反预乘**"，直接旋转 RGBA 会把透明像素的
  黑色插值进边缘，半透明边缘发黑（黑边）；
- 车头识别：AI 机车图里车头是**底部的红色排障器**（真机排障器在机车前端；
  从前往后是 排障器 → 烟囱 → 蒸汽穹 → 煤水车，与图里自下而上的顺序一致），
  脚本取"红色像素最多的连通块"定位排障器，并在其内侧补一枚**暖色前照灯**
  （运行时机车只有 64px，只靠一小块红不够醒目）。

### 3. UI 美术底板（程序化生成，九宫格）

引擎**没有 border-image**，面板/按钮要拉伸只能自己裁源矩形拼 9 块，
所以底板按九宫格设计：角上放圆角与铆钉，中间只留可拉伸的纯色/渐变。

| 文件 | 尺寸 | 切角 | 用途 |
|---|---|---|---|
| `ui_panel.png` | 96×96 | 24 | 面板底板（顶栏 / 底栏 / 菜单 / 结算框）：机油黑底 + 黄铜框 + 四角铆钉 |
| `ui_btn_sheet.png` | 768×48 | 14 | 按钮三态 × 普通/强调/禁用 共 8 帧（96×48 一帧） |
| `ui_gauge.png` | 96×96 | — | 压力表表盘（黄铜表圈 + 奶白表盘 + 刻度 + 红色危险弧）；指针运行时用线画，不进图 |
| `ui_shadow.png` | 64×64 | — | 接触阴影（径向衰减黑斑，站台/货箱/机车落地用） |

**烘焙脚本**：`client/tools/bake_ui.py`（纯程序化——大面积平铺的底板放
AI 噪点会在拉伸后变成条纹，代码画既精确又可复现）。

### 4. 背景低频层次（程序化生成）

俯视航拍视角没有地平线，所以层次不做"远山天际线"，而是给**云影 + 薄雾带 +
暗角**——低频（几十到几百像素尺度）的明暗变化，刻意避开高频噪点。

| 文件 | 尺寸 | 用途 |
|---|---|---|
| `bg_overlay.png` | 512×256 | 云影 + 薄雾带（叠在大图上，alpha ≤ 113） |
| `bg_vignette.png` | 256×256 | 暗角（把注意力收回画面中心） |

**烘焙脚本**：`client/tools/bake_bg.py`。

### 5. 皮肤包（client/assets/skins/rail/skin.css）

铁路风皮肤包：机油黑底 + 黄铜 + 信号灯红/绿。令牌名照
`packages/Zan.Gui/src/Gui/skins/base.css` 与 `Gui/Styling/Theme.zan` 抄；
圆角写两组（`--border-radius-*` 驱动控件圆角，`--radius-*` 只在本皮肤规则
里有效）。构建拷到 `build/rail/skins/rail/`，启动时
`host.App().UseSkin("dark")` → `host.App().UseSkin("rail")` 应用
（**顺序反了会被默认皮肤盖回去**）。色值与 `client/src/RailPalette.zan`
一一对应。

## 二、生成与后处理流程（可复现）

```
client/tools/gen_images.ps1   # AI 原图 → build/raw/（不入库）
client/tools/postprocess.py   # 原图 → 入库图（抠 alpha / 裁边 / 缩放）
client/tools/bake_facing.py   # 入库图 → 16 方向精灵表
client/tools/bake_ui.py       # → UI 底板（面板/按钮/表盘/阴影）
client/tools/bake_bg.py       # → 背景层次（云影/暗角）
client/tools/gen_sfx.py       # → 音效 WAV
```

## 三、音效（client/assets/sfx/）

| 文件 | 时长 | 触发时机 |
|---|---|---|
| `whistle.wav` | 0.55 s | 汽笛：关卡开始、机车抵达分岔 |
| `select.wav` | 0.09 s | 咔哒：玩家在分岔处确认路线（A/D 或点按钮） |
| `deliver.wav` | 0.30 s | 上行三音铃：货物送到**同色**站台，得分 +100 |
| `error.wav` | 0.26 s | 下行闷响：送到**异色**站台，扣 15 分 |
| `crash.wav` | 0.45 s | 噪声爆 + 闷锤：走进死路支线脱轨，扣 25 分、损失 5 秒 |
| `levelup.wav` | 0.52 s | 号角：本关货物送完，通关结算加分 |
| `win.wav` | 0.84 s | 长号角：3 关全过，全线贯通 |
| `fail.wav` | 0.51 s | 下行小调：倒计时归零，本关失败 |

音效走公共包 `Game.Foundation.SfxBank`（`SfxBank.LoadAll("assets/sfx", …)`），
磁盘优先 + 内嵌兜底；没有声卡时整库静默失效，游戏照常跑。

## 四、程序化叠加（不占位图预算）

- **货物类型色**：货箱位图外套一圈颜色框（红/蓝/黄），站台右上角同色徽标 + 汉字。
- **接触阴影**：站台/货箱/机车底下各贴一块 `ui_shadow.png` 软斑，物体才"落地"。
- **蒸汽**：行进时从烟囱冒出白雾（`Canvas.FillRadial`），停在分岔时不冒。
- **车身摇摆**：行进时机车整体做 ±2px 的低频摆动。
- **倒计时**：压力表表盘 + 指针（指针角度 = 剩余时间占比，满表左下 135°、
  空表右下 45°），旁边信号灯绿灯常亮、<10 秒转红并闪烁，秒数同步变红。
- **警示**：送错站台/脱轨时全屏红闪 + 红色边框（脱轨时机车外圈再加红环）。

## 五、许可与来源

全部自制：位图来自本项目调用的图像生成 API，方向帧/UI 底板/背景层次由本项目
脚本程序化生成，音效为本项目脚本合成。
未取用任何第三方游戏素材（含 OpenTTD/TTD 衍生件）。
