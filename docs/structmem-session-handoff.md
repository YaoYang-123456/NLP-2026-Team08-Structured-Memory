# D 读取首个真实 session 的说明

C 已完成 `conv-48/session_1` 的全部 18 条消息抽取，生成 34 条记忆，其中事实 22 条、关系 12 条。本包供 D 验证来源映射、数据库读取和检索接口；`conv-48` 共 30 个 session，目前仅完成第 1 个，不能据此开展完整会话的正式问答对照。

## 交接文件

本地压缩包为 `output/structmem/session-handoff/conv-48-session-001-20261019.zip`。解压后得到 `conv-48-session-001/`，目录内包含：

| 文件 | 用途 |
| --- | --- |
| `handoff.json` | 范围、collection、嵌入约定及包内文件 SHA-256 |
| `qdrant/` | 关闭客户端后复制的独立数据库 |
| `memories.json` | 34 条完整 payload 和向量导出 |
| `input.json` | 18 条来源消息、说话人和原始会话时间 |
| `source-examples.json` | 4 条来源与记忆对应示例 |
| `summary.json` | 成功构建的配置、请求、用量及耗时 |
| `factual-response.json`、`relational-response.json` | 两路真实模型原始响应 |
| `factual-prompt.json`、`relational-prompt.json` | 两路实际请求消息 |
| `run-record.json` | 成功运行与此前连接失败历史 |
| `read_structmem_session.py`、`README.md` | 验证入口与本说明 |

包内不含 `.env`、本机运行路径配置、嵌入模型权重、QA 或标准答案。数据及数据库保留在本地忽略目录，不加入 Git。压缩包大小、SHA-256 和本地副本验证结果记录在 `reports/structmem-session-handoff.json`。D 已在 [任务 #28](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/28) 中记录首个 session 的独立接收验证通过；完整三会话包的验收另行记录。

## 先验证独立副本

接收端使用 Python 3.11，数据库客户端对齐 C 的 `qdrant-client==1.15.1`。单纯读取无需 LightMem、DeepSeek 密钥或模型 API。

将压缩包解压至 D 自己的工作目录，关闭其他占用此目录的 Qdrant 客户端，在解压目录的父目录执行：

```powershell
python -m pip install qdrant-client==1.15.1
python ./conv-48-session-001/read_structmem_session.py ./conv-48-session-001
```

期望输出 `status=verified`、`entry_count=34`、事实 22、关系 12、来源消息 18，且 `conversation_complete=false`。验证先核对文件哈希，再独立打开数据库、比较全部 payload 和向量，并检查来源映射。若哈希或内容不符，保留收到的包并反馈失败，不重新调用抽取 API。数据库使用后可能更新本地存储文件；需要重新做原始文件哈希验证时，从原压缩包重新解压副本。

## 来源字段与时间

collection 名为 `structmem_events`。完整会话交接库将另用 `conv_48_events`，D 不应把当前单 session 样例当作该完整库。

| 字段 | 含义 |
| --- | --- |
| `memory` | 可供检索和综合的记忆文本 |
| `entry_type` | `factual` 或 `relational` |
| `source_sample_id` | `conv-48` |
| `source_session_id` | `session_1` |
| `source_message_id` | 原始消息 ID，例如 `D1:9` |
| `source_key` | 跨会话唯一的来源标识，例如 `conv-48/D1:9` |
| `source_id` | 当前 `input.json.messages` 数组内的零起始位置 |
| `speaker_id`、`speaker_name` | 说话人标识及名字 |
| `time_stamp`、`float_time_stamp` | 上游事件绑定时间，按消息顺序递增秒数 |
| `topic_id` | 此样例为 1，与 session 编号一致 |

消息来源使用 `(source_sample_id, source_message_id)` 或 `source_key`；不能跨会话只用 `D1:9` 匹配。原始时间字符串及解析后的会话时间保存在 `input.json`，绑定时间不是重新测得的逐消息发送时刻。

例如 `D1:9` 的 “Yes, I also have a pendant that reminds me of my mother...” 对应事实记忆 “Deborah also has a pendant that reminds her of her mother.”。关系示例 `D1:18` 的 “Looking forward to the next chat!” 对应 “Jolene expressed enthusiasm for continuing their connection, saying she looks forward to their next chat.”。完整示例包含记忆 ID 和完整原文，见包内 `source-examples.json`。

## 在 D 的副本中试读检索

嵌入模型必须使用 `sentence-transformers/all-MiniLM-L6-v2`，revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`，384 维、归一化，数据库距离为 cosine。C 使用 `sentence-transformers==5.1.1`、`torch==2.8.0`，CPU 运行。不要混用其他模型生成的查询向量。

以下代码使用已经准备好的同版本本地模型；替换两个本机路径后运行。只做本地嵌入和检索，不调用生成 API。

```python
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(r"D:/models/all-MiniLM-L6-v2",
                            device="cpu", local_files_only=True)
query = model.encode("What reminds Deborah of her mother?",
                     normalize_embeddings=True).tolist()
client = QdrantClient(path=r"D:/handoff/conv-48-session-001/qdrant")
try:
    hits = client.query_points("structmem_events", query=query,
                               limit=5, with_payload=True).points
    for hit in hits:
        print(hit.score, hit.payload["source_key"], hit.payload["memory"])
finally:
    client.close()
```

D 应在自己的副本上综合、检索和写入派生结果，避免与 C 共享同一个 Qdrant 存储目录。试读后需要反馈：包校验是否通过、能否读取 34 条、能否检索并取得来源字段。正式评分由 E 负责。

## 实际运行及适用范围

2026 年 10 月 19 日，模型返回名为 `deepseek-flash`，非思考模式，temperature 0、top_p 1、max_tokens 8192。成功运行两次抽取请求，输入 4517、输出 1096、合计 5613 tokens，构建耗时 13.375 秒。此前两次请求连接失败，未收到模型响应或用量；失败记录保留，不能将未知用量写为零费用。本次打包、复制、读回和本地检索不新增生成 API 请求。

该配置按完整 session 抽取，关闭压缩和话题切分；用于正式 S2 对照前仍需对齐团队的实验约定。C 和 D 已分别验证首个 session 的副本读取与来源映射；完整库验收、跨事件综合和正式评分分别记录。
