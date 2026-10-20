# B：S0 普通检索基线——与 A/F 正式交接对齐

负责人：`YaoYang-123456`；任务 [#24](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/24)。B 只负责原始对话向量检索；F 生成回答；E 评分。2026-10-19已完成真实5/30题检索与F模拟读取，真实回答及评分仍为0。实际命令与案例见[本机运行记录](../reports/s0-local-run-20261019.md)。

## A 的数据与嵌入契约（PR #38）

- 直接采用 A 冻结的 3 个开发会话 `conv-48`、`conv-42`、`conv-41`，30题及前5题子集，不另行选题；固定 ID、版本和文件 SHA-256 见 `configs/locomo-smoke.json`。
- `data/locomo/development.conversations.json` 仅包含完整的原始会话及来源；`data/locomo/smoke.inputs.json` 和 `development.inputs.json` 是 JSON 数组，每题仅含 `sample_id/qa_index/category/question`。两个输入文件的 SHA-256 在正式运行前必须符合 A 的 `output_sha256`。
- `*.labels.json` 只供 E 评分；B 严格禁止将答案、标注 evidence、预生成事件摘要或会话总结送入检索语料与 F 的问答输入。
- 统一使用 `sentence-transformers/all-MiniLM-L6-v2`，固定 revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`、384维、归一化向量、256-token 上限。B 按 A 配置离线加载，不自动换成 Ollama/BM25；本地模型权重不入 Git。

## B 检索的具体实现

按 `session_N` 数字顺序分块原始对话，保留会话日期、说话人、原始 `dia_id` 和块序号；A 保留的 BLIP 图片说明采用 `(image description: ...)`，不下载图片。默认每块约480字符；编码前用真实 tokenizer 检查256-token上限，超出则报告失败，不让嵌入模型静默截断。对每个会话只编码一次，缓存按模型、revision、文本与相关参数隔离。

问题与语料使用同一个嵌入模型，L2归一化后按余弦相似度选取 top-60；若不足60块，则取可用数量，平分时沿用对话顺序。S0 是**原始对话RAG**，不能冒称原论文的 flat fact memory 消融。

输出到新建的 `output/s0-...` 目录：

- `s0.inputs.jsonl`：每行恰好包含 `sample_id, qa_index, question, category, contexts`；上下文恰好有 `source_ids, kind=raw, text`，直接交给 F 的 [PR #35](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/35) 回答入口。
- `s0.retrieval.jsonl`：每题来源 ID、排名与余弦分数，分数不进入回答提示词。
- `s0.manifest.json`：源文件哈希、固定模型与版本、top-k、分块参数、题数和检索记录。此文件中 `accuracy=null`，回答生成调用数为0。

## 真实运行指令（需要 A/F 兼容文件与本地模型）

先按 [A 环境说明](../docs/locomo-data-environment.md) 在具备缓存的机器运行 `scripts/prepare_locomo.py` 并复验模型；不能拿构造数据当真实题。模型文件达到20MB时，请将该文件发送到小组微信群。

```powershell
python scripts/run_s0.py --selection data/locomo/smoke.inputs.json --out output/s0-smoke5
python scripts/run_s0.py --selection data/locomo/development.inputs.json --out output/s0-dev30
```

上述命令默认使用 A 的 `development.conversations.json` 与 `configs/locomo-smoke.json`，本地模型缓存为 `data/model-cache`。若缺少原始数据或嵌入模型，会停止报错，不回退到其他模型。

F 接收检索结果的后续真实问答命令（**此处未运行**）：

```powershell
python scripts/run_qa.py --method S0 --execute --input output/s0-smoke5/s0.inputs.jsonl --config configs/qa.example.json --out output/s0-qa-smoke5
```

在实际执行前须由 F 检查 API 配置和凭据，由 E 接收联合主键 `(method, sample_id, qa_index)` 并评分。不能改变已经冻结的题目，也不能把调用失败当成正常答错。

## 实际验收边界

本机独立Python3.12 CPU环境下，A/B/F **7＋8＋14＝29项针对性测试通过**。固定MiniLM真实加载，5/30题检索完成，每题60块；原始ID、时间、排序、字段隔离及题集哈希检查通过。5题是30题的子集，真实独立题数仍为30。没有触发256-token截断保护，未改变480字符分块设置。

F仅执行`--mock`，5/30行均为simulated，不计入模型成绩；真实回答/评分为0。缺少本机项目凭据及明确的本次付费额度，未调用付费API。F示例提示词须在真实生成前核对冻结。小型核验为 `reports/s0-local-verification-20261019.json`，个人两页材料见 `reports/s0-progress-20261019.md` 及 `reports/s0-seminar-20261019.tex`。完整日志、原始检索与模型权重保留本地，不提交Git。
