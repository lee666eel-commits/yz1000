# 手写字型自制管道（离线、免费、无需中国手机号）

把你自己写的字，1:1 描成真正的 `.ttf`。

**这条管道做不到的事**：mofont / 字体家「AI 神笔」卖的是生成式补全——你写 8~50 字，模型推出 6000 字全库。
那需要训练过的中文字形生成模型，本机做不到那个质量，别指望。

**这条管道做得到的事**：你写一个，字型里就精确有一个。零成本、离线、永久，
不受任何平台涨价／下架／要中国手机号影响。代价是你的手腕。

## 一次性依赖

```
python -m pip install fonttools potracer
```
已装：`fonttools 4.63.0`、`potracer 0.0.4`（另用系统已有的 `opencv-python 5.0.0`、`Pillow 12.2.0`、`numpy 2.4.4`）。
不需要 potrace.exe、不需要 FontForge、不需要 Inkscape。

## 三步

### 1. 出样张

```
python tools\make_template.py --out template
```
产出 `template\S1.html`、`S1.pdf`、`S1_preview.png`、`manifest.json`。

⛔ **`manifest.json` 是字↔格的唯一权威**，别手改、别删、别改名。
它记着四个定位标记与每一格的毫米坐标，切图完全按它走——所以「哪一格是哪个字」是结构决定的，不是靠猜。
重出样张会重出它，旧照片就配不上新 manifest 了。

打印 `S1.pdf`（或开 `S1.html` 按 Ctrl+P）。A4。

### 1b. v2 字帖（2026-08-21，讲座用的那份）

```
python tools\make_charset_v2.py
python tools\make_template.py --out template-v2 --chars-file template-v2-chars.txt --style mofont
python tools\render_sheet.py template-v2\S1.html
```
产出 `template-v2\S1.pdf`（单页 A4，实测 210.2×297.3mm）＋ `S1_preview.png` ＋ `manifest.json`。

跟 v1 的三个差别：
- **字表换了**：拿掉过于专指的名词（林子策／南华独中），补上主协办与赞助单位、
  以及 v1 漏掉的**阿拉伯数字 0-9 与 A I .**（不然「乐中学AI 2.0」打不出来）。
  必写 54 字由 `make_charset_v2.py` 断言覆盖，其余 46 格是高频填充。
- **红色格线＋米字格，格子里没有范字**。范字会被照描，出来的是印刷体不是他的手；
  要写哪个字改印在格子**上方**的小字。
- **红色不只是好看**：`#e23b32` 在灰阶里是 108，比 v1 的灰线更暗；
  但在**红色通道**里接近白。`manifest.json` 带 `grid_color: "red"`，
  `build_font.py` 看到就改读红色通道（`to_ink()`），格线因此完全不算墨。
  实测：格线被当成墨的像素 **红色通道 0 / 灰阶 6400**（`test\test_red_grid.py`）。
  ⚠️ 旧的 v1 sheet 没有这个栏位，照旧走灰阶，行为不变。

⚠️ 刻意写出格没关系，但**别整格涂满**：`strip_frame` 会把贴着裁切框的直线段当成印刷格线擦掉，
笔画长时间贴着框走可能被一起擦。样张抬头那句「不必写满格」就是这个意思。

**打印缩放不影响精度**——四角黑方块是定位标记，透视校正靠它们，缩放／偏移／歪斜都会被算掉。

### 2. 写 + 拍

- **黑色签字笔／原子笔，笔幅 0.7–1.0mm**，压过灰色范字。
- ⛔ 不要铅笔、不要浅蓝／浅灰笔——阈值会跟印刷灰字一起把它清掉。
- ⚠️ 0.38mm 以下的极细笔可能被误判「笔画过细」（见下面旋钮表最后一行）。
- 手机直拍即可，不必扫描仪。要求只有三条：
  **四个角的黑方块全部入镜**、纸摊平、光别一半亮一半暗。
- 写不完、跳过几格都没事——管道会把空格报出来并排除，**不会错位**。

### 3. 出字型

