# 严格拒答政策 v2：离线敏感性分析

## 结论与边界

已检查上一轮全部70条新回答的问题、参考与原题型，确认12条适用严格拒答政策，并隐藏旧标签与配置名逐条阅读完整回答重评；58条非适用项明确沿用v1，没有声称全部重新评审答案质量。12条均判No：9条uncertain→No，3条No→No，适用项没有原Yes。原9条不确定性全部由新政策消解，当前70条无剩余uncertain；这不证明评分者没有语义错误。

本轮新增评分版本 `external-ai-strict-abstention-v2` 是本项目政策，不是原论文标准。先保存configs中的政策并冻结到新派生目录，随后才导出评审包。当前APP外部AI评审，不是人工验收；精确部署版本未知。已保有上轮案例上下文，且完整回答可能自述规则，只能称隐藏标签复核，不是严格盲评。人工字段为空。

**本地模型调用0；没有启动Ollama、生成新回答、重训或读取测试集。** 原规则仍是在v1训练标签下学出的。以下是固定旧回答的事后重判，不能称为v2训练，也不能推演新的反思、合并或规则。

## 独立政策与适用范围

冻结政策见 [配置](../configs/external-ai-strict-abstention-v2.json)。S1要求正确承认不可回答且不对所问事实作无依据判断；S2将无依据具体值、范围、零值与倾向判断判No，可能/似乎不免责；S3允许不冒充实际答案的条件公式和演示，任意假设结果当作实际答案仍判No；S4按完整回答判断，真实歧义保留uncertain；S5其他题型沿用v1，可回答题因检索不足拒答不获Yes。

按原unanswerable评分指令与_abs元数据交叉核对，并人工式逐条检查70条问题/参考的适用范围（由AI完成）。没有用回答中的关键词决定标签。

|题目|数量|v1标签|v2标签|依据|
|---|---:|---|---|---|
|训练：意大利餐厅数|2|uncertain×2|No×2|一个猜零家，一个猜去过一些；S2|
|训练：Manager带队人数|2|No、uncertain|No×2|把Senior角色套成Manager，给5人或4人可能增加；S1/S2|
|训练：蛋挞次数|2|uncertain×2|No×2|从其他烘焙推断至少一次或很可能烤过；S2|
|验证：Sapiens剩余页数|3|uncertain×3|No×3|任意假设进度，给440、360–400或200页实际答案；S2/S3|
|验证：本科海报大学|3|No×2、uncertain|No×3|把其他研究会议套为本科课程，断言或推测Harvard；S1/S2|

这些回答都不是仅解释缺失信息或给纯条件演示。请求补充信息也不能抵消同一完整回答中无依据的事实判断。

## 训练标签的离线变化

|版本|Yes|No|uncertain|有效覆盖|
|---|---:|---:|---:|---:|
|v1历史|27|8|5|35/40|
|v2派生|27|13|0|40/40|

三组由不确定跳过变为全错：6aeb4375_abs为U/U→N/N；031748ae_abs为N/U→N/N；88432d0a_abs为U/U→N/N。**没有任何题组新增或丧失混合正误资格**，唯一混合组仍是9bbe84a2；原13组全对、3组全错、3组不确定、1组混合，在这批固定回答上变成13组全对、6组全错、1组混合。没有执行新反思或规则更新。

即使固定回答上的资格相同，也不能断言真实v2训练会产生相同回答或轨迹；本轮只陈述离线标签资格。

## 验证与配对

|配置|v1 Yes/No/U|v1有效覆盖|v2 Yes/No/U|v2有效覆盖|
|---|---|---|---|---|
|B0|4/5/1|9/10|4/6/0|10/10|
|B1|5/3/2|8/10|5/5/0|10/10|
|B2学习候选|5/4/1|9/10|5/5/0|10/10|

三组的判对数排序B1=B2>B0不依赖这次拒答政策，但有效分母、条件准确率与候选可选择性依赖政策：v1有效样本正确率为4/9、5/8、5/9；v2为4/10、5/10、5/10。不能把覆盖提高说成模型更强。

逐题变化（U即uncertain；表中写出完整标签）：

|验证题ID / 问题|B0 v1→v2|B1 v1→v2|B2候选 v1→v2|
|---|---|---|---|
|01493427 / How many new postcards have I added to my collection since I started collecting again?|No→No|Yes→Yes|Yes→Yes|
|06f04340 / What should I serve for dinner this weekend with my homegrown ingredients?|No→No|No→No|No→No|
|0a995998 / How many items of clothing do I need to pick up or return from a store?|No→No|No→No|No→No|
|2311e44b_abs / How many pages do I have left to read in 'Sapiens'?|uncertain→No|uncertain→No|uncertain→No|
|4388e9dd / I was going through our previous chat and I was wondering, what was Andy wearing in the script you wrote for the comedy movie scene?|Yes→Yes|Yes→Yes|Yes→Yes|
|7a87bd0c / How long have I been sticking to my daily tidying routine?|Yes→Yes|Yes→Yes|Yes→Yes|
|9d25d4e0 / How many pieces of jewelry did I acquire in the last two months?|No→No|No→No|No→No|
|a96c20ee_abs / At which university did I present a poster for my undergrad course research project?|No→No|uncertain→No|No→No|
|ad7109d1 / What speed is my new internet plan?|Yes→Yes|Yes→Yes|Yes→Yes|
|cc6d1ec1 / How long had I been bird watching when I attended the bird watching workshop?|Yes→Yes|Yes→Yes|Yes→Yes|

