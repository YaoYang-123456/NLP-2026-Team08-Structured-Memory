# 六篇结构化记忆论文复现条件核查

核查日期：2026-10-15。文中页码均指仓库本地 PDF 从第 1 页起的页序，实验数字均为原论文报告值。

六篇专题论文分别关注记忆的组织、检索、更新、利用和操作规范，评测基准、模型和任务各不相同，不适合直接拿准确率排座次，也不需要六套全复现。我们选定 **StructMem** 作为实现主线，其余五篇用于方法对比、错因分析与局部改进借鉴（整体安排见[项目方案](../docs/project-plan.md)与[阶段二规划](../docs/plans/2026-11-03-phase2.md)，另有早期[论文比较](paper-comparison.md)）。

## 1. StructMem

原文：[本地 PDF](../papers/structured-memory-group2/01_StructMem.pdf) · [ACL 页面](https://aclanthology.org/2026.acl-short.12/)

- **核心方法**：平铺事实记忆容易丢掉事件内部关系和跨事件联系，而显式知识图谱构建成本又太高。StructMem 用自然语言分别抽取事实与关系，按来源时间绑定成事件；再按时间窗口聚合新事件、检索历史种子并补齐事件上下文，生成单独保存的跨事件综合记忆（第 2–3 页、图 2、公式 1–6）。注：事件重建主要用在综合阶段，问答阶段并不自带同样的事件扩展。
- **实验与目标**：主实验在 LoCoMo 上用 `gpt-4o-mini` 和 `text-embedding-3-small` 评测，不含对抗题，共 1,540 题（单跳 841、多跳 282、时间 321、开放域 96）。附录第 8 页给出默认参数：1 小时综合窗口、15 个历史种子、问答检索 60 条事件 + 5 条综合。第 4 页表 1 报告总体 76.82%、时间题 81.62%；构建阶段消耗 1.937M tokens、1,056 次调用（不含问答和裁判）。
- **关键消融**：第 4 页表 2 对比了 flat、event without synthesis 和完整 StructMem。我们用原始对话 Flat RAG 做基线（注意它不同于论文的平铺事实记忆），重点复现“去综合 vs 完整 StructMem”。论文中完整版在多跳题上从 66.31% 升到 68.77%，但并非表 1 所有外部基线中的单项最高。
- **局限与启发**：第 6 页提到对提示词敏感，且缺少显式冲突解决和记忆更新。适合作为课设切口的点包括检索粒度、综合记忆的来源可追溯性和时间信息利用；完整冲突更新改动会大很多。
- **代码核查**：官方实现位于 [LightMem StructMem 说明](https://github.com/zjunlp/LightMem/blob/8449d574df6bae1bdf3314a1564da65e2f37e046/StructMem.md) 和 [LoCoMo 实验说明](https://github.com/zjunlp/LightMem/blob/8449d574df6bae1bdf3314a1564da65e2f37e046/experiments/locomo/readme.md)（静态核查 [`add_locomo.py`](https://github.com/zjunlp/LightMem/blob/8449d574df6bae1bdf3314a1564da65e2f37e046/experiments/locomo/add_locomo.py) 与 [`search_locomo.py`](https://github.com/zjunlp/LightMem/blob/8449d574df6bae1bdf3314a1564da65e2f37e046/experiments/locomo/search_locomo.py)）：
  - 默认脚本用本地 Hugging Face 嵌入、384 维索引和 CUDA 压缩配置，和论文的 OpenAI 嵌入配置不同，复现时需明确记录；
  - 构建脚本实际参数名是 `--summary_top_k_seeds`，README 示例简写成了 `--summary_top_k`，以代码解析器为准；
  - 需对齐分段、压缩、提示词和事件来源标识，不能只开 `event` / `summary` 两个开关；
  - 上游问答脚本会把部分异常直接记成空答或 0 分，我们自己评测时要把调用失败和正常答错分开统计。

## 2. Hindsight

原文：[本地 PDF](../papers/structured-memory-group2/02_Hindsight.pdf) · [ACL 页面](https://aclanthology.org/2026.acl-demo.27/)

- **核心方法**：把记忆分成 `world`、`experience`、`observation`、`opinion` 四类，通过 `retain / recall / reflect` 写入、检索和反思。检索融合向量、关键词、图关系和时间四条通道，经 RRF 和重排输出；时间元数据区分“事件发生区间”和“信息被提及的时间”（第 2–5 页、图 1）。
- **实验**：第 6 页表 2 报告 OSS-20B 下 LongMemEval 83.6%、LoCoMo 83.2%。由于基座模型、检索和反思链路和 StructMem 不同，不能拿 83.2 和 76.82 直接比结构优劣。
- **局限与启发**：第 8 页提到抽取错误传播、仅评测英语、观点机制缺用户研究。多路召回、RRF、显式 token 预算和时间字段都可以借鉴为工程基础。
- **代码与位置**：[官方仓库](https://github.com/vectorize-io/hindsight/tree/d5b1d4282f3325116c06f76ce3e79dce5ea4e22c) 依赖 PostgreSQL + pgvector 服务部署，工程体量较大，课设暂不整套部署，作为检索与时间建模参考。

## 3. Semantic XPath

原文：[本地 PDF](../papers/structured-memory-group2/03_Semantic_XPath.pdf) · [ACL 页面](https://aclanthology.org/2026.acl-demo.28/)

- **核心方法**：面对层级结构任务，平铺检索容易“主题对但范围错”（比如改错日期的活动）。它将请求转成 XPath 风格查询，结合结构导航与语义打分，把命中的相关子树交给下游。旅行场景的层级是 `Itinerary → Version → Day → POI`，对应到 LoCoMo 就是 `Conversation → Session → Turn`（第 2–5 页、图 2、§3）。
- **实验**：三个自建领域（行程、待办、餐食，各 20 单轮 + 5 多轮）加 LoCoMo。第 7 页表 1 在 GPT-5 mini 下，LoCoMo 上 Flat RAG / Semantic XPath / In-context 分别为 35.71 / 65.19 / 74.55，平均输入 3,032 tokens（含查询生成）。摘要里的 176.7% 和 9.1% 是特定对比，不代表 LoCoMo 一般结论。
- **局限与启发**：依赖既有层级与查询生成质量，第 6–7 页错误分析显示检索仍是主要瓶颈。很适合借鉴“按结构范围选上下文”和分层错误归因的思路（也是阶段二多粒度打包的重要启发），不需要完整实现查询语言。
- **代码与位置**：[官方仓库](https://github.com/D3Mlab/SemanticXpath-Chat/tree/116a704fdf6496c2855fa212167702d01ca1a6df) 提供了树查询引擎和前后端 demo，暂未在目录中定位到独立全套论文评测脚本，适合做思路与演示参考。

## 4. Hybrid Self-evolving Structured Memory（HyMEM）

原文：[本地 PDF](../papers/structured-memory-group2/04_Hybrid_Self-evolving_Structured_Memory.pdf) · [ACL 页面](https://aclanthology.org/2026.findings-acl.549/)

- **核心方法**：面向电脑操作智能体，把离散策略/属性和连续多模态轨迹表示结合成图结构；新轨迹经检索和冗余判断后做 `ADD / MERGE / REPLACE`，执行中检测阶段切换并刷新工作记忆。连续表示直接接入 VLM 嵌入层，不是普通纯文本拼接（第 3–5 页、图 1）。
- **实验与成本**：在 WebVoyager、Multimodal-Mind2Web、MMInA 评测任务成功率；第 7 页表 2 报告 Qwen2.5-VL-7B 总体从 12.5% 升到 35.0%（+22.5 个百分点）。第 5 页用 2,883 条成功轨迹构建记忆，第 13 页附录用 Q-Former + LoRA 微调约 1.2% 参数，单张 H100 需 20 小时内。
- **局限与启发**：高度依赖网页环境、截图和 GUI 定位模型。可借鉴“有价值才更新”和“按阶段刷新工作记忆”的思想，但不适合在纯文本小预算环境下直接复现。
- **代码与位置**：[官方仓库](https://github.com/NickSiboZhu/HyMEM-GUI-Agent/tree/911722c99c8c3fa0052cbb1f596e13d691610ed5) 依赖多模态轨迹、连续记忆权重与本地绝对路径配置，作相关工作参考。

## 5. MetaMem

原文：[本地 PDF](../papers/structured-memory-group2/05_MetaMem.pdf) · [ACL 页面](https://aclanthology.org/2026.findings-acl.270/)

- **核心方法**：解决“证据检回来了，但模型不会用”的问题（比如把总里程和单日里程重复相加）。在事实记忆之外维护一套符号化的使用经验规则，通过多次采样、对照标准答案反思和 `ADD / MOD / DEL` 冲突过滤来更新规则，不改模型权重（第 3–5 页、图 2）。
- **实验与复现细节**：在 LongMemEval + LightMem 事实记忆上用 Qwen3-30B-A3B-Instruct / Llama3.1-70B-Instruct 评测，默认裁判为 Qwen3-235B-A22B。第 6 页表 1 中 LightMem → MetaMem 分别为 67.50 → 71.90（+4.40）和 66.17 → 69.08（+2.91）。附录第 11 页给出每样本采样 5 次、5 个 epoch、batch size 50，五折划分为 350 训练 / 50 验证 / 100 测试（切忌在测试答案上生成规则再测同一测试集）。
- **局限与启发**：依赖评测反馈，规则过多容易冗余和过拟合（第 12 页 A.6），且反复采样和判分的 API 成本不低。适合用来分析“证据利用错误”，或做小规模的固定规则对照（见组内早期个人试点）。
- **代码与位置**：[官方仓库](https://github.com/OpenBMB/MetaMem/tree/66232c1cb33d3d7939d323b431f21c741785142e) 流程齐全，默认配置依赖较大本地模型，换 DeepSeek 时需记录差异。

## 6. Text2Mem

原文：[本地 PDF](../papers/structured-memory-group2/06_Text2Mem.pdf) · [ACL 页面](https://aclanthology.org/2026.findings-acl.100/)

- **核心方法**：解决自然语言控制记忆时的歧义和执行不一致。定义了 12 类标准操作（Encode、Update、Label、Promote、Demote、Merge、Split、Delete、Lock、Expire、Retrieve、Summarize），通过 schema、validator、parser 和 adapter 执行，本质上是记忆操作语言与评测规范，而非问答检索算法（第 3–5 页、图 2、表 1）。
- **实验**：在 SQL/SQLite 参考后端测规划（SMA）、可执行率（ESR）和执行正确率（EMR）。第 8 页表 2 中 GPT-4o 的 ESR 为 0.9484，但 EMR 只有 0.2532，说明“能执行”离“做对了”还差很远。
- **局限与启发**：主实验集中在参考后端，跨真实记忆框架的大规模对比还是后续工作（第 5、7 页）。课设可借鉴其结构化校验和清晰操作日志的做法，不必造一整套“记忆操作系统”。
- **代码与位置**：[官方仓库](https://github.com/MemTensor/text2mem/tree/f934c4b9763297bdce049365b13d09ea6fb8fd33) 含 `bench/data/benchmark/benchmark.jsonl` 与评测代码，因任务形态不同，不单独另开第二条必做主线。

## 综合定位

| 论文 | 在本课设中的作用 | 主要门槛或差异 |
| --- | --- | --- |
| **StructMem** | 主复现对象与阶段二改进底座 | API 构建/问答成本、论文与代码配置对齐 |
| **Hindsight** | 多路检索、预算与时间建模参考 | 数据库服务部署重，原生 `reflect` 差异大 |
| **Semantic XPath** | 结构范围选择与分层归因启发 | 树结构与查询生成适配 |
| **HyMEM** | 记忆更新与工作记忆刷新参考 | 依赖多模态微调、轨迹与 GUI 环境 |
| **MetaMem** | 证据利用错误分析参考（衔接个人试点） | 需独立训练/验证集与多次 API 采样 |
| **Text2Mem** | 操作语义与接口校验设计参考 | 属于操作规范评测，与问答任务不同 |

补充基准文档：[LoCoMo](https://github.com/snap-research/locomo)（含对话时间、说话人、题型与证据标注，本课设主数据集）和 [LongMemEval](https://github.com/xiaowu0162/LongMemEval)（侧重知识更新与拒答；oracle 版只适合测证据利用，不能替代完整长历史）。仓库里 6 篇本地 PDF 的 SHA-256 均已核对并与 `sources.json` 一致。
