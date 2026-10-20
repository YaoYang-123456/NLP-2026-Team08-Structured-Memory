# D 读取完整开发会话事件记忆的说明

C 已完成 A 冻结的三个开发会话，共 91 个 session、1973 条输入消息，生成 3712 条真实事件记忆。该版本沿用完整 session 抽取，关闭压缩和话题切分，由 C 的用户明确要求继续运行；群内未回复不作为团队确认，正式 S2 对照仍需对齐实验配置。

## 交付范围

| 会话 | session | 输入消息 | 事实记忆 | 关系记忆 | 总条目 | collection |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| conv-48 | 30 | 681 | 799 | 478 | 1277 | `conv_48_events` |
| conv-42 | 29 | 629 | 733 | 427 | 1160 | `conv_42_events` |
| conv-41 | 32 | 663 | 777 | 498 | 1275 | `conv_41_events` |
| 合计 | 91 | 1973 | 2309 | 1403 | 3712 | 三个独立库 |

本地原始装配目录为 `output/structmem/handoff/`。便于交给 D 的压缩包为 `output/structmem/complete-handoff-20261019.zip`；包大小、SHA-256 和副本验证记录见 `reports/structmem-complete-handoff.json`。D 已完成完整包接收、来源/向量/读取及检索验收，并在 [C PR #43 审核](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/43#pullrequestreview-5582200937) 中批准，C 任务 #32 已结项。已发送的 ZIP 原样保留，包内 README 保留打包时状态，最新交接状态以仓库交接索引为准。

解压后根目录 `complete-handoff/` 包含三个会话各自的 `qdrant/`、装配记录 `handoff.json`、完整运行记录 `run-record.json`、包内文件校验表 `files.sha256.json`、来源消息 `inputs/<会话>/session-001.json` 等 91 份输入，以及本说明。没有 `.env`、QA、答案或 evidence 标签。模型权重由 D 按下述约定在本机准备。

## 读取独立副本

接收端使用 Python 3.11 和 `qdrant-client==1.15.1`。复制或解压前关闭占用目标目录的 Qdrant 客户端，D 在自己的副本上读取和综合，避免与 C 同时写同一个存储目录。读取数据库不需要生成 API 密钥。

下面在解压目录的父目录执行，校验全部文件后读取三个库：

```python
import hashlib
import json
from pathlib import Path
from qdrant_client import QdrantClient

root = Path("complete-handoff").resolve()
hashes = json.loads((root / "files.sha256.json").read_text(encoding="utf-8"))
for name, expected in hashes.items():
    path = (root / name).resolve()
    assert path.is_relative_to(root), name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name

handoff = json.loads((root / "handoff.json").read_text(encoding="utf-8"))
for cid, info in handoff["conversations"].items():
    client = QdrantClient(path=str(root / cid / "qdrant"))
    try:
        assert client.count(info["collection"], exact=True).count == info["entry_count"]
        points, _ = client.scroll(info["collection"], limit=3, with_payload=True)
        print(cid, info["entry_count"])
        for p in points:
            print(p.payload["source_key"], p.payload["entry_type"], p.payload["memory"])
    finally:
        client.close()
```

数据库打开后可能修改本地存储文件。需要重复核对原包哈希时，重新解压新的副本；先以收到的 ZIP 的 SHA-256 核对版本。

## 来源绑定及检索约定

消息唯一来源使用 `source_key`（如 `conv-48/D1:9`）或 `(source_sample_id, source_message_id)`。`source_session_id=session_1` 对应 `inputs/conv-48/session-001.json`，`source_id` 是该文件 `messages` 数组内零起始索引。`source_message_id` 保留原始消息 ID。`memory` 为记忆文本，`entry_type` 为 `factual` 或 `relational`。原始会话时间保存在输入文件，上游绑定时间按消息顺序递增秒数，并非真实逐消息发送时间。

检索使用 `sentence-transformers/all-MiniLM-L6-v2`，revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`，384 维、归一化、cosine 距离。C 使用 CPU、`sentence-transformers==5.1.1`、`torch==2.8.0`。D 编码查询时使用同版模型并设置 `normalize_embeddings=True`，再用 `query_points(collection, query=vector, limit=...)` 检索；只在所需会话自己的库中查询。首个 session 的试读示例见仓库 `docs/structmem-session-handoff.md`，完整库请改用上表 collection。

所有输入消息均已进入对应 session 的抽取请求；1936 条原消息被至少一条记忆引用，37 条消息没有直接对应的抽取条目。这是来源覆盖统计，不代表正式准确率、召回率或事实质量评分。

## 实际运行及校验

本次新增 90 个 session，180 次生成请求全部成功，未触发失败重试，跳过此前已成功的首个 session。新增可见输入 463314、输出 125888、总计 589202 tokens，90 个 session 构建耗时之和为 770.510 秒。

包含首个 session 后，91 个 session 共 182 次成功生成请求，实际返回模型均为 `deepseek-flash`；可见输入 467831、输出 126984、总计 594815 tokens。成功 session 构建耗时之和为 783.885 秒，此值不含入口校验、装配和打包耗时，不是端到端墙钟时间。此前首个 session 的两次连接失败保留在运行历史中，其用量未知，不能记为零费用。合成 smoke 运行不计入上述开发会话统计。

C 已核对全部检查点身份及导出哈希、3712 条记忆的来源映射、384 维向量归一化，以及三个装配数据库的完整 payload 和向量读回。压缩包重新解压后的副本也独立验证。D 已验收本版本并用于真实综合和回答；跨事件综合由 D 负责，正式评分由 E 负责。C 于 2026 年 10 月 21 日完成对 D PR #41 的指定来源/数值审核，范围及复核边界见 `reports/structmem-c-review-d-20261021.json`。
