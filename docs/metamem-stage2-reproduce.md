# 第二阶段运行与复核说明

本阶段主入口为[研究包](metamem-stage2.md)，方法与论文对应见[方法清单](metamem-stage2-method.md)。本机复用已有数据、独立`.venv`与Qwen，不下载、不重新训练、不读测试。此说明区分算法可重做、历史产物可核验和模型输出无法逐token保证相同。

## 冻结材料与边界

- [预先冻结计划](../configs/metamem-stage2-plan.json)：原任务起点epoch `1792119847`；总截止 `1792134247`（四小时），推理截止 `1792133647`（预留十分钟收尾）；最多180次本地生成请求，预热、失败和恢复预热均计数。计划132个回答＋1次预热，47次为排障余量，不是补跑目标。
- [生成配置](../configs/qwen-stability-sampling.json)：Qwen2.5-7B-Instruct Q4_K_M、temperature0.7、top-p0.95、回答上限1024；Ollama服务上下文8192。max_tokens不是上下文容量，seed未设置，重复输出不保证相同。
- [固定学习规则](../configs/rules-stage1-frozen.json)：v1训练规则的精确副本，本轮不更新；[严格拒答v2](../configs/external-ai-strict-abstention-v2.json)为本项目新增评分政策，其他题型沿用原rubric。
- `output/stage2-preparation/oracle.inputs.json`：两题参考辅助定位的真实历史证据补齐；不能作为自动检索使用。`oracle-diff.json`、`verification.json`保存来源和核验，`oracle-quality-policy.json`保存独立质量指标。
- `output/stage2-retrieval/validation.improved.inputs.json`：仅依赖问题、日期、历史的角色预算检索，user/other各10块与6,000字符，不回填余量。`metrics.json`、`facts-diff.json`记录工程量、来源fact ID及同ID正文变化；`inputs.frozen.json`固定生成输入字节哈希。
- 原始模型版本、数据revision与权重哈希见[第一阶段复现说明](metamem-stage1-reproduce.md)。本轮没有另一份模型安装流程，也不把新机配置当作已经验证。

## 本轮实际启动命令

```powershell
Set-Location -LiteralPath 'D:\2026下\实验\NLP'
.\.venv\Scripts\python.exe -X utf8 scripts/stage2_session.py --out output/stage2-experiment-20261015
```

这是已执行记录，不是邀请对相同目录重跑。目录存在就拒绝覆盖；计划绝对截止过后入口拒绝运行。未来新实验需另存新的预先批准计划、起点和输出，不能通过改旧计划延长本轮时间。worker按冻结顺序先oracle12条、再主实验120条：oracle每题原/补证各三次；主实验A原检索无规则、B原检索旧规则、C新检索无规则、D新检索旧规则，每组10题三次。规则组共享各自检索条件的同一facts哈希。

监督器只启动本项目11436端口服务，核对已有模型摘要、Ollama版本；预热后检查加载上下文。生成完成立即卸载并停服务，外部AI离线评审不会保持GPU占用。没有自动任务，也没有隐藏judge网络调用。

## 本轮实际故障与恢复

首次会话在94次请求（1次预热＋93条回答）后，Windows在原子替换 `answers.json.partial` 为 `answers.json` 时返回WinError5。原运行保留failed状态，监督器正常卸载、退出服务；这不是模型生成失败。第93个回答已在calls日志完整保存、queue有93条，但answers主清单当时只有92条generated。

仅对该已发生的PermissionError增加最多20次、间隔0.05秒的短暂保存重试（等待最多约0.95秒，不是重新请求模型）；其他异常继续抛出。恢复程序按sample ID唯一匹配，并重建完整answer_prompt逐字核对，只有status=ok且finish_reason=stop才恢复已保存答案。确实恢复1条，不重新生成；继承日志存为 `calls.inherited.jsonl` 并纳入成本统计。

