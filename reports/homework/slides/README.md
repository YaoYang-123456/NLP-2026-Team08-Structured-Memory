# 小组 Beamer 学术汇报模板

16:9 横版，白底、深蓝标题和蓝色强调。全组使用同一份 Beamer / LaTeX 源文件，导出 PDF 演示；版式统一在 `preamble.tex` 中设置，各成员编辑自己的论文章节。

当前按录屏讲解调整为 10pt 基准字号，正文行距系数 1.12，默认表格行距系数 1.15，并为正文与来源脚注保留独立留白。标题与章节页字号也相应收敛；表格后的解释文字留出明确间隔。

[当前 PDF 预览](preview.pdf)随源码保存，便于直接查看版式。它仍是工作模板，其他成员的个人部分和共同总结尚待填写；修改后重新编译并同步预览。

## 结构与时间

| 环节 | 文件 | 讲解安排 |
| --- | --- | --- |
| 开场 | `sections/00-opening.tex` | 主题、共同问题和路线，约 3 分钟 |
| StructMem | `sections/01-structmem.tex` | 7–9 分钟；已迁入本地既有演示稿正文和讲稿备注 |
| Hindsight | `sections/02-hindsight.tex` | 7–9 分钟，待对应成员填写 |
| Semantic XPath | `sections/03-semantic-xpath.tex` | 7–9 分钟，待对应成员填写 |
| HyMEM | `sections/04-hymem.tex` | 7页材料已编译并检查版式，待本人过稿、排练及录制；[个人PDF](hymem-preview.pdf)、[个人指南](../hymem-reading-guide.md) |
| MetaMem | `sections/05-metamem.tex` | YaoYang-123456；材料已由 PR #40 合入，待本人过稿、计时及录制；[任务 #39](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/39) |
| Text2Mem | `sections/06-text2mem.tex` | ngocnamd93-spec 已认领，7–9 分钟模块待交稿；[任务 #56](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/56) |
| 系统性总结 | `sections/07-synthesis.tex` | 10–15 分钟，先保留结构，待个人部分完成后共同填写 |
| 备用资料 | `sections/99-backup.tex` | 问答时按需使用，不计入正文页码；已迁入 StructMem 备用页 |

默认分配为 **3＋6×8＋12＝63 分钟**。若六人分别使用 7–9 分钟、总结使用 10–15 分钟，在开场 3 分钟的条件下，总长约 55–72 分钟，不含额外问答。需要控制在 60 分钟时，采用 **2＋6×8＋10＝60 分钟**，并更新开场时间页和讲稿备注。页数只作内容组织参考，最终以排练计时为准。

截至北京时间 2026-10-26 14:25，Semantic XPath 已在 [PR #57](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/57) 提交 13 页个人模块，尚待 F 审核合入，因此上表对应的主分支文件仍为占位。作者确认视频已录制 8 分 55 秒，视频文件尚未交验。主分支当前预览为 61 页，PR 内候选为 67 页；其余材料和视频状态见[平时作业进度](../README.md#当前进展2026-10-26)。

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

可用模块名为 `opening`、`structmem`、`hindsight`、`semantic-xpath`、`hymem`、`metamem`、`text2mem`、`synthesis`、`backup`。个人预览结束后注释掉该行，恢复全组导出。HyMEM另有 `hymem-preview.tex`，可直接编译个人模块而不改动全组主文件；当前状态见[个人指南](../hymem-reading-guide.md)。

## 编译

需要支持中文的 TeX Live、XeLaTeX、latexmk、Beamer、TikZ 和 PGFPlots；字体使用 TeX Live 自带的 Fandol。进入本目录执行：

```sh
latexmk -xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
cp ../../../output/homework-slides/main.pdf preview.pdf
```

生成文件为仓库根目录下 `output/homework-slides/main.pdf`，编译缓存也写入该忽略目录。定稿后将 PDF 复制为 `reports/homework/8队-结构化记忆-实际日期-slides.pdf`，与阅读报告 PDF 和视频一同整理。共享 LaTeX 源文件直接保留在仓库中。
