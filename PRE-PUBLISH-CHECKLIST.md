# 开源前置检查清单（推public前必看，别跳过）

这份 staging 目录（`D:\yz1000-opensource\`）是从 `D:\handwriting-font\` 挑出来的**干净子集**，
只含代码/方法论/空白字帖模板，已排除所有真人笔迹图像与最终字体档。

## 已排除，且不建议改变主意

以下内容**没有**复制进这个目录，理由是：一旦推上公开 GitHub，git 历史会永久留存，
即使日后删除也无法真正收回：

- `scans/`、`scans-liujiarui/`、`test/batscans/` — 真人手写拍照原图
- `spen/`、`strokes/` — S-Pen 采集的真迹笔画数据
- `build/` 整个目录 — 编译好的 .ttf 字体档（含 `0005MissHo-full.ttf`、`0010Phoon-full.ttf` 等，
  这些字体档本身就是能用真人笔迹写任何文字的工具，公开=仿冒风险，跟版权无关，是另一层风险）、
  proof 图、debug 裁图、`0010Phoon_TEST_merged_donor_DO_NOT_DISTRIBUTE.ttf`（原档名已自带警告）
- `Request and Feedback/` — 参与者的私人 PDF 与感谢信文字稿
- `kaggle/*/results-*/outputs/`、`kaggle/*/finetune-data/`、`kaggle/*/fonts/` — 训练/生成产出的
  真迹衍生图像
- `手写.pptx`、`D:handwriting-fontbuild_check_out.txt` — 未逐一核实内容，默认排除

## 已包含

- `tools/*.py` — 全部字体工程脚本
- `kaggle/**/*.py`、`kernel-metadata.json` — Kaggle 调度脚本（不含数据/产出）
- `chars-*.txt`、`donor-target-charset.txt`、`template-v2-chars.txt` — 字表定义，纯文字无个资
- `template/`、`template-1k/`、`template-latin-punct/`、`template-v2/` — 空白字帖模板
  （HTML/PDF/manifest/preview，未核实 preview 图是否为空白格线渲染 vs 真迹填写，
  推public前建议肉眼开一张确认）
- `README.md` — 沿用原档，已扫描过没有除本人外的真实姓名
- `LICENSE` — 新建，MIT，著作权人：林子策

## 还没做、推public前必须决定

1. **GitHub 账号**：确认/建好用 `lee666eel@gmail.com` 注册的个人账号，仓库建在这个账号下，
   不是 `nanhwappd` 组织
2. **template preview 图**肉眼抽查一张，确认不是真迹填写样本
3. **要不要跟何小姐／0010Phoon 打个招呼**：星洲日报讲座已公开"有人手写笔迹被数码化"这件事，
   但发布方法论代码是否要提前告知她们一声，你自己拿主意，不是必须但是个礼貌
4. **License 确认**：目前默认 MIT（最大化传播，任何人可自由使用/修改/商用，只要求保留署名），
   如果想要求衍生项目也必须开源（GPL 系）要在推之前换，推了之后改 license 不能溯及既往版本
5. 以上全部确认后，才在这个目录 `git init` + 推到你个人账号新仓库 —— 这一步我不会自己动手，
   等你明确说"推"才做