**懒人版**：把照片丢进 `scans\`（照片名 = 样张编号，`S1.jpg`、`S2.jpg`…），
**双击 `build-font.bat`**。它自己扫 `scans\` 里所有 jpg/jpeg/png、组好参数、出字型、
跑完自动开 proof 图给你看。也可以把任何装着照片的文件夹**拖到 `.bat` 上**，就用那个文件夹。
改字型名：用记事本开 `.bat`，改第一行 `set "FAMILY=LinHand"`。

⚠️ `.bat` 必须保持 **CRLF 换行 ＋ 纯 ASCII**（已验：1570 bytes、0 个非 ASCII、无 BOM）。
用 LF 存会让 `@echo off` 失效、整个档逐行当命令执行；里面写中文会在某些 codepage 下炸。

**手动版**：

```
python tools\build_font.py --manifest template\manifest.json --sheet S1=scans\S1.jpg --out build\LinHand.ttf --family "Lin Hand"
```
多张就多加几个 `--sheet S2=... --sheet S3=...`。

> 指令一律写成一行。`^` 是 cmd.exe 的续行符，PowerShell 不认，会当成多余参数直接报错；
> PowerShell 的续行符是反引号，太容易看漏，不如不折行。

产出 `.ttf` ＋ `LinHand_proof.png`（校对图）。

**装字型**：右键 `.ttf` → 安装。

## 示例产出（真人手写字体范例）

`examples/0000LiuJiaRui/` 是刘嘉瑞本人手写、跑通这条管道后的真实产出——`.ttf` 字体本体 +
`_proof.png` 校对图，已取得他本人同意公开作为开源范例。这不是模板/占位，是真实跑过验收三
道（cmap 集合相等／glyphs 实测计数／hollow 守卫）的成品，可以直接装字型看效果，也可以对照
proof 图核对每个字对不对得上。

其余参与者（0005MissHo／0010Phoon）的真迹字体不在此仓库公开范围内，见
`PRE-PUBLISH-CHECKLIST.md` 排除清单——只有明确同意公开的那一份才会出现在 `examples/` 下。

## 验收怎么算过

脚本自己跑三道，**报告里全印出来，任何一道不过就 exit 1**：

1. **`verify : cmap == inked set`** — 有墨的格子集合 vs 字型里的码位集合，**集合相等**。
   防错位：漏一格或换错张，后面每个字都挂错码位，而重叠率／IoU 这类指标**测不出配对错误**。
2. **`glyphs : N (measured from getGlyphOrder)`** — 实测计数，不是 `总数 − 失败数` 推算。
3. **`hollow : N cells under stroke-width …`** — 笔画中位宽度。
   这道是**踩过坑才加的**：曾经有个 bug 让所有笔画变成空心轮廓线，
   而第 1、2 道**全数通过**（码位对、计数对），只有肉眼看图才发现。
   所以第 3 道存在的唯一理由就是自动挡住那种「数字全对、东西全错」的情况。

第四道要你自己做：**打开 proof PNG 用眼睛读**。
字型能装进 Windows 不算证据；proof 图上每个字都是对的字，才算。

## 旋钮

| 症状 | 调什么 |
|---|---|
| 印刷灰范字没清掉（笔画外多出鬼影） | `--ink-thresh` 调低（默认 150），或重出样张时 `--tint "#e0e0e0"` |
| 笔画断断续续、细笔画丢失 | `--ink-thresh` 调高 |
| proof 图上「国 回 面」的中空被填实 | 加 `--reverse-contours` |
| 报 `FAIL … strokes thinner than` 但 proof 图其实好看（用了极细笔） | `--min-stroke 0.008`。**先看 proof 图再调**，别反射性调 |
| 字上带黑框／贴边横竖线（印刷格线漏进来） | 默认已自动清（看 `framed` 那行）。要关掉用 `--keep-frame` |
| 想看每一格切出来长什么样 | 加 `--debug-dir test\debug` |

`--reverse-contours` 目前实测不需要（potracer 的极性已在 `trace_to_glyph` 里处理，
且实测「国 回 面 有 目」中空正确），留作逃生口，已跑过确认不崩。

## 字数怎么选

| 字数 | 覆盖率 | 你要写多久（约 5 秒/字） |
|---|---|---|
| 100（已备好的试跑样张） | — | 10 分钟 |
| 1000 | 行文约 90% | 1.5 小时 |
| 2500 | 约 98% | 3.5 小时 |
| 3500（一级字表） | 约 99.5% | 5 小时 |

换字数：
```
python tools\make_template.py --out template-1000 --chars-file chars.txt --count 1000
```
`chars.txt` = UTF-8 纯文字档，要的字按**频率高→低**排进去（脚本自动去重、按顺序取前 N）。
每张 120 格，1000 字 = 9 张（最后一张 40 格）。
**分批做**：写完一张跑一次 build，字型是增量的，随时能用。

## 已验证 / 未验证（2026-08-17）

### 已验证

用 `tools\make_fake_scan.py` 合成带**印刷灰范字＋灰格线＋2.3° 旋转＋透视变形＋渐变光照＋高斯噪声**
的假拍摄照，走完整管道。四种墨色浓淡 × 两种印刷灰深浅，**五个案例全过、exit 0**：

| 案例 | 墨色 | 范字灰 | glyphs | hollow | verify |
|---|---|---|---|---|---|
| ink25_guide208 | 25 | 208 | 97 | 0 | pass |
| ink90_guide208 | 90 | 208 | 97 | 0 | pass |
| ink120_guide208 | 120 | 208 | 97 | 0 | pass |
| ink90_guide185 | 90 | 185 | 97 | 0 | pass |
| worst | 130 | 180 | 97 | 0 | pass |

- 故意留空 3 格（一、着、后）＝ 侦测到的 3 格，**完全对上**。
- proof 图肉眼复核：字序正确、「国 回 面 有」中空正确、标点正确、句子可读。
- `--reverse-contours` 逃生口跑过，不崩。
- `tools\test_hollow_guard.py` 全过：空心侦测器在真实产出上 **0/97 误报**，
  在真实 bug 产出上 **97/97 命中**。
- `build-font.bat` 三条路径都实跑过：
  ①正常单张 → exit 0 出字型＋开 proof 图；
  ②空文件夹 → 拒跑并说清楚要怎么命名，不会硬建；
  ③两张照片 → 两个 `--sheet` 参数都正确组出（用 manifest 里没有的 S2 验证，
  python 正确点名 `sheet id 'S2' not in manifest`，`.bat` 接住 errorlevel 印 BUILD FAILED）。

### 2026-08-18 首次真手写照片（林子策，S1 全 100 格写满）

`scans\S1.jpg`（205 KB 手机拍/扫描）→ `build\LinHand.ttf`。

**墨色阈值一次就过，没调任何旋钮**：`--ink-thresh 150` 预设值直接吃下真墨水，
100/100 格全部读到、0 空格、0 失败、0 空心、`verify` 集合相等。
合成图调出来的参数在真纸上直接可用——**这是这条管道最值得记的一次验证**。

**但真照片暴露了一个合成图造不出来的问题：印刷格线会漏进裁切框。**

- manifest 已经把墨区从 17.8mm 格内缩到 16.6mm（每边 0.6mm），实测格线宽约 0.3mm，
  照理绰绰有余。**没用**——四角定位的透视校正会留几 px 系统性残差，
  实测 100 格里 **顶边 22 格、底边 2 格** 吃到线，左右 0（偏移是系统性的，不是随机）。
- 描出来的字每个带黑框／横线，而 `verify`／`glyphs`／`hollow` **三道全过**。
  又一次「数字全对、东西全错」，**只有 proof 图肉眼看得出来**。

修法在 `strip_frame()` ＋ `is_frame_fragment()` 两段，都默认开，`--keep-frame` 关掉：

1. **整行/整列贴边** 且填满 >70% → 清掉那一行/列。
   只在最外 6% 的带内动手，所以「一 二 三」写在格中央的横笔碰不到。
   实测：顶 22→0、底 2→0。
2. **断续的贴边线段**。斜切进来的竖格线**是断的**（实测「里」的右框survive 成好几段，
   没有一段够半格高），所以 **长度判据完全抓不到**（第一版写了 `>=50% 高`，`framed: 0`）。
   改成「blob 整个落在最外窄带内 ＋ 该轴向厚度 ≤8px」才抓到：`framed: 97 段 / 43 格`。
   ⚠️ **这条教训跟守卫常数那条同族：判据要按实测的残留形态挑，不是按你想像中的形态挑。**

反向证据（证明它不是乱杀）：**同一套逻辑跑合成图 `worst.jpg`，`framed: 0`**——
干净输入上零动作，97 glyphs／3 空格全对，exit 0。回归五条命令全部 exit 0。

### 真照片这一轮的已知边界

- **`--keep-frame` 是逃生口**：若哪天样张改用无格线设计，或某字确实有贴边细笔画被吃掉，用它关掉再比对 proof 图。
- 清框是**有损**操作，`framed` 那行会印出动了几段、哪几个字，**看到数字异常大就去看 proof 图**。

### 过程中抓到并修掉的两个真 bug（留档，别改回去）

1. **potracer 极性反了**。`Bitmap(True=ink)` 会把整格外框当图形、把字当挖空。
   实测：纯 True 方块 → 得到「整框 + 一个洞」；传 `~bmp` → 得到方块本身。
   已在 `trace_to_glyph` 传反向位图。
2. **打光归一化不能按格做**。`normalise()` 的模糊半径必须**远大于笔画宽度**；
   在约 200px 的单格上，半径落到笔画宽度同一量级，会把笔画内部normalise成背景，
   **笔画变成空心轮廓线**。已改成整页只做一次。
   ⚠️ 这个 bug 第 1、2 道验收**全过**，proof 图才看得出来——这就是第 3 道守卫存在的理由。

### 未验证 / 已知边界

- ~~真手写照片没跑过~~ **2026-08-18 已跑过，见下。**
- `--min-stroke 0.012` 这条线是按合成样本定的。0.5mm 笔约落在 0.015，还有余量；
  0.38mm 以下没测过。
- 只出 TTF，没做 OTF/CFF。
- 没做字距微调（kerning）——中文全角等宽，每字 advance 固定 1000，不需要。
- 半角拉丁字母、数字也会是全角宽度。要正常拉丁宽度得另外处理。
- 竖排（`vert`/`vrt2`）没做。
- 归一化用**格子边框**而不是墨迹外框——刻意的：这样每字的大小／高低差异会保留，
  才像手写；改成按墨迹居中会被压得整整齐齐，反而露馅。

---

# 第二条路：S-Pen 触屏采集（`spen/`）

**这不是纸笔那条的替代品，是另一套字型。** 触控笔写出来的是好看的手写风字型，
不是你握笔写在纸上的笔迹——两套并存，family name 分开就行。

**最大差别：配对是结构性精确的。** 页面告诉你写哪个字，笔画就存在那个码位底下，
不存在错位的可能。纸笔那条防了整整一轮的错位风险，这条路天生没有。
所以这条路上 proof 图看的是**字形好不好看**，不是**字对不对**。

也因此，纸笔那套机器全部不适用：没有定位标记、没有透视校正、没有打光归一化、
没有墨色阈值——几何是直接给的，不是从照片里还原的。

## 用法

```
python tools\make_spen_page.py --out spen --manifest template\manifest.json
python tools\spen_serve.py
```
第二条会印出一个网址。**平板／手机连同一个 WiFi，开那个网址**，用 S-Pen 写，
写完点「交出」，档案直接落到 `strokes\`。不用传档、不用拷 USB。

```
python tools\build_font_strokes.py --strokes strokes\strokes-<id>.json --out build\LinPen.ttf --family "Lin Pen"
```

⚠️ `spen_serve.py` 绑在所有网卡上，任何同网段的人都能 POST 进来。
**只在可信网络开，写完 Ctrl-C 关掉**，别一直挂着。
没服务器也能用：直接开 `spen/writer.html`，点「交出」会变成下载 json，再自己搬到 `strokes\`。

## 页面里有的东西

- 灰底范字，压过去写（跟纸张那套同一个逻辑）。
- **压感**：S-Pen 的力道会变成笔画粗细。没压感的设备（手指）自动退回等宽，
  并在 build 报告里点名是哪些字没压感。
- **防手掌**：一旦侦测到笔，之后所有手指触摸全部忽略。手掌压在屏幕上不会画出东西。
- **每写完一笔就存 localStorage**，关掉重开不会丢；重开会自动跳到第一个还没写的字。
- 撤一笔／清空／字表跳转／进度 `N / 100`。
- 换字表 = 换 localStorage key，旧的work不会跟新字表混在一起。

## 已验证（2026-08-18，真浏览器实测）

用合成 pointer 事件在真 Chrome 里驱动页面，逐项实测：

| 项目 | 结果 |
|---|---|
| 笔画捕获 | 9 点，座标正确 |
| 压感保留 | 0.8 → 0.5，确认有变化不是常数 |
| 码位↔字 | `cp === char.codePointAt(0)` 成立 |
| 防手掌 | 笔之后的触摸事件被忽略，笔画数不变 |
| 重开续写 | reload 后笔画与压感都在，且自动跳到「华」（南已写） |
| 撤一笔 | 最后一笔撤掉时整个字一起移除 |
| 交出 | POST 成功，回「已送到电脑：strokes-59ea78d1.json（3 字）」 |

服务器四条路径实测：GET 送页（11317 bytes）／POST 存档 200／
**重复档名不覆写**（自动 `-2`）／目录穿越 `../../evil.json` 拒收 400（全盘搜无此档）／
空 body 拒收 413／错路径 404。

**整条回路实跑通**：浏览器写字 → POST → 服务器落档 → `build_font_strokes.py` 出 .ttf，
3 字 `verify : cmap == captured set, counts agree`。

笔画转字型另用手工定义笔画的字测过（`make_fake_strokes.py`：一二三十口日田士 全直笔，
预期结果没有歧义）：8 字全出，proof 图 `口 日 田` 中空正确，
`verify : cmap == captured set, counts agree`。

### 这条路上修掉的两件事

1. **纸笔那条的 `MIN_STROKE_FRAC = 0.012` 不能照搬**。它是按 199px 照片格子калиб 的，
   拿来卡 1000 单位的笔画箱，**每一个正确的采集都会被误判**（实测 0.0095）。
   已换成自校准检查：断言「光栅化出来的宽度 == 采集声明的宽度」
   （预期中位数 ≈ `base_w/(4*box)`，容许 0.6~2.5 倍）。
   **教训：守卫常数不能跨几何尺度搬，会变成误报。**
2. **Windows stdout 预设 cp1252，print 中文直接 UnicodeEncodeError 崩掉整个程序**
   （服务器就是印「交出」两个字崩的）。八个脚本全部补上
   `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`。

### 这条路未验证

- **真 S-Pen 没碰过**——上面全是合成 pointer 事件。真笔的压感曲线、取样密度、
  以及 Samsung 的笔迹平滑，都可能跟合成事件不同。
- 笔画是先光栅化再描（不是直接算变宽度外框）。这里没有打光、没有阈值、没有透视，
  所以那些坑不适用；代价约 0.5 个字型单位的量化误差。
- `--base-width 45` 是按「0.8mm 笔在 17.8mm 格」换算的，让两条路的字重可比。
  真写起来嫌粗嫌细就调它，页面和 build 两边要同一个值（值会写进采集档，build 自动读）。

---

## 回归自检（改了代码就跑这几条，全部要 exit 0）

```
python tools\test_hollow_guard.py
python tools\make_fake_scan.py --manifest template\manifest.json --sheet S1 --out test\thresh\worst.jpg --ink-fill 130 --guide-tint 180
python tools\build_font.py --manifest template\manifest.json --sheet S1=test\thresh\worst.jpg --out test\thresh\worst.ttf --family "T worst"
python tools\make_fake_strokes.py --out test\fake_strokes.json
python tools\build_font_strokes.py --strokes test\fake_strokes.json --out test\FakePen.ttf --family "Fake Pen"
```
`test\` 底下的产物（`fake_S1.jpg`、`thresh\worst.jpg`、各 ttf 与 proof png）是回归基线，**别删**——
`test_hollow_guard.py` 的 Part B 要用 `thresh\worst.jpg` 当 fixture。
