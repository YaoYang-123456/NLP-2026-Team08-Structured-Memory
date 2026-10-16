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

## 本地最小试点

- [运行入口与接口说明](docs/metamem-local-pilot.md)：独立环境、官方数据、B0/B1/B2、五题 smoke、错误统计及调用量。
- [2026-10-15 实际执行记录](docs/metamem-local-run-20261015.md)：真实数据已核验并划分；模拟流程已验证；没有真实模型性能结果。
- [模型下载与晚间五题入口](docs/metamem-evening-preparation.md)：Qwen2.5 7B 已下载；一小时手动试跑、及时保存、停止和人工复核已准备。本轮真实调用仍为 0，等待明确启动。
- [首次真实五题试跑](docs/metamem-real-smoke-20261015.md)：后续获授权完成 22 次真实调用，9 次有效判分；两次输出达到长度上限，没有学出规则，模型已卸载。这是训练 smoke，不是正式测试结果。
- [输出预算诊断复跑](docs/metamem-budget-diagnostic-20261015.md)：同五题 21 次真实调用，无截断，9 次有效判分；没有合格混合组、规则仍为空，清理核验成功。[五题 AI 辅助复核](docs/metamem-five-question-ai-review.md) 已记录判分与检索问题，尚未完成人工复核。
- [Judge 离线格式诊断与人工复核卡](docs/metamem-judge-diagnostic-review.md)：单标签允许句末英文句号，第二轮派生判分覆盖变为 10/10；原始记录保持不变，无新增模型调用或语义改判。
- [固定19条回答的 judge 校准](docs/metamem-judge-calibration-20261015.md)：旧、新模板各19次判分，均解析有效但两个语义误判未修正；40次真实调用含两次预热，按采用条件停止，没有进入20条训练或10条验证。

- [外部 AI 判分探索实验](docs/metamem-external-ai-run-20261015.md)：完成20条训练与三组10条验证，生成一条规则；因uncertain导致无候选满足完整覆盖，没有选定最终B2。[文件式协议](docs/metamem-external-ai-protocol.md)与此前7B自判实验分开，尚无人工金标准。

- [严格拒答 v2 离线敏感性分析](docs/metamem-strict-abstention-v2-analysis.md)：12条适用回答重评、58条沿用v1；9条uncertain变No，判对数不变。只作事后选择分析，未重训、未覆盖历史结论，本地模型调用0。

源码使用 Python 标准库，位于 `src/metamem_pilot/`；官方提示词的独立副本及许可证位于 `third_party/`。这仍是个人 MetaMem 的 BM25 RAG 试点，不是 LightMem 完整复现或全组选型决定。

## 当前个人试点交付

[前三阶段统一总报告](docs/metamem-integrated-report.md)串起规则学习、稳定性、检索诊断与回答约束；[组员上手](docs/metamem-team-start.md)、[课程差距](docs/metamem-course-readiness.md)和[十分钟/两分钟讲稿](docs/metamem-integrated-talk.md)提供整合入口。

[第三阶段研究包](docs/metamem-stage3.md)：同原BM25、无规则，两提示词各30条新回答；原17对、候选15对。候选更短且部分依据质量改善，但拒答未改善、晚餐三轮退步，保留可选候选，不切换默认。两组完整覆盖，独立AI复核并非人工金标准。

[MetaMem 第二阶段研究包](docs/metamem-stage2.md)：12条补证据诊断＋四组120条新回答。自动角色预算未补齐已知关键证据、未显示稳定收益，保留为可选实验而不替换基线；证据利用与评测口径问题并存。包含图表、逐题结果、恢复记录与十分钟讲稿。

[MetaMem 第一阶段研究包](docs/metamem-stage1.md)：三轮固定十题稳定性诊断、原史证据审计、十分钟讲解与复现入口。旧明信片优势未稳定重现；保守复核B0为17Y/13N，B2为18Y/11N/1U（各30次重复观察，仅10个独立题目）。不是正式测试或全组方案。

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
