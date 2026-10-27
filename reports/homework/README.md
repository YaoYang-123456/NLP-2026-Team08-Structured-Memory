# 小组平时作业

第 8 队的 6 名成员共同完成“长上下文场景结构化记忆建模”专题阅读，与课设共用本仓库的六篇论文、笔记和引用。每人先负责一篇论文，再共同形成系统性比较；阅读结论用于课设选型与实验分析，课设中的真实发现可反过来补充讨论。个人阅读和讲解是小组材料的一部分。

## 提交与讲解

依据[老师的新通知](../../docs/course/262701NLP-平时作业提交验收说明-2026-文字版.md)：

- 提交截止：**2026 年 11 月 1 日 23:59**。
- 本组属于专题类课设，准备一份系统性阅读报告、一份 PPT、一个讲解视频；总时长按队伍人数 × 10 分钟，本组 6 人约 60 分钟。
- 报告和汇报注明各成员分工及贡献百分比；个人额外整理可一并保留。
- 具体讲解时间最早预计 11 月 2 日，以老师后续安排为准。

本组报告统一使用 **LaTeX 写作、PDF 交付**，演示材料使用 [Beamer 模板](slides/README.md)并导出 PDF；[官方 Word 样例](../../docs/course/软件学报排版样例2025年版.doc)只作报告版式参考。

## 当前进展（2026-10-27）

