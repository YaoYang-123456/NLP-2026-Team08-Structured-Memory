# D：完整开发事件记忆接收与下一阶段准备

负责人：`lanshuheng9-oss`；2026-10-20；关联 [#28](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/28)。C 完整事件包已实际接收并独立验收，**不再缺开发会话事件记忆**。当前完成了真实事件检索和官方综合入口的离线预演，尚无真实跨事件综合或 S2 回答、评分。

## 1. 收到的版本与实际验收

原包 `complete-handoff-20261019.zip`：7,895,794 字节，SHA-256 `8c26e24fa7be2e6b19dbec91f3647d563e1145e909866e939f1b2b4e70427885`。用户同时提供的 `structmem-development-complete.json` 与包内 `run-record.json` 内容一致。保留 ZIP 位于 `data/structmem-received/`，解压原件位于 `output/structmem-development-receive-20261020/complete-handoff/`。

已验证 ZIP CRC、103 个声明文件的 SHA-256；只打开 D 的新数据库副本，验证结束后原件所有哈希仍一致。三个库实际读回如下：

| 会话 / collection | session | 输入消息 | 事实 | 关系 | 事件总数 | 被记忆引用的消息 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| conv-48 / conv_48_events | 30 | 681 | 799 | 478 | 1277 | 664 |
| conv-42 / conv_42_events | 29 | 629 | 733 | 427 | 1160 | 612 |
| conv-41 / conv_41_events | 32 | 663 | 777 | 498 | 1275 | 660 |
| 合计 | 91 | 1973 | 2309 | 1403 | 3712 | 1936 |

全部 91 份 session 输入的正文、已有图片描述、说话人、消息 ID 与原始会话时间均与 A 冻结文件一致；3712 条事件的来源索引及绑定时间均匹配。37 条输入消息没有直接对应的记忆条目，不能说成“37 条未处理”，也不把这个来源统计当作正式准确率或召回率。

所有向量均为有限、归一化的 384 维向量，所有 `consolidated` 标志均为 false。用固定 MiniLM、CPU、batch size 64 重算全部 3712 条记忆向量，最大分量绝对差 `1.8998980522155762e-07`，小于验收阈值 `2e-5`。本轮读回后自行导出了 JSON；原包没有全量 JSON 导出，因此没有声称与未收到的逐 session 原始导出逐字节比较。

## 2. 固定 30 题的真实事件检索

沿用 A 的同一 30 题及其中 5 题，问题文本、顺序和原始联合主键不变，不加载标签。每题从所属会话的真实事件库取 60 条，保留记忆 UUID、原消息 `source_key`、说话人及时间。

- 30 题返回 ID 集合与 Qdrant 均一致；29 题顺序完全相同，1 题只存在等分条目的顺序差异。最大分数差 `4.44e-16`。收到的库包含重复记忆文本，因此对照允许等分 ID 排列变化，但拒绝非等分错序、错误分数和缺失结果。
- `event-retrieval30.jsonl` 与 `event-retrieval5.jsonl` 已实际生成；**每题目前只有 60 条事件，没有 5 条真实综合记忆**，不能命名为完整 S2 输入。
- 已用 F 的正式入口、示例配置执行 30 行 `--mock`：30 simulated、真实成功回答 0；这只验证读取接口。

本地完整结果位于 `output/structmem-development-acceptance-20261020/`，包括原生事件导出、逐题 provenance、真实事件检索 JSONL 和模拟记录。小型证据见 [验收 JSON](../reports/structmem-development-receipt-20261020.json)。不把逐题原始数据加入 Git。

## 3. 官方综合入口已做离线预演

新增 `scripts/prepare_structmem_synthesis.py`，调用固定上游 `LightMemory.summarize`，不是另写综合算法。每个会话在新进程和独立副本中运行，保持 1 小时窗口、15 个种子、global、process_all。现有完整事件记忆不做重抽取；预演沿用 C 的关闭压缩和话题切分配置，差异继续明确记录。

| 会话 | 实际原生窗口 / 待调用输入 | 被覆盖事件 |
| --- | ---: | ---: |
| conv-48 | 30 | 1277 |
| conv-42 | 29 | 1160 |
| conv-41 | 32 | 1275 |
| 合计 | 91 | 3712 |

程序拦截生成回调，记录真实官方输入后，仅返回 `SYNTHETIC OFFLINE PLACEHOLDER`。HTTPX 发送方法被显式阻断，实际生成 API 请求为 0、usage 为 null。原生代码生成并入库的 91 条摘要都是**占位摘要**，存放在 `SYNTHETIC-summaries` 目录；不能当作模型结果，不能用于正式检索，也不能从其已标记 consolidated 的副本恢复真实运行。

本地调用提案为各目录的 `proposed-calls.jsonl`，包含模型、官方消息和候选生成参数：deepseek-flash、非思考、temperature 0、top_p 1、max_tokens 8192。它们是待审核的调用输入，不是已发送请求。本机没有项目 `DEEPSEEK_API_KEY`，也没有 `.env`；本轮付费额度尚未确认。真正综合时应从未修改的接收原件重新复制数据库，并使用已批准的调用设置。

输出根目录：`output/structmem-synthesis-preparation-20261020/`，其中 conv-48 成功目录为 `conv-48-r2`。第一次初始化因现有 SOCKS 代理缺少 `socksio` 失败，未发生成请求；在隔离环境补齐 socksio 1.0.0 后从新副本运行成功，原失败目录保留。

本轮新增 openai 2.3.0、tiktoken 0.12.0 以导入原生 LightMemory；未下载新模型。实际环境仍为 Python 3.13.9 / CPU PyTorch 2.11.0。上游声明 Python `>=3.10,<3.12`，本次原生导入和离线窗口执行通过，不声称与上游声明环境完全一致。

## 4. 回答提示词候选与待核对项

新增 [qa-structmem-candidate.json](../configs/qa-structmem-candidate.json)，基于 F 在 PR #42 使用的配置（提交 `49d8a6762cb7c51ae9b3f9ebdbcd1d8ead23e76d`）。保留其公共 system 指令、模型、回答 max_tokens 512、温度、top_p、超时和 S0 模板；S1、S2 使用**完全相同**的方法模板，避免后续消融同时改变提示词。

候选依据固定版 [StructMem 回答提示词](https://github.com/zjunlp/LightMem/blob/8449d574df6bae1bdf3314a1564da65e2f37e046/experiments/locomo/prompts.py) 中的时间推理、说话人区分及简短回答要求，按 F 的 JSON 上下文契约重新表述；不逐字复刻双说话人分组布局，也不要求在最终答案中输出推理过程。S0 与 StructMem 的方法指令仍有差异，不能把系统对照的全部差异单独归因事件绑定。

候选已通过 F 配置校验和 5 行 `--mock`，实际回答 0。仍需 F 负责人核对并冻结，不能把文件名 candidate 改成“已统一”来代替审核。真实综合与回答需要同一项目凭据、明确本次调用额度，以及最终生成配置；密钥应放在本机进程环境，不贴到聊天或提交到 Git。

## 5. 复跑与当前边界

完整接收验收及事件检索（输出目录必须是新的）：

```powershell
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
tmp/structmem-receive-venv/Scripts/python.exe scripts/verify_structmem_development.py `
  --bundle output/structmem-development-receive-20261020/complete-handoff `
  --frozen-config tmp/structmem-d-deps/a/configs/locomo-smoke.json `
  --out output/structmem-development-recheck
```

原生综合离线预演，三个会话各启动一次，使用各自的新输出目录：

```powershell
tmp/structmem-receive-venv/Scripts/python.exe scripts/prepare_structmem_synthesis.py `
  --bundle output/structmem-development-receive-20261020/complete-handoff `
  --sample-id conv-48 --upstream tmp/LightMem `
  --model-path data/model-cache/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/1110a243fdf4706b3f48f1d95db1a4f5529b4d41 `
  --out output/structmem-synthesis-recheck/conv-48
```

D 检索 12 项、完整验收/候选 4 项、F 14 项针对性测试共 30 项通过。当前真实事件读取、向量重算及检索已完成；真实跨事件综合、S2 回答和评分均为 0，准确率为 null。C 的 182 次历史抽取成功请求属于其既有构建，不计作 D 本轮调用。接收与数值一致也不代表全部抽取语义已人工验收。
