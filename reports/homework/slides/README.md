# 小组 Beamer 学术汇报模板

16:9 横版，白底、深蓝标题和蓝色强调。全组使用同一份 Beamer / LaTeX 源文件，导出 PDF 演示；版式统一在 `preamble.tex` 中设置，各成员编辑自己的论文章节。

当前按视频讲解调整为 10pt 基准字号，正文行距系数 1.12，默认表格行距系数 1.15。页脚仅保留章节、讲解人和页码。标题与章节页字号也相应收敛；表格后的解释文字留出明确间隔。

[仓库 PDF 预览](preview.pdf)已于 2026-10-27 更新为 68 页，包含六篇个人模块与补齐的开场、跨论文比较和总结。已通过编译、版式及 PDF.js 无外部 CMap 全页中文检查，详见[演示修订检查](style-check-20261027.md)。

## 结构与时间

| 环节 | 文件 | 讲解安排 |
| --- | --- | --- |
| 开场 | `sections/00-opening.tex` | 主题、共同问题和路线，计划 2 分钟，3 页备注齐全 |
| StructMem | `sections/01-structmem.tex` | hycx233；12 页模块和备注，待本次实际计时及录制 |
| Hindsight | `sections/02-hindsight.tex` | 8 分钟讲解稿已整理，9 页个人模块已编译；录制前由本人过稿并计时；[个人PDF](hindsight-preview.pdf)、[讲稿](../scripts/02-hindsight-8min.md) |
| Semantic XPath | `sections/03-semantic-xpath.tex` | #57 已审核合入，移除参考资料页后为12页；[个人PDF](semantic-xpath-preview.pdf)、[个人指南](../semantic-xpath-reading-guide.md)；旧视频按本次未交付计 |
| HyMEM | `sections/04-hymem.tex` | 7 页模块及 #67 七段录音稿已审核，待本人过稿、排练及录音；[个人PDF](hymem-preview.pdf)、[录音指南](../hymem-recording-guide.md)、[讲稿](../scripts/04-hymem-recording.md) |
| MetaMem | `sections/05-metamem.tex` | #63 已审核合入，8 页；[个人PDF](metamem-preview.pdf)、[交接与完整讲稿](../metamem-handoff.md)；讲稿已修订，待重新计时 |
| Text2Mem | `sections/06-text2mem.tex` | #59 已审核合入，8 页；[个人PDF](text2mem-preview.pdf)、[个人指南](../text2mem-reading-guide.md)；480 秒为计划，待本人过稿、计时及录制 |
| 系统性总结 | `sections/07-synthesis.tex` | 9 页比较与总结已补齐，计划 10 分钟，已通过 #66 集中审核 |

当前计划为 **2＋6×8＋10＝60 分钟**，不含额外问答。开场和总结的 12 页备注分别合计 120 秒、600 秒，并整理为[可独立阅读的讲稿](../scripts/00-opening-and-synthesis.md)。这些是计划时长，页数也只作内容组织参考，最终以本人排练计时为准。

六篇模块均已审核接入。正文页序：开场 1–3；StructMem 4–15；Hindsight 16–24；Semantic XPath 25–36；HyMEM 37–43；MetaMem 44–51；Text2Mem 52–59；总结与讨论 60–68。本人计时、音频与翻页时间表及贡献说明继续见[平时作业进度](../README.md#当前进展2026-10-27)。

录制时每人连续录完自己的模块，再按最终音频填写全组页码和实际翻页时间点；由组长用统一幻灯片画面合成视频。具体交接方式见[接下来的交付](../README.md#接下来的交付)。

## 编辑方式

主文件为 `main.tex`，按“开场 → 六人讲解 → 系统性总结”顺序输入各模块。每位成员填写章节页的讲解人，并只修改自己的 `.tex` 和相应图片，按 issue 认领范围协作。共享样式和开场、总结由相关成员集中整合。

六篇论文章节现均有实质内容，页数依讲解需要分别为 12、9、12、7、8、8 页。StructMem 与 Semantic XPath 页数较多，实际讲解仍需按 7–9 分钟控制，不能根据页数推定已完成排练。

综合部分已补齐六篇对照、机制联系与代价、行程变更案例、实验可比性、既定课设选择和三点结论。与报告采用同一证据和边界，明确区分作者结果、阅读分析及自拟案例；这些内容已由 YaoYang-123456 在 #66 集中审核。

### 文字、图表与讲稿

- 每页围绕一个问题或结论。有效的条件与局限用正常正文说明，删除重复的免责句、审核提醒和交接过程；标题、术语与指标单位保持一致。
- 图表与文字保留足够字号和留白；拥挤时先精简措辞，再调整布局。
- 演示不显示逐页文献脚注。原文位置保留在 `.tex` 的 `% 来源：` 注释中，详细引用见报告；教学案例在标题或正文中简短标明。
- 图表优先保留为 LaTeX 表格、TikZ 或 PGFPlots；引用论文图可放入按需创建的 `images/`，保留比例和来源。示例插图命令已经以注释形式放在方法页。
- `\note{讲稿或时间提示}` 附在对应页面。当前默认隐藏备注；需要演讲者视图时，将 `preamble.tex` 中 `hide notes` 改为 `show notes on second screen=right`，输出变为“幻灯片在左、备注在右”的双屏 PDF。分享或提交前恢复 `hide notes`。

### 个人模块预览

在 `main.tex` 的 `\begin{document}` 前启用一行：

```tex
\includeonlylecture{structmem}
```

可用模块名为 `opening`、`structmem`、`hindsight`、`semantic-xpath`、`hymem`、`metamem`、`text2mem`、`synthesis`。个人预览结束后注释掉该行，恢复全组导出。Hindsight、Semantic XPath、HyMEM、MetaMem 和 Text2Mem 均有独立预览入口；五份个人演示已同步本轮措辞和样式，当前版本统一见[演示清单](style-artifacts.json)；旧交接清单保留原验收记录。

## 编译

需要支持中文的 TeX Live、XeLaTeX、latexmk、Beamer、TikZ、PGFPlots，以及安装 pypdf 的 Python；字体使用 TeX Live 自带的 Fandol。进入本目录执行：

```sh
latexmk -xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
python3 ../../../scripts/fix_hymem_pdf_unicode.py ../../../output/homework-slides/main.pdf preview.pdf
```

导出步骤复用现有 Unicode 映射脚本，为缺少 ToUnicode 的 Adobe-GB1 / Identity-H 字体补映射，避免 PDF.js 未配置外部 CMap 时缺中文。该脚本也适用于全组 PDF；保留原始编译输出以便核对。

生成文件为仓库根目录下 `output/homework-slides/main.pdf`，编译缓存也写入该忽略目录。定稿后将 PDF 复制为 `reports/homework/8队-结构化记忆-实际日期-slides.pdf`，与阅读报告 PDF 和视频一同整理。共享 LaTeX 源文件直接保留在仓库中。
