# 小组 Beamer 学术汇报模板

16:9 横版，白底、深蓝标题和蓝色强调。全组使用同一份 Beamer / LaTeX 源文件，导出 PDF 演示；版式统一在 `preamble.tex` 中设置，各成员编辑自己的论文章节。

当前按录屏讲解调整为 10pt 基准字号，正文行距系数 1.12，默认表格行距系数 1.15，并为正文与来源脚注保留独立留白。标题与章节页字号也相应收敛；表格后的解释文字留出明确间隔。

[仓库 PDF 预览](preview.pdf)目前仍是 #54 的 61 页旧快照，未反映已合入的 Hindsight。最新源码、待审模块及 PDF 中文兼容状态见下方进度说明；整合后需重新编译、检查并同步预览。

## 结构与时间

| 环节 | 文件 | 讲解安排 |
| --- | --- | --- |
| 开场 | `sections/00-opening.tex` | 主题、共同问题和路线，约 3 分钟 |
| StructMem | `sections/01-structmem.tex` | 7–9 分钟；已迁入本地既有演示稿正文和讲稿备注 |
| Hindsight | `sections/02-hindsight.tex` | 8 分钟讲解稿已整理，9 页个人模块已编译；录制前由本人过稿并计时；[个人PDF](hindsight-preview.pdf)、[讲稿](../scripts/02-hindsight-8min.md) |
| Semantic XPath | `sections/03-semantic-xpath.tex` | oioioi-521；13 页模块已在 [PR #57](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/57) 提交，待审核合入；旧视频暂按本次未交付计 |
| HyMEM | `sections/04-hymem.tex` | 7 页模块和个人材料已合入，待本人过稿、排练及录制；[个人PDF](hymem-preview.pdf)、[个人指南](../hymem-reading-guide.md)；中文显示修复由 [#62](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/62) 跟踪 |
| MetaMem | `sections/05-metamem.tex` | YaoYang-123456；#40 原模块已合入，[PR #63](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/63) 新交 8 页修订稿及中文兼容 PDF，待 F 审核；核心稿估计 7 分 59 秒，本人尚未实际计时或录制 |
| Text2Mem | `sections/06-text2mem.tex` | ngocnamd93-spec；8 页模块已在 [PR #59](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/59) 提交，待审核合入；本人过稿、排练及录制按 [#56](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/56) 推进 |
| 系统性总结 | `sections/07-synthesis.tex` | 10–15 分钟，先保留结构，待个人部分完成后共同填写 |
| 备用资料 | `sections/99-backup.tex` | 问答时按需使用，不计入正文页码；已迁入 StructMem 备用页 |

默认分配为 **3＋6×8＋12＝63 分钟**。若六人分别使用 7–9 分钟、总结使用 10–15 分钟，在开场 3 分钟的条件下，总长约 55–72 分钟，不含额外问答。需要控制在 60 分钟时，采用 **2＋6×8＋10＝60 分钟**，并更新开场时间页和讲稿备注。页数只作内容组织参考，最终以排练计时为准。

截至北京时间 2026-10-26 21:48，主分支 `1850da7` 已有 StructMem、Hindsight、HyMEM、MetaMem 四篇材料；Semantic XPath #57、Text2Mem #59 初稿和 MetaMem #63 修订稿待 F 审核。六篇均有稿件记录。此前 17 页报告 / 68 页幻灯片仅是旧主分支加 #57/#59 的本地预览，已不代表最新合稿。#63 作者报告的 14 / 64 页也未包含 #57/#59，不当作当前完整组稿。本人计时、视频、字体兼容和后续安排见[平时作业进度](../README.md#当前进展2026-10-26)。

## 编辑方式

主文件为 `main.tex`，按“开场 → 六人讲解 → 系统性总结 → 备用资料”顺序输入各模块。每位成员填写章节页的讲解人，并只修改自己的 `.tex` 和相应图片，按 issue 认领范围协作。共享样式和开场、总结由相关成员集中整合。

待填写的论文模块各提供章节页与六张正文页：研究问题、整体流程、关键机制、实验设置、关键结果、局限与阅读判断。可按内容增加、合并或拆分页面，不要求机械填满固定页数。StructMem 沿用已有约 9 分钟讲解版本，作为有实际内容的示例。

现有综合总结页只提供对照表、机制取舍、共同案例、实验可比性和小组结论的版式，不填入尚未讨论的结论，也不自动导入报告的综合分析草稿。

### 来源、图表与讲稿

- 每页围绕一个问题或结论，优先保留足够大的图表及其解释；拥挤时拆页，避免只缩小字号。
- `\source{原文位置}` 设置当前页及后续页的来源脚注。换图、换表或换证据时更新，注明原论文页码 / 图表编号；自己的推测和实验分别标明。
- 图表优先保留为 LaTeX 表格、TikZ 或 PGFPlots；引用论文图可放入按需创建的 `images/`，保留比例和来源。示例插图命令已经以注释形式放在方法页。
- `\note{讲稿或时间提示}` 附在对应页面。当前默认隐藏备注；需要演讲者视图时，将 `preamble.tex` 中 `hide notes` 改为 `show notes on second screen=right`，输出变为“幻灯片在左、备注在右”的双屏 PDF。分享或提交前恢复 `hide notes`。
- 备用页使用 `[noframenumbering]`，不挤占正文页码。将不影响主线的参数、补充实验和长案例移入该部分。

### 个人模块预览

在 `main.tex` 的 `\begin{document}` 前启用一行：

```tex
\includeonlylecture{structmem}
```

可用模块名为 `opening`、`structmem`、`hindsight`、`semantic-xpath`、`hymem`、`metamem`、`text2mem`、`synthesis`、`backup`。个人预览结束后注释掉该行，恢复全组导出。Hindsight 和 HyMEM 都有独立预览入口，可直接编译个人模块而不改动全组主文件。Hindsight 预览 PDF 为 9 页，大小 208,722 字节，SHA-256 为 `e0b443a40ca858d5f19f9b01f2ca9644c848a991a0abf95eeacbf9d0716dd88b`。

## 编译

需要支持中文的 TeX Live、XeLaTeX、latexmk、Beamer、TikZ 和 PGFPlots；字体使用 TeX Live 自带的 Fandol。进入本目录执行：

```sh
latexmk -xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
cp ../../../output/homework-slides/main.pdf preview.pdf
```

生成文件为仓库根目录下 `output/homework-slides/main.pdf`，编译缓存也写入该忽略目录。定稿后将 PDF 复制为 `reports/homework/8队-结构化记忆-实际日期-slides.pdf`，与阅读报告 PDF 和视频一同整理。共享 LaTeX 源文件直接保留在仓库中。
