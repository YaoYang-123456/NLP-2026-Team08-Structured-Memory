# 10 月 22 日研讨：F 进展与材料收口

更新：2026-10-20；负责人：hycx233；关联任务 [#19](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/19)。这里先交付 F 自己的两页，供后续组内合并；不是六人研讨定稿。

## 已交付

- [f-progress.tex](f-progress.tex)：两张内容页，沿用小组 Beamer 版式，包含每页讲稿备注；介绍真实 S0 回答、统一接口和下一步联调。
- [f-progress-preview.pdf](f-progress-preview.pdf)：对应的两页 PDF，可离线展示。
- [main.tex](main.tex)：个人预览入口；合并到全组材料时，只需在相应 lecture 中引入 `f-progress.tex`，不另起一份全组报告。
- [qa-structmem-20261020.json](../../configs/qa-structmem-20261020.json)：F 已核对的 S1/S2 回答配置，与 D 候选原内容逐字节相同，没有重跑 S0。

本配置来源为 D [PR #41](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/41) 的固定提交 `cb79d2c7c53bb88ff1042410579c239eae438c9f`，文件 SHA-256 为 `5c26490902627d5199cd0194fd65b725275efe8844eb07b678daa467ad495abe`。公共参数和 S0 模板与 F 已运行版本一致，S1/S2 的方法指令相同。时间推理与简短回答规则对照固定 LightMem `8449d574` 的 `experiments/locomo/prompts.py` 核对；JSON 展示、共同 system 指令和仅输出最终答案属于已记录的适配，不声称逐字复刻上游布局。

文件只冻结回答配置（最多输出 512 tokens）。D 的综合提案 8192 tokens 是另一个调用角色；91 个窗口的实际输入、本轮费用和真实运行记录仍由 D 提交。本次没有执行综合、回答或评分 API 请求，不能把占位摘要当作综合结果，也不能将配置审核视为付款或费用验收。

## 当前材料清单

| 包 / 负责人 | 成员已提供的材料 | F 的收口状态 |
| --- | --- | --- |
| A / ngocnamd93-spec | [两页进展，PR #38](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/blob/1d651da44cd1bf101ead69794a74f45f91c507a3/reports/locomo-a-progress.md) | 数据与环境内容可用于合并；A 分支仍待原有流程处理 |
| B / YaoYang-123456 | [两页 Beamer，PR #37](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/blob/62410cdd231d4af2438eefdcd423e988f1471acc/reports/s0-seminar-20261019.tex) | 检索内容可复用；原页的“真实回答0”是当时快照，后续状态以 F 的真实30题页说明 |
| C / oioioi-521 | [个人进展，PR #43](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/blob/433de349595a54e4f0f0f2073d745bb1d830a4ea/reports/structmem-progress-20261019.md)及同目录 PDF | 已有本人两页；完整事件的数值验收沿用 C/D 记录，F 本次未复验其数据库 |
| D / lanshuheng9-oss | [两页进展，PR #41](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/blob/cb79d2c7c53bb88ff1042410579c239eae438c9f/reports/structmem-d-progress.md) | F 配置审核已通过；真实综合及 S2 结果尚未交付 |
| E / onlysonder | [任务 #31](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/31) | 尚无评分、至少4个核查案例及个人页交付，不填入准确率 |
| F / hycx233 | 本目录两页及 [S0 真实运行 PR #42](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/42) | 30题预测和交接包已在仓库分支可获取；完整评分链路和整组演练待后续 |

本清单按 2026-10-20 可见记录整理，保留各人的原始技术内容和分支来源，不提前生成团队共识。21 日晚前收齐真实评分、案例和各人的最终页后，再合并、固定结果表并演练。

## 本次审核与验证

- [PR #40 的审核](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/40#pullrequestreview-5579766040)：论文图1、主表、消融、划分及学习参数核对通过；隔离副本的全报告编译成功（11页），个人 MetaMem lecture 编译为7页并渲染检查，无 Overfull。本人阅读和实际讲解计时仍待负责成员完成。
- [PR #41 的 F 范围审核](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/41#pullrequestreview-5579766167)：公共参数、S0 不变、S1/S2 同指令及时间推理适配通过；D 的12项、完整/候选4项、F的14项针对性测试共30项通过。事件库数值部分仍由 C 指定 reviewer 核对。
- F 两页使用共享 XeLaTeX/Beamer 模板编译并渲染检查；配置与 D 候选的字节一致性、F 配置校验、公共字段及 S0 模板一致性、S1/S2 相同指令均通过。

个人预览命令，在本目录执行：

```sh
latexmk -xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
cp ../../output/seminar-20261022-f/main.pdf f-progress-preview.pdf
```

缓存留在忽略目录 `output/`，需要交给成员的两页 PDF 小于 20 MB，直接纳入仓库。本轮没有制作六人最终 PDF，也未执行课堂计时。
