# 第一阶段复现与恢复入口

本说明复现的是个人 BM25 RAG＋元记忆试点，不是论文全量五折或LightMem。研究结论入口为 [阶段报告](metamem-stage1.md)。本机已有数据、环境和模型，**不要重复下载或重建**。没有自动运行任务；下列生成命令只有明确手动执行才启动本地模型。

## 1. 版本与必要文件

- Python 3.14.7、标准库、独立`.venv`；Ollama 0.34.0；RTX 5080 Laptop GPU 16GB。没有PyTorch训练依赖。
- 数据：[官方cleaned S固定revision](https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/tree/98d7416c24c778c2fee6e6f3006e7a073259d48f)，下载脚本`download_data.py`固定SHA-256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`。本机`data/raw/longmemeval_s_cleaned.json`为277,383,467字节。
- 模型：[Qwen2.5标签](https://ollama.com/library/qwen2.5:7b-instruct-q4_K_M)，固定manifest摘要`845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`。标签本身可能变化，必须核对摘要。[小型模型来源记录](../configs/stage1-model-reference.json)保留blob哈希；它不是另一台机器已经核验的证明。
- 固定输入为`data/pilot/validation.inputs.json`，10题，参考在独立`validation.labels.json`；训练20题、测试20题的划分保持不变。本轮不执行任何test命令。
- [生成配置](../configs/qwen-stability-sampling.json)：8192上下文、temperature0.7、top_p0.95、max_tokens1024，seed不设置。[执行前冻结设计](../configs/metamem-stability-plan.json)记载3轮、同题配对、轮间交替顺序、哈希与本次原始时间预算。
- B0为`configs/rules-b0.json`；[学习规则精确副本](../configs/rules-stage1-frozen.json)来自v1训练rules-01，字节哈希与原文件相同。这是冻结研究材料，不是新选择的正式候选。
- [严格拒答v2](../configs/external-ai-strict-abstention-v2.json)保持不变；其中`analysis_only`记录其最初离线敏感性分析来源。本次独立稳定性实验明确采用这些评分条款，不把旧规则称为v2训练所得。

## 2. 在现有本机直接重跑的边界

为保留本次证据，不重用`output/stage1-stability-20261015`。下列是**未来获准时**可运行的入口；本轮已经完成，不自动再跑：

```powershell
Set-Location -LiteralPath 'D:\2026下\实验\NLP'
.\.venv\Scripts\python.exe -X utf8 scripts/stability_session.py --out output/stability-new-run
```

默认从手动执行时开始两小时总预算，预留最后10分钟清理；最多70次本地请求，计划61（预热1＋回答60）。目录存在就拒绝覆盖。若预算早于命令开始计时，用`--started-epoch`传入那个起点，不重新计时。本轮实际起点epoch1792117292，用户后来取消50分钟噪音截止，推理截止采用1792123892，总截止1792124492。

本轮实际通过Python调用既有监督器，等价操作如下；参数与子进程完整命令另保存在session.json。这段历史命令的绝对截止已过，**不能现在照抄重跑**：

```python
import time
import sys
from pathlib import Path
sys.path[:0] = ["src", "scripts"]
import evening_smoke
evening_smoke.ACTIVE_SECONDS = max(0, 1792123892 - time.time())
evening_smoke.TOTAL_SECONDS = max(0, 1792124492 - time.time())
evening_smoke.start(Path('output/stage1-stability-20261015').resolve(),
    Path('configs/qwen-stability-sampling.json'), Path('scripts/run_stability.py').resolve())
```

新入口只是封装同一监督器；60次生成发生在新增worker中。所有请求逐次保存`calls.jsonl`，所有计划条目事先写入`answers.json`，有generating/failed/interrupted/not_started状态；错误或未完成不记作No。生成结束即卸载模型、停止本轮所属服务，不为等APP评审而占用GPU。

停止正在进行的会话：

```powershell
.\.venv\Scripts\python.exe scripts/evening_smoke.py stop --out output/stability-new-run
```

会话结束后检查`session.json`的unload、loaded_after_unload、server_stopped；服务进程与子进程按身份核验，11436无监听；再用`nvidia-smi`区别其他程序显存与本模型残留。不要关闭无关应用。

## 3. 文件式APP AI评审：不是全自动API

生成后读取`smoke/queue.hidden.json`和`policy.frozen.json`。只向评审者提供这两个文件及评审格式，不提供`answers.json`、calls、方法/规则映射、旧分数或期望结论。队列含完整问题、参考/rubric、完整回答、原题型标准、是否适用严格拒答、输入哈希；完整回答可能自述规则，不能宣称严格盲评。

在当前APP中请AI逐条阅读全文，写`smoke/reviews.json`：

```json
{
  "version": "external-ai-strict-abstention-v2",
  "queue_sha256": "由data.digest(queue)计算",
  "policy_sha256": "由data.digest(policy)计算",
  "reviewer": {"type":"external_ai_app", "identity":"实际可确认身份", "exact_model_version":"unknown", "human_gold":false},
  "results": [{"sample_id":"原样保留", "input_sha256":"原样保留", "label":"Yes或No或uncertain", "reason":"简短依据", "unsupported_expansion":"yes或no或unknown", "quality_reason":"独立质量说明"}],
  "human_acceptance": null
}
```

这只是格式示例，不能把示例当评分结果。`digest`是UTF-8、键排序、紧凑JSON的SHA-256，使用`metamem_pilot.data.digest`避免序列化差异。真实歧义保留uncertain；对非拒答题不暗中增加“所有扩写必须有检索出处”的扣分标准。APP没有API usage，评审条数另计，未知token不写成0。

收到完整评审后，仅离线执行：

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/summarize_stability.py --out output/stability-new-run/smoke
```

