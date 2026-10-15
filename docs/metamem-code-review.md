# MetaMem 官方代码审阅与运行前检查

日期：2026-10-15。这是有范围的静态审阅，不是完整安全审计，也不是模型复现报告。上游：[OpenBMB/MetaMem](https://github.com/OpenBMB/MetaMem)，核对时最新提交为 `66232c1cb33d3d7939d323b431f21c741785142e`。没有向上游提交修改。

## 已审阅入口

| 上游文件 | 作用 | 读取时 blob SHA |
| --- | --- | --- |
| README.md | 环境、模型和运行顺序 | c14a88b7b64b90bfcb55ef11da1bc0b4c89204ed |
| src/process_train_data.py | 将原始问题与提取记忆按 question_id 合并 | 454d21753a73392f0f4c89ae9abeea1503c9c71d |
| src/split_data.py | 五折训练、验证、测试划分 | 5ffc96be3d8ea2b53d1beff690e548f7bd275be3 |
| src/train_metamem.py | 多次回答、判分、反思、规则编辑 | 6ce266c81b64590eca1bd231ef3284a7e728122f |
| src/infer_metamem.py | 用固定元记忆回答并判分 | 11aa128896d860620a16e84e29522eabbd60ac39 |
| scripts/train_metamem.sh | 默认第一折训练配置 | 443509fe3777649851a59853334356fc5bd316f0 |
| scripts/eval_metamem.sh | 默认第一折验证、遍历规则版本 | a8ddca4b18e2cf0b11cba377d3f022dedf931bae |

文件固定入口可写为 `https://github.com/OpenBMB/MetaMem/blob/66232c1cb33d3d7939d323b431f21c741785142e/<路径>`。本轮没有审完 construct_memory.py、eval_metamem.py 或 LightMem 内部实现，因此不能宣称整条管线已验证。

## 已确认、会影响实验解释的行为

1. **350/50/100 划分与附录一致。**split_data.py 默认用 500 条、5 折、每折测试 100、验证 50，余下 350 训练。脚本并没有按任务类型分层；小规模试点不能直接照抄默认参数，否则可能产生空折或分布失衡。
2. **默认只反思部分正确的问题组。**train_metamem.py 的 MetaMemoryUpdater.run 在 `only_partial_correct=True` 时仅保留 `0 < 平均 reward < 1` 的组；main 在 num_samples > 1 时开启它。某一批规则没有更新可能是筛选结果，不一定是程序坏了。学习率很低的小模型可能全错，必须记录保留组数。
3. **问题文本被用于分组和缓存匹配。**训练代码按 problem 字符串聚合多次尝试；跨不同 ID 的同文问题需要检查，避免混为同一个问题。缓存存在时会复用中间结果；修改模型、数据、提示词应使用新的 experiment_name。
4. **模型调用失败可能被记成错误回答。**LLM.chat 重试后返回空字符串；判分解析也会把未识别输出返回 False。infer_metamem.py 的异常分支写 reward=0。因此原始准确率可能混合能力错误和服务错误。正式实验应分别记录成功、生成失败、judge 失败和解析失败，保留覆盖率。
5. **规则文件缺失会退化成无规则。**infer_metamem.py 找不到规则文件时只警告并用空集合继续。这适合上游容错，但对课设对照会造成“声称用了规则，实际没加载”的问题。我们应该在运行前检查文件存在、可解析、规则数量符合预期。B0 的空规则文件须显式提供。
6. **论文参数不等于代码中所有调用的参数。**论文测试输出上限 2000、学习 4000；已读脚本采用 4096。LLM.chat 没有传 top_p，反思等调用未显式传 max_tokens 时使用函数默认 16384。不能把命令行的 4096 当成所有阶段的统一硬上限。
7. **训练 judge 与生成模型共用 api_key 参数。**main 正确读取 judge_base_url 和 judge_model_name，但将 args.api_key 也传给 judge；不能假设它支持两个独立服务商密钥。推理脚本则有单独的 judge_api_key。需要异源服务时应先做明确的小修改。
8. **默认 shell 脚本只配置第一折。**不能运行一次就写“五折复现完成”。eval_metamem.sh 读的是 fold_1_val.json，且带 --no_baseline；最终测试必须另走固定 checkpoint 的推理，基线也需单独运行。

## 本轮实际运行了什么

使用上游 split_data.py 原文件，在临时目录生成了 500 个仅含 question_id 的合成条目，运行默认划分并检查：五折分别为 350/50/100；每折三集合 ID 两两不交；五个测试折两两不交并覆盖 500 个 ID。全部检查通过。

这只验证默认划分逻辑，不证明真实数据没有重复用户、重复历史、近重复问题或其他泄漏。没有加载真实 LongMemEval、没有生成事实记忆、没有调用 LLM、没有得到任何模型准确率。临时合成文件和上游源码未纳入本仓库。

## 开始真实实验前需要做的有限修正

- 固定实际模型标识、上游提交、数据哈希、提示词和输出目录；逐阶段记录实际生效参数。
- 在数据边界检查 question_id、problem、memories、groundtruth、task，检查缺失、重复 ID 和跨集合重叠；按会话/历史检查潜在关联泄漏。
- 将测试回答模型与标准答案分离；judge 单独接收答案，不能把测试反思反馈到规则。
- 对有规则实验检查规则文件；对调用错误保留独立状态，最终同时报告完成率和质量。
- 先在本地服务或已确定预算的 API 上跑 5 个训练样本的连通性检查，再扩大规模。没有可用模型服务时，可先完成数据和划分，但不能把模拟响应标为实测。

这些是本轮阅读发现的具体检查点，不要求重新开发通用 Agent 框架。试点范围见 [metamem-pilot.md](metamem-pilot.md)。
