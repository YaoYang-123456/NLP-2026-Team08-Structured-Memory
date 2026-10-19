# F：统一回答入口与 B/D/E 交接

负责人：hycx233；关联 [#19](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/19)。2026-10-19 提供首版入口与离线检查，随后完成 [S0 固定 30 题真实回答](../reports/s0-answer-run-20261019.md)，评分待 E。构造题、模拟响应和测试仍不计入实验结果。

## 交付与下一步

- `src/llm_client.py`、`scripts/run_qa.py`：B/D 共用的 DeepSeek 回答入口，无新增第三方依赖，使用 Python 3.11+。
- `configs/qa.example.json`、`configs/qa-smoke.inputs.jsonl`：参数与提示词示例、两道构造题；`tests/test_qa.py` 验证输入隔离、API 处理及结果交接。
- A 的冻结题单与 B 的真实 S0 检索输出已在本地核对，F 按前 5 题、剩余 25 题完成真实回答；E 的评分仍待交付。D 有真实事件和综合记忆后接入 S2。
- 公共格式合并前，请一位相关成员集中核对 B/D 的来源与时间保留方式，以及 E 的联合主键和失败处理。
- 10 月 21 日合并研讨材料时，F 提供入口与联调进展；各成员仍自行提供技术页和真实案例。评分和研讨材料合并尚未完成，不能将 #19 全部标为完成。

## B/D 输入

入口只读取显式指定的 UTF-8 JSONL，一行一道题，每行恰好包含以下字段：

| 字段 | 含义 |
| --- | --- |
| `sample_id` | LoCoMo 原始会话标识，非空字符串 |
| `qa_index` | 在该会话原始 `qa` 数组中的 **0 起始下标**；过滤题型后不重新编号 |
| `question` | 原始问题文本 |
| `category` | 原始题型整数 1–4，仅作结果元数据，不放入模型提示词 |
| `contexts` | 按检索顺序排列的上下文数组；允许为空，表示没有检索结果 |

**题目主键是 `(sample_id, qa_index)`**，同一会话可有多道题。区分不同方法的预测时再加 `method`。整批输入在首次请求前校验，拒绝重复主键、额外字段和不支持的题型。

下面展开一行构造数据，实际 JSONL 将整个对象写在一行：

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

每个上下文恰好包含三个字段：

- `source_ids`：非空字符串数组。B 保存原始消息/分块的稳定 ID；D 保存事件条目或综合记忆的稳定 ID，能追到原始消息时一并保留。这些 ID 必须来自检索结果，不能用标准答案的 evidence 标注填充。
- `kind`：`raw`、`event`、`synthesis` 之一，表示原始对话块、事件条目和综合记忆。
- `text`：非空文本。B/D 保留说话人、来源时间、相对时间及上游实际记忆内容。F 完整序列化上下文数组，不重排、不截断、不重建记忆。S2 的条目与综合记忆放在同一数组中，以 `kind` 区分。

`answer`、标准答案的 `evidence` 及其他标签不进入输入。字段白名单可以阻止结构化标注混入，但无法识别手动拼进 `text` 的答案，A/B/D 仍需遵守答案隔离约定。

## 统一设置与方法提示词

共用配置 `configs/qa.example.json` 使用 `deepseek-flash`、`temperature=0`、`top_p=1`、`max_tokens=512`、单次请求超时 60 秒。代码固定 `thinking={"type":"disabled"}`、`stream=false`，请求官方 `https://api.deepseek.com/chat/completions`。非思考模式下 `top_p` 实际固定为 1，示例据此填写，不作为额外调参维度。

依据 [DeepSeek 官方 Chat Completions 文档](https://api-docs.deepseek.com/api/create-chat-completion/)和[模型说明](https://api-docs.deepseek.com/quick_start/pricing/)，核对日期为 2026-10-19。运行记录保存请求模型和返回模型，避免把别名当作固定版本。费用由实际 `usage` 按运行当日价格估算，本入口不增加计费框架。

`system_prompt` 是共用指令；`method_prompts.S0/S1/S2` 是各方法的用户提示模板，只接受 `{context}` 和 `{question}`。字面花括号写成 `{{`、`}}`。完整配置、实际请求和哈希均保存，便于核对方法差异。

S0 的通用提示词已冻结用于本轮原始对话基线。**S1/S2 示例提示词仍只用于接口检查，不是 StructMem 官方提示词复刻。** D 接入时需在配置中保存核对后的方法提示词；如某项上游输入尚未包含在 `contexts.text` 中，应在真实运行前补齐并核对。公共指令和方法提示词一起审阅、冻结后，所有方法使用同一份配置。不能用示例运行声称完成论文配置复现。

## 命令与请求数

在仓库根目录离线检查，无需密钥，不访问 API：

```sh
python3 scripts/run_qa.py --mock --method S0 \
    --input configs/qa-smoke.inputs.jsonl \
    --config configs/qa.example.json \
    --out output/qa-smoke-s0
```

每次使用新输出目录，已存在的目录会被拒绝。模拟输出状态为 `simulated`，预测是明显标识的占位字符串，`usage` 与返回模型为 `null`，真实成功回答数为 0。

真实执行必须先固定输入与配置，显式选择执行模式，例如：

```sh
python3 scripts/run_qa.py --execute --method S0 \
    --input data/locomo/smoke5-s0.retrieval.jsonl \
    --config configs/qa.example.json \
    --out output/qa-s0-smoke5
```

`data/locomo/...` 是路径示例；本次已完成运行的实际分批命令与固定配置见[运行记录](../reports/s0-answer-run-20261019.md)，勿重复提交已有 5 题。真实运行前在进程环境设置 `DEEPSEEK_API_KEY`；脚本不自动读取 `.env`，不把密钥写入配置或记录。保留系统代理设置，拒绝携带鉴权的 HTTP 重定向。

真实模式每行一次 **POST**，使用 Bearer 鉴权；不预热、不重试、不扫描数据目录。5 行最多 5 次，30 行最多 30 次；输入校验失败、输出目录冲突时不发请求。Ctrl+C 后停止后续题目。命令必须显式选择 `--mock` 或 `--execute`。

## E 读取结果

| 文件 | 内容 |
| --- | --- |
| `run.json` | 方法、模拟标志、输入/配置路径与哈希、代码哈希、完整配置、题目清单哈希、预定及处理题数、各状态计数、时间 |
| `predictions.jsonl` | 联合主键、问题/题型、上下文及来源、预测、状态、返回模型、原始用量、耗时和失败原因 |
| `calls.jsonl` | 同一联合主键对应的完整请求体、原始响应 JSON、原始 `usage`、停止原因与状态；不含 Authorization 请求头 |

`question_set_sha256` 对有序的 `(sample_id, qa_index, question, category)` 清单计算；同题集不同检索结果应一致。`input_sha256` 包括上下文，通常随方法变化。E 核对题集哈希和预定题数后，按 `(method, sample_id, qa_index)` 关联答案，不能仅按会话覆盖多道题。标准答案仅由 E 在此后加载。

| 逐题状态 | 评分处理 |
| --- | --- |
| `ok` | 得到非空、自然结束的真实回答，可以评分；生成成功不表示答对 |
| `failed` | HTTP、网络、格式错误、截断、空响应或意外思考模式等；`prediction=null`，保留失败与预定分母，不当成正常答错或删题 |
| `interrupted` | 请求被 Ctrl+C 中断，实际用量可能未知，不当作零消耗 |
| `simulated` | 未调用模型，不计入准确率或实验覆盖率 |

`usage` 原样保留提供方对象，包括缓存等扩展字段；缺失为 `null`。被判定为截断的响应也保留实际用量。HTTP 错误只保存状态码和异常类型，不记录可能包含秘密的错误正文；无有效 JSON 时没有 `raw_response`。`seconds` 是调用墙钟耗时。

单题生成失败后继续下一题，批次退出码为 1；成功或纯模拟批次退出码 0；Ctrl+C 返回 130。`run.json` 保留 `planned_questions`；中断后未执行的题目没有预测行，E 用 A 的冻结清单补出缺失项，不把已处理数当预定分母。纯模拟批次状态为 `simulated`，不写成真实实验完成。

## 验证与验收边界

```sh
python3 -m unittest discover -s tests -p test_qa.py -v
```

覆盖联合主键、标签隔离、整批预检、提示词/来源保留、关闭思考、原始响应/用量、截断及网络失败、中断、防覆盖、模拟模式、跨方法题集哈希。HTTP 成功和失败由离线替身提供，没有真实 API 请求。旧 MetaMem 测试需要本工作目录中不存在的 `data/pilot`，本次不下载其数据或重跑研究实验。

当前已有 A/B 的真实交接输入及 F 的 30 题预测，下一次验收需要 E 的真实评分与人工核查产出。完整“检索→回答→评分”链路及研讨材料合并仍待交付。
