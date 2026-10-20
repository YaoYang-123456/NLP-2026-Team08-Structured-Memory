# 第一次研讨：当前候选与保留的历史草稿

本轮恢复材料制作，按 10 月 21 日前可展示准备。**PR #48的F技术审核已通过并合并；全组署名、贡献比例、真人视频及上传仍未确认。** 2026-10-21新增[评分复算验收](../e-score-verification-20261021.json)，幻灯片保留生成时快照，正式使用前应同步其中“尚待复算”的状态文字。 旧六页及原说明保留在 [历史说明](README-before-final-20261020.md)，其中“暂缓”和旧分数不是当前入口。

1. 打开 [可编辑 PPTX](final-candidate.pptx) 或 [PDF 预览](final-candidate-preview.pdf)：9 页正文、2 页备用。
2. 使用 [逐页讲稿](script-8min.md) 与 [答辩参考](questions-and-answers.md)。
3. 检查 [一页交接](handoff-checklist.md)、[验收报告](final-audit.md)、[来源索引](source-index.md)。

正文源：[统一内容 JSON](seminar-content.json)、[Beamer 源](final-candidate.tex)。PPTX 含可编辑表格、图表、备注；PDF 为 PPTX 渲染预览。PR #48最终修正的Beamer源已由F隔离编译并检查11页，无缺字或溢出；#49补了离线回归测试。所有真实结果均注明证据层次；原始 16/30 与复核 15/30 分开。

视频是每组要求，**主讲、录制和上传未核实分配，不自动归于 B**。本地合成样片只供审阅计时，不是组员录音，不由本代理提交。全部成员实际贡献比例与人工验收字段保持待确认。

## 再制作与离线复核

`tools/build_deck.mjs` 使用 @oai/artifact-tool 和 Codex presentation validators，需要本机已安装的对应运行时；调用参数为仓库根及新输出目录。`tools/make_pdf_tex.py 输出目录` 生成同版预览及 Beamer 源。修改内容后应重新渲染核查，不能只改幻灯片数值。

`tools/narrate.ps1 -ContentPath seminar-content.json -OutDir 新音频目录` 使用 Windows 离线 Microsoft Huihui Desktop；`tools/build_video.py --help` 为本地合成样片。标准 FFmpeg 解码核验方法见交接说明。没有安装或调用额外模型 API。

`tools/verify_handoffs.py --s0-dir 解压S0目录 --s2-dir 解压S2目录 --selection 固定30题清单 --out 新核验JSON` 验证真实回答包，与评分复算是不同工作。原始数据/回答缓存/视频不纳入此目录。
