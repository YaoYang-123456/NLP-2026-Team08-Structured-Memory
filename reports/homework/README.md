# 小组平时作业

第 8 队的 6 名成员共同完成“长上下文场景结构化记忆建模”专题阅读，与课设共用本仓库的六篇论文、笔记和引用。每人先负责一篇论文，再共同形成系统性比较；阅读结论用于课设选型与实验分析，课设中的真实发现可反过来补充讨论。个人阅读和讲解是小组材料的一部分。

## 提交与讲解

依据[老师的新通知](../../docs/course/262701NLP-平时作业提交验收说明-2026-文字版.md)：

- 提交截止：**2026 年 11 月 1 日 23:59**。
- 本组属于专题类课设，准备一份系统性阅读报告、一份 PPT、一个讲解视频；总时长按队伍人数 × 10 分钟，本组 6 人约 60 分钟。
- 报告和汇报注明各成员分工及贡献百分比；个人额外整理可一并保留。
- 具体讲解时间最早预计 11 月 2 日，以老师后续安排为准。

本组报告统一使用 **LaTeX 写作、PDF 交付**，演示材料使用 [Beamer 模板](slides/README.md)并导出 PDF；[官方 Word 样例](../../docs/course/软件学报排版样例2025年版.doc)只作报告版式参考。

## 当前进展（2026-10-26）

截至北京时间 **21:48**，已核对主分支 `1850da7`、相关 issue / PR 及交接文件：**六篇论文均已有稿件记录，4 篇已合入、2 篇初稿待审核；另有 MetaMem 修订稿待审核。** 当前材料审核队列为 #57、#59、#63。这反映仓库可见交付，不把材料完成等同于本人阅读、录制或最终提交。

