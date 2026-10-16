# Judge 格式诊断与三张人工复核卡

本轮模型调用为 **0**，没有启动服务、重跑五题、读取测试答案或学习规则。以下为训练材料的 AI 辅助整理；人工字段保持空白。原始文件未修改。

## 格式修改与离线影响

解析版本 `single-label-v2` 使用完整匹配 `(yes|no)\.?`（ASCII 大小写不敏感），只额外允许首尾空白及单个紧随标签的英文句号。拒绝子串、矛盾标签、解释、空输出、多余标点、引号和 Markdown 包装。原始 judge 文本保留，未来 evaluate 记录解析版本。

| 来源 | 历史判分 | 离线派生判分 |
| --- | --- | --- |
| evening-smoke-20261015-1454 | 9/10，3 Yes、6 No | 不变 |
| budget-diagnostic-20261015-2038 | 9/10，6 Yes、3 No | 10/10，6 Yes、4 No |

唯一变化是第二轮 `gpt4_a56e767c` attempt 0：原文 `No.`，由格式失败/null 转为 valid/false。第一轮截断回答仍没有判分。此修改不能修复语义误判，不回算学习、不改历史汇总或规则。新派生文件 `output/judge-reparse-v2-20261015/derived.json` 含原文、原判分、新解析、来源路径与 SHA-256、版本及变化列表；核验两轮全部 38 个文件哈希未变。脚本拒绝输出到来源目录，使用独占创建，不覆盖已有派生文件。

实际命令：

```powershell
.venv\Scripts\python.exe scripts/reparse_judges.py --runs output/evening-smoke-20261015-1454 output/budget-diagnostic-20261015-2038 --out output/judge-reparse-v2-20261015/derived.json
.venv\Scripts\python.exe -m unittest discover -s tests -p test_judge_parser.py -v
```

专项测试 4 项：有效变体、拒绝情形、evaluate 原文/版本及 No=False、离线不改原文且不恢复调用失败。测试内模拟不计模型结果。

## 现行提示词检查及最小建议（本轮不实施）

来源：`third_party/metamem_judge.py`，保留自官方 MetaMem 提交 `66232c1cb33d3d7939d323b431f21c741785142e` 的原函数，本轮未改。

- 非拒答的普通/跨会话模板提供 Question、Correct Answer、Model Response；明确接受语义等价或含完整中间步骤的答案，信息不全判 No。时间推理另允许天数等 off-by-one。判分器没有收到检索事实，因此不能独立审核所有附加事实。
- knowledge-update 提供同样三字段，但措辞强调 updated answer。对于问“以前”的题容易造成时间指向歧义。建议未来只补一条通用约束：按问题要求的时间点与参考答案比较，接受语义等价，不默认最新值就是所问值。不要按题号添加特例。
- preference 把参考作为 Rubric，明确无需覆盖所有点，正确回忆并利用个人信息即可。现行文字已支持本卡的个性化回答；没有证据说明必须收紧或重写。可在后续校准时明确把“偏好匹配”和“事实支持”分开报告；不要暗中将额外质量要求并入原分数。
- `_abs` ID 强制走拒答模板，参考答案作为 Explanation；仅检查是否识别信息不足，没有明确约束“先拒答再猜测”。若后续确认需要严格拒答，可统一补充“承认信息不足后不得又断言/猜测所问事实”，但这是语义评分标准变更，须另设版本并经人工决定。本轮不实施。
- 格式要求仍为 yes/no only；此次解析容忍单句号不改变上述评分标准。不能通过解析修复 Apex 或 Premiere Pro 的语义判定，也不能把这些 AI 意见写回学习标签。

## 人工复核材料

来源均为首次真实运行 `output/evening-smoke-20261015-1454/`；下列问题、事实、回答、参考和实际 judge 标准从 `review-inputs.json`、`smoke/rollouts-00.json`、`smoke/calls.jsonl` 提取。文档保留所选事实片段与完整回答，无删节；事实片段本身可能在原检索切块处终止。最终对话中的短卡会显式标出省略。

### Apex 目标更新：`9bbe84a2` / attempt 1

原问题：

> What was my previous goal for my Apex Legends level before I updated my goal?

中文释义：在更新目标之前，我的 Apex Legends 等级目标是什么？

必要证据（所选原始检索片段）：

`answer_c6a0c6c2_1:0:0`

> 2023/06/16 (Fri) 04:38 user: I'm thinking of getting a new gaming mouse to pair with my new keyboard. Can you recommend some good options for FPS games like Apex Legends? By the way, I've been playing a lot of Apex lately and I'm determined to reach level 100 before the end of the year.

`answer_c6a0c6c2_2:8:0`

