# 本机试点接回与验证记录

日期：2026-10-16（Asia/Shanghai）。关联 issue #8，负责人为当前连接账户 `lanshuheng9-oss`。依赖 PR #7，最终接回的版本为 `5afb9641d9a7ad2aaf1e0c5233196911d70bcd58`；使用独立任务分支，不合并或覆盖原 PR。

**本机已完成前三阶段代码与材料接回、相同数据划分重建、程序校验和进度保存修复；本轮真实模型请求为 0。** 先前真实探索在另一台机器进行，本机没有其原始回答、评审和完整日志，不能称重新验真了历史成绩。

## 先看哪些材料

|目的|现成入口|
|---|---|
|了解目前实际做到了哪一步|[前三阶段统一总报告](metamem-integrated-report.md)|
|准备个人讲解|[十分钟与两分钟讲稿](metamem-integrated-talk.md)|
|对接课设与小组讨论|[课程交付差距](metamem-course-readiness.md)、[组员上手](metamem-team-start.md)|
|检查最新真实实验|[第三阶段研究包](metamem-stage3.md)、[实际运行说明](metamem-stage3-reproduce.md)|
|核对当前电脑的状态|[本机核验JSON](../reports/metamem-local-handoff-20261016.json)|

第三阶段已完成两种提示词对十道开发题各三次、共60条真实回答：原提示词17/30、候选15/30。候选更短且部分依据质量改善，拒答仍未改善；原机器保留候选而未替换默认。这是远端材料的结果，不是本轮在此机重新跑出的成绩，也不是正式测试或人工金标准。

## 本机完成事项

|项目|实际结果|
|---|---|
|代码|从较早main接回最新试点，保留main和独立任务分支；整合依赖分支并发更新，没有覆盖其提交|
|环境|项目`.venv`使用Codex随附Python3.12.14；仅标准库、无pip、未安装第三方依赖|
|原始数据|复制用户微信附件至`data/raw/longmemeval_s_cleaned.json`；277,383,467字节、500条，SHA-256与固定官方版本一致|
|划分重建|20/10/20；清单及全部输入/标签文件哈希与旧记录一致；跨集合问题、会话ID、会话内容及完整历史均无直接重叠|
|测试|最终60项通过，包含新增接回的第三阶段检查及本机合成HTTP夹具；合成回复不是模型响应|
|模拟流程|smoke、learn、select分别36/144/40次模拟调用完成；真实请求0，不记模型成绩或token|
|代码修复|共用原子保存对替换步骤的短暂PermissionError作有界重试；移除二、三阶段的重复私有包装，不重发模型请求|

原始数据SHA-256：`d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`。

划分清单SHA-256：`057be7b8d131e56df62d2884c89463ad485a378b88c6f53f67288705526f6936`。

本轮复制来源记录保存在本地`data/raw/longmemeval_s_cleaned.source.json`，没有重新联网下载数据。重建会解析完整原始JSON、生成三个集合的独立标签文件并计算哈希，不能说完全未触及测试字节。未查看测试答案来修改方法，未运行test阶段。

## 不重复开展已完成的实验

工作开始时远端最新为第二阶段`e32bc3f`，本机曾离线导出四题两提示词、各三次的24个未执行请求。提交期间依赖分支新增第三阶段真实实验`5afb964`，已经覆盖这项研究方向，因此撤下本机重复的配置、脚本和测试，直接沿用现有第三阶段材料。

实现期间的两份准备草稿保留在忽略目录`output/prompt-diagnostic-prepared-20261016/`和`output/prompt-diagnostic-prepared-20261016-r2/`，另存`superseded.json`标记撤回。它们没有生成回答、不是成绩、不得作为后续正式计划。没有为追求正结果额外启动新方案。

## 本机具体限制

本机RTX4060 Laptop、8,188MiB显存，Ollama客户端0.35.0；原实验为RTX5080 Laptop、Ollama0.34.0。默认用户模型清单仅发现embedding模型`bge-m3:latest`，原项目专用模型目录不存在。没有扫描所有磁盘，不能断言其他位置绝无权重。

原机器的`D:\2026下\实验\NLP`和历史`output/`产物在此不可用。Git中的小型汇总、图表和讲稿已接回，原始逐条日志未迁移。本轮未下载Qwen、启动服务、预热或推理，未启用付费API。以后若要本机运行，先核对回答模型、服务版本及新的有限运行预算；不能把另一机器摘要复制成这里的安装证明。

共享数据超过仓库阈值：**请将该文件发送到小组微信群。** 用户将自行发送，目前未确认发送日期，本机来源记录仍为`group_sent_at=null`。不把数据、权重或完整日志加入Git。

## 实际故障与验证命令

系统Anaconda的venv/ensurepip初始化失败，改用Codex随附Python创建无pip环境。初次测试受系统临时目录的沙盒写入限制，改用项目`tmp/python-tests/`；合成HTTP夹具在允许本机回环连接的环境完成，未用真实模型代替。

模拟学习与一项测试实际复现Windows进度文件原子替换`PermissionError/WinError5`。将已有阶段私有重试收敛到共用`write_atomic`：仅对替换步骤最多尝试20次，间隔0.05秒；持续失败继续抛出，其他异常立即暴露，旧快照不变。对应测试验证暂时恢复、持续失败保留快照及其他异常不重试。

失败的`output/local-handoff-20261016/mock-learn/`与被拒绝的`mock-select/`均保留；修复后使用`*-fixed`新目录，不改写失败记录。最终实际验证命令：

```powershell
$env:TEMP = (Resolve-Path tmp/python-tests).Path
$env:TMP = $env:TEMP
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 scripts/run_pilot.py smoke --mock --out output/local-handoff-20261016/mock-smoke-fixed
.\.venv\Scripts\python.exe -X utf8 scripts/run_pilot.py learn --mock --out output/local-handoff-20261016/mock-learn-fixed
.\.venv\Scripts\python.exe -X utf8 scripts/run_pilot.py select --mock --training-run output/local-handoff-20261016/mock-learn-fixed --out output/local-handoff-20261016/mock-select-fixed
```

输出目录已存在，勿直接覆盖复跑。60项最终测试日志为`output/local-handoff-20261016/tests-latest-stage3.txt`，本机核验记录为该目录`verification.json`。模拟运行只验证流程；正式测试和人工验收仍未完成。
