# 小组平时作业

第 8 队的 6 名成员共同完成“长上下文场景结构化记忆建模”专题阅读，与课设共用本仓库的六篇论文、笔记和引用。每人先负责一篇论文，再共同形成系统性比较；阅读结论用于课设选型与实验分析，课设中的真实发现可反过来补充讨论。个人阅读和讲解是小组材料的一部分。

## 提交与讲解

依据[老师的新通知](../../docs/course/262701NLP-平时作业提交验收说明-2026-文字版.md)：

- 提交截止：**2026 年 11 月 1 日 23:59**。
- 本组属于专题类课设，准备一份系统性阅读报告、一份 PPT、一个讲解视频；总时长按队伍人数 × 10 分钟，本组 6 人约 60 分钟。
- 报告和汇报注明各成员分工及贡献百分比；个人额外整理可一并保留。
- 具体讲解时间最早预计 11 月 2 日，以老师后续安排为准。

本组报告统一使用 **LaTeX 写作、PDF 交付**，演示材料使用 [Beamer 模板](slides/README.md)并导出 PDF；[官方 Word 样例](../../docs/course/软件学报排版样例2025年版.doc)只作报告版式参考。

## 阶段状态（2026-11-03）

本阶段已完成并提交，11月3日由hycx233确认结项。最终报告15页、演示68页、视频59分50.24秒（8个章节）。六人的论文报告、讲解与讨论，以及开场、系统总结、录音整合和分工比例均已完成。

归档入口：[阶段归档](archive-20261101.md)及[最终文件清单](submission-artifacts.json)。提交包名为`8队-结构化记忆-20261101.zip`，内含实名报告、实名幻灯片和压缩视频；实名材料、原始音频和视频制作文件继续保留在Git忽略的本地目录。

| 论文 | 阅读负责人 | 最终材料与录音 |
| --- | --- | --- |
| StructMem | hycx233 | 与开场合录09:51.211；系统总结另录09:31.711 |
| Hindsight | onlysonder | 9页演示模块；实际录音07:52.387 |
| Semantic XPath | oioioi-521 | 12页演示模块；本次新录音08:58.288已整合 |
| HyMEM | lanshuheng9-oss | 7页演示模块及录音配套稿；实际录音08:04.352 |
| MetaMem | YaoYang-123456 | 8页演示模块；实际录音08:05.138 |
| Text2Mem | ngocnamd93-spec | 8页演示模块；实际录音07:27.147 |

### 最终预览与验证

- [报告PDF](report-preview.pdf)：15页，完成语言统一、StructMem精简、JOS版式对照、中英文作者对齐及分工填写。
- [演示PDF](slides/preview.pdf)：68页，开场、六篇模块与系统总结齐全，已移除逐页文献和末尾备用页。
- 两份主报告与5份个人报告共41页已完成XeLaTeX编译、PDF.js中文提取、渲染、字体嵌入及Unicode处理前后画面核对；最终文件与ZIP再次完成大小、SHA-256及完整性校验。
- 详细技术记录见[报告修订检查](report-style-check-20261027.md)、[报告清单](report-style-artifacts.json)、[演示修订检查](slides/style-check-20261027.md)和[整合清单](integration-artifacts.json)。各次检查的历史页数与警告记录保留原版本含义。

### 后续工作

11月1日阅读作业已结项。课程设计的实现、实验与最终验收继续按[项目方案](../../docs/project-plan.md)及后续通知推进。10月22日研讨材料见[研讨归档](../seminar-20261022/README.md)。

## 个人阅读材料

| 论文 | 报告 | 演示 | 讲稿与说明 |
| --- | --- | --- | --- |
| StructMem | [共享章节](sections/01-structmem.tex) | [共享模块](slides/sections/01-structmem.tex) | 逐页 Beamer 备注 |
| Hindsight | [共享章节](sections/02-hindsight.tex) | [个人 PDF](slides/hindsight-preview.pdf) | [8 分钟讲稿](scripts/02-hindsight-8min.md) |
| Semantic XPath | [3 页 PDF](semantic-xpath-preview.pdf) | [12 页 PDF](slides/semantic-xpath-preview.pdf) | [个人指南](semantic-xpath-reading-guide.md) |
| HyMEM | [2 页阅读报告](hymem-reading-report.pdf)、[2 页录音配套报告](hymem-recording-report.pdf) | [7 页 PDF](slides/hymem-preview.pdf) | [录音指南](hymem-recording-guide.md)、[七段讲稿](scripts/04-hymem-recording.md) |
| MetaMem | [2 页 PDF](metamem-reading-report.pdf) | [8 页 PDF](slides/metamem-preview.pdf) | [交接与完整讲稿](metamem-handoff.md) |
| Text2Mem | [2 页 PDF](text2mem-report-preview.pdf) | [8 页 PDF](slides/text2mem-preview.pdf) | [个人指南](text2mem-reading-guide.md) |

个人材料与历史编译清单分别保留；最新整合报告和演示以本页的整合清单为准。实际录音和翻页点已收齐，本次课程提交已完成，最终版本见阶段归档。

## 共同编辑

`main.tex` 是阅读报告入口，`sections/01-structmem.tex` 至 `sections/06-text2mem.tex` 分别对应六篇论文，成员在 issue 中认领后编辑对应章节。文件里的“待填写”标明尚未完成的内容，不代表已有阅读或实验成果。六篇个人章节现均已接入；`sections/07-synthesis.tex` 已编入主稿，摘要、背景、比较与总结形成可审核正文。共同部分已由 YaoYang-123456 集中复核；署名、分工与贡献比例已按实际工作填写。`references.bib` 的六篇条目来自 ACL Anthology 官方 BibTeX 导出。

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