| 论文 | 阅读负责人 | 材料交付 | 本人过稿与视频状态 |
| --- | --- | --- | --- |
| StructMem | hycx233 | 报告、幻灯片和备注已由 [PR #15](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/15) 合入 | 本次约 60 分钟作业的个人录制及实测时长尚无登记 |
| Hindsight | onlysonder | [PR #60](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/60) 已合入报告章节、9 页个人幻灯片及[8 分钟讲稿](scripts/02-hindsight-8min.md)；不再记为未认领或未交稿 | 讲稿标注建议时长，录制前仍需本人过稿与实际计时；尚无本次视频交付记录 |
| Semantic XPath | oioioi-521 | [PR #57](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/57) 已提交 4 页个人报告、13 页幻灯片及讲稿，指定 F 审核，尚未合入 | **本次视频暂按未交付计**。[#55](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/55) 所述 8 分 55 秒为此前录制，待 F 检查与当前幻灯片的内容衔接、风格及音画效果后决定能否复用 |
| HyMEM | lanshuheng9-oss | [PR #54](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/54) 已由 F 审核合入；[PR #61](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/61) 已补交 2 页个人报告、7 页幻灯片及校验记录；PDF 中文兼容问题由 [#62](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/62) 跟踪 | [#53](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/53) 保留本人过稿、实际计时排练及录制待办 |
| MetaMem | YaoYang-123456 | [PR #40](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/40) 已合入正文和原模块；新增 [PR #63](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/63) 提交 8 页模块、规则编辑示例、完整讲稿、2 页个人报告及中文映射修复，指定 F 审核，尚未合入 | [#39](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/39) 保留本人过稿与录制；新核心稿估计 7 分 59 秒，仍非实际排练记录，替代此前仅约 6 分 25 秒的备注估时 |
| Text2Mem | ngocnamd93-spec | [PR #59](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/59) 已提交 3 页个人报告、8 页幻灯片及讲稿，指定 F 审核，尚未合入 | [#56](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/56) 保留本人过稿、实际计时排练与录制；480 秒为计划时长，视频尚未录制 |

### 预览版本与已知问题

- 仓库 [全组预览](slides/preview.pdf) 仍是 #54 的 **61 页旧快照**，SHA-256 为 `1abab03db0ea939a91bf3025c324bad60a31d6a12ed554b296b054646bfdf44e`，未反映已合入的 Hindsight。此前 F 基于 `fde4f86` 编译的 12 / 61 页主分支版及 17 / 68 页本地候选也已是历史预览，不能继续称为当前完整合稿。
- HyMEM 的 [#62](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/62) 记录：缺少内嵌 ToUnicode 时，未配置外部 CMap 的 PDF.js 会丢失中文；此前单一渲染器检查不足以证明跨预览器兼容。修复已推送到 [分支提交 b64f1cf](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/commit/b64f1cf)，尚未见修复 PR 或合入记录，issue 仍开放。
- MetaMem [PR #63 的交接说明](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/blob/caca33885628bd99771ecddc26a44db52c2b01de/reports/homework/metamem-handoff.md)报告已为个人 PDF 补齐中文映射，并完成 PDF.js 与 PDFium 检查；作者基于 `1850da7` 接入该修订后编译的全组报告 / 幻灯片为 14 / 64 页。此为作者验证记录，不是 F 本轮复验，也未包含 #57 / #59 的待审模块。
- 本轮只核对进度与交接记录，没有重新编译合稿、复验字体修复或审核三份待审 PR 的论文内容，也未核看视频。

### 接下来的交付

1. F 集中审核 #57、#59、#63：论文数字与来源、共享材料编译和版式、讲稿页序与时长安排；特别核对 Semantic XPath 的历史分工说明、Text2Mem 指标口径和 MetaMem 规则示例与 PDF 中文兼容。
2. 跟进 HyMEM #62 的修复交付和验收；整合稿重新导出时也检查 PDF.js 无外部 CMap 的中文显示，避免只依据编译成功或单一渲染器结果。
3. 六篇稿件完成审核后共同补齐系统性比较、摘要、总结与实际贡献说明，重新编译并同步全组预览；当前综合草稿仍未编入报告，幻灯片总结仍为结构模板。
4. 收集个人视频及实际时长，安排开场和共同总结，核验约 60 分钟合稿，记录文件版本、交接与最终上传状态。当前尚无本次作业可计为已交付的个人视频；Semantic XPath 的旧视频继续按未交付跟踪。

10 月 22 日研讨阶段已结项：[PR #52](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/52) 已合入，[#19](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/19) 与 [#31](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/31) 已关闭；11 月 1 日的阅读报告、约 60 分钟视频及课程上传仍按本页跟踪。

## 个人阅读材料

HyMEM负责人 `lanshuheng9-oss` 的[个人报告PDF](hymem-reading-report.pdf)、[个人演示PDF](slides/hymem-preview.pdf)和[讲稿及阅读指南](hymem-reading-guide.md)已整理并完成个人模块编译与逐页检查；[文件大小及SHA-256](hymem-artifacts.json)随材料保存。正文已由 F 在 #54 审核，PDF 的跨预览器中文兼容问题继续由 [#62](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/62) 跟踪。当前仍待本人过稿、排练及录制，不能据此标记全组作业已定稿或提交。

## 共同编辑

`main.tex` 是阅读报告入口，`sections/01-structmem.tex` 至 `sections/06-text2mem.tex` 分别对应六篇论文，成员在 issue 中认领后编辑对应章节。文件里的“待填写”标明尚未完成的内容，不代表已有阅读或实验成果。当前先完善各自的论文章节，待大家完成后再推进共同总结；`sections/07-synthesis.tex` 保留为综合分析草稿，暂不编入主稿。摘要、总结与贡献说明由相关成员整合，合并前请一位相关成员集中复核。`references.bib` 的六篇条目来自 ACL Anthology 官方 BibTeX 导出。

每篇至少说明问题与背景、核心方法、关键实验、优缺点和对本组课设的启发，引用标明论文页码 / 图表编号。公共讨论围绕组织、检索、更新、利用和操作规范比较六篇工作，不直接按不同模型和任务下的准确率排名。论文报告结果、本组已验证结果和计划开展的实验分别注明；阅读报告不等待课设实验全部完成。

## 系统性总结与团队讨论

保留每人介绍一篇论文的安排。待个人部分完成后，把后面的综合分析作为报告和 PPT 的主要内容之一。现有综合草稿先保留，不提前定稿；后续由小组核对、讨论和修订，不代表已经形成团队共识。计划覆盖：

- **统一对照表**：对齐研究对象、表示、主要机制和比较边界，说明六篇工作分别解决什么问题。
- **机制之间的联系**：讨论组织与访问、取回与利用、更新与操作语义的关系，同时说明组合所需条件。
- **共同取舍与局限**：比较抽取误差、上下文预算、更新风险、验证范围与成本，避免只复述各篇的优点。
- **实验可比性**：区分任务、数据、模型、反馈、预算、指标与成本，不直接按原论文分数排优劣。
- **共同案例**：用同一个自拟场景检查各方法的解释范围，区分讨论推演与实际验证。
- **课设选择与结论**：说明主线选择、参考机制和不纳入的部分，记录依据及仍待验证的分歧。

各论文负责人参与综合章节的证据核对与讨论；由一位成员整合行文，相关成员复核。用原文页码、图表或实际结果支撑结论；团队讨论后再把共识和分歧补入文稿，不虚构讨论经过。具体论文阅读和团队整合工作都按实际情况计入贡献说明。

Slides 沿用同一报告结构，采用“开场 → 六人各 7–9 分钟 → 系统性总结 10–15 分钟”的安排。默认开场 3 分钟、每人 8 分钟、总结 12 分钟，合计约 63 分钟；若需控制在 60 分钟，采用开场 2 分钟、每人 8 分钟、总结 10 分钟。具体模块、编译和讲稿备注见 [slides 说明](slides/README.md)。最后的综合部分需要解释论文之间的关系、取舍依据和共同认识，待各成员完成后共同填写。

## 编译报告

共享版式来自 [软件学报社区模板](../templates/jos/README.md)。在本目录执行：

```sh
latexmk -xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
```

本目录的 `.latexmkrc` 设置共享模板搜索路径和输出目录，生成 `output/homework/main.pdf`，编译中间文件也留在 `output/`。定稿后将 PDF 复制到本目录；PPT 源文件和最终导出按需加入，不提交缓存。

## 最终整理

报告、slides、视频使用相同的主题短名和日期，例如 `8队-结构化记忆-20261101.pdf`、`8队-结构化记忆-20261101-slides.pdf`、`8队-结构化记忆-20261101.mp4`，打包名为 `8队-结构化记忆-20261101.zip`，日期使用实际定稿日期。打包上传老师通知中的云盘。

单文件达到 20 MB 时，**请将该文件发送到小组微信群**，不要提交 Git 或 PR 附件；仓库只记录文件名、大小、SHA-256、用途和交接日期。此处的平时作业截止时间不替代课设最终验收时间，课设安排继续见[项目方案](../../docs/project-plan.md)及后续通知。
