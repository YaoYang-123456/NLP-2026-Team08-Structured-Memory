# NLP-2026-Team08-Structured-Memory

天津大学 2026 年 NLP 课程设计｜第 8 队｜6 人小组｜长上下文场景结构化记忆建模。

本仓库由 6 人小组共同准备同一主题的平时作业和课程设计，集中保存课程要求、论文、阅读笔记、LaTeX 阅读报告、课设实现和汇报材料。平时作业形成六篇论文的系统性比较，为课设选型、实现和实验分析提供依据；课设中的实际发现再用于补充阅读讨论。老师文档中的论文分组为“专题 4，组 2”，与我们的队号“第 8 队”是不同编号。

## 先从这里开始

- [老师要求原文](docs/course/NLP初步课设与平时作业安排-贺瑞芳-20260920.pdf)：总体说明见第 1 页，所选专题的 6 篇论文见第 9 页。
- [平时作业提交验收说明](docs/course/262701NLP-平时作业提交验收说明-2026-文字版.md)：2026 年 10 月新通知的完整文字版；[预览复制 PDF](docs/course/262701NLP-平时作业提交验收说明-2026-本地复制版.pdf)和[来源记录](docs/course/README.md)一并保存。
- [第一次课设研讨与视频补充通知](docs/course/seminar-notice-20261020.md)：8 分钟汇报与视频、创新性论证、当前分工及贡献比例；研讨云盘有效期至 10 月 22 日 14:30。
- [小组平时作业](reports/homework/README.md)：六人协作、LaTeX 报告入口、PPT / 视频与提交安排。
- [小组 Beamer 汇报模板](reports/homework/slides/README.md)：开场、六人各 7–9 分钟讲解、10–15 分钟系统总结；共享蓝色学术版式，导出 PDF。
- [软件学报 LaTeX 模板](reports/templates/jos/README.md)：社区模板、字体适配和编译方法；[官方 Word 样例](docs/course/软件学报排版样例2025年版.doc)只作版式参考。
- [协作与文件约定](docs/collaboration.md)：issue 分工、分支、PR、自查与审核、大文件传输。
- [项目方案与任务认领](docs/project-plan.md)：六包已认领；S0/S2 同一 30 题回答及 E 自动评分已有记录，当前推进人工复核与审核收尾，slide 制作、录制和汇报准备暂缓。
- [D 真实综合与 S2 交接](docs/structmem-real-run-20261020.md)：91 条真实综合、固定 30 题的 60＋5 检索与回答；评分包已由 F 接收，评分报告与独立验收分开记录。
- [统一回答入口与联调说明](docs/qa-integration.md)：F 的 DeepSeek 调用、B/D 输入和 E 评分交接；真实 S0/S2 回答已完成，评分结果与人工验收状态分别记录。
- [六篇论文复现条件核查](notes/six-paper-comparison.md)：原文数字、固定代码版本与复现注意事项。
- [AGENTS.md](AGENTS.md)：给 GPT 等编程助手的工作约定，也适用于成员协作。

平时作业由全组共同完成，提交截止为 **2026 年 11 月 1 日 23:59**；本组按专题类课设准备一份系统性阅读报告、一份 PPT 和约 **60 分钟（6 人 × 10 分钟）**的讲解视频，注明成员分工及贡献百分比。报告统一使用 LaTeX 编写并导出 PDF，Word 样例仅作格式参考；老师通知中的 DOCX 要求在原文中保留。具体讲解时间最早预计 11 月 2 日。课设最终提交方式和日期仍待后续通知，不把平时作业截止日期当作课设实验截止日期。

第一次课设研讨继续按 **10 月 22 日**安排，提前提交幻灯片和 **8 分钟视频**，并参加线下汇报及 2–5 分钟问答。当前只更新要求、项目方案和进展记录，等待结果进一步复核后再推进 slide、录制与汇报准备；这不改变研讨云盘 **10 月 22 日 14:30** 的有效期。

