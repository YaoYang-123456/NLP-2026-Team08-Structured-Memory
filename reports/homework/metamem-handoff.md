# MetaMem 个人模块交接（2026-10-26）

> 演示于2026-10-27统一修订文字和样式，已移除文献脚注与灰色旁注。当前个人PDF及全组68页演示的大小、哈希与源码见[演示清单](slides/style-artifacts.json)，验证见[修订记录](slides/style-check-20261027.md)。下文原核查过程和旧版估时保留为历史记录，录制前按新稿重新计时。

负责人：`YaoYang-123456`；关联 [Issue #39](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/39)。本轮从 main `1850da7` 核查，保留 [PR #40](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/40) 已审核章节及此前个人材料；不关闭 #39，不代表本人阅读、试讲或录制完成。

## F 的直接读取入口

- 共享阅读章节：[`sections/05-metamem.tex`](sections/05-metamem.tex)，本轮核对后无须实质修改；SHA-256 为 `622f4c9cd876bb6fba395583aad42022db3f9df0ab763a9a74a3d64257f6fecf`，与任务起点一致。
- 共享演示：[`slides/sections/05-metamem.tex`](slides/sections/05-metamem.tex)，章节页＋7页正文，共8页；[`slides/metamem-preview.pdf`](slides/metamem-preview.pdf) 为本轮编译并修复中文映射后的个人预览。
- 全组合稿的完整口语稿：[`scripts/05-metamem-8min.md`](scripts/05-metamem-8min.md)。正文逐页对应共享 `\note{}`，包含显示重点、翻页位置、预计时间和累计时间。
- 独立报告预览：[`metamem-reading-report.pdf`](metamem-reading-report.pdf)，2页，直接读取相同共享章节；不另维护平行正文。
- 内容及时间源：[`metamem-content.json`](metamem-content.json)；来源、核查与文件哈希：[`metamem-artifacts.json`](metamem-artifacts.json)。公开材料只使用 GitHub 账号。

## 8分钟与10分钟的关系

两种稿件沿用同一套8页主题。核心版按每分钟255个等效中文音节，并加入标点及翻页停顿，估计 **7分59秒**；完整稿增加公式之间的联系、规则编号与冲突、验证边界、分项退步及成本解释，估计 **10分05秒**。语速范围与逐页计算保留在内容 JSON 中。二者均未进行本人朗读计时或合成语音计时。

| 页 | 主题 | 10分钟版的额外解释 |
|---|---|---|
| 1 | MetaMem | 与核心版相同 |
| 2 | 旅行计数与包含关系 | 与核心版相同 |
| 3 | M/E及回答公式 | 与核心版相同 |
| 4 | 候选回答、评价、反思与更新 | 式(6)–(10)的衔接；代码混合正误筛选与论文公式的区别 |
| 5 | 一次规则编辑 | 空集合先ADD；已有编号才能MOD/DEL；冲突处理 |
| 6 | 设置与数据隔离 | 标准答案边界；训练/测试生成参数分别记录 |
| 7 | 主结果与消融 | Llama偏好退步；不凭微小差异声称显著性 |
| 8 | 局限及StructMem联系 | Table 4在线成本与完整学习成本的区别 |

个人可编辑 PPTX 与同版 PowerPoint 导出 PDF、两份完整中文稿保留本地，使用用户确认的本人署名；共享 Beamer 仍是全组合稿正式入口。个人 PDF/PPTX 使用同样页序，但保留原有原生图表和更适合录屏的字号，不声称与 Beamer 逐像素相同。原13页个人版本完整保留，新版从其对象和内容复用整理。

## 原文核查结论

论文 PDF SHA-256 与来源清单一致：`d51f68adc7fd535a0fc23adfaa1ea8aa65aa448b22a5112128957df257a424c6`。已对照原文方法、主要表格及对应页面：

- p.1 Figure 1：1800＋1200＝3000，300为已包含部分。
- p.3 式(1)–(3)：事实记忆M、元记忆E及学习/回答输入；p.4–5 Figure 2、式(4)–(10)：采样、反馈、反思、提案、过滤、执行。
- p.5 §4、p.11 A.3/A.5：模型、top-k20、5轮/50题/5次采样、350/50/100的五折用途。350/50与正文400构建数据不矛盾。
- p.6 Table 1：Qwen 67.50→71.90，Llama 66.17→69.08，分别为4.40和2.91个百分点；不把摘要“3.6%”套成所有模型都提高3.6个百分点。
- p.7 Table 2：Qwen完整71.90、无反思70.02、无演化68.33；无反思仍可由原始回答生成编辑。
- p.11 Table 4：LightMem在线Qwen 17.59→19.87秒、Llama 11.23→14.86秒，不覆盖完整离线规则学习成本。

保留原文自身的口径问题：Table 1的Qwen LightMem Avg.为67.50，而p.12 Table 5展示的五个折Avg.均值为65.86；本模块按主表原值引用，不擅自“修正”作者结果。平均提升也不保证所有题型受益。规则示例明确标为教学构造，本组简化试点与论文主实验、团队LoCoMo对照分开。

## 实际验证与已知提示

使用便携 **Tectonic 0.17.0（XeTeX）**：个人报告2页、MetaMem模块8页、当前全组报告14页、接入后的全组演示64页均编译成功。未改共享主文件、全局模板、其他五篇或共同总结。个人模块无Overfull/Underfull、缺字或未定义引用；全组报告有原StructMem/Hindsight的两项Underfull，以及algorithm/algorithmic依赖的UTF-8提示和Fontconfig提示，不能写成零警告。

个人PPTX已用PowerPoint 16.0实际打开、导出PDF、逐页导出PNG并重新打开；8页备注含核心/扩展稿，无原生文字高度溢出候选，1个原生图表和6张原生表格可编辑。包结构检查通过。Artifact Tool导入旧PPTX失败（`Format_InvalidStringWithValue -2068027336`），因此保留原Office对象编辑并用Office核验，没有把导入失败当成通过。

两份MetaMem编译PDF确有Fandol/Adobe-GB1缺失ToUnicode，已用 [`metamem-assets/embed-cmap.py`](metamem-assets/embed-cmap.py) 仅补缺失映射，未改变共享字体或模板。资源 [`Adobe-GB1-UCS2`](metamem-assets/Adobe-GB1-UCS2) 来自捆绑Poppler的Adobe CMap资源，版本9.000、Copyright 1990–2020 Adobe，文件自带完整再分发许可，来源见[Adobe仓库](https://github.com/adobe-type-tools/cmap-resources)。PDF.js不设置外部cMapUrl，报告2页、共享8页及个人8页均正常渲染和提取中文；两份修复PDF在PDFium中与修复前逐像素一致。全部个人页已目视检查。

原始PDF、编译缓存和详细检查图留本地output/handoff。没有录制视频、访问麦克风/摄像头、运行新模型实验或上传课程平台。

## 复编译与导出

已有XeLaTeX/latexmk可按仓库原方法编译。以下是本轮实际采用的Tectonic调用（从仓库根目录执行，先创建输出目录）：

```powershell
tectonic reports/homework/metamem-preview.tex -Z search-path=reports/templates/jos --outdir output/metamem-report --keep-logs --keep-intermediates
tectonic reports/homework/slides/metamem-preview.tex --outdir output/metamem-slides --keep-logs --keep-intermediates
python reports/homework/metamem-assets/embed-cmap.py output/metamem-report/metamem-preview.pdf output/metamem-report/metamem-reading-report-mapped.pdf
python reports/homework/metamem-assets/embed-cmap.py output/metamem-slides/metamem-preview.pdf output/metamem-slides/metamem-preview-mapped.pdf
```

映射脚本拒绝覆盖既存目标，也不会猜测其他CID编码；导出后应再次渲染检查。公共预览同步使用mapped版本。完整组稿的字体兼容策略由F统一确认，本轮没有替换全组preview.pdf。

## 仍需本人及F完成

本人过稿、按实际语速排练、确认个人署名，并另行录制和交接；这些事项仍在#39，不关闭。F核对8页的衔接与整体约60分钟安排，保留每人7–9分钟及共同总结的既定节奏。老师通知以DOCX/PPT为例并写“其他扩展名也可以”，仓库采用LaTeX/PDF；最终接收格式仍由F整合时确认。本轮不代全组决定格式或贡献比例。

[PR #58](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/58) 正在更新两份README的全组进度；本轮不重复改这两份文件，避免覆盖F的相邻更新，整合时可将MetaMem入口指向本页。最终审核指定F `hycx233`，重点为论文证据、讲稿与共享页序、PDF中文兼容及全组接入，不以素材技术完成代替本人验收。
