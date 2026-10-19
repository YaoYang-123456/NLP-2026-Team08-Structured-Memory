# D 接收首个真实 session：实际验收记录

负责人：`lanshuheng9-oss`；2026-10-19；任务 [#28](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/28)。接收 C 的 `conv-48-session-001-20261019.zip`，完成真实数据库读取、与 A 的来源核对、固定模型加载及本地检索检查。**这是完整 session 的接收验收，不是完整会话 S2 实验。**

## 文件与独立副本

- 原 ZIP：229,007 字节，SHA-256 `39a4efd0eb2c246372e1b103b9cc248070942fdbf37065adcdaa275a355a4c07`。
- 保留副本：`data/structmem-received/conv-48-session-001-20261019.zip`。接收解压目录：`output/structmem-session-receive-20261019/conv-48-session-001/`。
- 验收程序另复制 Qdrant 到 `output/structmem-session-acceptance-20261019/qdrant-work/` 后打开；没有写入 C 工作目录。验证结束后，接收目录的 14 个声明文件哈希仍全部匹配。
- 完整本地结果：`output/structmem-session-acceptance-20261019/receipt.json`。小型公开记录：[structmem-session-receipt-20261019.json](../reports/structmem-session-receipt-20261019.json)。ZIP、原始会话、数据库、完整模型缓存与日志继续留在忽略目录。

## 实际通过的检查

| 检查 | 结果 |
| --- | --- |
| ZIP CRC 与清单 SHA-256 | CRC 通过，14 个声明文件哈希全部匹配 |
| C 提供的读回脚本 | 已审阅后实际执行，返回 `status=verified` |
| 独立 Qdrant 读回 | 34 条，完整 payload、向量与 JSON 导出逐项一致 |
| 类型及来源 | 事实 22、关系 12；18 条原始消息均有来源引用 |
| 与 A 对齐 | 消息正文、图片描述、消息 ID、说话人、原始会话时间一致；34 条绑定时间均对应原消息位置 |
| 模型实际加载 | 固定 MiniLM revision，CPU、384 维、归一化、最大长度 256 |
| 全部记忆重新嵌入 | 34 条，最大逐分量绝对差 `1.4156103134155273e-07`，小于验收阈值 `2e-5` |
| 本地检索对照 | 3 个检查问题，各 top-5；D 余弦排序与 Qdrant 全部一致，最大分数差 `3.33e-16` |
| 针对性测试 | D 12 项、F 14 项全部通过 |

检查问题在运行前依据来源文本选定，用于确认读取与来源追溯，不是 A 的固定评测题，也没有自动判分或准确率：

| 检查问题 | top-1 记忆 | 来源 | 余弦分数 |
| --- | --- | --- | --- |
| What reminds Deborah of her mother? | Deborah also has a pendant that reminds her of her mother. | `conv-48/D1:9` | 0.792998 |
| Where and when did Jolene's mother give her the pendant? | Jolene's mother gave her the pendant in 2010 in Paris. | `conv-48/D1:8` | 0.899372 |
| How does Deborah want to support her community? | One of Deborah's goals is to keep teaching yoga and supporting her community. | `conv-48/D1:13` | 0.651465 |

来源绑定正确和向量可复现，不等于所有抽取文本的语义都已人工验收；人工语义核查仍为 `null`。`time_stamp` 是 C 按消息顺序分配的事件绑定时间，不是独立测量的逐消息发送时刻。

## 运行环境与复跑

隔离环境为 `tmp/structmem-receive-venv/`，复用本机 CPU PyTorch，没有改变系统包。实际 Python 3.13.9、PyTorch 2.11.0，与 C 的 Python 3.11 / PyTorch 2.8.0 不同；qdrant-client 1.15.1、sentence-transformers 5.1.1 相同。完整依赖版本见核验 JSON。本轮数据库读回及向量差异是实测结果，不据此声称完整 LightMem 环境通过。

首次导入遇到继承自 Conda 的科学计算库与 PyTorch 的重复 OpenMP。通过在隔离环境安装 NumPy 2.2.6、SciPy 1.15.3、scikit-learn 1.7.2 的 pip wheel 解决，没有使用 `KMP_DUPLICATE_LIB_OK`。

固定模型下载到 `data/model-cache/`，revision 为 `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`。`model.safetensors` 实际 90,868,376 字节，SHA-256 `53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db`。这是本地嵌入模型，没有下载回答模型。按大文件约定，请将该文件发送到小组微信群；发送日期未确认，权重不加入 Git 或 PR 附件。

模型缓存已准备后，在仓库根目录执行；复跑使用新的输出目录：

```powershell
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
tmp/structmem-receive-venv/Scripts/python.exe scripts/verify_structmem_session.py `
  --bundle output/structmem-session-receive-20261019/conv-48-session-001 `
  --out output/structmem-session-acceptance-recheck
```

入口先核对接收文件，再核对 A 数据、来源与向量；只打开自身数据库副本，并使用已有离线模型缓存。不重新抽取、不调用 DeepSeek、不自动重试失败步骤，不覆盖已有结果目录。已有副本缺失时，从保留的 ZIP 解压；不要用已被其他程序修改的数据库替代原始快照。

## 本次配套改动与剩余工作

C 现已提供 `source_sample_id`、`source_message_id`、`source_key`。D 适配已在 F 的原有 `source_ids` 数组中同时保留记忆 UUID 与原始 `conv-48/D1:9` 一类来源键；综合项在已有事件映射时也保留关联消息来源。字段不完整、来源键不一致或指向其他会话会报错，不伪造映射；原先没有消息映射的上游 point 仍保留记忆 ID。新增两个针对性测试验证这些条件，没有改变 F 接口、回答参数或检索算法。

本次生成、综合、评分 API 调用均为 **0**；本地嵌入和真实事件检索已实际执行。收到的是 `conv-48/session_1`，该会话仍为 **1/30 sessions**，未收到 `conv-42`、`conv-41` 的完整事件库；包中没有跨事件综合记忆，也没有完整 LightMemory 构建配置。正式 5/30 题 S2、完整会话比较和评分仍未运行。C 当前关闭压缩与话题切分的配置差异也需在正式方法中保留说明，不把这个样例冒称论文原设置复现。