六篇个人论文章节、摘要、背景、跨论文比较、总结及对应讲稿已补齐。整份报告 20 页，演示 68 页；[#66](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/66) 已由 YaoYang-123456 完成集中技术审核并批准，本轮同步修正 ESR 的计数口径。个人录音、实际翻页点与最终视频仍待交付。共同整理任务见 [#65](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/65)。

| 论文 | 阅读负责人 | 已整合材料 | 本人过稿与录音状态 |
| --- | --- | --- | --- |
| StructMem | hycx233 | #15 报告、12 页模块和备注 | 尚无本次录制及实测时长登记 |
| Hindsight | onlysonder | #60 报告、9 页模块和[8 分钟讲稿](scripts/02-hindsight-8min.md) | 待本人过稿、实际计时及音频与翻页时间表交付 |
| Semantic XPath | oioioi-521 | #57 报告、12 页模块、[个人指南](semantic-xpath-reading-guide.md)；已修复个人 PDF 中文映射 | **本次视频未交付**；8 分 55 秒为旧录制，待 F 核看当前幻灯片衔接、风格和音画后决定能否复用；[#55](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/55) 保持开放 |
| HyMEM | lanshuheng9-oss | #54 正文、#61 个人材料、#64 中文 PDF 修复均已合入；7 页模块，[个人指南](hymem-reading-guide.md) | #62 已结项；[#53](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/53) 保留本人过稿、计时和录制 |
| MetaMem | YaoYang-123456 | #40 正文及 #63 修订已合入；8 页模块、规则示例、[完整讲稿与交接](metamem-handoff.md) | [#39](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/39) 保持开放；讲稿已修订，待本人重新计时 |
| Text2Mem | ngocnamd93-spec | #59 报告、8 页模块、[阅读与讲稿指南](text2mem-reading-guide.md)；已修复个人 PDF 中文映射 | [#56](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/56) 保留本人过稿、计时及录制；480 秒为计划 |

### 当前整合预览与检查

- [整份报告 PDF](report-preview.pdf)：**20 页**；[整份幻灯片 PDF](slides/preview.pdf)：**68 页，已移除备用页和独立参考资料页**。10 月 27 日已完成共同部分及全组 report / slides 的文字整理，已通过 PR #66 集中技术审核。
- 报告统一摘要、背景、六篇章节、比较与总结的行文；删除重复自我辩解、交接状态和可见原文位置，保留六处首次引用与文末文献。图表使用软件学报模板的自动编号和题注，实验数据保持一致。
- 开场 3 页、综合 9 页均已填写逐页备注，并提供[独立讲稿](scripts/00-opening-and-synthesis.md)。计划采用 **2＋6×8＋10＝60 分钟**；这不是实际排练记录。
- 主报告与四份个人报告均通过 latexmk / XeLaTeX，共 29 页完成 PDF.js 中文提取、渲染和版面检查。无 Overfull、Underfull hbox、缺字或未定义引用；主报告保留 3 条 Underfull vbox 及数学字体尺寸替代提示。补 Unicode 映射前后 PDFium 画面一致，软件学报模板未改。
- 最新报告验证见[报告修订检查](report-style-check-20261027.md)及[报告清单](report-style-artifacts.json)，slides 验证见[演示修订检查](slides/style-check-20261027.md)及[演示清单](slides/style-artifacts.json)。[整合清单](integration-artifacts.json)记录当前入口；早期检查保留对应版本记录。

### 接下来的交付

1. 确认封面成员、实际定稿日期、开场/总结讲解人。**贡献比例按本轮要求暂留空**，最终按实际工作填写并合计 100%。
2. 每人完整录制自己的模块，提交一份连续音频及实际翻页时间表；开场和总结采用同样方式。页码使用统一 68 页演示的全组页码，时间以该音频开头为零点。音频经过剪辑后，按最终文件重新核对时间点，最后一页保持到音频结束。
3. 收集各段实测时长，按约 60 分钟的整体安排检查语速与衔接，再用统一幻灯片画面合成视频。Semantic XPath 旧视频仍按本次未交付计，是否复用另行核看。
4. 整理最终报告、幻灯片、视频版本和上传记录。

10 月 22 日研讨阶段已结项：[PR #52](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/52) 已合入，[#19](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/19) 与 [#31](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/31) 已关闭；11 月 1 日的阅读报告、约 60 分钟视频及课程上传仍按本页跟踪。

## 个人阅读材料

| 论文 | 报告 | 演示 | 讲稿与说明 |
| --- | --- | --- | --- |
| StructMem | [共享章节](sections/01-structmem.tex) | [共享模块](slides/sections/01-structmem.tex) | 逐页 Beamer 备注 |
| Hindsight | [共享章节](sections/02-hindsight.tex) | [个人 PDF](slides/hindsight-preview.pdf) | [8 分钟讲稿](scripts/02-hindsight-8min.md) |
| Semantic XPath | [3 页 PDF](semantic-xpath-preview.pdf) | [12 页 PDF](slides/semantic-xpath-preview.pdf) | [个人指南](semantic-xpath-reading-guide.md) |
| HyMEM | [2 页 PDF](hymem-reading-report.pdf) | [7 页 PDF](slides/hymem-preview.pdf) | [个人指南](hymem-reading-guide.md) |
| MetaMem | [2 页 PDF](metamem-reading-report.pdf) | [8 页 PDF](slides/metamem-preview.pdf) | [交接与完整讲稿](metamem-handoff.md) |
| Text2Mem | [2 页 PDF](text2mem-report-preview.pdf) | [8 页 PDF](slides/text2mem-preview.pdf) | [个人指南](text2mem-reading-guide.md) |

个人材料与历史编译清单分别保留；最新整合报告和演示以本页的整合清单为准。本人过稿、实际计时、录制及课程提交仍按上表状态推进。

## 共同编辑

`main.tex` 是阅读报告入口，`sections/01-structmem.tex` 至 `sections/06-text2mem.tex` 分别对应六篇论文，成员在 issue 中认领后编辑对应章节。文件里的“待填写”标明尚未完成的内容，不代表已有阅读或实验成果。六篇个人章节现均已接入；`sections/07-synthesis.tex` 已编入主稿，摘要、背景、比较与总结形成可审核正文。共同部分已由 YaoYang-123456 集中复核；贡献说明本轮保留原占位。`references.bib` 的六篇条目来自 ACL Anthology 官方 BibTeX 导出。

每篇说明问题与背景、核心方法、关键实验、局限和课设启发。正文保留必要的学术引用，详细原文页码及图表位置放在源码注释或阅读指南中。公共讨论围绕组织、检索、更新、利用和操作规范比较六篇工作，不直接按不同模型和任务下的准确率排名。论文报告结果、本组已验证结果和计划开展的实验分别注明；阅读报告不等待课设实验全部完成。

## 系统性总结与团队讨论

保留每人介绍一篇论文的安排。综合分析现已接入报告和 slides，作为个人介绍之后的共同主线，并已通过集中技术审核。已覆盖：

- **统一对照表**：对齐研究对象、表示、主要机制和比较边界，说明六篇工作分别解决什么问题。
- **机制之间的联系**：讨论组织与访问、取回与利用、更新与操作语义的关系，同时说明组合所需条件。
- **共同取舍与局限**：比较抽取误差、上下文预算、更新风险、验证范围与成本，避免只复述各篇的优点。
- **实验可比性**：区分任务、数据、模型、反馈、预算、指标与成本，不直接按原论文分数排优劣。
- **共同案例**：用同一个自拟场景检查各方法的解释范围，区分讨论推演与实际验证。
- **课设选择与结论**：说明主线选择、参考机制和不纳入的部分，记录依据及仍待验证的分歧。

各论文负责人参与综合章节的证据核对与讨论；由一位成员整合行文，相关成员复核。用原文页码、图表或实际结果支撑结论；团队讨论后再把共识和分歧补入文稿，不虚构讨论经过。具体论文阅读和团队整合工作都按实际情况计入贡献说明。

Slides 沿用同一报告结构，计划开场 2 分钟、每人 8 分钟、总结 10 分钟，合计 60 分钟。开场时间页、综合内容及讲稿已同步，具体模块和编译见 [slides 说明](slides/README.md)。实际排练后再调整各段时长；不能用计划秒数代替本人计时。

## 编译报告

共享版式来自 [软件学报社区模板](../templates/jos/README.md)。在本目录执行：

```sh
latexmk -xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
```

本目录的 `.latexmkrc` 设置共享模板搜索路径和输出目录，生成 `output/homework/main.pdf`，编译中间文件也留在 `output/`。定稿后将 PDF 复制到本目录；PPT 源文件和最终导出按需加入，不提交缓存。

## 最终整理

报告、slides、视频使用相同的主题短名和日期，例如 `8队-结构化记忆-20261101.pdf`、`8队-结构化记忆-20261101-slides.pdf`、`8队-结构化记忆-20261101.mp4`，打包名为 `8队-结构化记忆-20261101.zip`，日期使用实际定稿日期。打包上传老师通知中的云盘。

单文件达到 20 MB 时，**请将该文件发送到小组微信群**，不要提交 Git 或 PR 附件；仓库只记录文件名、大小、SHA-256、用途和交接日期。此处的平时作业截止时间不替代课设最终验收时间，课设安排继续见[项目方案](../../docs/project-plan.md)及后续通知。

分享整份报告预览前，在仓库根目录运行（Python 需安装 pypdf）：

```sh
python3 scripts/fix_hymem_pdf_unicode.py output/homework/main.pdf reports/homework/report-preview.pdf
```

该步骤复用现有 GB1 中文映射导出脚本，保留原始编译 PDF，并保证未配置外部 CMap 的 PDF.js 仍可读取中文。
