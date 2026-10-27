# 报告文字与版式修订（2026-10-27）

基线：`97bd3c388b3105009e30d5c2ec37e3c3e3b9bb25`。任务 [#65](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/65)，交付 PR [#66](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/66)。

## 成稿

- [主报告](report-preview.pdf)：20页。
- [Semantic XPath](semantic-xpath-preview.pdf)：3页；[HyMEM](hymem-reading-report.pdf)：2页；[MetaMem](metamem-reading-report.pdf)：2页；[Text2Mem](text2mem-report-preview.pdf)：2页。
- [文件清单](report-style-artifacts.json)记录源码、PDF、模板的大小及SHA-256。五份PDF均小于20 MB。

摘要、背景、六篇章节、跨论文比较与总结统一为机制、证据、结果和局限的直接叙述。删除反复声明未复现、不得如何解读、尚非共识等审核式文字，以及个人任务交接状态。必要的模型、数据、预算与指标条件融入分析。

正文仅保留六篇首次出现时的上标引用，文末保留六条文献。原文页码和图表定位保存在源码注释中。StructMem与Hindsight图表改用模板的题注和自动编号，共23张表、2幅图；调整结果表与解释段落的位置，参考文献整体排在末页。

沿用`jos.cls`与`jos.bst`，未修改模板字体、字号、页边距和标题层级。成员贡献段落与基线逐字一致。Slides、讲稿与参考文献数据库未改。

## 实际验证

- 在`reports/homework/`运行latexmk / XeLaTeX，主入口与四个个人入口均成功。
- 五份PDF共29页，全部通过不配置外部CMap的PDF.js中文提取及渲染，并检查版式。无裁切、叠字、缺字或孤立表格页。
- 五份PDF补充Unicode映射前后的每页PDFium渲染在1.5倍比例下逐像素一致。
- 无Overfull、Underfull hbox或未定义引用。主报告保留3条Underfull vbox及数学字体尺寸替代提示；对应页面已检查，四份个人报告无上述排版警告。
- 五篇的数值表格行与基线逐项一致；Hindsight六项主结果保持一致，原表中的参照系统数值移入正文。
- 核对六处首次引用、23个表题、2个图题、公式及中文；确认正文没有原文位置串、灰色说明或重复免责句。
- `git diff --check`通过，文件UTF-8/LF、清单大小与哈希经核对。

PR沿用YaoYang-123456集中审核整组交付。贡献比例留空；视频状态和实际计时另按README跟踪。
