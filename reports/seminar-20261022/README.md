# 10 月 22 日研讨：合稿草稿与 F 进展

更新：2026-10-20；整合负责人：hycx233；关联任务 [#19](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/19)。已有六页可编译合稿，**保留为 E 评分提交前的快照，不是当前完整进展或最终定稿**。

**当前暂缓 slide 制作、视频录制和实际汇报准备。** 本次只更新说明与项目计划，不修改 `.tex` 或重新导出 PDF。E 已在 [PR #46 / a9cf151](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/blob/a9cf151a3048b5df2b58f91420da3dfce0eb161b/reports/e-score-20261020.md) 提交自动评分及四例分析草稿：S0 16/30、S2 19/30；人工复核与标签证据回查仍待完成。旧页面中的“暂无评分”反映制稿时状态，最新进展以[项目方案第 10 节](../../docs/project-plan.md#10-当前进展与下一步)为准。

[老师补充通知](../../docs/course/seminar-notice-20261020.md)要求提前上传幻灯片和 8 分钟视频，仍须线下汇报及 2–5 分钟问答；研讨云盘有效期为 10 月 22 日 14:30。题目、选题理由、整体方案、创新性、当前分工及贡献比例均需在后续完整版本中覆盖；本次不制作这些页面、不代填贡献比例，也不表示已上传或登记 Excel。

## 已有材料快照

- [assembly-draft.tex](assembly-draft.tex) / [assembly-draft-preview.pdf](assembly-draft-preview.pdf)：A、B、C、D 原稿选排，加 F 两页，共六页；按下表预留 E 结果与案例位置。
- [f-progress.tex](f-progress.tex) / [f-progress-preview.pdf](f-progress-preview.pdf)：F 自己的两页，含讲稿备注；[main.tex](main.tex) 是个人预览入口。
- [members/sources.json](members/sources.json)：成员原稿的固定提交、路径与 SHA-256。A/C/D 仅从本人原稿选取文字和表格进行 Beamer 排版；B 保留本人第一张内容页原文。没有代写成员技术结论。标题、来源、状态提示和计时备注由 F 整理。
- [B 答辩备忘](../s0-defense-20261020.md)：可离线备查；其关于 S2 尚未完成的文字是旧快照，当前 D 状态以本页和 PR #41 新提交为准。B 的第二张案例页未放入短讲，F 保留同一真实预测作为未评分样例。

## 原六页草稿的时间分配（暂存）

原表依据 B 在 [#19 的交接](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/19#issuecomment-6281868123)整理，新增通知也明确全组 8 分钟，与平时作业约 60 分钟的视频分开。下表保留原草稿分配，不是当前已批准的讲述顺序，未实际计时；其中 E“待交”等状态已被上方最新进展替代。后续恢复制作时再依据完整内容调整，本轮不排练。

| 环节 | 内容 | 秒数 |
| --- | --- | ---: |
| F 开场 | 口头说明长对话记忆问题与本次开发试跑范围 | 20 |
| A | 固定数据、30题和标签隔离 | 35 |
| B | 原始对话向量检索与真实回答交接 | 45 |
| C | 事实/关系事件记忆及来源统计 | 50 |
| D | 真实综合、60＋5检索及尚待评分的 S2 | 60 |
| F 两页 | 统一调用、真实 S0、联调与交接边界 | 90 |
| E（待交） | 同口径结果表及一例人工核查，其他案例备查 | 90 |
| F 收尾 | 方法差异、未完成项和下一步 | 30 |
| 转场及机动 | 不临时增加方法或运行 API | 60 |
| 合计 | 8分钟；缺失 E 内容不以虚构成绩补齐 | 480 |

S0/S2 是整套系统对照，方法提示词和输入形态存在差异；不能把分数变化单独归因于事件绑定。S1/S2 保持相同方法提示词，S1 尚未执行，按原计划研讨后补齐。

## 当前材料与审核状态

| 包 / 负责人 | 固定来源 | 当前状态 |
| --- | --- | --- |
| A / ngocnamd93-spec | [main bf716a4 的个人进展](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/blob/bf716a49a7f0b0655fef898b0694e010514892bc/reports/locomo-a-progress.md) | PR #38 已合并；合稿只选固定数据和隔离口径 |
| B / YaoYang-123456 | [main bf716a4 的两页 Beamer](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/blob/bf716a49a7f0b0655fef898b0694e010514892bc/reports/s0-seminar-20261019.tex) | PR #37/#45 已合并；短讲只选第一页 |
| C / oioioi-521 | [PR #43 / 433de349 的个人进展](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/blob/433de349595a54e4f0f0f2073d745bb1d830a4ea/reports/structmem-progress-20261019.md) | D 已批准完整事件交接；PR 尚未合并，不代表 E 语义验收 |
| D / lanshuheng9-oss | [PR #41 / 43dc389 的两页进展](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/blob/43dc38916b8c7acdc834e00bf5095cf6700ec9f6/reports/structmem-d-progress.md) | 选排来源保持不变；38214e5 已补充 C/F 审核与交接状态，F 范围已批准，C 对 D 的事件/数值审核仍待完成 |
| E / onlysonder | [PR #46 / a9cf151](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/46) | 自动评分 60/60 次完成，S0 16/30、S2 19/30；四例分析及个人页已提交，待人工核查并修正题型中文名称，尚未编入本目录 |
| F / hycx233 | 本目录及 [S0 交接 PR #42](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/42) | S0/S2 评分包可从仓库获取；D 已批准 PR #44 的配置与交接范围，#42 仍待 E 审核；材料制作与排练暂缓 |

D 已通过微信发送约1.05 MB评分包，F 已取得并完成实际逐条核验，原包直接入库，见[包、哈希和 E 读取入口](../artifacts/README.md)及[机器核验记录](../s2-handoff-verification-20261020.json)。先前把“仓库没有包”推断成“D未交付”不准确，[原请求修改](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/41#pullrequestreview-5581148679)已撤回，并提交[新的 F 范围批准](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/41#pullrequestreview-5581231548)。不要求 D 重复发送，原包内关于“未发送”的文字保留为打包时快照。

## 固定回答配置

[qa-structmem-20261020.json](../../configs/qa-structmem-20261020.json) 来源为 D 的固定提交 cb79d2c7c53bb88ff1042410579c239eae438c9f，SHA-256 为 5c26490902627d5199cd0194fd65b725275efe8844eb07b678daa467ad495abe。公共参数和 S0 模板与 F 已运行版本一致，S1/S2 方法指令相同；本轮未改配置。

时间推理与简短回答规则已对照固定 LightMem 8449d574 的 experiments/locomo/prompts.py 核对；JSON 展示、共同 system 指令和仅输出最终答案属于已记录适配，不声称逐字复刻上游。回答最多512 tokens；D的综合8192 tokens是另一调用角色，配置审核不是付款或账单验收。

## 已有验证记录与编译方式

- 上一轮 [PR #40 审核](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/40#pullrequestreview-5579766040) 核对论文和排版；PR #40 已合并。[PR #41 旧配置审核](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/41#pullrequestreview-5579766167) 通过30项针对性测试，保留原有范围结论。
- 本轮仅复核 #41 新增范围：隔离提交43dc389的 runner 4项及 F QA 14项共18项通过；6个代码哈希、阶段 token 加总和事件/摘要/题型分母算术通过。随后取得微信包，CRC及9文件哈希通过，逐条核对同一30题、5＋25批次指纹、冻结配置、60＋5上下文、完整请求重建、原始响应与预测及usage一致，4次弃答保留；四类候选均对应题目上下文。包内没有91条原始综合调用或完整原生库，未独立回放这些数据，来源核验不替代 E 语义人工验收。
- 两页个人预览和六页合稿使用共享 XeLaTeX/Beamer 模板编译，导出后逐页渲染检查。成员原稿哈希、B摘录一致性、UTF-8/LF、相对链接和 diff 检查见本轮 PR 验证。

在本目录执行：

```sh
latexmk -xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
cp ../../output/seminar-20261022-f/main.pdf f-progress-preview.pdf
latexmk -xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error assembly-draft.tex
cp ../../output/seminar-20261022-f/assembly-draft.pdf assembly-draft-preview.pdf
```

缓存留 output/，两个小型预览 PDF 直接入库。以上编译与核验记录来自现有草稿制作及交接轮次，本次文档更新没有重新编译、修改 slide 或新增 API 请求。当前先完成评分人工复核与剩余审核，再根据进展推进完整材料、实际排练与录制；老师的上传时间保持不变。
