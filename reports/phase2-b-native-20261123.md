# B 组原生开发集离线联调

2026-11-23 · `YaoYang-123456` · [Issue #71](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/71) · [PR #79](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/79)

B 的 M/N 在冻结开发集原生事件库上完成了 1、5、30 题的预算检查和请求重建。主预算下两组各有 30 份合法上下文，B 与 D 的 M/N 输入、排序指纹及模拟请求内容一致。11 月 4 日的受限首样单独保留。[当时的记录](phase2-b-offline-20261104.md)

## 候选与比较条件

- 每题从所属会话的完整事件库取向量前 120 和 BM25 前 120 的并集。保留原生事件向量，对问题和综合原句使用固定 MiniLM `1110a243` 编码。30 题共有 5,911 个事件候选、1,911 个综合句候选，均按逐题出现次数计。
- 综合来源为每题历史 S2 的原五个父综合。逐题核对原五条的 ID、顺序、完整文本和句位；完整 91 条原生库用于来源核查。选取范围见[共享接口说明](../docs/phase2-b-retrieval.md)。
- `hybrid_rank` 供 M/N/A 共用。BM25 的 `k1=1.2`、`b=0.75`，RRF 的 `k=60`，MMR 的相关性与冗余权重为 `0.7/0.3`，平分按稳定 ID。M 固定原五条完整综合，再用事件 MMR。N 联合选择事件与综合完整句。D 的 A 在 N 的候选和打分上额外保留所需前文，S1 从 A 删除综合块，事件原文和顺序保留。
- 四组使用 main `f658cc7` 的 F 公共渲染、`EvidenceBudget` 和 `configs/qa-phase2.json`。主预算为 4,096 `cl100k_base` 证据 tokens，包含编号、类型、正文、分隔符与省略标记。正式运行费用依赖提供商 usage，本报告仅有证据长度和模拟记录。

## 原生交接与来源

| 件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| [D 原生记忆包](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/blob/11879a0f6c4718f2ed51da8e13bc8eb73b10800b/reports/artifacts/phase2-native-memory-20261123.zip) | 14,690,363 | `1e5efddc3a730375596adb7d099426edac2e26c71aad958dc567db9238aa5955` |
| [D 原生首样和依赖核对包](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/blob/11879a0f6c4718f2ed51da8e13bc8eb73b10800b/reports/artifacts/phase2-d-native-contract-20261123.zip) | 1,337,034 | `e3a0476c1a3b3ad1e5602497948e6ff7bcaa74ff3e2c8923d066bce944f439b6` |

包内 CRC 和 SHA-256 校验通过。六份原生导出与阶段一运行台账匹配，覆盖 `conv-48/42/41` 的 3,712 条事件与 91 条综合。按会话、消息偏移、ID 和说话人逐项核对了事件来源。每条事件被综合覆盖一次，30 题的原五条与 S2 归档逐字相符。原始 91 条生成回复的逐条比对来自 D 的留档，本机复核了历史导出和调用文件的登记哈希以及现有归档文本。[D 交接及复核范围](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/blob/11879a0f6c4718f2ed51da8e13bc8eb73b10800b/reports/phase2-d-native-20261123.md)

B 使用 Windows 本地 PyTorch CPU 2.11.0、sentence-transformers 5.1.2 和 transformers 4.57.1 重建问题及句子向量。相对 D 归档首题，问题向量与句向量元素的最大绝对差分别约为 `6.33e-8` 和 `8.75e-8`，原生事件向量逐值相同，候选 ID 和最终四组首题上下文一致。逐字节确定性结论基于同一候选 bundle。完整 30 题 bundle 的文件 SHA-256 为 `93e8fee1e30af3152c9fd6eecfc32df2d947edd85c621c58f369cff7d60cc01a`。

## B 组结果

| 4,096 主预算 | M 通过题数 | M 平均 / 最大 | N 通过题数 | N 平均 / 最大 | F 模拟请求重建 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 首题 `conv-48/86` | 1/1 | 4,063 / 4,063 | 1/1 | 4,094 / 4,094 | 2/2 |
| 冻结联调子集 | 5/5 | 4,072.00 / 4,091 | 5/5 | 4,091.20 / 4,095 | 10/10 |
| 冻结开发集 | 30/30 | 4,082.50 / 4,096 | 30/30 | 4,092.20 / 4,096 | 60/60 |

30 题 M 共 122,475 tokens（4,058–4,096），N 共 122,766 tokens（4,085–4,096）。各阶段从同一冻结顺序的前缀开始，两次独立 CLI 进程使用不同的 Python 哈希种子。每个阶段的输入、trace、manifest 和 bundle 快照逐字节一致。逐题核对来源、原五条、标签隔离和预算后，用 F 的 `verify_qa_run.py` 从运行快照完整重建 72 条模拟请求。

2,048 档在同一 30 题上复跑 N，范围 2,023–2,048，平均 2,043.70，总计 61,311，30 条模拟请求重建通过。M 的五条原完整综合在 26/30 题已经超预算，4/30 题的固定部分可容纳。完整 M 条件在此档不可行，保留 30 题的可行性统计。两种预算均未生成真实回答，也无新评分或证据支持覆盖结果。

B 与独立 D 检出共享候选及排序哈希，4096 档 M/N 上下文、trace 和逐题请求指纹完全一致，2048 档 N 输入一致。D 的 A 与 N 在主预算下有 25/30 题上下文不同。D 的配对 S1 逐题保留从 A 删除综合后的事件数组。依赖缺口的统计仅对应规则闭包，C/E 仍需复核 315 条原型依赖的必要性。来源追溯记录原消息链接，语义蕴含需另行核对。[PR #80 的独立审核](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/80#pullrequestreview-6020280521)

## 复跑及交接

1. 使用冻结的 `development.inputs.json` 和 `smoke.inputs.json`。取上面的 D 原生记忆包，在含 main `f658cc7`、B `7126895` 和 D `11879a0` 的隔离检出上解包校验。复用本地固定模型和分词器缓存。[冻结数据说明](../docs/locomo-data-environment.md)
2. 用 D 的 `prepare_d_candidates.py --memory-index <解包>/memory-index.json --questions <开发题单>/development.inputs.json --model-cache <缓存> --out output/dev-native` 准备 30 题共同 bundle。按文件顺序取前 1 或 5 行即可检查子集，保留原行字节及换行。这两个子集使用 `smoke.inputs.json` 校验，30 题使用 `development.inputs.json`。
3. 在 B 分支运行 `python scripts/run_mn.py --bundle <bundle.jsonl> --questions <冻结题单> --tokenizer-cache <缓存> --out <新目录>`。M/N 分别交给 F 的 `run_qa.py --mock --method S2 --variant M` 或 `N`，再用 `verify_qa_run.py` 核验。运行命令与字段详见[接口说明](../docs/phase2-b-retrieval.md)。
4. 2,048 档从约束一致的 4,096 运行读取同候选，并使用 `EvidenceBudget(2048,...)` 调 B 的 N 选择器。本轮为 N 的 QA 单独复制 F 配置并只改证据预算。四组联合核查可用 D 的 `run_d_budget_ablation.py`。M 先计所有题的原五条，超额题保留，分母固定。[D 预算对照入口](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/blob/11879a0f6c4718f2ed51da8e13bc8eb73b10800b/docs/phase2-d-packing.md)
5. 运行检查时设置 `QA_TOKENIZER_CACHE` 指向本地词表缓存。B 的 54 项测试含原 S0 8 项、StructMem 12 项、QA 23 项及共享排序 11 项，均通过。D 交叉审核含同一组和 D 自有检查，共 67 项通过。两个环境均为 0 失败、0 跳过。F 的原始单题在 Windows 也通过官方核验。

附[机器可读汇总和输入指纹](phase2-b-native-20261123.json)，共 11,259 字节，SHA-256 为 `2b6c75b966ed6a623acf335aea70eecd685057b0669d200b431250ec41b40cdc`。运行快照、`run.json`、完整 trace 及 30 题 bundle 存于 NLP 项目本地忽略目录 `tmp/phase2-native-verification-20261123/`。真实回答、裁判、学校服务和记忆构建请求均为 0，费用为 0。后续由 C/E 冻结依赖，D 合入 A/S1，E 修订 #84 的题单、裁判原文与请求次数绑定，F 登记真实请求和费用后再取得授权。留出集仍按 A 的冻结流程独立处理。
