# NLP-2026-Team08-Structured-Memory

天津大学 2026 年 NLP 课程设计｜第 8 队（6 人小组）｜长上下文场景结构化记忆建模。

本仓库用于存放全组的平时作业与课程设计材料，包括课程通知、论文原文、阅读笔记、LaTeX 报告、实验代码和汇报文件。注：老师文档里的论文分组编号是“专题 4，组 2”，我们的队号是“第 8 队”。

## 当前阶段（阶段二：多粒度证据打包）

11 月 1 日的平时作业已提交并归档（15 页报告、68 页演示、约 60 分钟视频，详见[平时作业归档](reports/homework/archive-20261101.md)）。目前全组聚焦课程设计的阶段二改进与实验。

**阶段二做什么**：在阶段一复现的 StructMem 上做一个面向长对话的证据打包改进。原来回答问题时，系统把 top-60 条事件和 top-5 条完整跨事件综合直接拼进去，光 5 条综合就占了一半上下文额度，还夹杂了不少无关句子。阶段二把综合拆成句子，和事件放在同一个 token 预算（默认 4,096）里一起筛选；选到依赖前文的综合句时，顺带把缺的人物指代和时间前文一起带进去，再在相同条件下对比回答准确率、证据覆盖率和成本。

- **离线试点结果**：在 30 道开发题、4,096 token 预算下，普通逐句打包（N）和上下文保留打包（A）的证据支持覆盖都达到 **50/51**，高于旧的固定 5 条综合 + MMR（M，48/51）。不过离线覆盖不等于真实回答准确率，保护前文对最终答对题有没有独立提升，还需要正式跑完回答和评分来验证。
- **任务入口**：总览与最新进展看 [阶段二总览 #69](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/69)，六人各自任务见 `#70`–`#75`。

## 文档导航

### 课设阶段二（当前推进）

- [阶段二完整规划](docs/plans/2026-11-03-phase2.md)：核心思路、实验设计（M / N / A）、六人分工、接口约定和调用规模。
- [方向与创新定位](notes/phase2-direction-decision-20261103.md)：为什么选这个方向、与 6 篇课程论文及邻近工作的关系、可直接对老师使用的表述。
- [多粒度打包离线试点](reports/phase2-anchor-pilot-20261103.md)：30 题、2,048 / 4,096 两档预算下整段 / 逐句 / 上下文保留的离线对比。
- [统一回答入口与联调说明](docs/qa-integration.md)：F 维护的 DeepSeek 回答脚本、输入输出格式与 B / D / E 对接方式。

### 课程要求与协作约定

- [协作与文件约定](docs/collaboration.md)：issue 分工、分支命名、PR 审核、目录和 20 MB 大文件传输约定。
- [AGENTS.md](AGENTS.md)：给 AI 编程助手（Codex / GPT 等）与组员共用的工作和写作约定。
- [老师课设与平时作业安排](docs/course/NLP初步课设与平时作业安排-贺瑞芳-20260920.pdf)：总体要求见第 1 页，本专题 6 篇论文见第 9 页。
- [平时作业提交验收说明](docs/course/262701NLP-平时作业提交验收说明-2026-文字版.md)：文字版说明（另存[本地复制 PDF](docs/course/262701NLP-平时作业提交验收说明-2026-本地复制版.pdf)及[来源记录](docs/course/README.md)）。
- [第一次课设研讨通知](docs/course/seminar-notice-20261020.md)：10 月 22 日 8 分钟汇报与视频要求。

### 历史阶段与归档

- [平时作业归档](reports/homework/archive-20261101.md)：已提交的 11 月 1 日阅读作业版本与校验信息（源文件见 [reports/homework/](reports/homework/README.md)、[Beamer 模板](reports/homework/slides/README.md)、[软件学报 LaTeX 模板](reports/templates/jos/README.md)及[官方 Word 版式样例](docs/course/软件学报排版样例2025年版.doc)）。
- [10 月 22 日第一次研讨归档](reports/seminar-20261022/README.md)：阶段一汇报材料与讲稿。
- [阶段一项目方案与复现记录](docs/project-plan.md)：阶段一六包分工，以及 S0（15/30）和 S2（19/30）在 30 道开发题上的基线结果（D 的综合与交接见 [structmem-real-run-20261020.md](docs/structmem-real-run-20261020.md)，S0 运行记录见 [s0-answer-run-20261019.md](reports/s0-answer-run-20261019.md)，复算记录见 [e-score-verification-20261021.json](reports/e-score-verification-20261021.json)）。
- [六篇论文比较](notes/paper-comparison.md) 与 [复现条件核查](notes/six-paper-comparison.md)：六篇专题论文的对比、原文数字与代码版本。
- 早期 MetaMem 个人探索（2026-10-15，仅作参考，非全组选型）：[阅读笔记](notes/05-metamem-YaoYang-123456.md)、[代码审阅](docs/metamem-code-review.md)、[实验方案](docs/metamem-pilot.md)、[本地试点说明](docs/metamem-local-pilot.md)、[执行记录](docs/metamem-local-run-20261015.md)（源码在 `src/metamem_pilot/`，上游提示词副本在 `third_party/`）。

## 已收录论文

| 编号 | 论文 | 本地文件 |
| --- | --- | --- |
| 01 | StructMem: Structured Memory for Long-Horizon Behavior in LLMs | [PDF](papers/structured-memory-group2/01_StructMem.pdf) |
| 02 | Hindsight: Structured Agent Memory that Retains, Recalls, and Reflects | [PDF](papers/structured-memory-group2/02_Hindsight.pdf) |
| 03 | Semantic XPath: Structured Agentic Memory Access for Conversational AI | [PDF](papers/structured-memory-group2/03_Semantic_XPath.pdf) |
| 04 | Hybrid Self-evolving Structured Memory for Computer-Use Agents | [PDF](papers/structured-memory-group2/04_Hybrid_Self-evolving_Structured_Memory.pdf) |
| 05 | MetaMem: Evolving Meta-Memory for Knowledge Utilization through Self-Reflective Symbolic Optimization | [PDF](papers/structured-memory-group2/05_MetaMem.pdf) |
| 06 | Text2Mem: A Unified Memory Operation Language for Memory Operating System | [PDF](papers/structured-memory-group2/06_Text2Mem.pdf) |

论文来源、下载日期、页数和 SHA-256 记录在 [sources.json](papers/structured-memory-group2/sources.json)。

## 目录结构

| 路径 | 用途 |
| --- | --- |
| `docs/course/` | 老师的要求、通知原文及排版参考 |
| `docs/` | 协作规范、方案规划和接口文档 |
| `papers/structured-memory-group2/` | 专题 6 篇论文 PDF 及来源信息 |
| `notes/` | 阅读笔记、论文比较和方向讨论 |
| `src/`、`scripts/`、`tests/` | 核心代码、运行脚本和单元测试 |
| `configs/` | 数据划分、模型与实验配置（不含密钥） |
| `reports/homework/` | 平时作业的 LaTeX 报告与 Beamer 模板 |
| `reports/templates/jos/` | 软件学报社区 LaTeX 模板 |
| `reports/` | 课设各阶段实验报告、交接包与汇报材料 |
| `data/`、`output/`、`tmp/` | 本地数据、运行产物和临时文件（不入 Git） |

**大文件约定**：单文件达到 20 MB（20,000,000 字节）时，通过小组微信群传文件，不要提交到 Git 或 PR 附件，仓库里只记文件名、用途和校验信息。
