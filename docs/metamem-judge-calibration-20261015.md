# 固定回答 judge 校准：未通过扩大条件

完成19条固定完整回答的旧、新模板各一次判分，**38次judge＋2次预热，共40次真实本地生成请求**。两版均19/19解析有效、9 Yes/10 No，归一化标签逐项一致；两项明确疑似假阴性未修复，故**不采用新模板，不进入20条训练或10条验证**。所有复核是AI辅助意见，非人工金标准或人类验收。没有重生成回答、重判任何项目、下载模型或使用付费API。

## 时间、环境与预算

- 工作起点：2026-10-15 21:05:59 America/New_York（2026-10-16 01:05:59 UTC）；推理最晚截止21:55:59，总截止22:05:59。实际01:10:18 UTC已卸载最后一次模型，01:11:13 UTC完成独立清理核验，提前结束。
- 起始提交 `5ae227f`，沿用PR #7分支并依赖PR #5。没有覆盖其他工作。
- Ollama 0.34.0，Qwen2.5-7B-Instruct Q4_K_M，模型摘要 `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`。独立服务127.0.0.1:11436，实际加载上下文8192，复用E盘权重。启动前GPU 0 MiB/0%。
- 沿用 `configs/qwen-budget-diagnostic.json`：answer1024、reflection2048；judge32/temperature0/top_p1。校准只调用judge与8-token预热。两版设置相同，按固定输入序号交替先旧/先新，未选择有利样本。
- seed未传入。[Ollama官方兼容文档](https://docs.ollama.com/api/openai-compatibility)列出seed支持；本轮未额外请求验证当前二进制的seed行为，也不宣称temperature0保证确定性，不把判分变化全部归因于提示词。
- 代码核算：一轮20题训练=40回答＋40judge＋最多40反思＋20提案＋4合并=144请求。初始空规则及4个批检查点最多5个不同B2候选，10题验证最多100请求；空候选与B0输入一致可复用为B0，B1另20请求。加38校准＋一次预热，上限303；因保存中断增加一次预热后为304，低于420。未增加采样或候选。

## 模板与采用决定

旧版 `upstream-66232c1` 保留官方函数原文。新版 `object-time-equivalence-v1` 仅在非拒答模板前补充：按所问对象/时间点比较参考、接受语义等价、不默认最新值是所问值；偏好题按原rubric使用个人信息即可，不要求全部rubric点、不增加所有额外事实必须来自检索的条件。没有题号、具体答案或卡片特例。拒答分支与旧版逐字相同，拒答后猜测的风险单列。

两版使用 `single-label-v2` 解析。19条来自前两轮相同五道训练题的9＋10份完整回答；第一轮Premiere Pro attempt0以length结束，明确排除。**这是训练开发样本，不是独立验证，不能估计总体judge准确率。**

采用条件未满足：

1. 第一轮Apex attempt1最终明确旧目标level100，参考也是level100；旧、新仍均No。错误回答旧目标150则仍判No。
2. 第一轮Premiere Pro attempt1利用软件偏好并提及高级设置，原rubric不要求覆盖所有点；旧、新仍No。额外书目真实性未核实，但本轮没有把它加为基准扣分条件。
3. Roscioli四份明确答案仍均Yes，第二轮Apex两份和Premiere Pro两份也仍Yes，未发现新增明确误判。
4. 意大利餐厅的“信息不足＋猜测”维持原结果和歧义，不把Yes当作无幻觉认证。

通用时间/等价澄清未解决已知问题。judge只返回标签，不能确定内部误判机制，不能声称已证明具体长度偏差或量化导致错误。本轮不再修改模板或反复判到满意，默认版本仍为旧版，新版只保留作诊断候选。`adoption-decision.json` 保存拒绝采用依据及来源哈希，人工字段为null。

## 阶段、成本与未完成项

| 阶段 | 请求 | 有效覆盖 | Yes / No | 无效 | 请求耗时 | 输入 / 输出token |
| --- | --- | --- | --- | --- | --- | --- |
| 旧模板校准 | 19 | 19/19 | 9 / 10 | 0 | 2.497秒 | 8706 / 38 |
| 新模板校准 | 19 | 19/19 | 9 / 10 | 0 | 2.605秒 | 10356 / 40 |
| 预热 | 2 | 不计判分 | 不适用 | 0 | 约9.37秒 | 68 / 4 |
| 20题训练 | 0 | 未启动 | 不适用 | 不适用 | 0 | 0 |
| B0验证 | 0 | 未启动（0/10已执行） | 不适用 | 不是10条失败 | 0 | 0 |
| B1验证 | 0 | 未启动（0/10已执行） | 不适用 | 不是10条失败 | 0 | 0 |
| B2候选验证 | 0 | 未启动 | 不适用 | 不适用 | 0 | 0 |

总请求40，无HTTP/生成失败、无输出截断，输入19130/输出82 token；两段模型会话合计49.90秒，worker合计14.83秒。最大单次输入＋输出925，小于8192；不是上下文压力测试。显存采样峰值5136 MiB，第二段采样启动较晚，只采到已卸载状态，因此该峰值不能代表两段完整峰值。

**本轮没有真实反思、提案、合并或学习规则保存。** 这是训练未启动，不是“训练后得到空规则”；没有新规则来源、泄漏候选或验证选择结果。旧规则不变。B0/B1/B2没有可报告的验证判对数，不用0分代替缺失实验。没有读取测试输入/答案或调用test命令。

后续协议保持：初始空检查点＋每批检查点、按规则哈希去重、只允许10/10有效判分候选、最大判对数、并列取最早检查点；不根据验证错误回训。候选须先保存来源/通用性/答案泄漏审查，明确答案泄漏者排除。本轮没有候选可审查或冻结。

## 中断、恢复与清理

第一段 `output/judge-calibration-20261015-2108/` 在第21次judge已成功fsync后，`comparison.json.partial`原子替换被Windows拒绝（WinError5），快照落后一项；调用原文未丢失。可能被并行读取或其他短时占用，具体占用进程未确定。

最小修复仅对比较快照的PermissionError做最多5次、每次50ms的本地写重试，不重发模型请求。从日志恢复21个已判项目并核验完整提示词、配置与来源哈希，到全新目录 `output/judge-calibration-20261015-2110-continuation/` 补齐剩余17次judge，另预热1次。共38个不同source+qid+attempt+version键，无重复判分。原失败运行状态和日志保留，不改写为成功。

沿用既有supervisor的有限worker入口，截止始终为01:55:59 UTC，恢复不延后。Client首次硬上限39、恢复18，均含预热。run_pilot也支持 `--max-requests`，预热计入同一额度。无模型自动重试或自动续跑。

两段均确认unload的done_reason=unload、`/api/ps`为空、服务退出。最终独立核验：所属PID/启动时间身份匹配的服务和runner残留为空，11436监听数0，其他Ollama进程为空，GPU0 MiB/0%。未关闭游戏或无关应用。证据为两个session.json及最终cleanup-verification.json。

## 错误归因和下一步

- **judge**：Apex正确旧目标、Premiere Pro完整偏好回答的No，是停止扩大的主要证据；这些标签不能可靠地筛选正负轨迹来学习规则。
- **证据利用**：Apex把旧值答成新值，电影节遗漏已检索Portland/Austin，餐厅从缺失信息作推测。
- **检索不足**：电影节事实未支持参考四家的完整证据，不能把所有错误归给回答模型。
- **规则影响**：本轮未训练、未评估规则效果，未知。
- **未证实**：书目/网址真实性、judge内部错误原因、泛化可靠性均未知。拒答和无依据扩写分开记录。

**下一步最值得做的一件事：用更可靠且明确可用的judge，对这同一批固定19条回答做一次独立校准。** 不换题、不用更高Yes率代替可靠性。模型/服务及资源选择留待下一轮，本轮不下载或启用付费服务。

## 实际命令、检查与待运行命令

两段通过Python调用既有supervisor；第一段config为 `configs/qwen-budget-diagnostic.json`，第二段为 `output/calibration-continuation-config.json`（只增加原日志路径）；session为上述两个新目录。完整实际worker命令与配置保存于session.json/run.json。

```python
from datetime import datetime
from pathlib import Path
import time, sys
sys.path.insert(0, str(Path('scripts').resolve()))
import evening_smoke
start = datetime.fromisoformat('2026-10-16T01:05:59+00:00').timestamp()
now = time.time()
evening_smoke.ACTIVE_SECONDS = max(0, start + 3000 - now)
evening_smoke.TOTAL_SECONDS = max(0, start + 3600 - now)
# session/config 按上述实际两段取值；历史时间不可用于未来重跑。
evening_smoke.start(session.resolve(), config, Path('scripts/calibrate_judge.py').resolve())
```

专项检查：test_calibration.py 4项、test_judge_parser.py 4项、test_evening.py 12项，共20项通过。覆盖模板隔离、拒答保持、请求上限、日志恢复/有界本地写重试、解析及截止/清理。另执行一次mock smoke：仅1次模拟预热后因额度终止，无真实调用，验证预热计入上限。执行git diff --check，无全量或无关测试。

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p test_calibration.py -v
.venv\Scripts\python.exe -m unittest discover -s tests -p test_judge_parser.py -v
.venv\Scripts\python.exe -m unittest discover -s tests -p test_evening.py -v
.venv\Scripts\python.exe scripts/run_pilot.py smoke --mock --warmup --config configs/qwen-budget-diagnostic.json --max-requests 1 --out output/calibration-request-cap-mock-20261015
```

以下是**未执行、不得现在自动续跑**的底层阶段命令。只有未来judge通过校准、配置获采用且重新明确启动时间后才可运行，还须置于同等服务/截止/清理保护内。approvedConfig不是本轮已批准文件，各变量须在新轮次明确设置。

```powershell
.venv\Scripts\python.exe scripts/run_pilot.py learn --config $approvedConfig --out $newTraining --deadline-epoch $newDeadline --stop-file $stopFile --max-requests 144
.venv\Scripts\python.exe scripts/run_pilot.py select --config $approvedConfig --training-run $newTraining --out $newSelection --deadline-epoch $newDeadline --stop-file $stopFile --max-requests 100
```

第二条仅做B2候选选择；执行前仍需加入本轮要求的候选泄漏排除、逐题验证落盘，并安排B1验证及B0空候选复用。这部分因校准未通过而未实施，不能把这两条称为已完成的三组验证入口。当前无自动运行任务。原始数据、权重与调用日志不提交Git。

## 全部19项对照与AI辅助复核

A=evening-smoke-20261015-1454，B=budget-diagnostic-20261015-2038；attempt从0计，大小写/句号原样保留。本轮每项旧、新解析状态均为valid。完整问题、参考、事实、回答和三路判分在最终目录的 `ai-review-comparison.json`；未添加AI意见的生成记录为 `smoke/comparison.json`。人工字段全部null。两个run.json记录六个直接来源文件的哈希并核验未变；未写回旧目录。

| 来源/题ID/attempt | 历史原文/状态 | 本轮旧版/状态 | 本轮新版/状态 | AI辅助意见 |
| --- | --- | --- | --- | --- |
| A / 6aeb4375_abs / 0 | Yes / valid | Yes / valid | Yes / valid | 识别信息不足但又推测没试过很多家；现行拒答标准有歧义，Yes 不等于无幻觉。 |
| A / 6aeb4375_abs / 1 | No / valid | No / valid | No / valid | 把没有记录推成没试过任何一家；No 有合理依据，但拒答后推测的边界仍未由原标准明确。 |
| A / 9bbe84a2 / 0 | No / valid | No / valid | No / valid | 把旧目标答成150，已检索到100；No合理，错误在时间证据利用。 |
| A / 9bbe84a2 / 1 | No / valid | No / valid | No / valid | 最终明确旧目标100，参考100；旧新仍No，明显疑似judge假阴性未修复。 |
| A / gpt4_a56e767c / 0 | no / valid | no / valid | No / valid | 仅确定AFI至少一家；没有达到参考4，No合理。检索未支持第四家且忽略Portland/Austin。 |
| A / gpt4_a56e767c / 1 | No / valid | No / valid | No. / valid | 回答至少两家，漏用Austin；参考4，No合理，同时存在检索覆盖不足。 |
| A / 8464fc84 / 0 | Yes / valid | Yes / valid | yes / valid | Roscioli与直接事实及参考一致，Yes合理；不独立核验真实餐厅宣传。 |
| A / 8464fc84 / 1 | Yes / valid | Yes / valid | Yes / valid | Roscioli与直接事实及参考一致，Yes合理；不独立核验真实餐厅宣传。 |
| A / 8a2466db / 1 | No / valid | No / valid | No / valid | 明确使用Premiere Pro偏好且提到高级设置，按rubric应倾向Yes；旧新仍No。新增书目/作者不在事实中，未核实，单列质量风险而不擅自改标准。 |
| B / 6aeb4375_abs / 0 | No / valid | No / valid | No / valid | 承认没有直接记录后猜至少一家/0到4家或更多；有无依据推测，原拒答标准边界含糊，保留No且不当成人工金标准。 |
| B / 6aeb4375_abs / 1 | No / valid | No / valid | No / valid | 承认没有直接记录后猜至少一家/0到4家或更多；有无依据推测，原拒答标准边界含糊，保留No且不当成人工金标准。 |
| B / 9bbe84a2 / 0 | Yes / valid | Yes / valid | Yes / valid | 明确旧目标100、后来150，Yes与参考一致；未发现新增明确误判。 |
| B / 9bbe84a2 / 1 | Yes / valid | Yes / valid | Yes / valid | 明确旧目标100、后来150，Yes与参考一致；未发现新增明确误判。 |
| B / gpt4_a56e767c / 0 | No. / judge_parse_failed | no / valid | No / valid | 只围绕AFI回答至少一家或1；参考4，No合理。忽略已检索到的Portland/Austin，也缺少支持第四家的事实。 |
| B / gpt4_a56e767c / 1 | No / valid | No / valid | No. / valid | 只围绕AFI回答至少一家或1；参考4，No合理。忽略已检索到的Portland/Austin，也缺少支持第四家的事实。 |
| B / 8464fc84 / 0 | Yes / valid | Yes / valid | Yes / valid | Roscioli与直接事实及参考一致，Yes合理；不独立核验真实餐厅宣传。 |
| B / 8464fc84 / 1 | Yes / valid | Yes / valid | Yes / valid | Roscioli与直接事实及参考一致，Yes合理；不独立核验真实餐厅宣传。 |
| B / 8a2466db / 0 | Yes / valid | Yes / valid | Yes / valid | 利用Premiere Pro偏好及高级设置，Yes符合现行rubric；网址或资源真实性未独立核验，不作为新增扣分条件。 |
| B / 8a2466db / 1 | Yes / valid | Yes / valid | Yes / valid | 利用Premiere Pro偏好及高级设置，Yes符合现行rubric；网址或资源真实性未独立核验，不作为新增扣分条件。 |
