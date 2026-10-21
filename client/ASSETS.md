# 铁轨快递 · RAIL —— 素材清单

俯视铁路调度游戏。素材全部自制：位图由 AI 生成（gpt-image-2.5）后经
Python/PIL 抠 alpha、裁边、按显示尺寸 2 倍入库；音效由 Python/numpy 合成。

**入库总量**：位图 8 张（750 KB）+ 音效 8 个（184 KB）≈ **918 KB**
（口径 0.3–1.5 MB，达标）。原始生成图不入库，落在 `build/raw/`。

## 一、位图（client/assets/）

| 文件 | 尺寸 | 显示尺寸 | 用途 | 来源 |
|---|---|---|---|---|
| `bg_land.png` | 1024×640 | 1280×848 满铺 | 俯视乡村背景大图（田地/河/林/农舍） | AI 生成 → 缩放 + 128 色调色板 |
| `track_h.png` | 128×128 | 48–64 px/格 | 东西向直轨 | AI 生成 → 抠黑底 + 裁边 |
| `track_v.png` | 128×128 | 48–64 px/格 | 南北向直轨 | `track_h.png` 旋转 90° 派生 |
| `switch_n.png` | 128×128 | 48–64 px/格 | 分岔（东西直通 + 北向岔道） | `track_h` + `track_v` 上半拼合 |
| `switch_s.png` | 128×128 | 48–64 px/格 | 分岔（东西直通 + 南向岔道） | `track_h` + `track_v` 下半拼合 |
| `train.png` | 128×128 | 1.35 格 | 俯视蒸汽机车（车头有排障器） | AI 生成 → 抠黑底 + 裁边 |
| `cargo.png` | 64×64 | 0.36 格 | 车载木货箱 | AI 生成 → 抠黑底 + 裁边 |
| `station.png` | 160×160 | 1.35 格 | 乡村站台（雨棚 + 站台板） | AI 生成 → 抠黑底 + 裁边 |
| `panel.png` | 1024×64 | 顶栏 1280×76 / 结算 560×380 | 黄铜铆钉面板（HUD 顶栏 + 结算框） | AI 生成 → 抠黑底 + 裁条 |

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
- panel：`A single horizontal dark brass and steel riveted UI panel bar, beveled
  edges, empty smooth center, warm metal, isolated on pure black background`

## 二、后处理（build/postprocess.py 的口径）

1. AI 图没有 alpha（纯黑底）→ 从四边洪泛把连通的近黑像素抠成透明
   （阈值 14）；背景图整幅保留，不抠。
2. 按 alpha 包围盒裁边；再裁成**以内容为中心的正方形**并缩放到显示尺寸 2 倍。
3. 背景缩到 1024×640 后转 128 色调色板（PNG 索引色），体积从 1.5 MB 压到 470 KB。
4. 音效：22050 Hz / 16 bit / 单声道 WAV，`assets/sfx/<事件名>.wav`。

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
- **机车朝向**：俯视机车贴图本身左右对称，朝向用车头前的一颗光点表示。
- **HUD / 按钮 / 进度**：几何绘制（面板底、边框、文字），属界面部件，允许几何。

## 五、许可与来源

全部自制：位图来自本项目调用的图像生成 API，音效为本项目脚本合成。
未取用任何第三方游戏素材（含 OpenTTD/TTD 衍生件）。
