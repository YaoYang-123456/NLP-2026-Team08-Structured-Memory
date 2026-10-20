# D：真实综合、30 题 S2 回答与 E 交接

负责人：`lanshuheng9-oss`；2026-10-20；关联 [#28](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/28)、[PR #41](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/41)。**91 次真实综合和同一固定 30 题的 S2 回答已完成，E 评分及人工案例验收尚未完成。** 本记录接续[完整事件包验收与离线准备](structmem-development-receipt-20261020.md)，不将早先占位摘要计入本次结果。

## 运行结果

| 范围 | 事件 | 真实综合摘要 |
| --- | ---: | ---: |
| conv-48 | 1277 | 30 |
| conv-42 | 1160 | 29 |
| conv-41 | 1275 | 32 |
| 合计 | 3712 | 91 |

沿用 A 冻结的三个开发会话和同一 30 题；没有运行留出会话。每题实际输入 **60 条事件＋5 条真实综合记忆**。先执行固定 5 题并检查成功状态，再运行其余 25 题；共 30 个独立联合主键，没有重复请求。全部返回 `deepseek-flash`、`finish_reason=stop`，生成失败、截断、自动重试均为 0。其中 4 题为 `I don't know.`，原样保留，不从分母删除。类别 1/2/3/4 分母分别为 8/8/7/7。

| 实际成功请求 | 输入 tokens | 输出 tokens | 总 tokens |
| --- | ---: | ---: | ---: |
| 综合 91 次 | 304025 | 35834 | 339859 |
| 回答 30 次 | 586282 | 178 | 586460 |
| 合计 121 次 | 890307 | 36012 | 926319 |

以上为 API 原始 usage，不是账户账单；未估填实际扣费。C 的 182 次历史抽取与 F 的 S0 回答均不计入本轮。用户在本轮明确要求使用提供的统一凭据执行；凭据只注入临时进程环境，没有写入配置、日志或 Git。

## 固定设置与原生入库

上游 LightMem 固定为 `8449d574df6bae1bdf3314a1564da65e2f37e046`，MiniLM 固定 revision、384 维及归一化约定不变。综合采用 1 小时窗口、15 种子、global、process_all、跨事件上下文；非思考、temperature 0、top_p 1、max_tokens 8192。新增 `scripts/run_structmem_synthesis.py` 使用 F 现有 Client 发送已保存的官方输入，传输超时为 120 秒，首个失败即停止，无自动重试。

F 已在[正式审核](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/41#pullrequestreview-5579766167)中接受原候选；其 [PR #44](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/44) 提交 `14b7b41b561fde1ed5193422ed3084211572e15a` 的 `configs/qa-structmem-20261020.json` 与候选逐字节相同，SHA-256 为 `5c26490902627d5199cd0194fd65b725275efe8844eb07b678daa467ad495abe`。本轮使用该固定副本，回答上限 512、超时 60 秒，公共参数和 S0 模板不变；S1/S2 同提示词。未合并或改写 F 的分支。

模型输出先逐次落盘，再由 `prepare_structmem_synthesis.py --responses` 在每个会话的新进程、新数据库副本中回填原生 `LightMemory.summarize`。**全部 91 组请求与新构建的原生消息逐字核对一致**，回填阶段不再调用模型。该方法保存了中断恢复所需的真实响应，避免为了重新入库重复付费；没有手写摘要 payload 替代原生流程。

原生输出保留事件、摘要的向量和完整 payload。摘要 covered IDs 对所有 3712 事件恰好覆盖一次，seed IDs 均指向同会话事件，正文/来源/事件 ID 未改。与旧验收 JSON 的向量分量最大差约 `1.90e-8`，归一化后的分量差小于 `1e-14`；不声称两个导出逐字节相同。原始接收包的 103 个文件哈希再次全部通过，旧占位目录没有用于真实检索。

## 输出和复跑入口

完整本地目录为 `output/structmem-live-20261020/`：

- `attempt-2/calls.jsonl`、`run.json`：91 次真实综合原始记录。
- `materialized/conv-48-r2`、`conv-42`、`conv-41`：原生私有库、events/summaries JSON、回填核验记录。
- `memory-index.json`、`retrieval30/`：带哈希的真实记忆索引、完整 30 题检索与 provenance。
- `qa5/`、`qa25/`：F 原入口的原始预测、调用和批次记录。
- `handoff-for-E/`：按 A 原始顺序合并的 30 条预测/调用、配置、批次记录及四类来源展示候选。

小型机器证据见 [structmem-real-run-20261020.json](../reports/structmem-real-run-20261020.json)。原始逐题内容、数据库和 ZIP 保留在忽略目录，不提交公开仓库。

若需要重新调用模型，先在本机配置 `DEEPSEEK_API_KEY`，并使用新的输出目录；已有真实成功记录可通过 `--recorded-calls` 校验后复用，不重复发送。以下命令属于付费执行入口，本记录不会自动再次运行：

```powershell
python scripts/run_structmem_synthesis.py --execute `
  --preparation output/structmem-synthesis-preparation-20261020/conv-48-r2 `
  --preparation output/structmem-synthesis-preparation-20261020/conv-42 `
  --preparation output/structmem-synthesis-preparation-20261020/conv-41 `
  --recorded-calls output/structmem-live-20261020/attempt-2/calls.jsonl `
  --out output/structmem-live-recheck
```

单个会话在固定本地模型环境中回填时，使用 `prepare_structmem_synthesis.py` 原来的 bundle/sample-id/upstream/model-path 参数，额外传入 `--responses .../attempt-2/calls.jsonl`，输出必须是新目录。`--responses` 本身不发起模型调用。完整 S2 检索实际使用 `retrieve_structmem.py` 和本次真实 memory-index；问答实际使用 `run_qa.py --execute --method S2`，输入为 smoke5/remaining25 两个互斥子集。

## E 交接与剩余验收

交接包：`output/structmem-live-20261020/s2-predictions-for-E-20261020.zip`，**1,051,426 字节**；SHA-256 `21a6e76a0f097193cdf5bb746dda76008d4237fae8a5d92028dcce1c51c12de6`。CRC 与包内 9 个文件哈希全部通过，没有密钥或标签。用户可发给 E；本次没有代发群消息，不表示 E 已接收或已评分。

E 读取 `predictions30.jsonl`，按 `(sample_id, qa_index)` 关联 A 的同版本标签，统一评分并核查至少 4 个案例。四类展示候选含真实预测及事件/摘要片段，只做来源展示，**没有标准答案判定，不冒称 E 已人工验收**。当前 `accuracy=null`，不与 S0 作准确率排名；S1 仍按原计划研讨后补齐。

实际校验：原 30 项针对性测试和新增付费执行入口 4 项共 **34 项通过**；新增测试覆盖首错停止、不重复付费、输入哈希变化及缓存请求不一致。真实运行又验证了全部原生消息一致、完整事件覆盖、同一 30 题、60＋5 上下文、调用/预测联合主键和成功状态。

首次默认沙箱连接被 WinError 10013 拒绝，未收到服务响应；定位后以已获授权的网络权限执行，成功请求仍为 121 次。第一次原生回填因临时目录变化而缺少 tiktoken 缓存失败；复制已有、官方哈希一致的 o200k 缓存后从新副本完成，没有重复生成。所有失败记录与旧目录保留。

方法限制继续明示：C 关闭压缩/话题切分；实际 Python 3.13 与上游声明 `>=3.10,<3.12` 不同；F 的 JSON 展示与原版双说话人模板有差异。调用成功与数值校验不替代语义评分、人工验收或论文严格复现。
