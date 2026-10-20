# 来源索引与冻结范围

所有结果属于固定 3 个开发会话、30 题，不是留出集。下表中“真实交付”与“本轮独立核验”分开，未合并不表示成果不存在。

| 材料 | 固定来源 | 本轮使用和限制 |
|---|---|---|
| A/B、MetaMem 与 B 个人材料 | main `bf716a49a7f0b0655fef898b0694e010514892bc` | A 30 题固定选择和 B 原始块检索；旧 MetaMem 试点不作为团队 S0/S2 数据 |
| C 完整事件 | [#43 / 433de349](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/43) | 91 sessions、1,973 messages、3,712 条（2,309 事实＋1,403 关系）；采用 D 已有完整包接收审核，不声称本轮重新抽取 |
| D 综合及 S2 | [#41 / 38214e55](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/41) | 91 条综合、30 答；实际 S2 评分交接包的全部回答对已核验；本轮未取得/回放全部综合原始调用 |
| F S0 | [#42 / 49d8a676](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/42) | 30 答；实际 S0 交接包全部回答对已核验 |
| F 合稿/配置/通知 | [#44 / d6215c31](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/44) | 当前协作分支的基底；旧六页保留，新材料不会倒写为原成员已确认 |
| E 评分/修订 | [#46 / 1cfd1770](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/46) | 原始 16/19；复核 15/19；六例对源核查；60 条原始 judge 尚缺独立复算 |
| E 安全协作补丁 | [#47 / df99b7f](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/47) | 输入绑定、逐次保存、输出保护、题型名称；7 项模拟测试，不产生新裁判 |
| 官方类别 | LoCoMo `cbfbc1dba6bc53d00625212a0f22d55ffee7c1fc` | 官方评价/生成代码、任务定义；链接与解释见 final-audit.md |
| 教师通知 | [仓库转发原文](../../docs/course/seminar-notice-20261020.md) | 视频是团队要求；具体录制人员、Excel 与场次未核实 |

可复算摘要见 [answer-audit.json](answer-audit.json)；逐类数值见 [results.csv](results.csv)。S0 预测 SHA-256 `d8b3d9159fdd0117985f2ddda58e38333dbb54342c6c3e1edb8b7860320379d6`，S2 预测 `307d5eb3c92940a12a3e33e9d4b38ac77685497e37e3b68403fe27d9becc3b79`。模型、原始请求、答案标签、完整对话不复制到公开最终材料。

本轮只有 AI 辅助核查、软件结构与渲染检查及合成语音计时。没有成员人工签收、真人排练、课程上传或教师确认的隐含记录。
