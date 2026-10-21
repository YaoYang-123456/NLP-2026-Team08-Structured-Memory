# 本地模型下载与晚间五题试跑准备

负责人：杨垚 / YaoYang-123456。日期：2026-10-15；关联 issue #6，依赖未合并的 PR #5。本轮按用户要求复用 PR #5 的实现与数据，从其 `acbe9e9` 建立分支 `YaoYang-123456/6-quiet-model-preparation`；依赖 PR 暂以 PR #5 分支为 base，待其正常审核合并后再调整到 main。本轮不合并、不请求审核、不催审。

**当前已停止准备，等待用户明确说“现在开始试跑”。没有创建自动启动任务。真实模型生成、预热、推理和训练请求均为 0。**

## 实际状态

| 层次 | 本轮结果 |
| --- | --- |
| 环境与模型文件 | 复用 `.venv`、Ollama 0.34.0；模型下载完整、所有 blob 哈希通过；零新增依赖 |
| 数据 | 复用既有 20/10/20 清单、BM25 检索事实与 B0/B1 文件；没有重新下载、划分或完整审计；本轮没有读取测试标签 |
| 程序流程 | 五条真实训练题＋模拟响应完成预热入口、smoke、汇总；停止和保存逻辑通过专项检查 |
| 性能结果 | **没有**。未加载模型；显存、速度、真实上下文截断、judge 可靠性均待晚上验证 |

这是个人 MetaMem 的简化 BM25 RAG 试点，仍不是论文 LightMem 完整复现或小组最终方案。此前的执行记录保持原样，本文件记录后续变化。

## 下载与存储核验