## 已收录论文

| 编号 | 论文 | 本地文件 |
| --- | --- | --- |
| 01 | StructMem: Structured Memory for Long-Horizon Behavior in LLMs | [PDF](papers/structured-memory-group2/01_StructMem.pdf) |
| 02 | Hindsight: Structured Agent Memory that Retains, Recalls, and Reflects | [PDF](papers/structured-memory-group2/02_Hindsight.pdf) |
| 03 | Semantic XPath: Structured Agentic Memory Access for Conversational AI | [PDF](papers/structured-memory-group2/03_Semantic_XPath.pdf) |
| 04 | Hybrid Self-evolving Structured Memory for Computer-Use Agents | [PDF](papers/structured-memory-group2/04_Hybrid_Self-evolving_Structured_Memory.pdf) |
| 05 | MetaMem: Evolving Meta-Memory for Knowledge Utilization through Self-Reflective Symbolic Optimization | [PDF](papers/structured-memory-group2/05_MetaMem.pdf) |
| 06 | Text2Mem: A Unified Memory Operation Language for Memory Operating System | [PDF](papers/structured-memory-group2/06_Text2Mem.pdf) |

论文来源、下载日期、页数和 SHA-256 记录在 [sources.json](papers/structured-memory-group2/sources.json)。认领论文和后续任务请使用 issue，负责人以 issue 的 assignee 为准。

## 阅读准备与课设试点

- [六篇论文比较](notes/paper-comparison.md)：方法、官方代码、实现负担和选题依据。
- [MetaMem 阅读笔记](notes/05-metamem-YaoYang-123456.md)：杨垚负责论文的 AI 辅助草稿，含方法、实验、局限和汇报结构。
- [MetaMem 官方代码审阅](docs/metamem-code-review.md)：默认划分、实际运行检查和实验前需处理的问题。
- [小规模实验方案](docs/metamem-pilot.md)：无规则、固定规则、学习规则三组对照及成本估算。

以上是 2026-10-15 的准备材料；尚未运行真实模型实验，也未确定为全组最终课设方案。

## 本地最小试点

- [运行入口与接口说明](docs/metamem-local-pilot.md)：独立环境、官方数据、B0/B1/B2、五题 smoke、错误统计及调用量。
- [2026-10-15 实际执行记录](docs/metamem-local-run-20261015.md)：真实数据已核验并划分；模拟流程已验证；没有真实模型性能结果。

源码使用 Python 标准库，位于 `src/metamem_pilot/`；官方提示词的独立副本及许可证位于 `third_party/`。这仍是个人 MetaMem 的 BM25 RAG 试点，不是 LightMem 完整复现或全组选型决定。

## 目录约定

| 路径 | 用途 |
| --- | --- |
| `docs/course/` | 老师的要求、后续通知、原文复制及官方排版参考 |
| `docs/` | 协作说明、方案和公共文档 |
| `papers/structured-memory-group2/` | 当前专题论文及来源记录 |
| `notes/` | 个人阅读笔记和论文比较，按需创建 |
| `src/`、`scripts/`、`tests/` | 实现、运行脚本和必要测试，开始实现时按需创建 |
| `reports/homework/` | 平时作业的共享 LaTeX 阅读报告、PPT / 视频协作说明 |
| `reports/templates/jos/` | 软件学报社区 LaTeX 模板、来源及编译说明 |
| `reports/` 其他目录 | 课设实验报告、讲稿和最终提交材料，按需创建 |
| `data/`、`output/`、`tmp/` | 本地数据、运行产物和临时文件，不纳入 Git |

**大文件：单文件达到 20 MB（20,000,000 字节）时，先提醒用户发到小组微信群，不提交到 Git 或 PR 附件；仓库只记录文件名、用途和获取说明。** 现有老师文档及每篇论文均小于该阈值。
