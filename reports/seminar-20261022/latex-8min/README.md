# 8 分钟 LaTeX 汇报与逐页讲稿

内容基于 2026-10-21 的项目进展，按 2026-10-22 第一次研讨制作。沿用小组蓝色 Beamer 版式，正文保留可直接用于讲述的完整句子。投影页仅保留页码，删去重复灰字和来源页脚；来源保存在备注与下方索引中。旧候选文件保留为历史版本，本目录是本轮 LaTeX 材料入口。

题目：**长对话结构化记忆复现与优化**。本版用于汇报准备：**F（hycx233）负责视频录制，A（ngocnamd93-spec）负责线下汇报**，两者共用本目录的幻灯片和逐页讲稿。

## 使用与编辑

- [汇报 PDF](slides-8min.pdf)：16:9，仅含 12 页正文，讲到第 12 页结束。
- [逐页讲稿 PDF](speaker-script-8min.pdf)：7 页，含时间表与 12 页可朗读正文。计划时间合计 480 秒，约 1,700 个汉字；没有进行真人录音计时。
- [补充说明与答辩准备 PDF](qa-notes.pdf)：3 页，独立整理原备用页、协作方式与问答备忘，供答辩前准备和现场查阅。
- [幻灯片入口](main.tex)、[讲稿入口](speaker-script.tex)、[答辩文档入口](qa-notes/main.tex)、[共用口述正文](speeches.tex)：正文与 Beamer notes 引用同一份讲稿，修改口述内容时编辑 `speeches.tex`。
- [完整交接 ZIP](team08-seminar-latex-8min.zip)：包含上述 PDF、全部编译所需 TeX、说明与包内 SHA-256 清单，可直接分享给同学。文件大小与哈希见 [交付清单](delivery-manifest.json)。

`preamble.tex` 是仓库 `reports/homework/slides/preamble.tex` 的原样副本，用于让当前项目与交接包独立编译；本轮仅在 `main.tex` 中调整局部版式，没有改动共享模板。使用 XeLaTeX 和 TeX Live 自带的 Fandol 字体，不依赖本机商业字体或外部图片。进入本目录运行：

```sh
latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build -jobname=slides-8min main.tex
latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build -jobname=speaker-script-8min speaker-script.tex
latexmk -cd -xelatex -interaction=nonstopmode -halt-on-error -outdir=../build -jobname=qa-notes qa-notes/main.tex
```

也可以在 Codex 内打开本目录，以 `main.tex` 查看幻灯片，或显式选择 `speaker-script.tex` 编译讲稿；打开 `qa-notes/` 可独立编译答辩文档。正文备注默认隐藏，演讲者双屏视图可将模板中的 `hide notes` 改为 `show notes on second screen=right`。

## 本轮内容口径

1. 将旧候选中的“逐题评分尚待复算”更新为：60 个输入指纹已核对，分类和总体分数离线复算一致。
2. 保留原始自动裁判 S0 16/30、S2 19/30；正文展示应用已有一条证据裁决后的 15/30、19/30。原始裁判与案例证据裁决分别保留。
3. 回答输入为 132,531 和 586,282 tokens，约 4.42 倍；这不是总费用倍数。S0/S2 的记忆表示、输入长度和方法指令均有差异，不作单模块因果结论。
4. S1、检索预算调整与留出评价均列为后续方案，不写成已完成实验。开发集现象不写成稳定泛化优势。
5. 第 10 页展示六位成员的工作与“目前大致贡献”，各为 1/6；不再单列比例换算与合计说明。成员沿用 GitHub 账号。

6. 新增第 3 页统一分析框架，将六篇论文按组织、检索、利用、更新与验证联系起来；第 8 页以同一时间案例连接 StructMem、Hindsight 和 MetaMem。该框架是本轮综合分析，未将六套方法描述为已经完整集成。
7. 第 11 页简要说明 GitHub 协作、微信群沟通与线下讨论；已去掉 PR 截图和末页的“谢谢老师”，不另加致谢页。

8. 进展页聚焦已完成产物；S1 消融和留出评价统一按后续研究计划表述。表格前后增加至约 3–4 mm 留白。

## 逐页时间

| 页 | 内容 | 时长 | 累计 |
| --- | --- | --- | --- |
| 1 | 题目与范围 | 15 秒 | 0:15 |
| 2 | 研究问题 | 35 秒 | 0:50 |
| 3 | 六篇论文的系统性提炼 | 60 秒 | 1:50 |
| 4 | StructMem 方法 | 40 秒 | 2:30 |
| 5 | 实验设计 | 40 秒 | 3:10 |
| 6 | 实际进展 | 30 秒 | 3:40 |
| 7 | 结果与输入成本 | 55 秒 | 4:35 |
| 8 | 共同案例与论文视角 | 45 秒 | 5:20 |
| 9 | 创新性论证与后续方案 | 45 秒 | 6:05 |
| 10 | 六人分工与目前大致贡献 | 40 秒 | 6:45 |
| 11 | 小组协作方式 | 50 秒 | 7:35 |
| 12 | 阶段结论与下一步 | 25 秒 | 8:00 |

## 主要依据

以下路径以仓库为根。交接 ZIP 只包含展示文件与源码，不复制原始数据集、完整模型调用或参考答案包。

| 内容 | 仓库依据 |
| --- | --- |
| 老师要求、8 分钟与分工要求 | `docs/course/seminar-notice-20261020.md` |
| 范围、实验设计、后续方案及分工 | `docs/project-plan.md`，2026-10-21 版本 |
| 方法来源和复现差异 | `notes/six-paper-comparison.md`；`papers/structured-memory-group2/01_StructMem.pdf` 第 2–3 页图 2、第 8 页参数 |
| 六篇论文的系统性提炼 | `reports/homework/sections/07-synthesis.tex`；`notes/six-paper-comparison.md`：StructMem 第 2–3 页图 2；Hindsight 第 2–5 页图 1；Semantic XPath 第 2–5 页图 2；MetaMem 第 3–5 页图 2；HyMEM 第 3–5 页图 1；Text2Mem 第 3–5 页图 2 / 表 1 |
| 协作方式 | `docs/collaboration.md`；本轮用户对微信群沟通与线下讨论的说明 |
| 事件记忆规模 | `reports/structmem-development-complete.json`；`reports/structmem-development-receipt-20261020.json` |
| S0/S2 生成、综合与用量 | `reports/s0-answer-summary-20261019.json`；`reports/structmem-real-run-20261020.json`；`reports/seminar-20261022/answer-audit.json` |
| 最新评分与复算 | `reports/e-score-verification-20261021.json`；`reports/e-score-20261020.md`；`reports/e-judge-audit-handoff-20261021.json` |
| 案例与判改 | `reports/e-case-adjudications-20261020.json`；`reports/seminar-20261022/final-audit.md` 中的原文证据核查（不沿用其中旧审核状态） |
| 综合核查的范围 | `reports/structmem-c-review-d-20261021.json` |
| 回答指令差异 | `configs/qa-s0-20261019.json`；`configs/qa-structmem-20261020.json` |

仓库基线为 `6f6a52f`。本轮未调用回答或裁判 API，未新增实验结果。材料完成不表示已经真人排练、录制、上传或确认课程提交格式。
