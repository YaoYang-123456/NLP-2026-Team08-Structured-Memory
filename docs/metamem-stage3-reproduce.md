# 第三阶段运行、评审与复核入口

先读[第三阶段报告](metamem-stage3.md)和[统一总报告](metamem-integrated-report.md)。本轮只用既有十道开发题；不重训规则、不读取测试。原数据、模型与环境的获取见[组员上手](metamem-team-start.md)。

## 冻结内容

- [计划](../configs/metamem-stage3-plan.json)：任务起点1792123281，三小时总预算、最多100次本地请求；计划60回答＋1预热，39次仅作余量。实际没有用余量追加实验。
- [唯一候选全文](../configs/evidence-answer-v1.txt)：区分事件/对象/参照时间、累计与增量、件/对，要求简短可核验的fact ID依据，不足时停止猜测，区分个人事实和一般推荐。没有题号、答案或特例。
- 基线仍为`pipeline.answer_prompt(row, [])`及原上游模板；两组规则均为空。原BM25 facts、question date、模型与[生成配置](../configs/qwen-stability-sampling.json)相同。8192是服务上下文，1024是输出预算；temperature0.7、top_p0.95、未设seed。
- 正确性沿用[严格拒答v2](../configs/external-ai-strict-abstention-v2.json)与其余原rubric；[依据质量v1](../configs/evidence-quality-v1.json)是独立六维评价，不反向改写正确性。该v2是本项目政策，不冒充论文标准。
- 先首饰、明信片、海报、Sapiens四题，各两臂三轮共24条；仅检查运行完整性后继续其余36条。轮次顺序为基线/候选、候选/基线、基线/候选；事实哈希逐题一致。不把重复三次说成30道独立题。

## 实际执行命令

```powershell
Set-Location -LiteralPath 'D:\2026下\实验\NLP'
.\.venv\Scripts\python.exe scripts/stage3_session.py --out output/stage3-experiment-20261016
```

这是本轮已执行的历史命令，不能覆盖同目录重跑。绝对预算到期即拒绝；未来重复研究需要另存新授权计划与起点，不修改旧计划或删除登记文件重置请求数。新运行可复现方案，不保证随机文本逐token相同。

监督器启动本项目11436服务，核对已有模型摘要及Ollama版本，预热后确认8192上下文。模型调用只做回答，不做网络judge。生成完成即卸载、退出所属服务，后续APP AI文件评审不继续占用GPU。

## 保存、中断与恢复

`answers.json`预写60个坐标，调用前/后逐次落盘；`calls.jsonl` flush/fsync完整提示词、回答、状态、tokens和耗时；`pending-call.json`记录在途请求。失败、截断、缺失和uncertain不补为No。

若在原预算内中断，可用`--resume-from <最近会话>/smoke`和新的`--out`目录。恢复校验计划、输入、坐标及完整提示词，继承已消耗/可能在途请求；已完成回答不重复生成，先前失败/中断不静默重试。首24条门禁在进入后36条前重新检查，恢复不能绕过。预热仍计请求数。服务启动在创建smoke前失败的边界需先检查进程及保存记录，不盲删registry绕过。

```powershell
.\.venv\Scripts\python.exe scripts/evening_smoke.py stop --out output/stage3-experiment-20261016
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv
Get-NetTCPConnection -LocalPort 11436 -State Listen -ErrorAction SilentlyContinue
```

stop只用于对应活跃会话；本轮已结束，不设置自动续跑。

## 文件式AI评审与离线命令

先将`smoke/queue.hidden.json`及正确性政策交给APP AI；不含条件、规则、历史标签。完成正确性后，再评`quality.queue.hidden.json`中的实际输入facts。回答风格/引用可能暴露条件，且设计者有历史上下文，所以只能称隐藏标签复核，不能称严格盲评。AI不是人工金标准，精确部署版本未知，人工字段null。

```powershell
.\.venv\Scripts\python.exe scripts/stage3_quality.py --out output/stage3-experiment-20261016/smoke --export
.\.venv\Scripts\python.exe scripts/summarize_stage3.py --out output/stage3-experiment-20261016/smoke
.\.venv\Scripts\python.exe scripts/stage3_quality.py --out output/stage3-experiment-20261016/smoke
.\.venv\Scripts\python.exe scripts/summarize_stage3.py --out output/stage3-experiment-20261016/smoke --prepare-audit output/stage3-independent-review
```

这些命令按顺序需已有对应AI评审文件；不是自动评分API。首次export/summary拒绝覆盖既有文件。独立复核范围按冻结规则选整对：拒答、衣物/观鸟异常、正确性变化、正确性与质量冲突、不确定项。独立复核不读取主评标签；各项一次复核，分歧保守保留uncertain，不反复评到一致。引用存在性另做机械核查。

```powershell
.\.venv\Scripts\python.exe scripts/summarize_stage3.py --out output/stage3-experiment-20261016/smoke --audit output/stage3-independent-review
.\.venv\Scripts\python.exe scripts/stage3_quality.py --out output/stage3-experiment-20261016/smoke --audit output/stage3-independent-review
.\.venv\Scripts\python.exe scripts/verify_stage3.py --out output/stage3-experiment-20261016/smoke
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_stage3.py -v
```

复核统计新建`.reviewed`文件，原主评和生成记录不覆盖。核验重建60条实际提示词与请求payload哈希、配置、回答绑定、原始事实与历史关键文件哈希。只跑本轮相关合成测试，不重跑全套。

## 本地原始产物

`output/stage3-experiment-20261016/session.json`保存启动、时间及清理；同目录`gpu-samples.jsonl`为运行中采样，峰值仅是采样峰值，不保证瞬时最大。`smoke/`保存冻结计划、完整回答/调用/隐藏队列/主评/质量主评/派生统计及verification。`output/stage3-independent-review/`保存一次独立复核与范围。Git仅收代码、配置、小型统计、图表和文档，不收原始大日志/数据/权重。

正确性与质量都由外部APP AI给出；本地61次请求和AI评审条数分别统计，APP token/费用未作为本地模型token估算。