实际恢复命令为：

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/stage2_session.py --out output/stage2-experiment-20261015-resume1 --resume-from output/stage2-experiment-20261015/smoke
```

恢复继承94次请求、原始四小时截止，不重置预算；最终确实完成132条回答＋2次预热＝134次请求。原失败目录与resume1目录均保留。复核修复代码确认其只重试文件保存，不重试生成；四项相关测试含已落日志回答恢复、权限错误窄重试、角色预算与配对/uncertain统计。未再运行无关全量测试。

## 中断、保存和恢复

`smoke/answers.json`事先保存132个坐标，逐次原子替换；`calls.jsonl`每个已完成请求flush/fsync，`pending-call.json`记录可能在途请求。每条完整回答后更新`queue.hidden.json`。强杀在写入边界仍可能留下在途或刚完成但未回填的记录，不能默认全部完整。failed/interrupted/not_started不记成答错。

尚在**原四小时预算内**且需要继续未开始的槽位时，使用新目录和最近一次smoke：

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/stage2_session.py --out output/stage2-resume-02 --resume-from output/stage2-experiment-20261015-resume1/smoke
```

`output/stage2-session-registry.json`要求从最近一次会话恢复，不能另开目录把请求数归零。恢复验证原计划、输入哈希和坐标；继承既有请求及可能在途请求，先前失败/中断项不会偷偷重试，只继续not_started槽位。恢复预热也消耗预算。若最新会话启动失败且尚未留下可恢复smoke，不删除登记文件盲目绕过；先核查所属进程、calls及pending，保存故障事实再处理。预算过期则只整理已有产物，不续跑。

停止当前会话：

```powershell
.\.venv\Scripts\python.exe scripts/evening_smoke.py stop --out output/stage2-experiment-20261015-resume1
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv
Get-NetTCPConnection -LocalPort 11436 -State Listen -ErrorAction SilentlyContinue
```

恢复会话需把stop命令目录改成当前目录。结束核查session.json中的卸载响应、空模型列表、所属服务退出，以及独立进程/端口核验；GPU其他程序占用不能算本模型残留。不关闭无关应用。

## 文件式AI评审

只把 `smoke/queue.hidden.json`、冻结政策和评审格式交给主评。评审包不含条件名、规则或历史标签，但完整回答可能泄露行为线索，且组织者已有背景，所以不能称严格盲评。评分为Yes/No/uncertain，理由和无依据扩写另列；人工验收字段保持null。外部AI评审条数与本地请求数分开统计，未知APPtoken记未知。

记录完整输入哈希、政策版本、可确认评审身份；精确部署版本不可确认时写unknown，不猜。复核范围在生成前冻结：所有拒答、衣物和观鸟回答，以及主要四组配对出现初判分歧的同题同轮完整四组；oracle12条全部纳入正确性复核，晚餐6条另查预注册质量指标。初判与复核都保留，标签分歧在独立保守派生统计里变为uncertain，不覆盖初判，不反复判到满意。

评分引用参考不代表参考进入生成。worker只以问题、检索facts和规则构造answer_prompt，参考只用于回答完成后的评审导出。该隔离需通过实际prompt重建与哈希核验，不能仅凭目录分开就声称通过。

## 离线统计命令

完整主评文件保存为 `smoke/reviews.json` 后：

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/summarize_stage2.py --out output/stage2-experiment-20261015-resume1/smoke
.\.venv\Scripts\python.exe -X utf8 scripts/summarize_stage2.py --out output/stage2-experiment-20261015-resume1/smoke --prepare-audit output/stage2-independent-review
```

第二条只导出预先规定范围，不调用模型。完成该目录内的独立AI `reviews.json` 后：

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/summarize_stage2.py --out output/stage2-experiment-20261015-resume1/smoke --audit output/stage2-independent-review
```

本轮独立复核实际目录为 `output/stage2-independent-review`，最终保守统计为 `output/stage2-experiment-20261015-resume1/smoke/summary.reviewed.json`。目标已存在时不覆盖；先保留初判汇总，再产生reviewed派生统计，不能把同一命令反复运行当作增加独立证据。这些统计不会启动Ollama，也不改变冻结规则或历史选择记录。

