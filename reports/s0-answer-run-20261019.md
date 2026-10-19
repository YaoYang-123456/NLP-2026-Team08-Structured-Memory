# F：S0 固定 30 题真实回答与 E 交接

负责人：hycx233（[#19](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/19)）；2026-10-19。**30/30 题真实回答完成，评分与人工核查待 onlysonder（E / #31）。** 本文记录生成结果，不给出准确率。

## 输入、审核与固定配置

审核 B 的 [PR #37](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/37) 固定提交 `62410cd`，已提交批准；未发现阻塞 F 接入的问题。附件输入 SHA-256 为 `17237f37ca5a6bcf867b4aead8b73eec88cf6c5dc86189c1e1bbf317381faac5`，与 B 的运行记录一致。F 的 [PR #35](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/35) 经 B 审核批准后已合并，回答代码仍为 `4206096`。

使用 A [PR #38](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/38) `1d651da` 的固定原始版本与 3/7 会话划分，重新生成的文件 SHA-256 全部一致。30 道题的原始联合主键、问题、题型与 A 相同，四类题数为 8/8/7/7；全部 1800 个检索上下文与固定开发会话重建的原始块逐条相同，来源、时间、说话人和 BLIP 描述完整。标准答案及 evidence 标注没有进入回答输入或提示词。

[本次固定配置](../configs/qa-s0-20261019.json) 与已审核的示例配置逐字节相同，本次仅将其中 **S0** 设置冻结用于真实运行；S1/S2 的示例提示词未用于实验。请求 `deepseek-flash`，`thinking.type=disabled`、temperature 0、top_p 1、最大输出 512 tokens、单次超时 60 秒，不重试。配置内容哈希为 `42ae848bd919065e0faf62b0f357e3a1bd620cba5ad9d35786e958b36a8fd421`。

本轮预算设为 5 元。首次请求前按全部提示词 UTF-8 字节数、每题额外 256 framing tokens、每题最大输出及无缓存高峰价作保守量级估算，为 1.041286 元；此估算没有当作实际账单。运行中按真实 usage 复核。

## 实际运行

从原始 30 行取前 5 行和剩余 25 行，各执行一次；前 5 题全部成功且预算充足后才继续，没有将 30 行再次全量提交。

```sh
python3 scripts/run_qa.py --execute --method S0 \
    --input data/locomo/s0-retrieval-20261019/first5.inputs.jsonl \
    --config configs/qa-s0-20261019.json --out output/s0-answer-20261019/first5
python3 scripts/run_qa.py --execute --method S0 \
    --input data/locomo/s0-retrieval-20261019/remaining25.inputs.jsonl \
    --config configs/qa-s0-20261019.json --out output/s0-answer-20261019/remaining25
```

调用使用项目进程环境中的 `DEEPSEEK_API_KEY`，不读取其他项目配置。密钥不进入 Git、日志或交接包。上述输出目录已有产物，入口会拒绝覆盖；不要为重复已有结果而新建输出目录重跑。

| 项目 | 真实结果 |
| --- | --- |
| 预定/独立题数 | 30 / 30 |
| 两阶段请求数 | 5 + 25 = 30，无重试或重复 |
| 成功 / 失败 / 模拟 | 30 / 0 / 0 |
| 自然结束 / 截断 | 30 stop / 0 |
| 输入 tokens | 132,531，缓存命中 0、未命中 132,531 |
| 输出 tokens | 421 |
| 总 tokens | 132,952 |
| 调用耗时之和 | 30.449 秒；不包含阶段间核验和材料整理 |
| 自动评分 / 人工核查 | 0 / 0，准确率尚无 |

请求从北京时间 16:09:27 开始，剩余 25 题于 16:10 左右完成，具体时间见[机器可读汇总](s0-answer-summary-20261019.json)。API 返回的模型名均为 `deepseek-flash`，没有返回更具体的 checkpoint 名；官方当日模型说明将该别名映射至 DeepSeek-V4.1-Flash-1017，不能将文档映射当作响应中观测到的版本。

当日为周一，本次调用处于北京时间 14:00–18:00 高峰段。按[官方价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)的每百万 tokens 缓存命中 0.04 元、未命中 2 元、输出 8 元计算：`132531 × 2 / 10^6 + 421 × 8 / 10^6 = 0.26843 元`。这是依据实际 usage 的估算，未核对账户账单，不是发票或已确认扣款。

## 未判分的实际回答示例

以下仅展示模型原始预测，不据此判断对错，也没有读取标准答案来调整配置：

- `conv-42/15`：When did Nate get purple hair?
  - 实际预测：Nate dyed his hair purple in the week before 15 April 2022 (he mentioned it on 15 April 2022, saying he dyed it "last week").

- `conv-41/41`：Does John live close to a beach or the mountains?
  - 实际预测：I don't know.

## 验证范围与给 E 的交接

本机执行 A/B/F 的 7+8+14=29 项针对性测试全部通过，包含真实固定数据重新生成；已完成附件哈希、30 题联合主键、1800 个来源块、跨批次相同配置/代码、状态、原始 usage、无思考响应及无重复的核验。此次没有重新加载 MiniLM 或重新执行真实向量检索，相关运行证据仍来自 B。没有运行旧 MetaMem 实验。

根目录 `output/s0-answer-20261019/predictions.jsonl`、`calls.jsonl` 按原 30 题顺序合并；`first5/`、`remaining25/` 保留原始批次。它们仍在忽略目录，未提交 Git。交接包包含合并结果、两个原始批次、S0 检索输入、固定回答配置、A 的冻结清单、逐文件 SHA-256 清单和说明，不含标准答案或密钥。

- 接收人：**onlysonder（E / #31）**。按 `(method, sample_id, qa_index)` 关联 A 的标签，先核对全量题集哈希 `99ebf28b673b715886b13d8f88768cc82b1775033b37d59ffae0893b285c0a26`。
- 包名：`s0-predictions-for-E-20261019.zip`，662,513 字节。
- ZIP SHA-256：`62a7f1da68590f7b80f2a753e1c60307a22620b84d0d6c81b92177500d19a3aa`；ZIP CRC 和每个归档文件的 SHA-256 均通过。
- 当前交接状态：**本地包已准备，微信群转交日期仍为空**。公开仓库仅保留本记录、配置及汇总，不把“包已生成”写成 E 已收到或已评分。

E 后续提供总体及分类正确数/总数、评分覆盖率、失败计数、原始裁判记录和至少 4 个代表案例核查。`#19` 的真实“检索→回答→评分”验收及研讨材料合并仍未完成，不能因生成 30 条预测就关闭任务。
