# NLP-2026-Team08-Structured-Memory

天津大学 2026 年 NLP 课程设计｜第 8 队｜6 人小组｜长上下文场景结构化记忆建模。

本仓库集中保存课程要求、论文、阅读笔记、课设实现和汇报材料。老师文档中的论文分组为“专题 4，组 2”，与我们的队号“第 8 队”是不同编号。

## 先从这里开始

- [老师要求原文](docs/course/NLP初步课设与平时作业安排-贺瑞芳-20260920.pdf)：总体说明见第 1 页，所选专题的 6 篇论文见第 9 页。
- [协作与文件约定](docs/collaboration.md)：issue 分工、分支、PR、自查与审核、大文件传输。
- [AGENTS.md](AGENTS.md)：给 GPT 等编程助手的工作约定，也适用于成员协作。

按现有老师文档，各类课设通常每 6 人一组；平时作业需要论文阅读总结、系统性的 PPT 和 Word 文档，以及录制汇报视频。具体课设提交方式后续通知，以老师最新通知为准。

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

## 目录约定

| 路径 | 用途 |
| --- | --- |
| `docs/course/` | 老师的原始要求和后续通知 |
| `docs/` | 协作说明、方案和公共文档 |
| `papers/structured-memory-group2/` | 当前专题论文及来源记录 |
| `notes/` | 个人阅读笔记和论文比较，按需创建 |
| `src/`、`scripts/`、`tests/` | 实现、运行脚本和必要测试，开始实现时按需创建 |
| `reports/` | 小组汇总报告、PPT、讲稿及最终提交材料，按需创建 |
| `data/`、`output/`、`tmp/` | 本地数据、运行产物和临时文件，不纳入 Git |

**大文件：单文件达到 20 MB（20,000,000 字节）时，先提醒用户发到小组微信群，不提交到 Git 或 PR 附件；仓库只记录文件名、用途和获取说明。** 现有老师文档及每篇论文均小于该阈值。
