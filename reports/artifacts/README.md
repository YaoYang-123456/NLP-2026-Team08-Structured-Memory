# 评分交接包

## S0：2026-10-19

- 文件：[s0-predictions-for-E-20261019.zip](s0-predictions-for-E-20261019.zip)，662,513字节。
- SHA-256：`62a7f1da68590f7b80f2a753e1c60307a22620b84d0d6c81b92177500d19a3aa`。
- 读取入口：ZIP根目录的`predictions.jsonl`；运行信息见[运行记录](../s0-answer-run-20261019.md)。E已在PR #42批准CRC、16文件哈希、30题和用量交接。

## E逐题评分：2026-10-21

PR #46的[60条最小裁判交接](../e-judge-audit-handoff-20261021.json)已由F逐条核对冻结输入指纹并复算，见[验收记录](../e-score-verification-20261021.json)。原始S0 16/30、S2 19/30，日期裁定后15/30、19/30；至少4例成员本人核查仍待确认。不公开完整标签或带参考答案的请求。

## S2：2026-10-20

D（lanshuheng9-oss）已通过微信发送，F（hycx233）下载后完成以下核验并将原包入库；关联 [PR #41](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/41)、[F 材料 PR #44](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/44)。不要求 D 重复发送，也不将此前“仓库没有包”记作“D 未交付”。

- 文件：[s2-predictions-for-E-20261020.zip](s2-predictions-for-E-20261020.zip)
- 大小：1,051,426 字节。
- SHA-256：`21a6e76a0f097193cdf5bb746dda76008d4237fae8a5d92028dcce1c51c12de6`，与 D 提交的记录一致；ZIP 原字节保留。
- F 核验：[s2-handoff-verification-20261020.json](../s2-handoff-verification-20261020.json)。CRC 与包内9个文件哈希通过；同一固定30题、5＋25互斥批次、每题60事件＋5综合、冻结配置及全部请求重建一致；预测与原始响应/用量逐条对应，4次弃答保留。

包内清单：

| 文件 | 用途 |
| --- | --- |
| predictions30.jsonl | E 的评分入口，30题完整预测与上下文 |
| calls30.jsonl | 30条原始回答请求、响应及 usage |
| qa-structmem-20261020.json | 冻结回答配置，与 F 配置逐字节相同 |
| qa5.run.json / qa25.run.json | 原始5题与25题批次记录和指纹 |
| retrieval.run.json | 固定数据、60＋5检索及记忆索引哈希 |
| synthesis.run.json | 91次综合的运行汇总；不含91条原始综合调用 |
| case-candidates.json | 四类来源展示候选，尚非 E 人工验收结论 |
| README.md / files.sha256.json | D 原始说明及9文件哈希表 |

E（onlysonder / #31）将包解压到本地新目录，读取 predictions30.jsonl，按 `(sample_id, qa_index)` 关联 A 同版本 labels；标签不加入回答输入或本仓库。固定分母30、分类8/8/7/7，保留弃答与服务失败状态。S0 评分交接仍见 [PR #42](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/42)，两个方法使用同一题单及评分口径。

包内 README 关于“由用户转发、未送达”的文字是打包时快照，以此处已微信接收并入库的状态为准。没有重打包或修改历史记录。包内不含密钥、标准答案标签或 Qdrant 原库；完整原生数据库与91条原始综合调用仍由 D 保存在本地，本次没有独立回放这些文件。E逐题评分及F复算已完成；至少4例成员本人语义核查仍待确认，来源对应核验不替代该项人工验收。新增真实 API 请求为0。
