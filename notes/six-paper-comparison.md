# 六篇结构化记忆论文复现条件核查

阅读与代码入口核查日期：2026-10-15。页码均指仓库 PDF 从第 1 页开始的页序，不是论文页脚的会议连续页码。以下实验数字均为论文报告值；本笔记未报告新的复现实验结果。

六篇论文覆盖了记忆的组织、访问、更新、利用和操作规范，适合共同构成课设的文献基础。它们的任务、模型和评测方式不同，不适合直接按论文准确率排名，也不需要各自完整复现一套系统。建议以 StructMem 为实现主线，其余工作用于比较、诊断和选择局部改进。具体安排见[项目方案](../docs/project-plan.md)。本笔记补充原文数字、固定代码版本与复现注意事项；已有的[论文比较](paper-comparison.md)及 MetaMem 个人试点另行保留。

## 1. StructMem

原文：[本地 PDF](../papers/structured-memory-group2/01_StructMem.pdf)；[ACL 页面](https://aclanthology.org/2026.acl-short.12/)。

**问题与方法。** 平铺的事实记忆容易丢失事件内的关系与跨事件联系，显式知识图谱又增加构建成本。StructMem 用自然语言分别提取事实和关系，将同一来源时间的条目绑定为事件；按时间窗口汇集新事件，检索历史种子条目，再补齐对应事件上下文，生成单独保存的跨事件综合记忆。事件重建首先出现在记忆综合阶段，不能据此假定问答阶段已经采用同样的事件扩展。见第 2–3 页、图 2、公式 1–6。

**实验与具体复现目标。** 主实验是 LoCoMo 问答，采用 `gpt-4o-mini` 和 `text-embedding-3-small`。第 8 页附录给出 1 小时综合窗口、15 个历史种子、问答检索 60 个条目和 5 个综合记忆。四类题目分别为单跳 841、多跳 282、时间 321、开放域 96，共 1540 题；这一口径不含对抗题。第 4 页表 1 报告总体 76.82%、时间题 81.62%；构建阶段为 1.937M tokens、1056 次调用。这些构建开销不包含完整问答与评分开销。

**关键消融。** 第 4 页表 2 比较 flat、event without synthesis 与完整 StructMem。简化方案保留后两组，另以原始对话 Flat RAG 建立基线；原始对话检索不同于论文的平铺事实消融，不能混称。完整方法多跳为 68.77%，高于自身去掉跨事件综合的 66.31%，但不是表 1 所有外部基线中的最高分。应该复现具体机制和分类变化，不能把论文的总体优势扩写为“每一类都领先”。

**局限与启发。** 第 6 页明确指出提示词敏感，以及缺少显式冲突解决和记忆更新机制。对课设而言，检索粒度、综合记忆的证据可追溯性、时间信息利用都是可检查的小切口；冲突更新还涉及历史状态保留，改动明显更大。

**代码条件。** 官方实现位于 [LightMem 的 StructMem 说明](https://github.com/zjunlp/LightMem/blob/8449d574df6bae1bdf3314a1564da65e2f37e046/StructMem.md)，并有 [LoCoMo 实验说明](https://github.com/zjunlp/LightMem/blob/8449d574df6bae1bdf3314a1564da65e2f37e046/experiments/locomo/readme.md)。本次核查发现：

- 当前构建脚本采用本地 Hugging Face 嵌入、384 维索引和 CUDA 压缩配置，不能把默认运行直接称为论文的 OpenAI 嵌入配置复现。
- 构建脚本完整参数名是 `--summary_top_k_seeds`；说明示例写成较短的 `--summary_top_k`。后续命令应以固定版本的解析器为准。
- 需要对齐实际分段、压缩、提示词、更新步骤与事件来源标识，不能只打开 `event` 和 `summary` 两个选项就认为配置完全一致。
- 当前问答脚本将部分生成/评分异常落成空回答或 0 分；项目评测需单独记录运行失败与正常错误回答，保留总分母和覆盖率，不能静默删题。

以上来自对固定版本 [`add_locomo.py`](https://github.com/zjunlp/LightMem/blob/8449d574df6bae1bdf3314a1564da65e2f37e046/experiments/locomo/add_locomo.py) 与 [`search_locomo.py`](https://github.com/zjunlp/LightMem/blob/8449d574df6bae1bdf3314a1564da65e2f37e046/experiments/locomo/search_locomo.py) 的静态检查；尚未安装或执行。

## 2. Hindsight

原文：[本地 PDF](../papers/structured-memory-group2/02_Hindsight.pdf)；[ACL 页面](https://aclanthology.org/2026.acl-demo.27/)。

**问题与方法。** 将 world、experience、observation、opinion 四类信息分开，区分事实、经历、综合观察和主观观点。`retain` 写入，`recall` 检索，`reflect` 利用记忆推理。检索融合向量、关键词、图关系和时间四条通道，再通过 RRF 和交叉编码器排序；时间元数据区分事件发生区间与信息被提及的时间。见第 2–5 页、图 1。

**实验。** 第 6 页表 2 报告 OSS-20B 下 LongMemEval 83.6%、LoCoMo 83.2%，另有更大模型结果。其 backbone、检索和反思流程与 StructMem 不同，不能用 83.2 与 76.82 直接判定结构优劣。正文分类对比也不能替代逐一关闭四条检索通道的受控消融。

**局限与启发。** 第 8 页指出抽取错误可能传播、评测仅覆盖英语、观点机制缺少正式用户研究。可借鉴多路召回、时间字段和证据/观点分离；这些机制已经是已有工作，简单移植不能声称首创。

**代码条件与项目位置。** [官方仓库](https://github.com/vectorize-io/hindsight/tree/d5b1d4282f3325116c06f76ce3e79dce5ea4e22c) 有服务和部署入口；论文系统依赖 PostgreSQL 与 pgvector。当前工程规模和版本演进增加了论文版本对齐成本。可作为后续外部系统对照的参考，当前简化方案不要求部署。若只接入 `recall` 并使用项目统一回答器，须标注为检索模块对照；原生 `reflect` 的端到端结果另列。

## 3. Semantic XPath

原文：[本地 PDF](../papers/structured-memory-group2/03_Semantic_XPath.pdf)；[ACL 页面](https://aclanthology.org/2026.acl-demo.28/)。

**问题与方法。** 对具有层级结构的任务状态，平铺检索容易找对主题却找错范围，例如把另一天的活动拿来修改。方法将用户请求翻译成 XPath 风格查询，结合结构导航、节点/位置选择和语义分数聚合，定位相关子树后交给下游生成与更新。旅行示例使用 Itinerary → Version → Day → POI；LoCoMo 使用 Conversation → Session → Turn 的自然层级。见第 2–5 页、图 2、§3。

**实验。** 三个自建领域是行程、待办和餐食计划，每个领域有 20 个单轮会话、5 个多轮会话；另外评测 LoCoMo。第 7 页表 1 中，GPT-5 mini 下 LoCoMo 的 Flat RAG / Semantic XPath / In-context 分别为 35.71 / 65.19 / 74.55；Semantic XPath 的平均输入为 3032 tokens，包含查询生成。摘要中的 176.7% 和 9.1% 不能当作 LoCoMo 上的一般结论。

**局限与启发。** 依赖已有层级和查询生成、语义评分的质量；第 6–7 页错误分析显示检索仍是主要失败来源。课设可借鉴“检索正确范围”和按查询、检索、生成分层归因，不必实现完整查询语言。

**代码条件与项目位置。** [官方仓库](https://github.com/D3Mlab/SemanticXpath-Chat/tree/116a704fdf6496c2855fa212167702d01ca1a6df) 提供树查询引擎和前后端 demo；本次目录与 README 核查未定位到独立的论文全套评测入口，不能据此认定数据不存在。适合演示参考或后续小规模对照，暂不列为必做复现。

## 4. Hybrid Self-evolving Structured Memory（HyMEM）

原文：[本地 PDF](../papers/structured-memory-group2/04_Hybrid_Self-evolving_Structured_Memory.pdf)；[ACL 页面](https://aclanthology.org/2026.findings-acl.549/)。

**问题与方法。** 面向电脑操作智能体，结合离散策略/属性与连续多模态轨迹表示，以图组织经验。新轨迹经过相关节点检索和冗余判断，执行 ADD、MERGE、REPLACE；任务执行时检测阶段变化并刷新工作记忆。连续表示要接入 VLM 的嵌入层，不能简单等同于给聊天 API 多传一段文本。见第 3–5 页、图 1。

**实验与成本。** 在 WebVoyager、Multimodal-Mind2Web、MMInA 上评估任务成功率。第 7 页表 2 报告 Qwen2.5-VL-7B 总体从 12.5% 到 35.0%，是 22.5 个百分点。第 5 页使用 2883 条成功轨迹构建记忆；第 13 页附录报告 Q-Former 与 LoRA 训练更新约 1.2% 参数，单张 H100 在 20 小时内完成。这是作者条件下的成本，不能直接折算到游戏本或 DCU。

**局限与启发。** 网页可用性、截图、定位模型、轨迹数据和执行环境都会影响复现。可以借鉴“只在新增信息有价值时更新”和“必要时刷新上下文”的思想，但在纯文本项目中移植思想不构成 HyMEM 的完整复现。

**代码条件与项目位置。** [官方仓库](https://github.com/NickSiboZhu/HyMEM-GUI-Agent/tree/911722c99c8c3fa0052cbb1f596e13d691610ed5) 分训练和推理两部分，README 要求连续记忆 checkpoint、轨迹与模型服务，且提示训练脚本含机器相关绝对路径。当前桌面 GPU 和几十元 API 预算下，将其作为相关工作与更新策略参考。

## 5. MetaMem

原文：[本地 PDF](../papers/structured-memory-group2/05_MetaMem.pdf)；[ACL 页面](https://aclanthology.org/2026.findings-acl.270/)。

**问题与方法。** 关注“证据已经取回，但模型不会正确利用”：例如将旅行总里程与其中一天里程重复相加。事实记忆之外维护可迁移的使用经验，通过多次回答采样、带标准答案的评价、自我反思、ADD/MOD/DEL 和冲突过滤更新元记忆。这里的优化对象是符号经验，不是通过反向传播更新基座参数。见第 3–5 页、图 2。

**实验。** 使用 LongMemEval、LightMem 事实记忆，backbone 为 Qwen3-30B-A3B-Instruct / Llama3.1-70B-Instruct，默认判断模型为 Qwen3-235B-A22B。第 6 页表 1 中 LightMem → MetaMem 为 67.50 → 71.90、66.17 → 69.08，分别增加 4.40、2.91 个百分点；不应将摘要的“超过 3.6%”改写成两种模型都增加至少 3.6 个百分点。

**复现细节。** 第 11 页 A.3/A.5 给出每样本采样 5 次、5 个 epoch、batch size 50；五折每折为 350 训练、50 验证、100 测试。正文概括的“400 用于构建”需要结合附录理解。不能在测试答案上生成规则，再报告同一测试集的改进。

**局限与启发。** 依赖评价反馈，规则过多可能导致冗余和过拟合（第 12 页 A.6）。不训练基座不等于成本低：反复采样与评分会消耗 API。在更深入研究中可尝试的小改进是：在独立开发数据中生成少量规则并冻结，与无规则、人工规则进行对照。这个缩小版本要标注为受 MetaMem 启发的实验。

**代码条件。** [官方仓库](https://github.com/OpenBMB/MetaMem/tree/66232c1cb33d3d7939d323b431f21c741785142e) 给出了构建、数据划分、优化和评价脚本；README 的原配置包含较大的本地模型。后续若采用 DeepSeek，仍需记录替换条件，不能默认完整复现原表格。

## 6. Text2Mem

原文：[本地 PDF](../papers/structured-memory-group2/06_Text2Mem.pdf)；[ACL 页面](https://aclanthology.org/2026.findings-acl.100/)。

**问题与方法。** 解决自然语言记忆控制的歧义与执行不一致。定义 12 类操作，包括 Encode、Update、Label、Promote、Demote、Merge、Split、Delete、Lock、Expire、Retrieve、Summarize；由结构化 schema 经 validator、parser、adapter 执行。它是操作语言与评测规范，不是一种直接替代 StructMem 的问答检索算法。见第 3–5 页、图 2、表 1。

**实验。** SQL/SQLite 参考环境中分别评测规划和执行效果。SMA 衡量生成结构与参考的相似性，ESR 衡量能否执行，EMR 衡量数据库断言是否满足。第 8 页表 2 中 GPT-4o 的 ESR 为 0.9484，而 EMR 为 0.2532，说明可执行不等于实现了正确意图。表中是不同指标，不能拿 EMR 与 LoCoMo 问答准确率直接比较。

**局限与启发。** 主实验集中在参考后端，大规模跨真实记忆框架对比仍是后续工作（第 5、7 页）；正文中较宽泛的适配描述不能替代实际跨后端实验。课设可以借鉴明确的记忆操作记录和结果校验，无需因此实现一整套“记忆操作系统”。

**代码条件与项目位置。** [官方仓库](https://github.com/MemTensor/text2mem/tree/f934c4b9763297bdce049365b13d09ea6fb8fd33) 包含 `bench/data/benchmark/benchmark.jsonl` 与 benchmark 代码。它可以形成独立的小型操作正确性实验，但与主问答任务不同，暂不扩展为第二条必做主线。

## 综合判断

| 论文 | 在本项目中的作用 | 主要成本或边界 |
| --- | --- | --- |
| StructMem | 主复现对象；去除跨事件综合的消融 | API 构建与问答开销，论文与代码配置对齐 |
| Hindsight | 检索与时间建模参考 | 服务部署、版本与原生 reflect 差异 |
| Semantic XPath | 范围感知检索和错误归因参考 | 树结构、语义评分与评测数据适配 |
| HyMEM | 记忆更新和工作记忆刷新参考 | 多模态训练、轨迹、网页环境 |
| MetaMem | 证据利用错误分析参考，衔接已有个人试点 | 独立训练/验证数据，多次 API 采样 |
| Text2Mem | 操作语义与验证设计参考 | 与问答不同的任务和指标 |

补充阅读限定为所选基准的原始说明：[LoCoMo](https://github.com/snap-research/locomo)、[LongMemEval](https://github.com/xiaowu0162/LongMemEval)。前者有对话时间、说话人、问题类别及部分证据标注；后者可检查知识更新与拒答，但 S 版本历史已经较长，oracle 版本只适合证据利用诊断，不能冒充完整长历史任务。当前不需要继续扩充一长串方法论文。

本次六个本地 PDF 的 SHA-256 均与仓库 `sources.json` 一致。官方仓库核查仅确认了可访问的说明、目录和部分关键代码；可运行性、模型兼容性及实验效果由后续复现阶段验收。