> 2023/09/30 (Sat) 12:45 user: I think I'll focus on completing my daily and weekly challenges to earn more experience points and level up faster. It'll be a great way to stay motivated and track my progress. Speaking of which, my current goal is to reach level 150, and I'm determined to get there eventually. Thanks for the tips and advice!

原始回答（完整）：

> To determine the user's previous goal before updating their goal to level 150, I'll analyze the relevant memory fragments step-by-step.
> 
> 1. **Initial Goal (2023/06/16):** The user mentioned their initial goal was to reach level 100 before the end of the year.
>     - Memory Fragment: "I'm determined to reach level 100 before the end of the year."
> 
> 2. **Updated Goal (2023/09/30):** The user updated their goal to level 150.
>     - Memory Fragment: "I'm actually more interested in playing Apex Legends with my friends this weekend. Do you think it's a good idea to focus on ranking up to level 150, or should we just play for fun and not worry too much about leveling up?"
> 
> 3. **Contextual Analysis:**
>     - The user initially wanted to reach level 100 by the end of the year.
>     - They then considered the idea of reaching level 150, which was a more ambitious goal than their original one.
>     - The user's current goal of level 150 is mentioned in the context of balancing fun with the desire to rank up.
> 
> Based on this analysis, the user's previous goal before updating to level 150 was to reach level 100 before the end of the year.
> 
> **Final Answer:**
> Your previous goal before updating to level 150 was to reach level 100 before the end of the year.

参考答案 / Rubric：

> level 100

实际 judge 标准（完整前导指令）：

> I will give you a question, a correct answer, and a response from a model. Please answer yes if the response contains the correct answer. Otherwise, answer no. If the response contains some previous information along with an updated answer, the response should be considered as correct as long as the updated answer is the required answer.

实际 judge 末尾要求：

> Is the model response correct? Answer yes or no only.

原始判分：`No`。

**AI 辅助意见（不是人工结论）：** 现行标准：倾向符合，最终明确回答 level 100；原 No 为高置信疑似假阴性。依据支持旧目标100及新目标150，未发现影响此答案的无依据扩写。

人工填写：是否符合当前评分标准：________；是否包含无依据扩写：________；依据 / 备注：________。

### 意大利餐厅拒答：`6aeb4375_abs` / attempt 0

原问题：

> How many Italian restaurants have I tried in my city?

中文释义：我在自己的城市尝试过多少家意大利餐厅？

必要证据（所选原始检索片段）：

`answer_3f9693b7_abs_2:2:0`

> 2023/05/26 (Fri) 13:19 user: I think I'll go with kimchi and bokkeumbap. By the way, have you tried any good Korean restaurants in my city lately? I've tried four different ones so far, and I'm always looking for new recommendations.

`answer_3f9693b7_abs_1:8:0`

> 2023/05/20 (Sat) 08:03 user: By the way, speaking of noodles, have you tried any good Korean restaurants in your city lately? I've tried three different ones recently, and each has its own unique flavor and style.

原始回答（完整）：

> Based on the memory fragments provided, there isn't any direct information about how many Italian restaurants you have tried in your city. However, we can infer some information and provide a synthesized response.
> 
> 1. **Identifying Relevant Information:**
>    - There is no mention of trying Italian restaurants in the provided memories.
>    - The memories do mention trying different Korean restaurants multiple times, but this does not relate to Italian restaurants.
>    - There is no specific mention of a city or location, which makes it hard to pinpoint the exact context.
> 
> 2. **Synthesizing Information:**
>    - Since there is no direct information available, we can infer that the user might not have tried many Italian restaurants in their city. However, without more specific context or direct statements, we cannot provide a precise number.
> 
> 3. **Formulating the Answer:**
>    - Given the lack of specific information, it would be reasonable to conclude that the user has not tried many Italian restaurants in their city, but the exact number cannot be determined from the available data.
> 
> **Final Answer:**
> Based on the information provided, it seems that you haven't tried many Italian restaurants in your city. However, without more specific details, I cannot provide an exact number. If you would like to try Italian cuisine, I can suggest some ways to find great Italian restaurants in your area, such as checking online review sites like Yelp or TripAdvisor, asking friends and colleagues for recommendations, or exploring local food blogs and social media.

参考答案 / Rubric：

> The information provided is not enough. You mentioned trying Korean restaurants but not Italian restaurants.

实际 judge 标准（完整前导指令）：

> I will give you an unanswerable question, an explanation, and a response from a model. Please answer yes if the model correctly identifies the question as unanswerable. The model could say that the information is incomplete, or some other information is given but the asked information is not.

实际 judge 末尾要求：

