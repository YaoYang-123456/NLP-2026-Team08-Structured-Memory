# 小组 Beamer 学术汇报模板

16:9 横版，白底、深蓝标题和蓝色强调。全组使用同一份 Beamer / LaTeX 源文件，导出 PDF 演示；版式统一在 `preamble.tex` 中设置，各成员编辑自己的论文章节。

当前按录屏讲解调整为 10pt 基准字号，正文行距系数 1.12，默认表格行距系数 1.15，并为正文与来源脚注保留独立留白。标题与章节页字号也相应收敛；表格后的解释文字留出明确间隔。

[仓库 PDF 预览](preview.pdf)已于 2026-10-27 更新为 73 页（正文 69 页＋备用 4 页），包含六篇个人模块与补齐的开场、跨论文比较和总结。已通过编译、版式及 PDF.js 无外部 CMap 全页中文检查，详见[共同部分检查](../shared-sections-check-20261027.md)。

## 结构与时间

| 环节 | 文件 | 讲解安排 |
| --- | --- | --- |
| 开场 | `sections/00-opening.tex` | 主题、共同问题和路线，计划 2 分钟，3 页备注齐全 |
| StructMem | `sections/01-structmem.tex` | hycx233；12 页模块和备注，待本次实际计时及录制 |
| Hindsight | `sections/02-hindsight.tex` | 8 分钟讲解稿已整理，9 页个人模块已编译；录制前由本人过稿并计时；[个人PDF](hindsight-preview.pdf)、[讲稿](../scripts/02-hindsight-8min.md) |
| Semantic XPath | `sections/03-semantic-xpath.tex` | #57 已审核合入，13 页；[个人PDF](semantic-xpath-preview.pdf)、[个人指南](../semantic-xpath-reading-guide.md)；旧视频按本次未交付计 |
| HyMEM | `sections/04-hymem.tex` | 7 页模块和个人材料已合入，待本人过稿、排练及录制；[个人PDF](hymem-preview.pdf)、[个人指南](../hymem-reading-guide.md)；个人 PDF 中文显示修复 [#64](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/64) 已合入，#62 已结项 |
| MetaMem | `sections/05-metamem.tex` | #63 已审核合入，8 页；[个人PDF](metamem-preview.pdf)、[交接与完整讲稿](../metamem-handoff.md)；7 分 59 秒为估时 |
| Text2Mem | `sections/06-text2mem.tex` | #59 已审核合入，8 页；[个人PDF](text2mem-preview.pdf)、[个人指南](../text2mem-reading-guide.md)；480 秒为计划，待本人过稿、计时及录制 |
| 系统性总结 | `sections/07-synthesis.tex` | 9 页比较与总结已补齐，计划 10 分钟，待集中审核 |
| 备用资料 | `sections/99-backup.tex` | 问答时按需使用，不计入正文页码；已迁入 StructMem 备用页 |

当前计划为 **2＋6×8＋10＝60 分钟**，不含额外问答。开场和总结的 12 页备注分别合计 120 秒、600 秒，并整理为[可独立阅读的讲稿](../scripts/00-opening-and-synthesis.md)。这些是计划时长，页数也只作内容组织参考，最终以本人排练计时为准。

六篇模块均已审核接入。正文页序：开场 1–3；StructMem 4–15；Hindsight 16–24；Semantic XPath 25–37；HyMEM 38–44；MetaMem 45–52；Text2Mem 53–60；总结与讨论 61–69；备用 70–73。本人计时、视频及贡献说明继续见[平时作业进度](../README.md#当前进展2026-10-27)。

## 编辑方式

主文件为 `main.tex`，按“开场 → 六人讲解 → 系统性总结 → 备用资料”顺序输入各模块。每位成员填写章节页的讲解人，并只修改自己的 `.tex` 和相应图片，按 issue 认领范围协作。共享样式和开场、总结由相关成员集中整合。

六篇论文章节现均有实质内容，页数依讲解需要分别为 12、9、13、7、8、8 页。StructMem 与 Semantic XPath 页数较多，实际讲解仍需按 7–9 分钟控制，不能根据页数推定已完成排练。

综合部分已补齐六篇对照、机制联系与代价、行程变更案例、实验可比性、既定课设选择和三点结论。与报告采用同一证据和边界，明确区分作者结果、阅读分析及自拟案例；这些内容仍待相关成员集中审核，不声称已经完成团队讨论。

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

可用模块名为 `opening`、`structmem`、`hindsight`、`semantic-xpath`、`hymem`、`metamem`、`text2mem`、`synthesis`、`backup`。个人预览结束后注释掉该行，恢复全组导出。Hindsight、Semantic XPath、HyMEM、MetaMem 和 Text2Mem 均有独立预览入口；文件版本见各个人交接清单。

## 编译

需要支持中文的 TeX Live、XeLaTeX、latexmk、Beamer、TikZ、PGFPlots，以及安装 pypdf 的 Python；字体使用 TeX Live 自带的 Fandol。进入本目录执行：

```sh
latexmk -xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
python3 ../../../scripts/fix_hymem_pdf_unicode.py ../../../output/homework-slides/main.pdf preview.pdf
```

导出步骤复用现有 Unicode 映射脚本，为缺少 ToUnicode 的 Adobe-GB1 / Identity-H 字体补映射，避免 PDF.js 未配置外部 CMap 时缺中文。该脚本也适用于全组 PDF；保留原始编译输出以便核对。

生成文件为仓库根目录下 `output/homework-slides/main.pdf`，编译缓存也写入该忽略目录。定稿后将 PDF 复制为 `reports/homework/8队-结构化记忆-实际日期-slides.pdf`，与阅读报告 PDF 和视频一同整理。共享 LaTeX 源文件直接保留在仓库中。
