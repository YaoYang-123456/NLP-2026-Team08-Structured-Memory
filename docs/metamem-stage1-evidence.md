# 阶段一：固定十题的原始历史与检索证据审计

本文件对应子任务为独立 AI 辅助研究审计，不是人工验收、重新判分或模型实验。只审计 `data/pilot/validation.inputs.json` 与 `validation.labels.json` 的固定十题，结合已有 B0/B1/B2 回答定位证据问题。未修改检索、模型、标签或规则，未启动服务，该审计子任务模型调用为 0，未生成新回答；主任务的61次调用另见阶段主报告，本文随研究包提交。

审计者可确认身份为本 APP 中的 Codex AI 代理；精确部署模型版本未知。被审计的历史运行模型由 `output/external-ai-experiment-20261015-2143/model.json` 确认：`qwen2.5:7b-instruct-q4_K_M`，7.6B、Q4_K_M，digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`。该文件是历史快照，本轮没有重新加载模型核验。

## 范围、来源与复核方式

原始来源为 `data/raw/longmemeval_s_cleaned.json`，采用增量 JSON 数组解析：仅保留验证 ID 白名单对应记录，其他记录立即丢弃，不输出或查看其内容。没有打开 `test.inputs.json`、`test.labels.json`，没有查看测试问题、历史或答案。读取 manifest 时曾附带看到测试 ID、题型和文件哈希元数据，不能声称完全没有接触任何测试元数据。

本地证据在 `output/stage1-evidence/`：

- `validation-history.json`：白名单十题的原始记录；这是开发审计缓存，包含验证参考，不得当作盲测输入。
- `*.answer-sessions.jsonl`：原数据 `answer_session_ids` 指定会话的完整 turn；来源标注帮助定位，但不代表该会话每一句都支持参考。
- `evidence-map.json`：本文关键 fact ID 对应原文、日期、角色、turn、当前检索名次；未检索的 chunk ID 按现行 180 词分块规则构造。
- `source-hashes.json`、`verification.json`：来源 SHA-256、183 条检索事实与原史的前缀一致性检查、时间异常。

ID 格式为 `会话ID:从0开始的turn:从0开始的chunk`，下文用完整 fact ID 同时给出会话与 turn 定位。原史保留换行，检索会归一化空白且可能受字符预算截断。183/183 条检索事实均是对应原史分块文本的前缀，无错误回接。此检查验证来源一致性，不验证回答正确性或召回完整性。另以题目相关词检查十题中重点问题的完整历史；这是定向检索加阅读，不是所有历史句子的穷尽语义审核。

## 总览

|验证 ID|参考|主要诊断|证据边界|
|---|---|---|---|
|a96c20ee_abs|无法确定|错误跨事件推断|thesis 海报和 Harvard 参会不证明本科课程研究海报|
|7a87bd0c|4 weeks|证据已检索且可正确使用|最新直接自述4周覆盖旧3周，不外推连续坚持时长|
|9d25d4e0|3|历史有关键事实未检索，兼有日期误读|项链、耳环已检索，订婚戒指漏检；一对耳环按一个获得物计是参考口径|
|4388e9dd|untidy, stained white shirt|证据已检索且可正确使用|直接引用剧本 assistant 描述，不能一律丢弃 assistant|
|06f04340|cherry tomatoes、basil、mint|历史有关键事实未检索，兼有无依据补全|有关食材的整个来源会话未进入20条|
|ad7109d1|500 Mbps|证据已检索且可正确使用|用户明确升级套餐，不等同实测带宽|
|cc6d1ec1|Two months|给定历史支持相对时间计算；日期异常|关键历史晚于提问37分钟，不能宣称严格截至提问时间有效|
|2311e44b_abs|无法确定|实体混淆与缺失后猜测|Sapiens 阅读速率不是当前页；440页属于 The Nightingale|
|01493427|25|检索已有，B0未用好|累计25与阶段新增8不同；B1/B2答25不证明稳定收益|
|0a995998|3|已有证据漏用，参考计数口径未知|待取blazer与换码boots已检索；第三件的来源/事件状态有歧义|

类别允许重叠。不能把“历史有未检索”和“答案错误”看作互斥，更不能据十题推导总体比例或预期提升。

## 逐题证据

### 1. a96c20ee_abs：本科课程海报的大学

- `answer_ef84b994_abs_1:0:0`（2023/05/23，user，rank 1）：原文 “I actually just presented a poster on my thesis research on it at my first research conference over the summer.”
- `answer_ef84b994_abs_2:0:0`（2023/05/30 02:26，user，rank 3）：原文 “I've been to Harvard University to attednd my first research conference and saw some interesting projects on AI in education.” 保留来源中的拼写错误。

两条分别支持 thesis 海报和 Harvard 参会；题目增加了 `undergrad course research project` 限定。已查看的相关原史没有建立此限定与上述研究的同一性。Harvard 是相关线索，不是所问事实的充分证据；即使同为 first research conference，也不能补出本科课程项目。B0完整回答把两件事接成确定的 Harvard 答案，是错误推断，不是大学名称漏检。拒答政策应检查所问实体、事件和研究类型，不能只检查是否出现大学。

### 2. 7a87bd0c：日常整理坚持多久

- `answer_d08a934d_1:0:0`（2023/06/11，user，rank 1）：“it's already been 3 weeks!”
- `answer_d08a934d_2:0:0`（2023/09/30 17:52，user，rank 2）：“I've been sticking to my daily tidying routine for 4 weeks now”。问题日期同日23:15。

最新直接自述支持4周。相隔数月的3周与4周不是一条连续时长的起终点，不应按日历差相加，也无证据推定中间没有中断。该题现有检索足够，历史三配置均答对，不构成学习规则带来收益的证据。

### 3. 9d25d4e0：最近两个月新增首饰

- `answer_fcff2dc4_1:0:0`（2023/05/28 09:02，user，rank 9）：“I just got a new silver necklace with a small pendant on the 15th of last month”。相对该会话为4月15日，不能改成5月15日。
- `answer_fcff2dc4_2:0:0`（2023/05/21，user，rank 10）：“I just got a new pair of earrings last weekend at a flea market - a stunning pair of emerald earrings”。同会话 turn 8 再次提及，是重复证据，不是第二对。
- `answer_fcff2dc4_1:8:0`（2023/05/28 09:02，user，未检索）：“I also wanted to ask you about resizing my engagement ring. I got it a month ago”。
- `answer_fcff2dc4_3:0:0`（2023/05/28 14:40，user，未检索）：“I got my engagement ring a month ago”。与前条为同一戒指，不能重复计数。
- 同会话组 `answer_fcff2dc4_1:4:0` 提到 grandma 赠的 diamond earrings，但没有近期取得日期，不能自动加入两个月窗口。

原史支持项链、祖母绿耳环、订婚戒指三个近期获得物。参考3与“耳环一对算一个获得物”的计数方式相容；题目 `pieces` 本身没有解释成套计数，不能宣称原标签已给完整计数规范。当前检索漏掉戒指，三配置基于项链/耳环答至少2或估计2，与这一证据瓶颈吻合；补回戒指能否使模型正确去重仍未实验。已有回答还把项链日期说成5月15日，B2将两次购买说成同日，这些是证据利用错误，不能都归因于漏检。

### 4. 4388e9dd：剧本中 Andy 的衣服

- `answer_sharegpt_qTi81nS_0:0:0`（2023/05/20，user，rank 1）：“Andy wears an untidy, stained white shirt.”
- `answer_sharegpt_qTi81nS_0:1:0`（同会话，assistant，rank 5）：“He wears an untidy, stained white shirt.” 该句紧接 Andy 人物介绍，处于真正生成的剧本中。

题目问的是 assistant 写过的剧本，后一条直接支持参考，前一条是创作要求的交叉支持。其他人物的 pinstripe suit 属于 John，不可串到 Andy。三配置均能利用现有证据。这个正例约束任何未来“只取 user”策略：应按问题来源调整角色权重，不能无条件删除 assistant 记忆。

### 5. 06f04340：使用自种食材的周末晚餐

- `answer_92d5f7cd:0:0`（2023/05/23，user，未检索）：“I'm trying to find some new recipe ideas that use fresh basil and mint.”
- `answer_92d5f7cd:4:0`（同会话，user，未检索）：“I've been using basil and mint in my cooking lately. I've even harvested some cherry tomatoes from my garden.”

原史直接支持已经收获自家 cherry tomatoes，并在做菜时用 basil/mint。严格说后两种香草是否也亲自种植没有同样明确的独立断言；参考把它们合并为自种食材偏好是合理的上下文口径，但不能扩成所有香草/蔬果都来自自家。

当前20条检索没有该会话，较多为鸡尾酒以及无关内容。历史回答围绕 cocktails；B0断言 `your homegrown pomegranate`，B1称 `homegrown mangoes and jalapenos`，这些自种归属并非检索支持。主瓶颈为食材来源漏检，同时生成没有守住已知食材边界。原参考的“不偏好其他建议”是倾向性评分说明，原史并未明确排斥所有其他菜肴；宜评价是否真正使用关键食材，而非擅造饮食禁忌。

### 6. ad7109d1：新网络套餐速度

- `answer_679840f8:4:0`（2023/05/24，user，rank 1）：“I upgraded to 500 Mbps about three weeks ago”。该信息夹在笔记本电池问题中。

500 Mbps 有直接证据，三配置历史回答均正确。这里说明词面主题为电池的 turn 也可能含目标事实；按整段主话题过滤有丢失风险。原文是套餐升级自述，不支持实际下载一直达到500 Mbps。

### 7. cc6d1ec1：参加观鸟工作坊时已有多久经验

- `answer_be73098b_1:0:0`（2023/05/21 08:56，user，rank 2）：“I've been getting into bird watching for about three months now”。
- `answer_be73098b_2:0:0`（2023/05/21 20:08，user，rank 1）：“I recently attended a bird watching workshop at the local Audubon society a month ago”。

按数据提供的历史，两条同日自述推出参加工作坊时约3−1=2个月，支持参考的月级近似，不能声称精确天数。历史三配置均答对。

但问题时间是同日19:31，第二会话在20:08，晚37分钟。当前检索另外还有该会话其他3条及另一20:44会话2条，共6条晚于问题时间，详见 verification.json。此为原数据/输入时序异常，不能把该题当作严格“只使用问题发生前历史”的成功证据。此轮保留固定输入和标签，不自行纠正时间，也不以异常抹掉原给定历史的语义支持。

### 8. 2311e44b_abs：Sapiens 剩余页数

- `answer_bf633415_abs_1:2:0`（2023/05/22，user，rank 7）：“I've been enjoying "Sapiens" but it's really slow going.”
- `answer_bf633415_abs_2:2:0`（2023/05/30，user，rank 8）：“I've been reading "Sapiens" at a pace of 10-20 pages a week.”
- `answer_bf633415_abs_2:0:0`（同会话，user，rank 4）：“I just got back to reading "The Nightingale" and I'm excited to finally finish it - it's a long one with 440 pages!”
- `answer_bf633415_abs_1:8:0`（2023/05/22，user，未检索）：“I'm currently on page 250 of 'The Nightingale' by Kristin Hannah”。

440总页与250进度属于 The Nightingale。Sapiens 只给速度与阅读体验，没有起读时间、已读页数或版本总页数，不能推出剩余量；补回未检索的250页也不能解答 Sapiens。

B0/B1把440串到 Sapiens，又假设未开始或读了4周；B2注意到440属于另一书，仍自行假设400总页并推出200剩余页。主要是错误实体绑定及知道缺失后继续猜测，不是通过更强算术即可修复。对一个不可答问题给区间也不是有证据的拒答。

### 9. 01493427：重新收藏以来新增明信片

- `answer_a7b44747_1:6:0`（2023/08/11，user，rank 2）：“I've added 17 new ones since I started collecting again”。
- `answer_a7b44747_2:0:0`（2023/11/30，user，rank 6）：“scored 8 more postcards for my collection”。
- `answer_a7b44747_2:6:0`（同会话，user，rank 1）：“I've added 25 new postcards to my collection since I started collecting again”。

问题以重新收藏为起点，最新同口径累计25直接可用，17+8可交叉印证；25−17=8是两个更新间增量。B0掌握两条累计却算差，是检索已有没用好。B1/B2最终25正确，但B1附加声称8张发生在11月30日之后，原史不支持；不能只因最终数字正确便把整段都标为无误。B2本次更简洁地抓住累计；单次已知差异不证明规则因果效果或泛化收益。

### 10. 0a995998：要从商店取回或退回多少衣物

- `answer_afa9873b_2:0:0`（2023/02/15 06:30，user，rank 7）：“I still need to pick up my dry cleaning for the navy blue blazer”。turn 10 再次说将去取，是同一件，未确认实际完成。
- `answer_afa9873b_3:6:0`（同日11:13，user，rank 4）：“I need to return some boots to Zara, actually. I got them on February 5th, but they were too small, so I exchanged them for a larger size. I just haven't had a chance to pick them up yet.” 此 turn 自身混有 need to return 与 exchanged 的状态歧义。
- `answer_afa9873b_1:4:0`（同日16:19，user，rank 1）：“I just exchanged a pair of boots I got from Zara on 2/5, and I still need to pick up the new pair.” 与前条共享商店、日期、换码事件。
- `answer_afa9873b_3:2:0`（同日11:13，user，未检索）：“I was thinking of wearing my green sweater, but I lent it to my sister and I'm not sure when she'll return it.”

待取 blazer 与新 boots 的证据已经检索。B0/B2没有正面给件数且漏 blazer，B1只列旧/新boots得2，也漏 blazer；这些问题独立于参考是否恰当，均可确认是已给证据未用好。

参考仅为3，没有解释第三件：可能按 blazer＋待归还sweater＋boots，但 sweater 在姐姐处，不是 `from a store`；也可能按 blazer＋旧boots退回＋新boots取回，但最新用户自述 exchanged 已完成，不能确定旧鞋仍待退。assistant 在 `answer_afa9873b_3:7:0`（已检索rank 9）建议 “pick up the new boots and return the old ones”，只是对上述模糊状态的回复，不等同用户确认存在两件独立未完成事项。

因此保留“参考口径未知”，不重写标签，不声称已证明3错，也不把补回 sweater 等同于解决计数。对来源与状态进行人工核对，比直接为迎合3训练规则更有价值。

## 最值得进一步研究的方向（未实施、无收益承诺）

1. **先分离召回覆盖与答案能力。** 晚餐的来源会话完全漏检、首饰漏戒指是两项最明确的召回缺口。未来可在保留当前对照的前提下，预注册证据覆盖检查；补证据实验必须明确为开发诊断，不把参考导向补检索包装成真实无标签检索提升。
2. **核验所问对象和事件，再决定是否作答。** 海报的研究类型、Sapiens的书名、衣物的店铺与事件状态都要求细粒度绑定；“优先最新”不能替代身份与范围检查。拒答需要抑制无依据数值、范围和具体地点，而不只是添加一句不确定。
3. **区分累计、增量、成套物品与重复事件。** 明信片是已检索误算；首饰重复戒指不能再计一次；衣物参考口径需要先解决。不能把三类都简化成“多加一个数”。
4. **按任务调整角色证据，不统一排除 assistant。** 首饰/晚餐中大段通用建议可能占用预算，用户事实值得优先；Andy题却必须保留生成剧本证据。这里只是候选检索设计问题，未跑消融。
5. **把数据歧义与模型错误分别记录。** 衣物的3与观鸟的时间戳是明确的进一步核验点。保留原官方口径并另记不确定性，不为了改善分数改标签，也不把已答对题当成没有数据问题。

本轮完成了原史定位、检索回接与错误分解；没有衡量任何修复收益，没有新增规则候选，也没有给新的模型成绩。