> Does the model correctly identify the question as unanswerable? Answer yes or no only.

原始判分：`Yes`。

**AI 辅助意见（不是人工结论）：** 现行标准只要求识别不可回答，回答明确说无法确定数量，因此 Yes 有文本依据；但同时推测没试过很多家，没有事实支持。是否这种混合回答应当算有效拒答，现行提示词未明确规定，不擅自改判。

人工填写：是否符合当前评分标准：________；是否包含无依据扩写：________；依据 / 备注：________。

### Premiere Pro 偏好：`8a2466db` / attempt 1

原问题：

> Can you recommend some resources where I can learn more about video editing?

中文释义：能推荐一些让我进一步学习视频剪辑的资源吗？

必要证据（所选原始检索片段）：

`answer_edb03329:0:0`

> 2023/05/21 (Sun) 14:21 user: I'm trying to learn more about some advanced settings for video editing with Adobe Premiere Pro, which I enjoy to use. Can you give me some tips on where to start?

`answer_edb03329:1:2`

> 2023/05/21 (Sun) 14:21 assistant: learn how to use the Media Encoder to batch-export files. 10. **Practice and Experiment**: The best way to learn Premiere Pro's advanced settings is by practicing and experimenting with different techniques and features. Start with small projects and gradually move on to more complex ones. To dive deeper into these topics, I recommend the following resources: * Adobe Premiere Pro's official documentation and tutorials * YouTube channels like Premiere Bro, Video Copilot, and Adobe Creative Cloud * Online courses on platforms like Udemy, LinkedIn Learning, and Skillshare * Premiere Pro communities and forums, such as Reddit's r/premierepro and Adobe's Premiere Pro forum Remember, mastering Premiere Pro's advanced settings takes time and practice. Start with the topics that interest you the most, and gradually build your skills to become a proficient video editor.

原始回答（完整）：

> Based on the retrieved memory fragments, I can provide you with several resources where you can learn more about video editing. Here are the key points I've synthesized:
> 
> 1. **Official Documentation and Tutorials**: Adobe Premiere Pro's official documentation and tutorials are a great starting point. These resources will help you understand the software's features and functions in depth.
> 
> 2. **YouTube Channels**: There are many YouTube channels that specialize in video editing tutorials with Adobe Premiere Pro. Some recommended channels include:
>    - Premiere Bro: Offers a wide range of tutorials and tips.
>    - Video Copilot: Known for its in-depth and professional video editing tutorials.
>    - Adobe Creative Cloud: Official channel from Adobe with tutorials and updates.
> 
> 3. **Online Courses**: Platforms like Udemy, LinkedIn Learning, and Skillshare offer structured courses that can help you learn video editing at your own pace. These courses often cover both the basics and advanced features of Premiere Pro.
> 
> 4. **Community and Forums**: Engaging with the Premiere Pro community can provide you with support, advice, and inspiration. Some useful forums include:
>    - Reddit’s r/premierepro: A community where users share tips, ask questions, and discuss editing techniques.
>    - Adobe Premiere Pro Forum: Official forum where you can interact with other users and Adobe representatives.
> 
> 5. **Books**: While not directly mentioned, books can be a valuable resource. Some popular books on video editing include:
>    - "Adobe Premiere Pro CC Classroom in a Book" by Adobe Creative Team: A comprehensive guide to Premiere Pro.
>    - "Video Editing with Adobe Premiere Pro CC" by David Blatner: Focuses on practical techniques and tips.
> 
> By leveraging these resources, you can enhance your skills in video editing and explore advanced settings in Adobe Premiere Pro. If you have specific areas of interest or need more detailed guidance, feel free to let me know!

参考答案 / Rubric：

> The user would prefer responses that suggest resources specifically tailored to Adobe Premiere Pro, especially those that delve into its advanced settings. They might not prefer general video editing resources or resources related to other video editing software.

实际 judge 标准（完整前导指令）：

> I will give you a question, a rubric for desired personalized response, and a response from a model. Please answer yes if the response satisfies the desired response. Otherwise, answer no. The model does not need to reflect all the points in the rubric. The response is correct as long as it recalls and utilizes the user's personal information correctly.

实际 judge 末尾要求：

> Is the model response correct? Answer yes or no only.

原始判分：`No`。

**AI 辅助意见（不是人工结论）：** 现行标准：倾向符合，利用 Premiere Pro 偏好并提到高级设置；无需覆盖 rubric 所有点，原 No 疑似假阴性。Books 两项书目及作者不在检索事实中，属于无证据扩写，未外部核实，不能据此直接断言为虚假。

人工填写：是否符合当前评分标准：________；是否包含无依据扩写：________；依据 / 备注：________。
