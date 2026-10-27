# 2026-10-27 共同部分整理与检查

> 本文保留 `fb0141d` 的22／73页检查记录。后续全组slides措辞与样式修订见[新检查记录](slides/style-check-20261027.md)，最新演示为68页。

本轮基于 `1862df9`（六篇个人材料已合入），对应 [#65](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/65)。摘要、背景、跨论文比较、共同案例、课设选择和总结已形成完整审核稿；贡献比例按要求留空。这里记录材料检查，不代表团队讨论、真人排练、视频验收或课程提交完成。

## 成稿与定位

- [完整报告](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/blob/fb0141d3caec8e9f16fd5d473547f7e4ff16ad1f/reports/homework/report-preview.pdf)：22 页。第 1 页为摘要与背景，第 18–21 页为跨论文综合，第 22 页为总结、引用及未填写的贡献说明。
- [完整 slides](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/blob/fb0141d3caec8e9f16fd5d473547f7e4ff16ad1f/reports/homework/slides/preview.pdf)：73 页，其中正文 69 页、备用 4 页。开场第 1–3 页，综合第 61–69 页；六篇个人模块页码保持不变。
- [共同部分讲稿](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/blob/fb0141d3caec8e9f16fd5d473547f7e4ff16ad1f/reports/homework/scripts/00-opening-and-synthesis.md)：与 Beamer 的 12 页备注逐段一致，开场计划 120 秒、总结计划 600 秒；加上六人各 8 分钟，总计 60 分钟。计划时间尚未经过本人排练验证。
- [当前清单](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/blob/fb0141d3caec8e9f16fd5d473547f7e4ff16ad1f/reports/homework/integration-artifacts.json)：记录本轮源文件、两份 PDF 的大小及 SHA-256。前一轮 18 / 71 页的结果保留在[历史整合检查](integration-check-20261027.md)。

| 模块 | PDF 页码 | 页数 |
| --- | --- | --- |
| 开场 | 1–3 | 3 |
| StructMem | 4–15 | 12 |
| Hindsight | 16–24 | 9 |
| Semantic XPath | 25–37 | 13 |
| HyMEM | 38–44 | 7 |
| MetaMem | 45–52 | 8 |
| Text2Mem | 53–60 | 8 |
| 系统性总结 | 61–69 | 9 |
| 备用资料 | 70–73 | 4 |

## 内容依据与表达边界

统一对照六篇的研究对象、表示、主要机制与成立条件，进一步讨论存储与访问、取回与利用、更新策略与操作语义之间的关系。跨论文联系是阅读分析，没有被写成已验证的组合系统。

实验比较使用原论文内部对照：StructMem PDF 第 4 页表 2 的多跳及开放域消融，MetaMem 第 7 页表 2 的反思与演化消融，Semantic XPath 第 7 页表 1 的输入规模与回答得分，Text2Mem 第 8 页表 3 的工作流 ESR / EMR。明确区分各自任务、模型、反馈、预算和评价分母，不按原文总分给六篇排名。

共同案例为自拟的三条行程记录，区分记录时间、出行时间、取消关系和路线补充；随后讨论“暂时别提”对应的操作契约。该案例用于解释机制边界，不是六套系统的运行结果。

课设选择依据版本 `1862df9` 的 `docs/project-plan.md`：以 LoCoMo 小子集上的 StructMem 复现为主线，对照原始对话 Flat RAG、去掉综合的事件记忆与完整 StructMem。这里说明既定设计，不把个人试点、作者成绩或尚未完成的对照登记为本组实验结果。

## 实际验证

1. 报告与 slides 均使用仓库配置运行 `latexmk -xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error main.tex`，退出 0。
2. 最终日志无 Overfull、Underfull hbox、缺字、未定义引用或引文。报告保留原有 3 条 Underfull vbox 与数学字体尺寸替代提示；slides 无相关排版警告。未修改共享字体或版式配置。
3. 复用 `scripts/fix_hymem_pdf_unicode.py` 补齐必要的 ToUnicode。PDF.js 在未设置外部 `cMapUrl` 的条件下完成报告 22 页、slides 73 页渲染与中文提取，每页均有中文，日志无警告。PDFium 以 1.5 倍比例逐页比较，补映射前后画面一致。
4. 检查整份报告的页面缩略图、slides 新增或重写的 12 页版式，修正表格断行与报告总结分页；未见截断或遮挡。六篇个人报告和 slides 的 `.tex` 与基线逐字节一致，不重复进行已审核模块的内容重写或模型实验。
5. 核对两份 PDF 均小于 20 MB、所有清单哈希、UTF-8/LF、Markdown 本地链接和 `git diff --check`。贡献说明与基线逐字节一致；讲稿与备注一致，逐页计划时间合计正确。

## 待真人确认

- 共同材料按仓库约定请一位相关成员集中审核，重点是跨论文联系、原文证据的解释和课设选择；尚未登记团队讨论结论。
- 封面成员、实际定稿日期、开场与总结的讲解人，以及贡献比例继续待确认。本轮没有代填贡献。
- 六人的实际讲解时长、视频及最终衔接仍待验收。Semantic XPath 的旧录制继续按本次视频未交付处理。
- 最终视频拼接、交接与课程上传尚未完成。
