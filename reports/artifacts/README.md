# 交接包索引

这里存放小组各阶段小于 20 MB、且不含密钥与标准答案的公共交接包，方便成员直接下载联调和复算。

## F阶段二接口首样：2026-11-03

- **文件**：[phase2-f-contract-20261103.zip](phase2-f-contract-20261103.zip)（8,272 字节）
- **SHA-256**：`7b879b26baf6e50077906c71e8a65ed448a63ce5519b61eeb9898f358e20b84`
- **内容**：`input.jsonl`、`expected.json`、`README.md`。
- **用途**：给 B / D / E 做阶段二公共预算与请求绑定的单题联调样例。输入取自开发集第 1 题（`conv-48 / qa_index=86`）的早期 `anchor_2048` 上下文（无答案标签），不是正式 4,096 实验结果。
- **使用方式**：解压和 mock 核验命令见 [F 接口说明](../../docs/qa-integration.md#阶段二公共预算与请求契约)；离线验证记录见 [phase2-f-offline-20261103.md](../phase2-f-offline-20261103.md)。

## S0 预测交接包（阶段一）：2026-10-19

- **文件**：[s0-predictions-for-E-20261019.zip](s0-predictions-for-E-20261019.zip)（662,513 字节）
- **SHA-256**：`62a7f1da68590f7b80f2a753e1c60307a22620b84d0d6c81b92177500d19a3aa`
- **入口与说明**：解压后读取根目录 `predictions.jsonl`；运行记录见 [s0-answer-run-20261019.md](../s0-answer-run-20261019.md)。E 已在 PR #42 核验并批准该交接包。

## E 逐题评分交接（阶段一）：2026-10-21

PR #46 提交的[60 条逐题裁判交接](../e-judge-audit-handoff-20261021.json)已由 F 核对输入哈希并复算一致（见[复算记录](../e-score-verification-20261021.json)）：原始自动判分为 S0 16/30、S2 19/30，日期题人工裁定后为 S0 15/30、S2 19/30。不含标准答案或带答案的原始请求。

## S2 预测交接包（阶段一）：2026-10-20

由 D（`lanshuheng9-oss`）通过微信群发送，F（`hycx233`）核验后原样入库（关联 [PR #41](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/41)、[PR #44](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/44)）。

- **文件**：[s2-predictions-for-E-20261020.zip](s2-predictions-for-E-20261020.zip)（1,051,426 字节）
- **SHA-256**：`21a6e76a0f097193cdf5bb746dda76008d4237fae8a5d92028dcce1c51c12de6`
- **核验记录**：[s2-handoff-verification-20261020.json](../s2-handoff-verification-20261020.json)（CRC、9 个文件哈希、30 题 5+25 批次、每题 60 事件 + 5 综合、请求/响应/用量与 4 次弃答均一致）。

包内主要文件：

| 文件 | 用途 |
| --- | --- |
| `predictions30.jsonl` | E 的评分入口，30 题完整预测与上下文 |
| `calls30.jsonl` | 30 条回答请求、响应及 `usage` |
| `qa-structmem-20261020.json` | 冻结回答配置（与 F 仓库配置一致） |
| `qa5.run.json` / `qa25.run.json` | 5 题与 25 题批次记录 |
| `retrieval.run.json` | 60+5 检索及记忆索引哈希 |
| `synthesis.run.json` | 91 次综合运行汇总（不含原始综合响应正文） |
| `case-candidates.json` | 四类题来源展示样例 |
| `README.md` / `files.sha256.json` | 打包时说明及 9 文件哈希表 |

说明：E 解压后读取 `predictions30.jsonl`，按 `(sample_id, qa_index)` 关联本地同版本标准答案评分（总分母 30，四类题 8/8/7/7，保留弃答与失败题）。包内 README 写的是打包当下的交接状态，实际已确认入库；完整的原生数据库和 91 条原始综合响应留在 D 本地。
