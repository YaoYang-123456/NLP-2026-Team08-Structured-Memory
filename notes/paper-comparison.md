# 六篇论文比较与课设选择依据

核对日期：2026-10-15。用途：专题阅读与选题讨论，不是六篇论文的复现报告。页码均指仓库 PDF 从 1 开始的文件页码。方法描述来自论文；难度和推进顺序是本组准备阶段的判断。六篇 PDF 均已与 `papers/structured-memory-group2/sources.json` 的 SHA-256 对照一致。

## 先看结论

建议先用 MetaMem 做一个小规模、可撤回的实验试点，因为它与杨垚的个人阅读直接衔接，核心变量是“是否提供学到的记忆使用规则”，便于设计对照。**这不是已经确定全组课设，也不意味着 MetaMem 全量复现最便宜。** 若侧重能直观看到状态变化的演示，Text2Mem 和 Semantic XPath 值得优先讨论；若侧重长对话问答，StructMem 是强候选。

不应把六篇文章的准确率排成统一排行榜：它们的任务、数据、模型、评判器、训练数据使用方式都不同。尤其 MetaMem 会在 LongMemEval 的部分样本上学习规则，与只在整套数据上零样本测试的方法不是同一协议。

## 方法、实验和实现负担

| 论文 | 核心问题与方法 | 论文评价对象 | 官方实现核对 | 课设负担判断 |
| --- | --- | --- | --- | --- |
| [01 StructMem](../papers/structured-memory-group2/01_StructMem.pdf) | 将事实与关系描述绑定到带时间的事件，周期性综合语义相关事件；用文本保留结构，不强制转成实体关系图 | LoCoMo；回答质量及记忆构建 token、调用次数、时间；见 §3–4，PDF pp.2–5 | [LightMem / StructMem.md](https://github.com/zjunlp/LightMem/blob/main/StructMem.md) 已说明 event 提取、独立摘要集合和跨事件综合入口 | 中等。需做提取、向量检索和多阶段调用；适合比较平面事实、事件绑定、跨事件综合 |
| [02 Hindsight](../papers/structured-memory-group2/02_Hindsight.pdf) | world、experience、observation、opinion 四类逻辑网络；retain、recall、reflect；融合语义、关键词、图和时间检索 | LongMemEval、LoCoMo；见 §3、§6，PDF pp.2–7 | [官方仓库](https://github.com/vectorize-io/hindsight) README 提供 Docker、客户端和多种后端入口 | 跑现成服务可较快，理解和修改完整系统更重。涉及 PostgreSQL、检索融合、重排等；演示成功不等于复现论文成绩 |
| [03 Semantic XPath](../papers/structured-memory-group2/03_Semantic_XPath.pdf) | 在树形任务记忆上生成 XPath 风格查询，结合结构导航与语义打分，检索子树再更新任务状态 | 行程、待办、餐单三类任务，以及 LoCoMo；正确性、token 使用；见 §3–4，PDF pp.3–7 | [官方仓库](https://github.com/D3Mlab/SemanticXpath-Chat) 有 Python 后端、CLI、React 界面；默认蕴含评分配置涉及 Modal，不能假定开箱全本地 | 中等。树结构和状态变化容易讲清；完整多轮评测、查询解析和评分配置仍需工作 |
| [04 HyMEM](../papers/structured-memory-group2/04_Hybrid_Self-evolving_Structured_Memory.pdf) | 融合轨迹连续表示与离散策略、属性；图检索、全局记忆更新、执行中刷新工作记忆 | WebVoyager、Multimodal-Mind2Web、MMInA；见 §3–4，PDF pp.3–7 | PDF 首页链接指向 [HyMEM-GUI-Agent](https://github.com/NickSiboZhu/HyMEM-GUI-Agent)；README 包含 Q-Former＋LoRA 训练、浏览器和模型服务 | 高。多模态模型、轨迹、检查点和交互环境同时参与；不建议作为第一条跑通路线 |
| [05 MetaMem](../papers/structured-memory-group2/05_MetaMem.pdf) | 在事实记忆外学习“如何使用事实”的经验规则；多次生成、评判、反思、批量编辑规则 | LongMemEval 五折；ShareGPT 用于域外经验学习；见 §3–5、附录 A.2–A.5，PDF pp.3–8、11–12 | [官方仓库](https://github.com/OpenBMB/MetaMem) 提供构建、训练、验证和推理脚本；主干不靠反向传播学习规则 | 核心原型中等，全量实验成本高。原配置有 30B/70B 生成模型和 235B judge，多次采样放大调用数 |
| [06 Text2Mem](../papers/structured-memory-group2/06_Text2Mem.pdf) | 自然语言 → 有类型的记忆操作 schema → 校验 → 执行；覆盖 12 个操作 | 自有 benchmark；schema 相似度、执行成功率、数据库断言满足率；SQLite 参考后端；见 §3–5，PDF pp.3–9 | [官方仓库](https://github.com/MemTensor/Text2Mem) 提供 mock、Ollama、OpenAI 路径和 CLI | 小原型相对可控。状态可验证，适合工程演示；要避免只做 CRUD 包装。mock 只验证流程，不证明自然语言理解能力 |

## 六篇如何组成一份系统调研

可以围绕“记什么 → 怎样组织 → 怎样找 → 怎样用 → 怎样改 → 怎样验证”组织汇报，而非连续堆六份摘要。

- **组织和检索：**StructMem 的事件层次、Semantic XPath 的树、HyMEM 的图与轨迹表示。
- **使用和演化：**MetaMem 的可迁移经验；Hindsight 的反思、意见和事实区分。
- **操作和验证：**Text2Mem 的类型化操作与执行后状态；Hindsight 的生命周期接口。

这只是比较维度，不能把某方法限制在其中一个模块。特别是 Hindsight 也有结构检索，HyMEM 也有更新机制。

## 选择课设时的三条路线

| 路线 | 可回答的问题 | 最小对照 | 暂时不加入 |
| --- | --- | --- | --- |
| A：MetaMem 小规模试点，当前优先建议 | 固定检索事实后，学到的使用规则能否改善时间、冲突或多会话推理？ | 无规则／人工固定规则／训练生成规则 | 五折全量、多模型横评、完整产品界面 |
| B：StructMem 事件组织 | 改变组织方式能否在相近上下文预算下改善问答？ | 平面事实／事件绑定／事件绑定＋跨事件综合 | 重做全部竞品系统 |
| C：Text2Mem 或 Semantic XPath 状态操作 | 怎样减少“执行成功但修改错对象”的情况？ | 基础生成／增加结构或状态约束 | 同时实现十二种操作和多个复杂后端 |

路线 A 不预先宣称优于 B 或 C。先跑通一个小样本闭环，观察真实调用量、失败类型，再让全组据此决定实施主线。第一轮不把六篇拼成一个大框架。

## 每位成员阅读时应提供的材料

每篇至少说明：任务与输入输出、核心方法图、一个贯穿例子、主实验和消融、局限、代码/数据入口、对课设可复用的部分。数字标明表号和实验条件。阅读草稿可以使用 AI 辅助，成员仍需核对并能解释自己负责的内容。

官方代码入口均在本轮读取过 README；其中 MetaMem 另审阅了训练、推理、数据处理和划分代码。其他仓库没有实际安装运行。更细的 MetaMem 结论见 [阅读笔记](05-metamem-YaoYang-123456.md)、[代码审阅](../docs/metamem-code-review.md) 和 [试点方案](../docs/metamem-pilot.md)。