- 来源：[Ollama 官方模型标签](https://ollama.com/library/qwen2.5:7b-instruct-q4_K_M)。下载开始 `2026-10-15T11:28:39Z`，完成 `11:42:43Z`；没有中断或从头重下。
- 实际标识：`qwen2.5:7b-instruct-q4_K_M`；GGUF，7.6B，`Q4_K_M`。
- manifest / API 模型摘要：`845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`。
- 五个 blob 合计 **4,683,087,332 字节**（约 4.68 GB / 4.36 GiB），另有 858 字节 manifest；不含文件系统元数据。下载后 E 盘可用 **186,525,712,384 字节**。
- 使用已存在的用户级 `OLLAMA_MODELS=E:\ollama-models`。下载前约 191.2 GB 可用；已有其他项目模型，故复用该位置，不另建重复副本、不迁移、不覆盖。D 盘优先规则用于需要新建存储位置时；本次不需要。未修改用户级或系统级环境变量。
- 既有其他模型的 manifest 摘要、四个 blob 名称和大小前后相同；没有重新读取其大权重计算哈希。新模型 manifest 摘要与 `/api/tags` 一致，五个 blob 的实际 SHA-256 与 manifest 全部一致；核验时节流读取。
- 下载专用服务使用 `127.0.0.1:11436`，仅该进程隐藏 CUDA/Vulkan 设备、关闭云模型、禁止 prune。`/api/ps` 始终为空。结束时已关闭本轮专用服务；端口无监听，`nvidia-smi` 为 **0 MiB / 0%**，服务日志没有生成请求。

完整本地证据：`output/model-download/{before.json,pull.jsonl,pull-result.json,show.json,verified.json,quiet-final.json}`；服务日志在 `output/ollama-service/`。`verified.json` 的模型摘要供晚间入口核对，模型或 Ollama 版本变化时拒绝直接继续。

超过 20 MB 的单个权重文件：

| 文件 | 大小、用途、获取方式 |
| --- | --- |
| `E:\ollama-models\blobs\sha256-2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730` | 4,683,073,952 字节；五题本地试跑权重；从上述官方标签获取，`scripts/pull_qwen.py` 使用 Ollama pull，可利用已有部分文件续传 |

该文件 SHA-256 就是文件名中 `sha256-` 后的内容。**请将该文件发送到小组微信群**。群内发送人/日期：尚未发送、未确认；模型和运行结果不提交 Git，不添加 PR 附件。完整 Ollama 安装还依赖 manifest 与其余小 blob；其他机器可用官方同名标签下载，并核对本记录摘要，不应只复制大 blob 就宣称安装完成。

## 本机配置与接口

配置在 `configs/qwen-library.json`，answer 和 judge 共用该 Qwen 模型及 `http://127.0.0.1:11436/v1`。沿用标准库客户端，不安装训练框架，不使用付费 API。

已对照当前安装的 **Ollama v0.34.0** 源码和官方文档：

- [OpenAI 兼容接口](https://docs.ollama.com/api/openai-compatibility)及[版本固定的 openai.go](https://github.com/ollama/ollama/blob/v0.34.0/openai/openai.go)：使用 `/v1/chat/completions`，传递 temperature、top_p、max_tokens；max_tokens 映射到 num_predict，属于输出上限。
- [FAQ](https://docs.ollama.com/faq)、[v0.34.0 envconfig](https://github.com/ollama/ollama/blob/v0.34.0/envconfig/config.go)和[默认选项](https://github.com/ollama/ollama/blob/v0.34.0/api/types.go)：服务进程显式设置 `OLLAMA_CONTEXT_LENGTH=8192`，同时设 `OLLAMA_NUM_PARALLEL=1`、`OLLAMA_MAX_LOADED_MODELS=1`。没有把 max_tokens 当作上下文容量。
- [已加载模型接口](https://docs.ollama.com/api/ps)：晚上预热后保存 `loaded-after-warmup.json`，核对实际加载的 context_length 是 8192，否则停止。

模型元数据标注的原生上下文为 32768；本机本轮准备采用的服务容量为 **8192 token**。回答/反思输出上限 512，judge 32，提案/合并 1024，预热 8。上下文包含输入和生成，权重大小不能代表总显存需求；本轮没有测量运行时显存和吞吐。保留完整服务日志以检查晚上是否截断输入；返回非 `stop`（包括输出达到长度上限）按调用异常记录，不判为答错。judge 与 answer 同模型存在共同偏差，需人工复核。

## 晚上手动启动与停止

以下真实启动命令**本轮没有执行**。先得到明确的“现在开始试跑”后，在 PowerShell 执行：

```powershell
Set-Location -LiteralPath 'D:\2026下\实验\NLP'
.\.venv\Scripts\python.exe scripts/evening_smoke.py start --out output/evening-smoke-01
```

输出目录必须是新目录；已有目录拒绝覆盖。入口从手动启动时计时，服务启动、加载和预热都计入前 50 分钟。它核对本机版本与已下载摘要，启动本项目独立服务，发一次短预热，然后仅使用既有训练清单前五题：每题两次回答、各一次 judge，只对同题有对有错且调用完整的组反思/提案，最多合并一次。预计 **21–37 次生成请求**（含一次预热；10 回答＋10 judge＋0–15 反思/提案＋0–1 合并），另有元数据和卸载请求；不保证一小时内全部成功。

最迟在第 50 分钟停止新调用并终止尚在运行的本次服务/runner，最后 10 分钟留给保存、汇总、GPU 检查和人工复核；若流程提前结束，立即收尾，不空等到 50 分钟。全对、全错或调用不完整的组如实跳过，不改用人工规则。不会运行完整训练集、验证选择或测试集。

要提前停止，可按一次 Ctrl+C；或者另开 PowerShell，针对同一目录执行：

```powershell
Set-Location -LiteralPath 'D:\2026下\实验\NLP'
.\.venv\Scripts\python.exe scripts/evening_smoke.py stop --out output/evening-smoke-01
```

停止命令写 STOP 标记并立即停止本会话拥有的服务进程树；已结束会话不会误停新会话。正常结束使用空提示、`keep_alive=0` 卸载本次模型，然后停止专用服务。进行中强制停止则直接结束该服务及其 runner 以卸载；不结束机器上的所有 Ollama 进程。

若主入口终端意外关闭，手动收尾命令为：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ollama_service.ps1 Stop
.\.venv\Scripts\python.exe scripts/review_smoke.py --session output/evening-smoke-01
nvidia-smi --query-gpu=name,memory.used,utilization.gpu --format=csv
Get-NetTCPConnection -LocalPort 11436 -State Listen -ErrorAction SilentlyContinue
```

服务脚本核对保存的 PID、可执行路径和进程启动时间，避免误停其他进程。GPU 是否空闲以实际输出为准；本机其他程序也可能使用 GPU。没有后台计划任务、自动续跑或自动重试。

## 保存与人工复核

本轮最小修改：

- `client.py` 每次调用前保存 pending 标记；结束即追加并 fsync `calls.jsonl`，保存实际参数、提示词、响应、状态、token 和耗时。STOP/超时截止单独标为 interrupted；无法确认完成的调用保持 unknown，不假设零 token。
- `pipeline.py` 原子更新逐题/逐次输出，保留已完成回答与判分。未完成状态包括 not_started、generation_interrupted、judge_interrupted、request_incomplete；只有有效 yes/no 判分计入有效评分。
- `run_pilot.py` 支持截止时间、STOP 文件和显式 smoke 预热，最终记录 completed / interrupted / failed。日志末尾因硬停止留下半行时，仍能读取前面的完整记录。
- `evening_smoke.py` 只编排一次手动试跑、停止及收尾；不是任务调度或断点续跑框架。
- `review_smoke.py` 只读取训练输入与训练标签，根据快照和调用日志恢复已完成输出，不覆盖已有人工复核填写内容。

晚间结果位于 `output/evening-smoke-01/`：

| 文件 | 用途 |
| --- | --- |
| `session.json`、`model.json`、`worker.log` | 起止、截止时间、配置、命令、模型摘要、停止原因、收尾和 GPU 状态 |
| `smoke/run.json`、`smoke/calls.jsonl`、`smoke/rollouts-00.json` | 运行状态、调用/用量、已完成与未完成输出；规则快照保存在同目录 |
| `review.txt`、`review-inputs.json` | 五题问题、检索事实、两次回答、参考答案及 judge 判断；参考答案仅在 judge/训练反思与复核使用 |
| `human-review.json` | 填写 human_correct、judge_agreement、evidence_missing、notes；默认空值，不伪造人工评分 |
| `summary.json` | 有效评分覆盖率、状态分布、调用和 token；仅训练 smoke，不是测试性能 |

`accuracy_on_valid` 只看有效评分；沿用的 `correct_over_planned` 是已确认正确比例下界，不能把未完成或服务错误解释为能力错误。无有效评分时不报告准确率；模拟模式的模型分数全部为 null / 0。硬停止遗留 pending 时，若完整日志已落盘则以日志为准；否则明确标记可能尚在途。

如果主入口来不及改写 run.json 即被系统终止，复核导出将遗留的 running 标注为 incomplete，并记录原状态、pending 与未完成项，保留原始记录用于排查。不要把关闭窗口当作正常结束。

## 本轮实际执行的低负载检查

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ollama_service.ps1 StartDownload
.\.venv\Scripts\python.exe -u scripts/pull_qwen.py
.\.venv\Scripts\python.exe output/model-download/verify_download.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ollama_service.ps1 Stop -ExpectedProcessId 5556
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_evening.py -v
.\.venv\Scripts\python.exe scripts/run_pilot.py smoke --mock --config configs/qwen-library.json --warmup --out output/quiet-preparation-final/smoke
.\.venv\Scripts\python.exe scripts/review_smoke.py --session output/quiet-preparation-final
```

- **11 项专项测试通过**，只检查配置、完成调用持久化、生成/judge 中断、残缺日志、复核恢复与保留人工填写、截止时间及停止所属服务；server/controller 响应全为模拟，没有实际运行真实晚间入口。日志：`output/quiet-preparation-tests.txt`。
- 最终五题模拟流程：37 个模拟调用、real_requests=0、valid_model_scores=0、accuracy_on_valid=null；产物在 `output/quiet-preparation-final/`，可提前查看 `review.txt` 的复核格式。
- 另执行预先存在 STOP 文件的模拟 smoke：0 个调用，状态 interrupted，1 个 generation_interrupted＋9 个 not_started；记录在 `output/quiet-stop-check/`。
- Windows PowerShell 5 语法解析通过；真实下载服务的按身份停止命令执行成功，专用端口无监听、GPU 0 MiB / 0%。`git diff --check` 通过。
- 未重复下载数据、未重跑完整审计或其他测试；未加载、预热、推理、训练；没有真实 B2 学习、选规则、测试评价或性能结果。

旧数据 manifest SHA-256 仍为 `057be7b8d131e56df62d2884c89463ad485a378b88c6f53f67288705526f6936`。晚间的实际调用授权是唯一待满足的启动条件；运行时速度、显存及输入是否截断仍需要实测。
