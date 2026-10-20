# C：A 的完整开发会话接入

负责人 oioioi-521，技术任务 #32。依赖 [A 的 PR #38](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/38)，本轮核对提交 `1d651da44cd1bf101ead69794a74f45f91c507a3`，没有合并该 PR。

## 输入与完整性

抽取只打开 `development.conversations.json`，按 A 的冻结配置核对整个文件的 SHA-256。数据准备由 A 的脚本独立完成；C 不打开原始数据、题目文件、标签、答案、evidence、observation 或预生成总结。冻结配置只用于核对版本、会话名单和文件哈希。

三个会话分别包含：

| 会话 | session 数 | 消息数 |
| --- | --- | --- |
| conv-48 | 30 | 681 |
| conv-42 | 29 | 629 |
| conv-41 | 32 | 663 |
| 合计 | 91 | 1973 |

全部 session 按数字顺序处理，不按 30 道题裁剪记忆。保留原始时间字符串、说话人、原消息 ID，以及上游格式的图片描述。时间解析只为上游绑定产生数值；没有时区转换，原文随输入保存。

消息主键保留为 `(source_sample_id, source_message_id)`，并生成 `source_key=conv-48/D1:1` 等组合标识。相同 dia_id 可以出现在不同会话，不能在同一会话重复。每个 session 有独立构建检查点；完成后再合并为所属会话的独立数据库，不把三个会话混在一起。

## 构建配置的实际差异

上游继续固定 `8449d574df6bae1bdf3314a1564da65e2f37e046`，本机使用此前独立 Python 3.11、PyTorch 2.8.0 环境，不声称 A 的 Python 3.13 环境已通过完整 LightMem 验证。

`configs/structmem-development.json` 使用 DeepSeek Flash 非思考模式，本地同 revision 的 all-MiniLM-L6-v2，384 维，明确归一化。记忆超过嵌入模型最大长度时停止，不静默截断。与 A 的嵌入配置对齐了归一化；此前合成 smoke 的原始配置不改写。

当前仍以完整 session 作为一个事件片段，**关闭压缩和话题切分**，复用官方双路抽取、时间绑定和入库。它可以产出完整会话的事件记忆，但仍需 D/团队接受预处理差异或进一步补齐官方切分/压缩配置，才能用于正式 S2 对照。不会把该差异隐藏成严格论文复现。

## 运行顺序

先在 C 的分支准备 A 交付的脚本与冻结配置，按 A 的说明运行 `python scripts/prepare_locomo.py --download`，确保根目录出现指定的 `data/locomo/development.conversations.json`。A 的 PR 尚未合并时，按其分支取得依赖，不自行合并远端 PR。

沿用 `output/structmem/local-runtime.json` 中的 Python、LightMem、嵌入路径和本地 `.env`。本机入口：

```powershell
# 只生成/检查 91 个 session 的完整输入和不可变计划，不调用模型
.\scripts\run_structmem_development.ps1

# 先用第一个真实 session 验证；至多两次生成请求
.\scripts\run_structmem_development.ps1 -Run -Conversation conv-48 -Limit 1

# 检查首份记忆后，继续三个完整会话；已成功的 session 不重复调用
.\scripts\run_structmem_development.ps1 -Run

# 全部成功后，生成三份独立的交接数据库并重新读取验证
.\scripts\run_structmem_development.ps1 -Assemble
```

单个完整会话先完成时，也可以指定 `-Conversation conv-48 -Assemble -HandoffRoot output/structmem/conv48-handoff` 提前交接。只完成部分 session 时不能把该会话标记为完整。

已存在失败/中断检查点时默认停止。检查具体失败后，用 `-RetryFailed` 显式创建新尝试目录；旧日志和原始响应保留。代码不自动重试 API 请求，不自动覆盖成功或失败产物。成功检查点在复用前检查输入、配置、来源身份、读回状态和导出哈希。

## 给 D 的读取方式

三个开发会话现已全部完成，91 个 session、1973 条输入消息共生成 3712 条记忆。完整库及独立压缩包的读取方式见 [D 读取完整开发会话事件记忆的说明](structmem-complete-handoff.md)，运行统计见 `reports/structmem-development-complete.json`。本次继续运行由用户授权，群内沉默不记作团队确认。

