# 本机试点接回与下一轮离线准备

日期：2026-10-16（Asia/Shanghai）。关联 issue #8。基于 PR #7 的第二阶段提交 `e32bc3fc26d8ae233ffa9b1cd3a588c4de77433a`，使用独立依赖分支；不修改或合并原 PR。负责人为当前连接账户 `lanshuheng9-oss`。

**本机已经完成代码接回、数据重建、程序校验和四题提示词对照的离线准备；本轮真实模型请求为 0。** 先前第一、第二阶段已在另一台机器运行，不重复列为尚待完成，也不把其原始日志说成已迁移到这里。小型历史汇总、图表和讲稿可直接从 [第二阶段研究包](metamem-stage2.md) 阅读。

## 已完成与证据

|项目|本机实际结果|
|---|---|
|代码|接回 PR #7 的固定版本，保留 main，建立独立任务分支|
|环境|项目 `.venv` 使用 Codex 随附 Python 3.12.14；仅标准库，没有安装第三方依赖|
|原始数据|复制用户提供的微信文件至 `data/raw/longmemeval_s_cleaned.json`；277,383,467 字节、500 条，SHA-256 与固定官方版本一致|
|划分重建|20/10/20；清单 SHA-256 与旧记录完全一致，所有输入/标签文件哈希核验通过；跨集合问题、会话 ID、会话内容和完整历史均无直接重叠|
|测试|56 项通过，含本机合成 HTTP 夹具；合成回复不是模型响应|
|模拟流程|smoke、learn、select 完成，分别 36/144/40 次模拟调用；真实请求 0，模型分数/token 均不计成绩|
|下一轮准备|固定四题、原提示词/证据绑定提示词、各三次，共 24 个未执行槽位；逐一重建 payload 与哈希通过|

机器可读结果见 [本机核验汇总](../reports/metamem-local-handoff-20261016.json)。原数据哈希为 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`，划分清单哈希为 `057be7b8d131e56df62d2884c89463ad485a378b88c6f53f67288705526f6936`。复制来源记录在本地 `data/raw/longmemeval_s_cleaned.source.json`；本轮没有重新联网下载数据。

数据准备会解析完整原始 JSON、生成三个集合的独立标签文件，并计算文件哈希；这不等于没有触及测试字节。此次四题准备脚本只读取验证输入，不读取参考答案或测试输入/标签。未运行 test 阶段，未打开测试答案用于提示词设计或评分。

## 下一轮已经固定的内容

准备命令（仅离线导出，不启动服务）：

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/prepare_prompt_diagnostic.py --out output/prompt-diagnostic-prepared-20261016-r2
```

上述目录本轮已经生成，重跑必须另选新目录；入口拒绝覆盖。更早的 `output/prompt-diagnostic-prepared-20261016/` 是实现期间的准备草稿，保留但不用于继续实验。

配置见 [对照定义](../configs/metamem-prompt-diagnostic.json)。四题为首饰 `9d25d4e0`、明信片 `01493427`、海报 `a96c20ee_abs` 和 Sapiens `2311e44b_abs`，均来自已经用于开发的验证集合。

- 两组使用相同的原 BM25 事实、顺序与 v1 学习规则精确副本；没有修改默认回答函数、默认检索器或规则。
- 原组逐字复用原回答提示词。新组仅追加一段通用要求：绑定对象/事件与来源、检查问题时间窗口、区分累计/增量/剩余量与计数单位，缺少必要事实时明确停止猜测。它是人工设计的提示词，不称为新学习规则或学术创新。
- 三轮顺序预先规定为原→新、新→原、原→新。生成参数沿用原配置；没有设置 seed，不声称受控随机种子。
- 保存固定协议、四题输入、24 个完整请求、规则、生成配置、严格拒答 v2 政策、实现与材料哈希。所有 response/correct 均为空、status 均为 not_started。

