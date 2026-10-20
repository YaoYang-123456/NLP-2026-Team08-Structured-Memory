# E 评分安全修订：供 #46 协作审阅

本补丁不重跑裁判、不修改评分模板或历史成绩，不覆盖 E 原分支。关联 #31、#46，处理 F 已提出的输入绑定、逐次保存和输出保护问题。

## 行为

- 离线重放必须提供已保存的实际 request；将其中唯一 user JSON 的 question、reference_answer、model_answer 与当前冻结标签和预测逐项比较。只有 ID 相同不足以复用；旧记录若没有 request 则明确拒绝，不能假定兼容。
- 每次请求开始前写入 pending，请求成功/失败后原子替换当前运行的检查点并 fsync。Ctrl+C 保存 interrupted，已完成调用不丢失；若进程被强制终止，最后一个 pending 保留为未完成，不伪称未付费或答错。
- CLI 拒绝非空输出目录；API 路径拒绝既存判分文件。只能新建运行目录，不覆盖旧结果。没有新增重试。
- 已评分标签必须是 yes/no，布尔 correct 必须一致；调用/评分失败仍独立计数，不算正常答错。

实际运行 `python -m unittest discover -s tests -p test_evaluate_safety.py -v`，7 项针对性检查通过；网络全部模拟，真实 API 请求为 0。覆盖实际输入变更、无 request、标签矛盾、完成一条后中断、旧输出拒绝、失败分母。`git diff --check` 通过。

## 题型及案例用语

冻结 LoCoMo `cbfbc1dba6bc53d00625212a0f22d55ffee7c1fc`：
category 1 多跳、2 时间、3 开放域、4 单跳。
对照 [evaluation.py](https://github.com/snap-research/locomo/blob/cbfbc1dba6bc53d00625212a0f22d55ffee7c1fc/task_eval/evaluation.py)、[hf_llm_utils.py](https://github.com/snap-research/locomo/blob/cbfbc1dba6bc53d00625212a0f22d55ffee7c1fc/task_eval/hf_llm_utils.py) 及 [任务定义](https://github.com/snap-research/locomo/blob/cbfbc1dba6bc53d00625212a0f22d55ffee7c1fc/index.html)，结合开发实例核对；官方仓库 issues #6/#29 中普通参与者的说明仅为旁证。只改报告/幻灯片中文名称，不改类别数字和分数。

过敏案例保留“大多数爬行动物”，不扩大成“所有”；Turtles 不符合冻结参考，也没有充分证据把它视为安全例外。日期改判、两条参考证据不足说明和原始裁判均保留。六例复核属于 AI 辅助证据核查，不是组员人工验收。

## 尚未解决的交接

此修订不能补造 E 的 60 条原始裁判响应。需要 E 提供不含密钥的逐题 request/response、输入绑定和原始判分，再执行离线复算，并单独应用原 adjudication。当前汇总仍标为“E 已报告”，不能因为七项模拟测试通过就声称真实裁判已独立验收。