首个真实 session 的独立样例包已准备，路径为 `output/structmem/session-handoff/conv-48-session-001-20261019.zip`。解压、校验、来源示例及检索方式见 [D 读取首个真实 session 的说明](structmem-session-handoff.md)，包大小与 SHA-256 见 `reports/structmem-session-handoff.json`。首样和完整三会话包均已由 D 独立验收，完整包已用于 D 真实综合与回答；PR #43 已合并，C 任务 #32 已按原范围结项。

完整交接位于 `output/structmem/handoff/`：

- `handoff.json`：状态、计划哈希、配置和各会话的数量。
- `conv-48/qdrant/`，collection 为 `conv_48_events`；另外两个会话按相同规则命名。
- payload 沿用上游字段，并包含 `entry_type`、`source_sample_id`、`source_session_id`、`source_message_id`、`source_key`。

复制数据库前关闭客户端；D 在自己的副本上综合和检索，不与 C 同时写一个 Qdrant 目录。D 也需使用相同模型、384 维及归一化配置。首个 session 的临时检查点 collection 仍为 `structmem_events`，不能冒充完整会话数据库。

## 当前验证状态

本轮已核对 A 的冻结原始字节哈希，由 A 的准备脚本重新生成了相同的派生文件；C 只消费对话派生文件。91 个 session、1973 条消息已完整准备。离线测试验证输入白名单、图像描述、完整覆盖、会话隔离、成功检查点跳过、失败需显式重试、篡改检测，以及合成数据库装配和独立读回。

接入包准备阶段的执行环境网络和 D 盘写权限受限，真实开发会话抽取尚未运行；该阶段真实生成请求为 0，未交付完整真实会话数据库。不能把测试夹具或输入准备记作真实模型结果。准备阶段记录见 `reports/structmem-development-preparation.json`。

### 2026-10-19 本地接入与首次运行

已在提交 `6b00770` 上检查并应用接入包补丁，核对 A 的两份输入文件哈希。14 项离线测试通过，完整计划生成 91 个 session、1973 条消息。

执行 `./scripts/run_structmem_development.ps1 -Run -Conversation conv-48 -Limit 1`，选中 `conv-48/session_1` 的全部 18 条消息。`attempt-001` 的事实、关系两路请求均以 `APIConnectionError` 失败，未取得模型响应，未导出记忆，不能计为真实抽取成功。失败日志及检查点保存在本地忽略目录 `output/structmem/development/`。

随后申请允许联网的执行环境，自动审批因缺少将这份会话发送至 DeepSeek API 的明确授权而拒绝；该次重试没有执行。用户随后明确授权发送这 18 条消息至 `https://api.deepseek.com/v1`，执行 `./scripts/run_structmem_development.ps1 -Run -Conversation conv-48 -Limit 1 -RetryFailed`，在 `attempt-002` 成功完成真实抽取；旧失败检查点保留。

实际模型为 `deepseek-flash`，事实 22 条、关系 12 条，共 34 条记忆；两路调用均成功，构建耗时 13.375 秒，输入 4517 tokens、输出 1096 tokens、合计 5613 tokens。成功产物位于 `output/structmem/development/conv-48/session-001/attempt-002/`，包含原始响应、输入、导出及 Qdrant 数据库。再次独立打开数据库，34 条 payload 和向量均与导出一致，384 维向量归一化通过；全部条目的来源索引、消息 ID、会话 ID 和组合来源标识核对通过，覆盖 18 条原消息。逐条查看了抽取文本，尚未开展正式质量评分。

来源示例：`conv-48/D1:9` 关于母亲纪念吊坠的原消息对应事实记忆 “Deborah also has a pendant that reminds her of her mother.”；`conv-48/D1:18` 对应关系记忆 “Jolene expressed enthusiasm for continuing their connection, saying she looks forward to their next chat.”。上游绑定按消息顺序递增秒数，原始会话时间保存在 `input.json` 中。

首个 session 阶段仅完成 `conv-48/session_1`；该阶段详细运行与失败历史见 `reports/structmem-development-first-session.json`。随后按用户指令运行剩余 90 个 session，全部成功；三个独立完整会话库已装配并读回验证，详情见 `reports/structmem-development-complete.json`。仍保留关闭压缩和话题切分的配置差异。