计划生成 24 条回答，若预热一次则共 25 次本地请求。**此准备包没有自动推理入口，没有沿用已经过期的旧任务截止时间，也没有安排自动任务。** 实际运行前需在有模型的机器上重新核验服务与模型、保存新的有限运行时段及请求上限，再按冻结 payload 生成。不能通过修改旧阶段计划延长原任务。

回答完成后，按固定 v2 政策隐藏条件名评审；分别记录最终正确性、引用来源是否真实支持实体/事件/时间/计数，以及是否存在无依据具体断言。引用一个存在的 ID 不自动证明依据正确；缺失、服务失败和 uncertain 不记成 No。人工验收字段继续为空。全部重复一次性报告，不按成绩追加采样。

这些题已影响提示词设计，只能支持开发诊断。新提示词还增加输入长度，因此即使有差异，也不能单独归因于证据约束的语义。准备不代表性能提升。

## 本机运行限制

本机为 RTX 4060 Laptop、8,188 MiB 显存，Ollama 客户端 0.35.0；原实验为 RTX 5080 Laptop、Ollama 0.34.0。本机默认模型清单仅发现 `bge-m3:latest`，它是 embedding 模型；原项目专用模型目录未找到。没有扫描所有磁盘，不能断言其他位置绝无权重。

原机器的 `D:\2026下\实验\NLP` 与 `output/` 原始回答、评审和完整日志在此不可用。Git 中现有小型汇总可以阅读，但没有逐条重新验真历史成绩。本轮未下载 Qwen、启动服务、预热或进行推理，未启用付费 API。真实四题实验仍受可用回答模型和新机兼容性核验阻塞；不能把另一机器的模型摘要复制成此机的安装证明。

共享数据文件超过仓库阈值：**请将该文件发送到小组微信群。** 用户表示将自行发送，目前未确认发送日期；本机来源记录仍保留 `group_sent_at=null`。不将数据、权重或完整运行日志提交 Git。

## 实际故障、修复与命令

系统 Anaconda 的 venv/ensurepip 初始化失败，改用 Codex 随附 Python 创建无 pip 的独立环境；本项目不需要安装依赖。初次测试又受系统临时目录的沙盒写入限制，改用项目 `tmp/python-tests/`。本机 HTTP 夹具在允许本机回环连接的执行环境完成；未用真实服务代替夹具。

模拟学习和一项测试实际复现了 Windows 的进度文件原子替换 `PermissionError/WinError5`。原第二阶段只在私有包装中有短暂保存重试，普通流程未覆盖。本次将它收敛到共用 `write_atomic`，只对替换步骤的 PermissionError 最多尝试 20 次、间隔 0.05 秒；持续失败继续抛出，其他异常不重试。保留旧快照的机制不变，不重发模型请求。对应测试核验短暂恢复、持续失败保留快照、其他异常立即暴露。

失败的 `output/local-handoff-20261016/mock-learn/` 与后续被拒绝的 `mock-select/` 目录均保留；修复后使用新的 `*-fixed` 目录，不把失败记录改成成功。

最终实际验证命令：

```powershell
$env:TEMP = (Resolve-Path tmp/python-tests).Path
$env:TMP = $env:TEMP
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 scripts/run_pilot.py smoke --mock --out output/local-handoff-20261016/mock-smoke-fixed
.\.venv\Scripts\python.exe -X utf8 scripts/run_pilot.py learn --mock --out output/local-handoff-20261016/mock-learn-fixed
.\.venv\Scripts\python.exe -X utf8 scripts/run_pilot.py select --mock --training-run output/local-handoff-20261016/mock-learn-fixed --out output/local-handoff-20261016/mock-select-fixed
```

这些输出目录本轮也已存在，勿直接覆盖复跑。最后 56 项测试日志在 `output/local-handoff-20261016/tests-final-fixed.txt`，数据/请求核验在该目录 `verification.json`。模型成绩、人工验收及正式测试仍未完成。
