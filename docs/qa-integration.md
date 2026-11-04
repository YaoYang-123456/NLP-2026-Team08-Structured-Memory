# F：统一回答入口与 B/D/E 交接

**2026-11-03 阶段二更新：** F 的 [#75](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/75) 已提供公共预算/渲染、运行标识、请求快照和离线复核入口，见下节。尚未运行新付费回答/裁判或留出实验；本轮离线检查不等于成员验收，完整进度见[阶段规划](plans/2026-11-03-phase2.md)。后文首阶段记录保留其日期和验收范围。

## 阶段二：公共预算与请求契约

新增配置为 [qa-phase2.json](../configs/qa-phase2.json)，所有方法共用一份提示词，取消统一六词限制，列举/比较题允许完整回答。默认证据额度为 4,096 `cl100k_base` 代理 tokens，输出上限仍为 512。历史配置不改；不带 `evidence_budget` 的旧 S0/S1/S2 命令继续按原 JSON 格式发送。

阶段二维持 `method=S2` 表示结构化记忆检索系列，另用 `--variant M/N/A/U` 区分具体方法。每次运行自动生成独立 `run_id`，记录到运行、请求、调用和预测中。E 的跨方法比较键应包含 `(run_id, variant, method, sample_id, qa_index)`，不能把三个 S2 文件按旧 method 键合并。**现有 `evaluate.py` 的多 variant 支持由 E 在 #74 实现，本次未修改其评分口径。**

### B/D 共用的计数与渲染

```python
from evidence_budget import EvidenceBudget

budget = EvidenceBudget(max_tokens=4096, tokenizer_cache="data/tokenizer-cache")
tokens = budget.count(contexts)  # 在完整候选选择上计数，不累加单块估计
prepared = budget.prepare(contexts)  # 超额明确报错；不裁剪或重新选择
```

`contexts` 继续使用下文三字段契约。B/D 负责完成依赖闭包、去重和句子顺序后再交 F；F 不改写文本、补依赖或代做选择。`render_evidence` 逐块生成 `[E1] event`、`[E2] synthesis` 等标题并保留完整正文，块间两个换行。这里 E 表示 evidence，实际类型由标题标明；编号仅在单题请求内有效。

证据正文、类型标题、编号和分隔符均计入额度；固定指令、问题及聊天消息封装不属于该证据额度。按完整渲染字符串计数，最后一块没有额外尾换行；空证据为零。长 `source_ids` 不进入模型提示词，在 `requests.jsonl` 的 `evidence.source_map` 保存短编号到来源的映射，原始 contexts 仍保留。正文中的说话人和时间照存。计数器处理文本中的特殊 token 字面量，不将其视为控制 token。

每批在创建客户端和写输出前完成全部输入校验、渲染及预算检查；任何一题超额都拒绝整批，不先发送前面的题。B/D 必须直接使用此模块打包，不能继续各自估计 token。实际测量已发现旧三组 4,096 原型的 90 份上下文在新格式下均超限，需上游重新打包，详见[离线检查](../reports/phase2-f-offline-20261103.md)。原型成绩和配置保持原样。

### 离线准备和真实首样

阶段二新增唯一计数依赖 [requirements-qa.txt](../requirements-qa.txt)；旧配置仍只需要标准库。建议使用独立 Python 3.11 环境，不覆盖成员已有 CUDA/嵌入环境：

```sh
python3.11 -m venv tmp/qa-env
tmp/qa-env/bin/python -m pip install -r requirements-qa.txt
# 仅首次准备静态计数器资源；不是模型回答调用。
TIKTOKEN_CACHE_DIR=data/tokenizer-cache tmp/qa-env/bin/python -c \
  'import tiktoken; tiktoken.get_encoding("cl100k_base")'
```

正式运行只读预备缓存，校验 `cl100k_base` 资源 SHA-256 为 `223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7`；缺失或损坏直接报错，不在选择/回答过程中补下载。

仓库提供[一个真实无标签首样包](../reports/artifacts/phase2-f-contract-20261103.zip)，大小、哈希和包内清单见[交接记录](../reports/artifacts/README.md#f阶段二接口首样2026-11-03)。它直接复用已冻结 `anchor_2048` 上下文，**只是接口样例，不是新检索结果，也不代表正式 A 组 4,096 实验**。不含标准答案、支持注记或预测。

```sh
tmp/qa-env/bin/python -m zipfile -e reports/artifacts/phase2-f-contract-20261103.zip output/f-contract
tmp/qa-env/bin/python scripts/run_qa.py --mock --method S2 --variant A \
  --input output/f-contract/input.jsonl --config configs/qa-phase2.json \
  --tokenizer-cache data/tokenizer-cache --out output/f-contract-run
tmp/qa-env/bin/python scripts/verify_qa_run.py --run output/f-contract-run \
  --tokenizer-cache data/tokenizer-cache
```

每次使用新输出目录。`--mock` 不需要密钥，不发送 HTTP；所有预测标明 simulated。将生成的 `requests.jsonl` 与包内 `expected.json` 对照，核对请求/上下文哈希和证据 token；`run_id` 每次不同，不属于请求内容哈希。B/D 可从此例直接接选择器，E 可先接离线绑定校验。

### E 可重建的记录

新运行格式标识为 `qa-run-v2`。在第一个调用之前写好全部 `inputs.jsonl` 与 `requests.jsonl`，即使后续失败/中断也保留预定题目及请求；下游不需要依赖可能已移动的原输入路径。

| 文件/字段 | 阶段二新增信息 |
| --- | --- |
| `run.json` | run_id、variant、端点/HTTP 方法、planned_posts、输入快照及请求文件哈希、计数器版本、弃答数；原有模型/配置/代码/时间保留 |
| `inputs.jsonl` | 本次已校验的全部输入行快照；标准答案仍禁止进入 |
| `requests.jsonl` | 全部题目的完整待发请求、input_row_sha256、contexts_sha256、request_sha256、实际渲染证据、源映射、代理计数及文本哈希 |
| `calls.jsonl` | 每个已处理题目的真实构造请求与其哈希、原始响应和 usage，关联 run_id/variant/输入/上下文；不含鉴权头 |
| `predictions.jsonl` | 同样的绑定字段、evidence_proxy_tokens、原始来源及回答状态；`abstained` 单独标记约定的 `I don't know` 回答 |

对象哈希采用已有 `digest`：UTF-8、键排序、紧凑 JSON；文件及证据文本哈希按 UTF-8 原字节。`input_sha256` 指原输入文件，`input_snapshot_sha256` 指重新序列化的本次快照，两者可能因空格不同而不同。`request_sha256` 对实际 HTTP JSON 请求对象计算，不包含 Authorization、run_id 或 variant；同输入同配置的不同 variant 可以得到相同请求哈希。

`verify_qa_run.py` 不发网络请求：校验快照/代码/配置/计数器版本，重新构造每个请求，逐条检查调用、预测、响应与 usage，保留失败和未处理题的预定分母；源码版本变化时需先检出记录版本。它只接受新 v2 格式，不重写或重新解释历史运行。`verified=true` 表示记录与重建一致，不代表回答正确或成员语义验收。

核验结果分别输出已记录 usage 小计和缺失调用数；缺失不是零成本，模拟调用不产生真实 token 用量。`abstained` 只识别配置约定的固定弃答短语，不做语义分类；成功弃答仍保留在原分母中，由 E 评分。失败/中断不生成默认答案。

真实调用仍须显式 `--execute`，每题最多一次 POST、不重试。本轮未执行；待 A/C 的规模与 B/D 正式输入齐备，再登记发送内容、次数和额度，并按执行当日价格估算费用。不依据代理 tokens 虚构提供商计费数。

验证命令：`python -m unittest discover -s tests -p 'test_qa*.py' -v`。预算测试需要已安装计数依赖及缓存，默认 `data/tokenizer-cache`，也可设 `QA_TOKENIZER_CACHE`；缺失时明确跳过。当前实际环境 22 项全部通过、无跳过；网络成功/失败/中断测试使用替身，30 题真实上下文只做离线模拟，详见离线报告。

## 首阶段记录（2026-10-19 至 2026-10-21）

负责人：hycx233；关联 [#19](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/19)。2026-10-19 提供首版入口与离线检查，随后完成 S0 的 30 题真实回答；D 已使用同一入口完成 S2 的 30 题回答。2026-10-20，E 在 [PR #46](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/46) 提交自动评分与案例；2026-10-21，F已逐条核验60个输入指纹并复算原始/裁定后分数，成员本人核查仍待完成。最新证据与审核边界见[项目方案](project-plan.md#10-当前进展与下一步)；构造题、模拟响应和测试均不是实验结果。

## 交付与下一步

- `src/llm_client.py`、`scripts/run_qa.py`：B/D 共用的 DeepSeek 回答入口，无新增第三方依赖，使用 Python 3.11+。
- `configs/qa.example.json`、`configs/qa-smoke.inputs.jsonl`：参数与提示词示例、两道构造题；`tests/test_qa.py` 验证输入隔离、API 处理及结果交接。
- A 的固定题单、B 的真实检索和 F 的回答入口已合并；S0 按 5＋25 题完成真实回答。D 已交同题 S2 预测，F 核对原始请求、响应、预测与用量并保存评分包，见[交接入口](../reports/artifacts/README.md)。
- E已批准PR #42的S0交接，C已批准PR #41的事件/数值范围；F已完成PR #46逐题评分复算，见[验收记录](../reports/e-score-verification-20261021.json)。已验收范围不重复审核。
- PR #48已归档候选幻灯片和讲稿；真实署名、贡献比例、成员本人核查及正式视频/上传仍待确认，#19不据此全部结项。

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

**示例提示词用于接口检查，不是 StructMem 官方提示词复刻。** 当前已保存正式 [qa-structmem-20261020.json](../configs/qa-structmem-20261020.json)，S0 模板与已运行版本一致，S1/S2 方法指令相同；JSON 展示与原版分组模板的差异已记录。新一轮实际运行仍需显式选择并核对相应配置，不能用示例运行声称完成论文配置复现。

## 命令与请求数

在仓库根目录离线检查，无需密钥，不访问 API：

```sh
python3 scripts/run_qa.py --mock --method S0 \
    --input configs/qa-smoke.inputs.jsonl \
    --config configs/qa.example.json \
    --out output/qa-smoke-s0
```

每次使用新输出目录，已存在的目录会被拒绝。模拟输出状态为 `simulated`，预测是明显标识的占位字符串，`usage` 与返回模型为 `null`，真实成功回答数为 0。

以下是单次真实调用的命令示例，不是要求重跑已完成的实验；输入与所选配置核对后才显式执行：

```sh
python3 scripts/run_qa.py --execute --method S0 \
    --input data/locomo/smoke5-s0.retrieval.jsonl \
    --config configs/qa.example.json \
    --out output/qa-s0-smoke5
```

`data/locomo/...` 是路径示例，已有真实结果从[交接入口](../reports/artifacts/README.md)读取，不能仅凭示例路径推断当前交付状态。真实运行前在进程环境设置 `DEEPSEEK_API_KEY`；脚本不自动读取 `.env`，不把密钥写入配置或记录。保留系统代理设置，拒绝携带鉴权的 HTTP 重定向。

真实模式每行一次 **POST**，使用 Bearer 鉴权；不预热、不重试、不扫描数据目录。5 行最多 5 次，30 行最多 30 次；输入校验失败、输出目录冲突时不发请求。Ctrl+C 后停止后续题目。命令必须显式选择 `--mock` 或 `--execute`。本次未执行真实命令。

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

当前S0/S2真实回答与60条固定裁判已完成输入指纹核对及离线复算。S0原始16/30、日期裁定后15/30，S2为19/30；成员本人案例核查和最终交付仍待完成。S0的[运行记录](../reports/s0-answer-run-20261019.md)及[原始评分交接包](../reports/artifacts/s0-predictions-for-E-20261019.zip)保留，后续见[当前项目安排](project-plan.md#10-当前进展与下一步)。
