# 组员上手：先理解结论，再复核运行

这是杨垚负责的MetaMem个人试点入口，不是全组已经确认的最终方案。三阶段均保留原记录、负结果和AI评分边界。

## 建议阅读顺序

1. 先读[统一阶段总报告](metamem-integrated-report.md)，了解从“规则是否有效”走到“检索还是利用”的研究线索；再看[课程交付差距](metamem-course-readiness.md)。
2. 需要讲解时用[十分钟与两分钟讲稿](metamem-integrated-talk.md)，不要逐页念历史日志。
3. 需要验证结论时读[阶段一](metamem-stage1.md)、[阶段二](metamem-stage2.md)、[阶段三](metamem-stage3.md)的逐题表及图表。每次只比较同一轮固定对照；不要把不同温度/政策的结果混成总准确率。
4. 准备实际复现时读[阶段三运行说明](metamem-stage3-reproduce.md)及[阶段二运行说明](metamem-stage2-reproduce.md)。这些记录区分真实命令、已过期的实验预算与未来新运行，不能照抄旧绝对截止来续跑。

## Git里有与没有的内容

|材料|获取与用途|
|---|---|
|源代码、冻结配置、政策、老师要求、六篇论文、简明统计和图表|Git中可直接审阅；从当前草稿PR检出对应提交，不自行合并PR5或PR7|
|Python/Ollama与模型|原机已有独立`.venv`和Ollama0.34.0；新机器需自行核实环境。代码主要使用标准库，不需要训练框架。模型摘要见`configs/stage1-model-reference.json`，标签相同不保证权重相同|
|真实原始数据|`data/raw/longmemeval_s_cleaned.json`，277,383,467字节；官方fixed revision及SHA见下文，不入Git|
|固定划分与检索输入|`data/pilot/train.inputs.json`、`validation.inputs.json`与独立labels、manifest；复核当前阶段只取训练与开发资料，不打开test文件|
|旧回答、逐次调用、AI评审与来源摘录|本机`output/`的忽略产物。只检出Git不能得到完整旧回答；需按阶段索引取得对应只读产物与哈希，否则只能在新预算内做新的运行，不能称逐字复现|

固定数据来源：官方`xiaowu0162/longmemeval-cleaned`的revision `98d7416c24c778c2fee6e6f3006e7a073259d48f`，SHA-256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`。取得文件后计算哈希，不能只看文件名。权重主blob约4.68GB，原始数据约277MB；需要交接时，**请将该文件发送到小组微信群**。这里只记录名称、用途、来源与哈希，不声称已经发送；权重优先按原下载记录核验，勿覆盖别的项目模型。

原机不要重复运行`prepare_data.py`，已有目录会拒绝覆盖；本阶段授权也不包含重新建立或查看测试题。另机若需要完整重建，必须另行约定数据访问边界，不能把读取整份原始集误称为只访问开发题。

## 安全的首次核验

在仓库根目录，先读`AGENTS.md`，查看`git status --short`、`git log -1 --oneline`，保留现有修改。确认数据、配置和摘要都与目标阶段一致，再按该阶段文档运行仅涉及本轮的离线验证。不要把旧mock成绩当作真实性能。

实际生成由各阶段`*_session.py`监督器启动本项目11436服务、记录逐次请求并卸载；需要新独立输出目录和新的授权预算。旧计划已完成且截止已过，不删除登记文件绕开预算。文件式AI判分不是可一键调用的隐藏API：生成后导出隐藏配置的队列，再由当前APP AI按冻结政策填写，严格验证ID、输入哈希与缺失项。人工字段保持空白，不能把缺失/uncertain当错。

通用停止入口（`<当前运行目录>`须替换成实际活跃会话，不直接照抄）：

```powershell
.\.venv\Scripts\python.exe scripts/evening_smoke.py stop --out <当前运行目录>
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv
Get-NetTCPConnection -LocalPort 11436 -State Listen -ErrorAction SilentlyContinue
```

检查`session.json`中的模型卸载、空加载列表、所属进程退出与端口释放；其他程序占用GPU要另记。不要关闭无关应用。中断必须沿原预算恢复到新目录，并核验已落盘调用，不能为恢复而重复已完成回答。

## 目前能复现与不能声称的内容

可以审阅算法、配置、事实差异、逐题派生统计和论文对应；取得完整忽略产物后可离线核验历史输入绑定、判分与统计。按新授权运行可以重复相同方案，但temperature0.7且未固定seed，不能保证逐token重现；APP评审也有不确定性，身份与版本要重新如实记录。

不能据此声称复现LightMem全量主实验、完成正式测试、拥有人工金标准或形成全队最终材料。正式测试前的冻结清单与人工确认事项见[课程交付差距](metamem-course-readiness.md)。

人工验收人：________　日期：________　意见：________
