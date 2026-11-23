# F：统一回答入口与 B/D/E 联调说明

> **阶段二更新（2026-11-03）**：[#75](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/75) 已补齐阶段二共用的证据预算计数/渲染、运行追踪（`run_id` / `variant`）、完整请求快照和离线核验脚本，见下一节。旧的阶段一接口与交接记录保留在文末。整体进度见[阶段二规划](plans/2026-11-03-phase2.md)。

## 阶段二：公共预算与请求契约

阶段二新增公共配置 [configs/qa-phase2.json](../configs/qa-phase2.json)：

- **统一提示词**：`M / N / A / U` 四组共用同一套 prompt，取消阶段一的“约 6 词”长度软限制，列举或比较题允许完整作答。
- **统一证据预算**：每道题送入模型的证据文本限制在 **4,096 token** 以内（按 `cl100k_base` 统计，用来做统一的长度上限；实际计费以 API 返回的 `usage` 为准）。回答输出上限仍为 512 token。
- **区分不同方案**：`method` 仍记为 `S2`（代表结构化记忆系列），新增 `--variant M/N/A/U` 区分具体方案，并且每次运行自动生成唯一的 `run_id`。
- **兼容旧命令**：不带 `evidence_budget` 的旧配置和阶段一 `S0 / S1 / S2` 命令保持原样，历史记录不受影响。

> **给 E 的提醒**：阶段二不能再只按 `method=S2` 合并结果文件，跨方案对齐请使用 `(run_id, variant, method, sample_id, qa_index)`。`evaluate.py` 的多 `variant` 支持由 E 在 [#74](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/74) 中补齐。

### 给 B / D：共用计数与渲染接口

B 和 D 做证据打包时，直接调用 F 提供的 `EvidenceBudget`，不要各自另写估算逻辑：

```python
from evidence_budget import EvidenceBudget

budget = EvidenceBudget(max_tokens=4096, tokenizer_cache="data/tokenizer-cache")
tokens = budget.count(contexts)     # 对完整候选列表统一计数，不要把单块估算相加
prepared = budget.prepare(contexts) # 校验并渲染；超预算直接报错，不会暗中裁剪
```

接口分工与计数规则：

- **上游负责选和排，F 只负责算和发**：`contexts` 沿用 `{source_ids, kind, text}` 三字段格式。B/D 需在送给 F 之前完成去重、依赖补齐和句子排序；F 不改写正文，也不替上游裁剪超长证据。
- **渲染格式**：`render_evidence` 按顺序生成 `[E1] event`、`[E2] synthesis` 等标题并保留完整正文，块之间空一行（两个换行符），最后一块末尾无多余空行。`E` 代表 evidence，编号只在当前题目内有效。
- **计入预算的内容**：证据正文、类型标题、`[E编号]` 和块间分隔符全部计入 4,096 预算；系统提示词、问题文本和对话消息封装不占这 4,096 额度。空证据记为 0。文本里的特殊 token 字符串按普通文本处理。
- **来源 ID 处理**：较长的 `source_ids` 不放进发给模型的 prompt（省 token），而是完整保存在 `requests.jsonl` 的 `evidence.source_map` 里，原始 `contexts` 也会保留。正文里的说话人和时间照常保留。
- **整批预检**：运行前会先校验整批所有题目的格式和预算；只要有一道题超限，就会在发任何请求前直接报错停止。

> **注意**：实测发现，阶段二早期原型（4,096 档）选出的 90 份上下文按新的公共标题和编号格式重新统计后全部略超 4,096（4,148–4,280 tokens，详见[离线验证报告](../reports/phase2-f-offline-20261103.md)）。因此 B/D 在正式实现里必须直接用 `EvidenceBudget.count` 重新打包。

### 环境准备与单题联调样例

阶段二新增计数依赖 [requirements-qa.txt](../requirements-qa.txt)（`tiktoken==0.12.0`）；旧配置仍仅需 Python 标准库。建议新建一个独立的 Python 3.11 虚拟环境，避免影响现有的 PyTorch / CUDA 环境：

```sh
python3.11 -m venv tmp/qa-env
tmp/qa-env/bin/python -m pip install -r requirements-qa.txt
# 仅首次拉取 cl100k_base 静态词表文件（本地缓存，不调用 LLM API）
TIKTOKEN_CACHE_DIR=data/tokenizer-cache tmp/qa-env/bin/python -c \
  'import tiktoken; tiktoken.get_encoding("cl100k_base")'
```

正式运行时只读本地缓存，并校验 `cl100k_base` 文件的 SHA-256（`223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7`）；缓存缺失或损坏会直接报错，不会在跑实验时联网补下。

仓库里放了一个**单题联调样例包** [phase2-f-contract-20261103.zip](../reports/artifacts/phase2-f-contract-20261103.zip)（大小、哈希和清单见[交接包说明](../reports/artifacts/README.md#f阶段二接口首样2026-11-03)）。里面复用的是冻结开发集第 1 题的 `anchor_2048` 上下文（无答案标签），专供 B/D/E 离线对接口：

```sh
tmp/qa-env/bin/python -m zipfile -e reports/artifacts/phase2-f-contract-20261103.zip output/f-contract
tmp/qa-env/bin/python scripts/run_qa.py --mock --method S2 --variant A \
  --input output/f-contract/input.jsonl --config configs/qa-phase2.json \
  --tokenizer-cache data/tokenizer-cache --out output/f-contract-run
tmp/qa-env/bin/python scripts/verify_qa_run.py --run output/f-contract-run \
  --tokenizer-cache data/tokenizer-cache
```

每次运行需指定新的 `--out` 目录。`--mock` 不需要 API Key 也不会发网络请求，输出全部标记为 `simulated`。跑完后可以把 `requests.jsonl` 里的上下文/请求哈希、证据 token 数和样例包里的 `expected.json` 对照（`run_id` 每次不同，不参与内容哈希）。

### 给 E：可重建的运行记录与离线核验

阶段二的新输出格式标为 `qa-run-v2`。程序在发第一个请求之前就会先把整批 `inputs.jsonl` 和 `requests.jsonl` 落盘，这样就算中途报错或中断，也能保留完整题单和待发请求，不依赖外部文件路径。

| 文件 | 阶段二新增或关键信息 |
| --- | --- |
| `run.json` | `run_id`、`variant`、API 端点与 HTTP 方法、`planned_posts`、输入快照和请求文件哈希、分词器版本、弃答题数（以及原有模型、配置、代码哈希、时间戳） |
| `inputs.jsonl` | 本次校验通过的全部输入快照（严禁包含标准答案） |
| `requests.jsonl` | 每道题实际构造的完整请求体、`input_row_sha256`、`contexts_sha256`、`request_sha256`、渲染后证据文本、`source_map`、代理 token 数及文本哈希 |
| `calls.jsonl` | 每道已处理题目的实际请求与哈希、原始响应 JSON 和 `usage`，关联 `run_id` / `variant` / 输入与上下文（不含鉴权头） |
| `predictions.jsonl` | 相同关联键、`evidence_proxy_tokens`、来源映射、预测文本和状态；`abstained` 单独标记约定的 `I don't know` 弃答 |

关于哈希与核验脚本 `verify_qa_run.py`：

- **哈希口径**：JSON 对象按统一 `digest`（UTF-8、键排序、紧凑序列化）算哈希；文件与纯文本按 UTF-8 原字节算。`input_sha256` 对应原输入文件，`input_snapshot_sha256` 对应落盘快照（空白符不同时两者可能不同）。`request_sha256` 只覆盖 HTTP 请求体本身，不含 `Authorization`、`run_id` 和 `variant`，方便核对不同方案是否发出了相同请求。
- **核验内容**：`verify_qa_run.py` 全程离线运行，负责检查输入快照、配置、代码和分词器版本，逐题重建请求，并核对 `calls.jsonl` / `predictions.jsonl` 中的响应、来源映射、usage 与总题数（如果本地代码已更新，需切回记录中对应的 commit 再验）。该脚本仅支持 `qa-run-v2`，不改动历史运行记录。
- **统计口径**：核验摘要会分别列出已记录的 `usage` 合计和缺失调用数（缺失不记作零费用，mock 不记真实用量）。`abstained` 只匹配配置里约定的固定弃答短语，弃答题和失败题都保留在固定总题数里，由 E 统一评分。

真实调用仍需显式传 `--execute`，每题最多发一次 POST、不自动重试。待 A/C 统计完数据规模、B/D 备齐正式输入后，再按当日价格估算费用并运行。

单元测试命令：

```sh
python -m unittest discover -s tests -p 'test_qa*.py' -v
```

预算相关测试依赖本地 `tiktoken` 缓存（默认读 `data/tokenizer-cache`，也可用环境变量 `QA_TOKENIZER_CACHE` 指定）。在已备缓存的环境下，22 项测试全部通过（网络成功/失败/中断用离线 mock 覆盖）。

---

## 阶段一记录（2026-10-19 至 2026-10-21）

负责人：`hycx233`；任务 [#19](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/19)。阶段一已完成同一 30 道开发题的 S0 和 S2 真实回答，并由 E 在 [PR #46](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/46) 完成自动评分、由 F 完成 60 条输入指纹与分数复算（详见[项目方案](project-plan.md#10-当前进展与下一步)）。

### 阶段一交付物

- `src/llm_client.py`、`scripts/run_qa.py`：B/D 共用的 DeepSeek 回答入口（Python 3.11+，阶段一仅用标准库）。
- `configs/qa.example.json`、`configs/qa-smoke.inputs.jsonl`：示例配置和 2 道联调示例题；`tests/test_qa.py` 覆盖输入隔离、API 异常处理与结果落盘。
- 真实 S0 / S2 30 题评分交接包见[交接包索引](../reports/artifacts/README.md)，F 复算记录见 [e-score-verification-20261021.json](../reports/e-score-verification-20261021.json)。

### B / D 输入格式

入口读取 UTF-8 JSONL，每行一道题，严格包含以下 5 个字段（拒绝重复主键、多余字段或非 1–4 题型）：

| 字段 | 含义 |
| --- | --- |
| `sample_id` | LoCoMo 原始会话 ID（非空字符串） |
| `qa_index` | 该会话原始 `qa` 数组里从 0 开始的下标（过滤题型后不重排） |
| `question` | 原始问题文本 |
| `category` | 原始题型编号 1–4（仅作元数据，不放进 prompt） |
| `contexts` | 按检索顺序排列的上下文列表；允许为空列表 |

题目主键为 `(sample_id, qa_index)`；区分方法时再加上 `method`（阶段二再加上 `run_id` 和 `variant`）。单行展开示例（实际写在一行）：

```json
{
  "sample_id": "synthetic-conversation",
  "qa_index": 0,
  "question": "When did Alex join the club?",
  "category": 1,
  "contexts": [
    {
      "source_ids": ["synthetic:D1:1"],
      "kind": "raw",
      "text": "2026-10-01 Alex: I joined the reading club yesterday."
    }
  ]
}
```

每条上下文包含 3 个字段：

- `source_ids`：非空字符串列表。B 填原始消息/分块的稳定 ID；D 填事件或综合记忆的 ID，并尽量保留原始消息 ID。不能把标准答案的 `evidence` 字段填进来。
- `kind`：`raw`、`event`、`synthesis` 之一。
- `text`：非空正文，保留说话人、时间和实际记忆文本。S2 的事件和综合放同一个列表，靠 `kind` 区分。

白名单会拦截结构化的 `answer` / `evidence` 等标签字段，但识别不了手动拼进 `text` 的答案，A/B/D 在生成输入时仍需确保不混入标准答案。

### 通用调用参数与提示词

阶段一示例配置 `configs/qa.example.json` 使用 `deepseek-flash`、`temperature=0`、`top_p=1`、`max_tokens=512`、单次超时 60 秒，代码固定 `thinking={"type":"disabled"}`、`stream=false`，请求 `https://api.deepseek.com/chat/completions`（依据 2026-10-19 核对的 [DeepSeek API 文档](https://api-docs.deepseek.com/api/create-chat-completion/)与[定价说明](https://api-docs.deepseek.com/quick_start/pricing/)）。记录里同时保存请求模型名和返回模型名，费用按实际 `usage` 与当日单价估算。

`system_prompt` 为公共指令，`method_prompts.S0/S1/S2` 为各方法模板，仅接受 `{context}` 和 `{question}`（字面花括号写 `{{`、`}}`）。阶段一 S2 正式运行使用的是 [configs/qa-structmem-20261020.json](../configs/qa-structmem-20261020.json)（示例配置仅作接口检查）。

### 阶段一常用命令

离线 mock 检查（无需 API Key）：

```sh
python3 scripts/run_qa.py --mock --method S0 \
    --input configs/qa-smoke.inputs.jsonl \
    --config configs/qa.example.json \
    --out output/qa-smoke-s0
```

真实执行命令示例（需在环境中设置 `DEEPSEEK_API_KEY`，脚本不自动读 `.env` 也不落盘密钥）：

```sh
python3 scripts/run_qa.py --execute --method S0 \
    --input data/locomo/smoke5-s0.retrieval.jsonl \
    --config configs/qa.example.json \
    --out output/qa-s0-smoke5
```

说明：输出目录已存在时会拒绝覆盖；真实模式下每行发一次 POST，不重试，Ctrl+C 立即停止后续题目。

### E 读取结果与状态约定

| 文件 | 内容 |
| --- | --- |
| `run.json` | 方法名、是否 mock、输入/配置/代码哈希、完整配置、题单哈希、总题数、各状态计数、时间 |
| `predictions.jsonl` | 题目主键、问题/题型、上下文与来源、预测文本、状态、返回模型、原始 `usage`、耗时、失败原因 |
| `calls.jsonl` | 对应请求体、原始响应 JSON、原始 `usage`、停止原因和状态（不含 `Authorization` 头） |

其中 `question_set_sha256` 只对 `(sample_id, qa_index, question, category)` 列表计算，同一题集跑不同方法时该哈希应一致；`input_sha256` 含上下文，会随方法变化。

| 状态 | 含义与评分处理 |
| --- | --- |
| `ok` | 正常返回非空回答，进入评分 |
| `failed` | HTTP/网络/格式错误、截断、空回复或意外开启思考模式等；`prediction=null`，保留在总题数中，不删题也不算正常答错 |
| `interrupted` | 被 Ctrl+C 中断，真实用量可能未知，不按零消耗处理 |
| `simulated` | mock 占位结果，不计入实验成绩 |

单题失败后会继续跑完后续题目，批次退出码为 `1`（全部成功或纯 mock 为 `0`，Ctrl+C 为 `130`）。`usage` 原样保存接口返回对象（缺失记 `null`）；HTTP 报错只记状态码和异常类型，不记录可能含敏感信息的错误正文。

阶段一结果回顾：30 道冻结开发题上，S0 原始自动判分 16/30（日期人工裁定后 15/30），S2 为 19/30。S0 运行记录见 [s0-answer-run-20261019.md](../reports/s0-answer-run-20261019.md)，评分交接包见 [s0-predictions-for-E-20261019.zip](../reports/artifacts/s0-predictions-for-E-20261019.zip)，完整状态见[项目方案](project-plan.md#10-当前进展与下一步)。
