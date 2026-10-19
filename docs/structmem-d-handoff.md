# D：综合、检索与 C/F 交接准备

负责人：`lanshuheng9-oss`；技术任务 [#28](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/28)。日期：2026-10-19。

当前完成的是原生 point 读取、检索适配、固定参数调用和离线接口检查。**真实事件记忆、真实综合、真实 S2 问答均未完成。** 本文是基于上游代码的交接提案，尚未得到 C/F 的人工确认；不能把读取公开交付理解为成员已经共同确认接口。

## 1. 已核对的 A 输入

读取 A 的 [PR #38](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/38)，固定提交 `1d651da44cd1bf101ead69794a74f45f91c507a3`。其代码仍在待审分支，本次仅在 `tmp/structmem-d-deps/a/` 使用固定副本，没有合并或修改 A 的交付。

已使用 A 的脚本在本机重新生成：

| 内容 | 本机路径或固定值 |
| --- | --- |
| 官方数据 | `data/raw/locomo10.json`，2,805,274 字节 |
| 数据 SHA-256 | `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4` |
| 开发会话 | `conv-48`、`conv-42`、`conv-41` |
| 3/7 会话划分 | 沿用 A；本轮不运行留出会话 |
| 30/5 题 | `data/locomo/development.inputs.json`、`data/locomo/smoke.inputs.json` |
| 构建输入 | `data/locomo/development.conversations.json`；仅对话，不含 `qa` 或标签 |
| 题目主键 | `(sample_id, qa_index)`；原始 0 起始索引，不重编号 |
| 上游 | LightMem `8449d574df6bae1bdf3314a1564da65e2f37e046` |
| 嵌入 | all-MiniLM-L6-v2 `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`，384 维、归一化、最大长度 256 |

A 的所有输出文件哈希与冻结配置一致；D 的后续入口只读题目与记忆，不加载 `*.labels.json`。标准答案仅由 E 评分时关联。完整 LightMem/CUDA 依赖、本机 MiniLM 加载未在本轮验证；已下载的是小型数据及上游源码，没有新模型权重。

## 2. C → D：沿用原生格式交接

C 负责人为 `oioioi-521`（[#32](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/32)）。当前 issue 尚未提供真实记忆或构建配置。请先交一份完整 session 的真实事件记忆，随后交三个开发会话的完整版本，并保留构建命令、配置、状态及来源映射。

1. C 使用 A 的完整开发对话，保留时间、说话人和消息 ID；不使用问题答案、评分 evidence 或数据集预生成总结来构建记忆。
2. C 关闭相关 Qdrant 客户端后交付明确版本的数据库副本，说明实际 `collection_name`、目录、条目数和文件哈希。D 使用自己的副本运行综合，不写 C 的工作目录。
3. 导出时使用上游 retriever 的 `get_all(with_vectors=True, with_payload=True)`，保留原生 `id`、`payload`、`vector` 数组，使用 JSON 保存。不要手写“简化事实表”替代原始 point，不将 SQLite pickle 当作交接格式。
4. 同时提供原始消息 `dia_id` 与抽取条目的映射（如已保留）。原生 point UUID 能标识记忆，但不自动等于原始消息 ID；D 不从标准答案 evidence 补造映射。

原生事件 payload 在上游 `offline_update` 中保存 `memory` / `original_memory` / `compressed_memory`、`time_stamp`、`float_time_stamp`、`weekday`、`topic_id`、`speaker_id/name`、`consolidated` 等字段；额外字段原样保留。D 的展示文本取上游相同的 memory 优先级，并保留完整 ISO 时间与说话人。检索分数和全部 payload 另存 provenance，不丢弃额外元数据。

综合后的原生摘要 payload 为 `summary`、`time_range`、`covered_entry_ids`、`seed_entry_ids`、`created_at`、`entry_count`、`seed_count`。D 校验摘要关联的事件存在于同一会话快照；不能把不同会话的 point 混在一起。

这些字段来自固定版代码，不要求 C 为 D 重写上游存储结构。JSON 导出只是读取边界，额外的索引清单用于标识版本、会话及文件哈希。

## 3. 综合调用与已发现的上游差异

当前提供 `src/structmem_retrieve.py::summarize_memory` 薄调用，对已有原生 LightMemory 实例执行：

```python
memory.summarize(
    retrieval_scope="global",
    time_window=3600,
    top_k_seeds=15,
    process_all=True,
    enable_cross_event=True,
)
```

此函数只有参数转交测试，**未实际加载 LightMemory 或发起综合请求**。真实执行前仍需 C 的可加载构建配置、事件数据库副本，以及与 F 对齐的 DeepSeek 抽取/综合客户端设置和明确调用条件；本次没有生成带凭据的配置或新增模型客户端。

固定版代码核对发现：

- `StructMem.md` 的示例参数写作 `top_k`，实际 `LightMemory.summarize` 和 `add_locomo.py` 使用 **`top_k_seeds`**；D 使用实际签名。
- `add_locomo.py::load_lightmem` 的摘要集合及目录使用 **`<sample_id>_summary`**，`QdrantEntryLoader` 默认后缀却是 `_summaries`。应读取实例实际的 `summary_retriever` 导出；不按默认后缀猜路径，也不以空集合当作 S2 成功。
- 上游综合会修改事件的 `consolidated` 标记，并使用模块级 `GLOBAL_LAST_SUMMARY_TIME`。每个会话应在新进程、D 独立数据库副本中运行；不在同一进程连续处理三份会话而继承时间指针，不通过重置 C 的原库标记来重跑。
- 上游完整包声明 Python `>=3.10,<3.12`。本轮标准库适配在 Python 3.12.14 检查通过，不能据此声称完整 LightMem 可导入或 CUDA 构建通过。

原文位置：[综合签名](https://github.com/zjunlp/LightMem/blob/8449d574df6bae1bdf3314a1564da65e2f37e046/src/lightmem/memory/lightmem.py#L752)、[摘要存储](https://github.com/zjunlp/LightMem/blob/8449d574df6bae1bdf3314a1564da65e2f37e046/src/lightmem/memory/utils.py#L547)、[构建入口](https://github.com/zjunlp/LightMem/blob/8449d574df6bae1bdf3314a1564da65e2f37e046/experiments/locomo/add_locomo.py)、[读取及向量排序](https://github.com/zjunlp/LightMem/blob/8449d574df6bae1bdf3314a1564da65e2f37e046/experiments/locomo/retrievers.py)。文件 SHA-256 见核验 JSON。

## 4. D 的读取索引与命令

完成真实综合、导出 events 和 summaries 后，在本地 `data/structmem-d/memory-index.json` 登记以下结构；三个开发会话分别登记，下面只展开一项。路径相对该 index 文件；占位哈希必须替换为实际值。此提案待 C 审核，不表示 C 已交付这些文件。

```json
{
  "upstream_revision": "8449d574df6bae1bdf3314a1564da65e2f37e046",
  "source_conversations_sha256": "87cc2e08c7c32344a9f0c17aa6d2729520e5156a9062c9d04d8e85de2ccbc136",
  "embedding": {
    "model_id": "sentence-transformers/all-MiniLM-L6-v2",
    "revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
    "dimensions": 384,
    "normalize_embeddings": true,
    "max_seq_length": 256
  },
  "synthetic": false,
  "conversations": {
    "conv-48": {
      "event": {"path": "conv-48.events.json", "sha256": "<实际哈希>"},
      "synthesis": {"path": "conv-48.summaries.json", "sha256": "<实际哈希>"}
    }
  }
}
```

已有 A 固定模型离线缓存和完整真实记忆后运行；当前未执行这条真实命令：

```powershell
python scripts/retrieve_structmem.py `
  --input data/locomo/smoke.inputs.json `
  --frozen-config tmp/structmem-d-deps/a/configs/locomo-smoke.json `
  --memory-index data/structmem-d/memory-index.json `
  --model-cache data/model-cache `
  --out output/structmem-d-real5
```

A 合并后，`--frozen-config` 改用仓库中的 `configs/locomo-smoke.json`。真实 30 题仅将 input 改为 `development.inputs.json`，使用新输出目录。

入口在加载嵌入前检查 A 的有序 5/30 题和精确文件哈希、开发会话、上游/模型版本、原始对话哈希及 point 文件哈希。缺少摘要、无向量、错误维度、非有限数、零向量、重复 ID、标签字段、摘要悬空引用都会报错，不静默跳过。CLI 拒绝构造记忆，无自动下载、API 调用或覆盖旧输出。

排序是固定版 `VectorRetriever` 全会话 combined cosine 排序的标准库移植；60 个事件条目与 5 个综合记忆分别取 top-k，条目不足时保留实际数目。没有加入 BM25、重排、额外补齐或说话人配额。模型仅在已有固定 revision 缓存中通过 SentenceTransformer 加载，查询归一化；本机未实际运行此模型路径。

输出：`retrieval.jsonl` 符合 F 的四个题目字段加 `contexts`；`provenance.json` 保存逐题分数及完整 payload；`run.json` 保存配置/输入/point/代码哈希和 `retrieval_only` 状态。检索完成不等于回答、评分或 S2 验收完成。

## 5. D → F 与本轮实际验证

F 固定版本为 [PR #35](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/35) 的 `4206096a2929256b4be55d28c105e441e367ad63`。首次离线核验使用 `tmp/structmem-d-deps/f/` 固定副本，当时未合并或改动 F 客户端。

后续检查确认 PR #35 已合并到 main `8b6fcd73c3a15acea4dcc00e52a4b2debc50146d`。D 分支已同步这次 main，保留 README 中双方的入口；当前直接使用仓库内的 `scripts/run_qa.py`、`src/llm_client.py` 和 `configs/qa.example.json`，不再依赖 F 临时副本。新增一个 D→F 离线测试，检验 D 产物可以被当前 F 入口读取并保持模拟状态；本次仍未改动 F 的客户端行为。

F 另在 [PR #42](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/42) 交付了 S0 的 30 题真实回答，等待 E 评分。这是 F/S0 的进度，不是 D/S2 的真实实验，也不消除 C 真实事件记忆缺失的依赖。D PR #41 仍待 C 审核，未请求重复审核或催审。

- `contexts` 每项仅含 `source_ids`、`kind`、`text`；kind 为 `event` 或 `synthesis`。
- ID 使用 `<sample_id>/event/<point_id>` 或 `<sample_id>/synthesis/<point_id>`；综合项同时列出原生 covered/seed 事件 ID。不将这些 ID 冒称原始 `dia_id`。
- 文本保留说话人、完整来源时间、事件内容和综合时间范围；所有原生 payload 保存在 provenance。
- F 当前只序列化 JSON 上下文，不能直接套用上游双说话人分组模板。**本轮没有冻结 S2 正式提示词**；真实调用前与 F 保留上游时间推理指令，明确 JSON 展示与原版分组格式的差异，再统一审阅配置。示例提示词只用于 mock。

实际结果：

| 验证 | 结果与边界 |
| --- | --- |
| A 数据复跑 | 30/5 题、开发对话及标签文件的输出哈希均匹配 A 冻结清单；D 未加载标签内容 |
| D 针对性测试 | 9 项通过，覆盖联合主键、标签隔离、来源/时间、版本/哈希、向量异常、摘要关联、防覆盖与综合参数 |
| F 固定版测试 | 14 项通过；临时副本最初漏取其 fixture，补回同一版本文件后通过，未修改 F 代码 |
| 上游排序对照 | 从固定源码取原版 VectorRetriever 类，用 NumPy 执行对照；2,275 个选中分数，排序一致，最大绝对差 `5.55e-17` |
| 5/30 题离线联调 | A 的真实冻结问题＋显式构造的事件/摘要/向量，每题 60＋5 个上下文，通过 F；分别 5/30 simulated，真实回答 0 |
| 未做 | 本机 MiniLM 加载、完整 LightMem 导入、C 真实记忆、真实综合/回答/评分、人工验收 |

核验：[structmem-d-verification.json](../reports/structmem-d-verification.json)。构造 point、逐题检索和模拟调用原始文件仅在 `output/structmem-d-offline-20261019/`，文本均有 SYNTHETIC 标记，CLI 不允许用于真实检索。差分检查临时脚本为 `tmp/check_structmem_d.py`；普通针对性测试可直接运行：

```powershell
python -W error::ResourceWarning -m unittest discover -s tests -p test_structmem_retrieve.py -v
```

上表保留首次检查的 9 项 D 测试和 14 项 F 测试历史。同步 main 后，D 测试增加到 10 项、F 仍为 14 项，全部通过；另用当前正式入口对先前明确构造的 5 题文件执行 `--mock`，得到 5 simulated、真实成功回答 0。补充记录见 [main 接入核验](../reports/structmem-d-main-integration-20261019.json)。

## 6. 下一次真实验收所需交接

1. C 给出完整 session 的真实事件副本、实际构建配置和 point 导出，确认模型/时间/来源映射；当前不是要求用户代写 C 的代码。
2. D 在独立副本和匹配的完整上游环境运行综合，导出真实摘要并记录调用与失败；本轮没有可据以填写的真实调用成绩。
3. F 与 D 对齐正式 S2 提示词及项目调用条件，再跑冻结 5 题，经 E 评分后推进同一 30 题。
4. 各人准备自己的 1–2 页进展；D 当前材料见 [进展页](../reports/structmem-d-progress.md)，尚未作人工案例核查或整组研讨定稿。

如记忆数据库、模型或日志单文件达到 20 MB，请将该文件发送到小组微信群；仓库只保留版本、大小、用途、获取方式及哈希，未发送时不填写发送日期。本轮没有代发群消息。
