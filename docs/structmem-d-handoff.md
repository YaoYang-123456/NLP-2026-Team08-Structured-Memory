# D：综合、检索与 C/F 交接准备

> 2026-10-21 更新：D 的 C/F 审核已通过，PR #41 已合并、任务 #28 已结项；60 条裁判输入已离线核对和复算，结果为原始 S0 16/30、S2 19/30，日期裁定后 15/30、19/30。E 任务记录已确认本人至少四例核查。当前状态见[个人结项进展](../reports/structmem-d-progress.md)及[结项机器记录](../reports/structmem-d-closeout-20261021.json)。下文保留 10 月 20 日技术交接与当时待办的历史快照，旧 accuracy=null 不改写。

负责人：`lanshuheng9-oss`；技术任务 [#28](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/28)。更新日期：2026-10-20。

当前已完成完整事件接收、91 次真实综合、同一 30 题的 60＋5 检索与真实 S2 回答。**E 已报告自动评分，逐题裁判独立复算及成员人工案例验收仍未完成。** 最新记录见 [真实运行与交接](structmem-real-run-20261020.md)；原事件包接收与离线准备保留为历史证据。

2026-10-19 首次收到 C 的 conv-48/session_1，历史记录见[首个 session 接收验收](structmem-session-receipt-20261019.md)。2026-10-20 已收到并验证 91 个 session、3712 条完整开发事件；旧记录的 1/30 范围仅描述首次交接。

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

A 的输出哈希与冻结配置一致；D 只读题目与记忆，不加载标签。固定 MiniLM 已实际加载并重算全部事件向量；原生 LightMemory 已导入并完成无网络综合预演。实际 Python 3.13 与上游声明版本不同，CUDA 未验证，环境差异见最新接收记录。

## 2. C → D：沿用原生格式交接

C 负责人为 `oioioi-521`（[#32](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/32)，实现 [PR #43](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/43)）。三个开发会话的完整事件库已通过用户文件交接，来源与 91 个 session 输入均已独立验收。以实际收到文件为依据，不据旧 issue 断言记忆仍缺失。

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

该函数先完成 91 窗口离线预演，随后官方输入已实际调用模型，91 次全部成功。真实响应在三个新进程、新副本中回填原生综合流程，全部请求与重建消息逐字一致，3712 条事件恰好覆盖一次；回填不新增 API 调用。占位摘要及预演库没有用于真实检索。完整调用、原生导出及验证见最新真实运行记录。

固定版代码核对发现：

- `StructMem.md` 的示例参数写作 `top_k`，实际 `LightMemory.summarize` 和 `add_locomo.py` 使用 **`top_k_seeds`**；D 使用实际签名。
- `add_locomo.py::load_lightmem` 的摘要集合及目录使用 **`<sample_id>_summary`**，`QdrantEntryLoader` 默认后缀却是 `_summaries`。应读取实例实际的 `summary_retriever` 导出；不按默认后缀猜路径，也不以空集合当作 S2 成功。
- 上游综合会修改事件的 `consolidated` 标记，并使用模块级 `GLOBAL_LAST_SUMMARY_TIME`。每个会话应在新进程、D 独立数据库副本中运行；不在同一进程连续处理三份会话而继承时间指针，不通过重置 C 的原库标记来重跑。
- 上游完整包声明 Python >=3.10,<3.12。标准库适配测试使用 Python 3.12.14；本机 Python 3.13.9 的原生导入与离线综合也已实际通过，但不声称与上游声明环境一致，CUDA 仍未验证。

原文位置：[综合签名](https://github.com/zjunlp/LightMem/blob/8449d574df6bae1bdf3314a1564da65e2f37e046/src/lightmem/memory/lightmem.py#L752)、[摘要存储](https://github.com/zjunlp/LightMem/blob/8449d574df6bae1bdf3314a1564da65e2f37e046/src/lightmem/memory/utils.py#L547)、[构建入口](https://github.com/zjunlp/LightMem/blob/8449d574df6bae1bdf3314a1564da65e2f37e046/experiments/locomo/add_locomo.py)、[读取及向量排序](https://github.com/zjunlp/LightMem/blob/8449d574df6bae1bdf3314a1564da65e2f37e046/experiments/locomo/retrievers.py)。文件 SHA-256 见核验 JSON。

## 4. D 的读取索引与命令

真实综合已完成，实际索引为 `output/structmem-live-20261020/memory-index.json`。下方保留结构说明，实际三个会话的 events/summaries 路径、哈希均由原生导出生成；示例占位哈希不用于运行。C 的数据/数值审核仍由指定 reviewer 核对。

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

完整 30 题已使用实际 memory-index 完成检索。下方为需要时另建输出目录的 5 题复跑命令，本轮没有为演示命令再次运行：

```powershell
python scripts/retrieve_structmem.py `
  --input data/locomo/smoke.inputs.json `
  --frozen-config tmp/structmem-d-deps/a/configs/locomo-smoke.json `
  --memory-index output/structmem-live-20261020/memory-index.json `
  --model-cache data/model-cache `
  --out output/structmem-d-recheck5
```

A 合并后，`--frozen-config` 改用仓库中的 `configs/locomo-smoke.json`。真实 30 题仅将 input 改为 `development.inputs.json`，使用新输出目录。

入口在加载嵌入前检查 A 的有序 5/30 题和精确文件哈希、开发会话、上游/模型版本、原始对话哈希及 point 文件哈希。缺少摘要、无向量、错误维度、非有限数、零向量、重复 ID、标签字段、摘要悬空引用都会报错，不静默跳过。CLI 拒绝构造记忆，无自动下载、API 调用或覆盖旧输出。

排序是固定版 `VectorRetriever` 全会话 combined cosine 排序的标准库移植；60 个事件条目与 5 个综合记忆分别取 top-k，条目不足时保留实际数目。没有加入 BM25、重排、额外补齐或说话人配额。模型仅在已有固定 revision 缓存中通过 SentenceTransformer 加载，查询归一化；该模型已实际完成全部事件重嵌入、原生综合向量生成及完整 30 题 S2 CLI 检索。

输出：`retrieval.jsonl` 符合 F 的四个题目字段加 `contexts`；`provenance.json` 保存逐题分数及完整 payload；`run.json` 保存配置/输入/point/代码哈希和 `retrieval_only` 状态。检索完成不等于回答、评分或 S2 验收完成。

## 5. D → F 与本轮实际验证

F 固定版本为 [PR #35](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/35) 的 `4206096a2929256b4be55d28c105e441e367ad63`。首次离线核验使用 `tmp/structmem-d-deps/f/` 固定副本，当时未合并或改动 F 客户端。

后续检查确认 PR #35 已合并到 main `8b6fcd73c3a15acea4dcc00e52a4b2debc50146d`。D 分支已同步这次 main，保留 README 中双方的入口；当前直接使用仓库内的 `scripts/run_qa.py`、`src/llm_client.py` 和 `configs/qa.example.json`，不再依赖 F 临时副本。新增一个 D→F 离线测试，检验 D 产物可以被当前 F 入口读取并保持模拟状态；本次仍未改动 F 的客户端行为。

F 在 [PR #42](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/42) 的 S0 真实回答不计作 D/S2 成绩。F 已批准本轮候选原内容，PR #44 固定配置与候选逐字节相同；本轮实际使用其固定提交 14b7b41b561fde1ed5193422ed3084211572e15a 的副本完成 5＋25 题回答。C 数据/数值审核仍保留。

- `contexts` 每项仅含 `source_ids`、`kind`、`text`；kind 为 `event` 或 `synthesis`。
- ID 使用 `<sample_id>/event/<point_id>` 或 `<sample_id>/synthesis/<point_id>`；综合项同时列出原生 covered/seed 事件 ID。收到原始来源映射后，同时保留经校验的 `<sample_id>/<source_message_id>`。UUID 与消息 ID 分开保存，不从评分标签推断来源。
- 文本保留说话人、完整来源时间、事件内容和综合时间范围；所有原生 payload 保存在 provenance。
- F 使用 JSON 上下文，保留已核对的上游时间推理指令；与原版双说话人分组格式的差异继续明示。本轮使用 F 已接受的固定配置；S1/S2 指令完全相同，回答 max_tokens 512，与综合上限 8192 分开记录。

以下表格保留 2026-10-19 首次离线检查历史；最新真实完成状态见本文首段和真实运行记录：

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

1. 完整开发事件库与来源映射已验收，C 数据依赖已解除；无需用户再次索要或重跑抽取。
2. 本轮用户已授权实际执行，91 次真实综合与新库回填完成；占位摘要未使用。密钥不持久保存，未来重跑仍由本机环境提供。
3. F 正式配置已核对，固定 5＋25 题真实回答完成；F 已确认接收评分包并在 PR #44 入库，D 本轮核对原包一致，不需要用户重复发送。E已取得并提交自动评分报告，逐题原始裁判交接、独立复算与至少四例成员人工验收尚待完成。
4. D 的 [进展页](../reports/structmem-d-progress.md) 已更新真实结果；准确率仍为 null，四类来源展示候选不等于 E 的人工验收，整组材料尚未定稿。

如记忆数据库、模型或日志单文件达到 20 MB，请将该文件发送到小组微信群；仓库只保留版本、大小、用途、获取方式及哈希，未发送时不填写发送日期。本轮没有代发群消息。

D 已在本轮完成指定的 C PR #43 与 F PR #44 审核并批准；审批仅覆盖各自说明范围，原 D PR #41 的 C 数值审核仍待指定成员完成。链接见[最新运行记录](structmem-real-run-20261020.md#本轮指定审核收口)。本轮没有重跑实验或新增 API 请求。

最新评分口径与四例实际输入回查见[证据链核对](structmem-case-traces-20261020.md)。C/F PR已合并，D已同步main并解决README冲突；未重跑真实模型。