## 可取得的产物

原始目录 `output/stage2-experiment-20261015` 与恢复目录 `output/stage2-experiment-20261015-resume1` 保存两段session、model、GPU采样和worker日志；最终resume1/smoke保存冻结计划/政策/输入清单、answers、calls、队列与评审。事实变化来自 `output/stage2-retrieval`，oracle与原史摘取来自 `output/stage2-preparation`。最终离线核验实际执行：

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/verify_stage2.py --out output/stage2-experiment-20261015-resume1/smoke
```

实际134次请求、0生成失败、0输出上限截断，调用耗时合计515.3445秒，报告输入/输出token为407,468/46,577；最大输入token＋输出预算4,867，小于8192服务上下文。132条完整prompt按固定问题、facts与规则重建一致，历史v1的51个文件及阶段一关键6个文件哈希未变。两段会话均卸载模型并退出所属服务，最终GPU0 MiB、0%。这些是运行和来源核验；总阶段工时还包含准备、故障处理、AI评审及整理，不能用调用耗时代替。

晚餐oracle独立质量复核：原检索两组必要食材同时正确使用0/3，补证3/3；无依据个人归属原检索3个yes，补证1个yes、2个uncertain。质量指标独立于原正确性评分，不能把2个uncertain当作已证明没有扩写。最终正确性首评132条、独立复核72条，标签无分歧；另6条晚餐质量复核，合计210条AI评审记录，不是210个独立回答或人类金标准。A/B/C/D分别16/17/15/17个Yes（各30条、完整有效覆盖、无uncertain）。拒答仍各0/6；衣物虽然均No，参考口径问题未解决。oracle晚餐1/3→3/3，首饰0/3→1/3，但首饰唯一匹配数字的回答把耳环按2计且未使用戒指，不能称补证推理成功。

质量队列已与实际原队列按sample ID、完整问题、回答及输入哈希回绑核验；对应验证重跑通过。两段监督会话合计545.4045秒，显存采样峰值5,142 MiB。最终研究结论不推荐替换BM25基线，保留角色预算作为可选负结果。下一轮四题24回答的提示词诊断仅是建议，本轮没有执行。

Git保存必要代码、配置、小型汇总、文档与图表；不保存原始数据、权重或大日志。若需向组内交付达到20MB的原数据或模型文件，**请将该文件发送到小组微信群**，仓库只记录名称、用途、来源与哈希，不记为已发送。另一台机器需独立核验现有模型与数据，不能仅复制摘要就宣称环境验证完成。

## 重建事实与图表

以下只适用于已取得冻结`data/pilot`、固定源数据和`output/stage1-evidence/validation-history.json`、目标准备目录尚不存在的新工作副本。本轮原目录已存在，不要删除或覆盖它们：

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/prepare_stage2_evidence.py
.\.venv\Scripts\python.exe -X utf8 scripts/prepare_stage2_retrieval.py
.\.venv\Scripts\python.exe -X utf8 scripts/prepare_stage2_evidence.py --audit-improved
```

本轮这三条均实际执行。oracle脚本中的题目/来源白名单只用于明确标识的oracle诊断；可部署候选`retrieve_balanced`没有这些分支，也不读参考。生成前需要保存新工作副本的输入清单哈希及新的独立预算，不能把当前绝对截止用于下一轮，也不能抹掉原注册文件绕过预算。仅检出Git无法逐字取得旧生成结果，必须取得忽略目录或独立重新生成、重新APP评审。

图表实际使用已有系统Python的Matplotlib3.11.1（不向课程venv安装依赖）：

```powershell
python -X utf8 scripts/plot_stage2.py --summary output/stage2-experiment-20261015-resume1/smoke/summary.reviewed.json --out reports
```

输出PNG和SVG，已查看PNG验证标签、柱值及配对方向。它们表达重复观察，不含独立样本置信区间。