脚本验证评分版本、政策/输入哈希、未知/重复/缺失ID、AI身份和理由，拒绝不完整评审，不默认补No；生成`assessed-answers.json`与`summary.json`。原始回答、评审文件不覆盖。已存在summary则拒绝重写，若要修正评审须新建带说明的派生目录。统计包括每轮、逐题配对、拒答与有效覆盖，不进行规则选择。

**能直接重跑的是本地生成和已有评审文件的离线统计；新回答仍需APP AI逐项重新评审。** 不提取客户端凭据，不假定API可用，不把网络调用伪装为文件操作。

## 4. 从哪里恢复

|状态|恢复位置与行为|
|---|---|
|生成已完成、尚未评审|保留queue与policy，重新开启APP评审；不需重新启动Ollama|
|评审已有、统计未完成|验证reviews后离线summarize；不需模型|
|生成中断|answers、calls、pending-call、run保留已完成/未完成状态；只评已有完整回答并报告覆盖。强杀可能未导出queue；此时先从answers/calls核验完成项，不能假定队列已完整保存。没有复杂断点续跑或自动补题；不得在同一预算外偷偷补全|
|本次已完成|直接从`output/stage1-stability-20261015/smoke/summary.json`及报告核查，不重新实验|
|历史v1训练|`output/external-ai-experiment-20261015-2143/smoke/training/`是实际轨迹；只读，不能用v2重判伪造新反思|

完整数据和原始日志不提交Git。新检出仓库仅靠小型报告不能逐字重放旧模型响应；需取得本地忽略产物，或重新生成并重新APP评审。复现算法/设置不保证相同token或相同分数，seed未设、平台也可能变化。

## 5. 换机器所需的明确准备

此节只记录方法，本轮未重新下载模型/数据、未重建全量划分。

1. 使用独立Python环境。取得官方固定revision数据，可用`download_data.py`；准备脚本`prepare_data.py`会创建固定划分，拒绝覆盖已有目录。数据准备阶段会解析源数据和分离所有标签；若要求测试内容不被处理，直接取得已有冻结`data/pilot`而不重建。研究者只打开train/validation，测试文件留作保留集。
2. 使用现有Ollama权重及相同manifest摘要；服务脚本复用已有用户级`OLLAMA_MODELS`（本机E盘），不要迁移其他项目模型。新机器需先配置自己的存储。旧`output/model-download/verified.json`是本机核验记录，不能凭空编造另一个机器已完成blob核验。
3. 监督器依赖上述核验记录；可从负责人取得它作为来源记录，启动时还会比对本地`/api/tags`的manifest摘要。若重下载，应依照[模型准备记录](metamem-evening-preparation.md)逐blob核验并保存新记录；当前没有一键自动生成完整blob核验记录的脚本。此人工准备缺口应明示，不能宣称新机全自动安装。
4. 固定计划引用原rules-01路径。新机可将仓库`configs/rules-stage1-frozen.json`精确复制到`output/external-ai-experiment-20261015-2143/smoke/training/rules-01.json`（仅当目标不存在），或取得原训练目录；核对文件SHA-256 `60f3e30726203ed560fa50fe435d08ec865065314f91842bd71678910ceaf42c`。这是恢复已知规则材料，不能宣称在新机完成训练。

超过20MB需共享的已有文件：原始数据277,383,467字节；主权重blob `sha256-2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730`为4,683,073,952字节。**请将该文件发送到小组微信群。** 两者用途/来源/哈希见前文与模型来源记录，群内发送日期未确认，不记为已发送；不能只复制主blob就当完整模型安装。

## 6. 本阶段必要核验

`test_stability_summary.py`四项测试覆盖未知/重复/缺失评审与哈希拒绝，以及失败/uncertain不计错。实际60条提示词离线重建完全一致，调用设置一致、三轮每题两配置配对齐全；调用日志无judge。模型日志61次truncated=0，完成标记均stop；无新增训练、反思或规则操作。证据审计对183条检索事实与原史做回接核验，新增证据从未加入本次生成输入。完整验证记录保存在本地run目录，独立复查见阶段主报告。

## 7. 本次独立复核的保守派生统计

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/summarize_stability.py --out output/stage1-stability-20261015/smoke --audit output/stage1-independent-review
```

这条命令本轮已执行。目标存在时拒绝覆盖；不要对原目录重复执行。审核包须是原队列精确子集，完整输入、政策和预先冻结范围哈希均核验。不同标签保留uncertain；另存`assessed-answers.reviewed.json`、`summary.reviewed.json`和`review-comparison.json`，原首评不覆盖。78是60条首评加18条定向复核，不是78个独立回答。复核是APP AI操作，不是自动裁决或人工金标准。

打包时生成配置由CRLF规范为仓库LF，JSON设置逐项相同。仓库计划的`generation_config_sha256`用于LF文件重跑，`executed_generation_config_sha256`保留本次执行前字节哈希；运行目录`plan.frozen.json`仍是原冻结文件，未覆盖。只变更文件换行，不改实验设计或生成设置。