|B2相对B0配对类别|v1|v2|题目|
|---|---:|---:|---|
|两者都对|4|4|4388e9dd、7a87bd0c、cc6d1ec1、ad7109d1（观鸟、整理习惯、网速、Andy着装）|
|仅B2对|1|1|01493427 明信片累计新增量|
|仅B0对|0|0|无|
|两者都错|4|5|原首饰、食材晚餐、衣物件数、本科海报；新增2311e44b_abs Sapiens|
|仍不可比较|1|0|v1的Sapiens双方uncertain，v2双方No|

每个类别的ID清单以summary.json为准，配对总数10。没有把原uncertain先默认成错来做v1配对。

若把原完整覆盖、最高判对数、并列最早检查点的候选选择规则应用于v2派生结果：初始空候选复用B0得4/10，rules-01到04内容相同、复用学习候选得5/10，因此**事后假设会选择rules-01.json**。B1不是B2候选。没有覆盖原selection.json的no_full_coverage_candidate，没有创建正式冻结候选；历史未选定结论仍成立。

## 规则可能帮助或干扰在哪里

既有规则原文：

> Prioritize recent memories, cross-validate facts, and understand context and chronology unless historical context is required.

它来自v1训练的Apex题组。明信片题B0把累计25与旧17相减为8，B2正确答25，与规则强调时间及近期证据相符，是可能帮助的观察；只有一次配对差异，不能证明因果或稳定提升。整理习惯、网速、着装、观鸟双方都对，不能据此声称规则带来增益。

海报、Sapiens、蛋挞及角色人数回答有套用近期记忆、跨事件推断或从缺失猜测的现象，说明规则没有有效约束拒答。部分回答显式援引“近期”策略，但海报/Sapiens的B0也错；没有仅B0对的验证题，因此没有观察到明确的B2净伤害配对，不能把这些失败直接归因于规则。训练Apex与5K等历史时间点问题提示“优先近期”的潜在干扰风险，训练中没有同题B0对照，风险不是已证明的因果作用。

晚餐偏好检索主要是调酒内容，规则不能凭空补足缺失食材证据；首饰/衣物统计的检索不足与证据利用比例仍未完全分解。AI评分可靠性、原参考口径和单次生成波动仍是剩余问题；v2也没有正例拒答来证明政策对合格回答的接受能力。

## 下一轮只建议一个固定实验（本轮未执行）

在同一固定10条开发验证题上，冻结当前B0与v1学出的rules-01，两配置分别使用预先固定的3个seed（例如11、29、47），每题每配置每seed一次，共60条新回答；保持模型、检索、回答提示词与预算不变，以v2隐藏方法名评审，不训练、不挑规则、不碰测试。若本地接口不能确认seed传递，应事先改记为三次重复而非声称受控seed。

目标仅回答：目前仅明信片一题的配对优势能否重复，以及两配置的严格拒答失败是否稳定。一次性报告全部配对与uncertain，不按结果追加轮次。这仍是开发集稳定性探索，不是独立泛化验证，也不是v2训练。

## 产物、命令和验证

新增派生目录 `output/strict-abstention-v2-20261015/`：policy.frozen.json、freeze.json、queue.hidden.json、reviews.json、mapping.private.json、derived.json、summary.json、源文件前后哈希。derived逐项记录完整输入哈希、原输入哈希、旧/新标签、适用条款、理由、评分版本；58条显式标carried_forward_v1。reviews在接回旧标签及方法名之前保存。

执行命令：

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/analyze_strict_abstention.py export --source output/external-ai-experiment-20261015-2143 --out output/strict-abstention-v2-20261015
# APP AI读取隐藏队列，逐项填写12条reviews.json；不是网络judge或自动关键词分类。
.\.venv\Scripts\python.exe -X utf8 scripts/analyze_strict_abstention.py summarize --out output/strict-abstention-v2-20261015
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_strict_abstention_analysis.py -v
```

3项新增针对性测试覆盖计数/uncertain不计错、五类配对互斥、评审范围/输入哈希/重复/缺失/政策哈希拒绝。实际70条派生逐项校验，58条沿用值一致，12条重评，9条改变；源运行目录51个文件前后SHA-256完全一致。脚本拒绝覆盖已有派生结果，且不依赖模型服务。未重跑已有全量测试。Git diff检查通过。

提交内容仅必要脚本、政策、测试和本文；原始回答与日志不入Git。现有分支及草稿PR #7继续依赖#5，不合并、不催审。
