# 10 月 22 日研讨：合稿草稿与 F 进展

更新：2026-10-20；整合负责人：hycx233；关联任务 [#19](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/19)。已有六页可编译合稿，**尚缺 E 评分、人工核查案例及实际排练，不是最终定稿**。

## 可直接使用的材料

- [assembly-draft.tex](assembly-draft.tex) / [assembly-draft-preview.pdf](assembly-draft-preview.pdf)：A、B、C、D 原稿选排，加 F 两页，共六页；按下表预留 E 结果与案例位置。
- [f-progress.tex](f-progress.tex) / [f-progress-preview.pdf](f-progress-preview.pdf)：F 自己的两页，含讲稿备注；[main.tex](main.tex) 是个人预览入口。
- [members/sources.json](members/sources.json)：成员原稿的固定提交、路径与 SHA-256。A/C/D 仅从本人原稿选取文字和表格进行 Beamer 排版；B 保留本人第一张内容页原文。没有代写成员技术结论。标题、来源、状态提示和计时备注由 F 整理。
- [B 答辩备忘](../s0-defense-20261020.md)：可离线备查；其关于 S2 尚未完成的文字是旧快照，当前 D 状态以本页和 PR #41 新提交为准。B 的第二张案例页未放入短讲，F 保留同一真实预测作为未评分样例。

## 全组 8 分钟安排

时长依据 B 在 [#19 的交接](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/19#issuecomment-6281868123)，与平时作业约 60 分钟的视频安排分开。本表是排练目标，未实际计时。

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
| C / oioioi-521 | [PR #43 / 433de349 的个人进展](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/blob/433de349595a54e4f0f0f2073d745bb1d830a4ea/reports/structmem-progress-20261019.md) | 完整事件与材料已提交；原 PR 尚未合并，数值审核沿用指定 C/D 分工 |
| D / lanshuheng9-oss | [PR #41 / 43dc389 的两页进展](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/blob/43dc38916b8c7acdc834e00bf5095cf6700ec9f6/reports/structmem-d-progress.md) | D 记录91次真实综合与30题 S2 回答；F 要求实际评分包入库后再核对逐题数据 |
| E / onlysonder | [任务 #31](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/31) | 暂无真实评分、至少4个核查案例及个人页，不填准确率 |
| F / hycx233 | 本目录及 [S0 交接 PR #42](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/42) | S0 30题预测和评分包可从仓库获取，PR #42 仍等 E 审核；本合稿继续待 E 和交接验收 |

D 的约1.05 MB包目前只在其本地，F 本机和仓库均未取得。已在 [PR #41 正式审核](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/41#pullrequestreview-5581148679) 直接要求 lanshuheng9-oss 将现有无密钥/标签的包加入 reports/artifacts/，附大小、SHA-256、清单与读取入口；不让用户转传，也不重新付费生成。该汇总的代码哈希与加总检查通过，不等于逐条原始记录验收。

## 固定回答配置

[qa-structmem-20261020.json](../../configs/qa-structmem-20261020.json) 来源为 D 的固定提交 cb79d2c7c53bb88ff1042410579c239eae438c9f，SHA-256 为 5c26490902627d5199cd0194fd65b725275efe8844eb07b678daa467ad495abe。公共参数和 S0 模板与 F 已运行版本一致，S1/S2 方法指令相同；本轮未改配置。

时间推理与简短回答规则已对照固定 LightMem 8449d574 的 experiments/locomo/prompts.py 核对；JSON 展示、共同 system 指令和仅输出最终答案属于已记录适配，不声称逐字复刻上游。回答最多512 tokens；D的综合8192 tokens是另一调用角色，配置审核不是付款或账单验收。

## 验证与编译

- 上一轮 [PR #40 审核](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/40#pullrequestreview-5579766040) 核对论文和排版；PR #40 已合并。[PR #41 旧配置审核](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/41#pullrequestreview-5579766167) 通过30项针对性测试，保留原有范围结论。
- 本轮仅复核 #41 新增范围：隔离提交43dc389的 runner 4项及 F QA 14项共18项通过；6个代码哈希、阶段 token 加总和事件/摘要/题型分母算术通过。缺少实际包，未声称完成30题逐条或原生数据库回填复验。
- 两页个人预览和六页合稿使用共享 XeLaTeX/Beamer 模板编译，导出后逐页渲染检查。成员原稿哈希、B摘录一致性、UTF-8/LF、相对链接和 diff 检查见本轮 PR 验证。

在本目录执行：

```sh
latexmk -xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
cp ../../output/seminar-20261022-f/main.pdf f-progress-preview.pdf
latexmk -xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error assembly-draft.tex
cp ../../output/seminar-20261022-f/assembly-draft.pdf assembly-draft-preview.pdf
```

缓存留 output/，两个小型预览 PDF 直接入库。没有新增真实 API 请求，没有重跑 S0、D 综合/回答或接管 E 评分；未进行整组实际排练。21日晚应补齐评分及案例、复核实际交接、更新受影响页面后冻结。
