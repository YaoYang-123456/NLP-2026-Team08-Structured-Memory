# 输出预算调整后的五题诊断复跑

这是个人 MetaMem BM25 RAG 试点的训练诊断，不是 LightMem 完整复现、严格复现、模型能力对照或测试成绩。真实数据、真实本地模型；没有读取测试答案、扩大样本、下载模型或使用付费 API。全部复核均为 **AI 辅助复核**，人工复核尚未完成。

## 实际范围与版本

- 起始代码：`cec76b175806fdb63b54e5e487cfa43edbacdcd3`，沿用 `YaoYang-123456/6-quiet-model-preparation`，草稿 PR #7 继续依赖 PR #5；均不合并。
- Ollama 0.34.0；`qwen2.5:7b-instruct-q4_K_M`，7.6B、Q4_K_M；摘要 `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`。复用 E 盘权重。
- 服务 `127.0.0.1:11436`，实际加载上下文 8192；answer 与 judge 共用模型。
- 新配置 `configs/qwen-budget-diagnostic.json`，原配置保留。仅 answer_train / answer_eval 输出上限 512→1024，reflect 512→2048；预热仍覆盖为 8 token，judge 32、propose/merge 1024、温度、top_p、超时、检索和提示词均不变。
- 数据 manifest SHA-256：`057be7b8d131e56df62d2884c89463ad485a378b88c6f53f67288705526f6936`。直接比较两轮十份回答提示词完全相同，五题 ID、问题、日期、检索事实、参考答案完全相同；未将复核意见送入学习或回答提示词。

## 时间与真实运行

本轮工作起点为 2026-10-15 20:32:42 America/New_York（2026-10-16 00:32:42 UTC）。推理截止 21:22:42，总截止 21:32:42，包含准备耗时，不在真正启动模型时重新计时。

`output/budget-diagnostic-20261015-2037/` 是一次启动前失败记录：旧服务 PID 已被 ChatGPT 复用，身份校验拒绝继续；真实调用为 0。修复后不触碰该无关进程，保留失败目录，改用新目录。只有下面一批真正执行了五题，无追加循环。

实际启动命令：在仓库根目录，将下列脚本通过 PowerShell here-string 送入 `.venv\Scripts\python.exe -`（其中绝对截止仅对应本次历史运行，不应直接用于未来启动）：

```python
import sys, time
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path('scripts').resolve()))
import evening_smoke
start = datetime.fromisoformat('2026-10-16T00:32:42+00:00').timestamp()
now = time.time()
evening_smoke.ACTIVE_SECONDS = max(0, start + 3000 - now)
evening_smoke.TOTAL_SECONDS = max(0, start + 3600 - now)
sys.exit(evening_smoke.start(
    Path('output/budget-diagnostic-20261015-2038').resolve(),
    Path('configs/qwen-budget-diagnostic.json')))
```

模型会话从 00:37:53 UTC 开始，57.13 秒后结束；00:38:46 UTC 已确认卸载，00:40:08 UTC 独立核验清理状态。均远早于截止。入口仍支持手动 `start --out <新目录> --config configs/qwen-budget-diagnostic.json`，但本轮不会自动启动或续跑。

## 与上轮并列

| 项目 | 上轮五题 | 本轮预算诊断 |
| --- | --- | --- |
| 本地产物目录 | `output/evening-smoke-20261015-1454/` | `output/budget-diagnostic-20261015-2038/` |
| 会话耗时（含加载与清理） | 54.68 秒 | 57.13 秒 |
| worker 耗时 | 47.08 秒 | 42.63 秒 |
| 真实生成调用 | 22：预热1、回答10、judge9、反思2 | 21：预热1、回答10、judge10 |
| 输出截断 | 2：回答1、反思1 | 0 |
| 有效判分 / 计划回答 | 9/10，90% | 9/10，90% |
| 原始 judge 结果 | 3 Yes、6 No | 6 Yes、3 No |
| 无效结果 | 回答截断1，不判分 | judge `No.` 解析失败1，不算答错 |
| 输入 / 输出 token（含预热） | 40349 / 3863 | 35573 / 3482 |
| 合格混合组 | 1，但反思截断 | 0 |
| 非空规则 | 无 | 无 |
| 每5秒显存采样峰值 | 5151 MiB | 5142 MiB |
| 清理 | 实际卸载/退出，脚本误报失败 | 卸载、退出、端口释放均核验成功 |

所有调用均有 token 记录。本轮 21 次传输/生成调用成功，但有一次判分格式失败；不能把“调用成功”当作“判分有效”。本轮 judge 输出 `No.` 原文保留，严格 yes/no 解析未放宽，未重试。分数未经人工复核，随机生成未固定种子，不能把 3→6 个 Yes 归因于预算调整或模型能力提高。

最长输入 3310 token，最大输入＋输出 3949，最长回答 639；小于已加载的 8192。服务日志没有发现输入截断或上下文移动信号。以上是日志核查，不是全上下文容量压力测试。显存为离散采样峰值，不是连续监控的绝对峰值；Ollama 报告模型 `size_vram=5133943438` 字节。

## 五题与规则

完整问题、检索事实、两次回答、参考答案和 judge 的本地入口是新目录下 `review.txt`、`review-inputs.json`；`human-review.json` 保持未填写。上轮和本轮的依据见 [五题 AI 辅助复核](metamem-five-question-ai-review.md)。

| 训练 ID | 本轮原始判分 | 学习处理 |
| --- | --- | --- |
| `6aeb4375_abs` | No / No | 全错，跳过 |
| `9bbe84a2` | Yes / Yes | 全对，跳过 |
| `gpt4_a56e767c` | `No.` 无效 / No | 判分不完整，跳过 |
| `8464fc84` | Yes / Yes | 全对，跳过 |
| `8a2466db` | Yes / Yes | 全对，跳过 |

沿用上游“同题多次回答同时有对有错才更新”的条件，`eligible_ids=[]`。没有触发 reflect / propose / merge，也没有以人工规则补位或追加样本。`smoke/` 中 `rules-00.json`、`rules-01.json` 已保存，规则原文均为：

```json
[]
```

快照中的 `training_ids` 为上表五题，只表示本轮训练来源，不代表每题贡献了一条规则。空规则中没有具体答案；没有非空规则可进行内容泄漏审查。2048 的反思预算已配置，但本轮未实际验证反思、非空规则生成与保存的真实模型链路。

## 清理修改与验证

`scripts/ollama_service.ps1` 按 PID、可执行文件和完整进程启动时间识别本项目服务；旧 PID 被复用时视为原进程已消失，不处理替代它的应用。停止前记录服务及子进程身份，停止后核查这些进程与专用端口，而不把 taskkill 的退出码单独当作清理结果。本轮 taskkill 再次报告已退出子进程，但后置核验成功；真实服务、runner 或端口残留仍会失败。

`scripts/evening_smoke.py` 新增显式配置路径，确认卸载返回 `done_reason=unload` 且 `/api/ps` 为空；卸载或服务停止错误仍使整体返回失败。逐次落盘、中断标记、限时停止及无效结果隔离机制保留。

只运行涉及本次路径的 `test_budget_diagnostic.py` 和 `test_evening.py`：共 15 个测试方法通过。新增配置差异核验、卸载失败不被掩盖核验，以及实际 PowerShell Stop 分支的五种模拟情形：进程全退、PID 复用通过；服务残留、runner 残留、端口占用失败。模拟响应仅验证程序，不计入上述真实调用或成绩。

实际测试命令（通过 Python subprocess 执行，完整输出保存为本轮目录下 `scoped-tests.txt`）：

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p test_evening.py -v
.venv\Scripts\python.exe -m unittest discover -s tests -p test_budget_diagnostic.py -v
git diff --check
```

独立清理核验 `cleanup-verification.json`：本项目进程残留为空，11436 监听数 0，其他 Ollama 进程为空，GPU 使用 0 MiB、利用率 0%。模型卸载前的 API 核验为 `models: []`；未为检查重新启动服务。未关闭游戏或无关应用。

本地证据还包括 `session.json`、`model.json`、`smoke/` 内逐次调用、`comparison.json`、GPU 采样，以及服务日志 `output/ollama-service/20261015-203754.stderr.log`。原始运行产物不提交 Git。

## 能否扩大到 20 条训练和 10 条验证

**技术入口可运行，但暂不建议扩大为有效的 B2 对照实验。** 已识别 judge 假阴性、拒答判分风险和格式失败；电影节题检索证据也不足。应先人工复核上述训练输出并确定判分可靠性，再决定下一轮是否扩大。非空规则学习真实链路仍未验证，不能宣称元记忆学习已跑通。这里不要求反复挑题试到成功，也不将 AI 复核改写成训练标签；本轮到此停止。
