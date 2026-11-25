# 阶段二评价与复核（E）

本说明记录阶段二的本地评分入口。回答输入、预测、标签与评分文件必须分开保存；答案和支持标注不能进入检索或回答输入。

## 运行约定

每个 M、N、A 方案各提供一个真实的 `qa-run-v2` 运行目录。正式汇总前，先按 F 的说明逐个运行 `scripts/verify_qa_run.py`，确认请求、预测、模型响应和用量绑定一致。评价入口会再次要求 F 的核验器可用，并检查三个方案使用同一冻结题单、方法、模型和提示词配置。模拟运行不能计分。

开发集和留出集都通过 `--labels` 读取 E 本地冻结的 JSON 标签文件。若答案标签和问题输入分开保存（A 的冻结文件采用这种形式），还要用 `--questions` 提供配对的无答案题目文件；两份文件必须有相同的题目键和类别。留出标签由 A 的确定性准备脚本用 `--with-labels` 在本地生成；**不要把标签文件、DeepSeek 密钥或完整裁判记录提交到 Git**。

收到的开发集 `support-units.json` 覆盖 30 道开发题，共 51 个支持单元。开发集支持覆盖必须和这 30 道题对应的三份 M/N/A 运行、开发标签及开发输入一起计算；不要把它和 100 道留出题的标签或运行混用。留出集不传 `--support-annotations`。

## 评分命令

已有裁判记录时：

```sh
python3 scripts/evaluate.py phase2 \
  --run output/qa-phase2-m \
  --run output/qa-phase2-n \
  --run output/qa-phase2-a \
  --labels data/locomo-phase2/scoring/heldout.labels.json \
  --questions data/locomo-phase2/model/heldout.inputs.json \
  --judgments output/phase2-judgments.json \
  --tokenizer-cache data/tokenizer-cache \
  --out output/phase2-evaluation
```

开发集支持覆盖需另用 30 题开发集运行和配套文件：

```sh
python3 scripts/evaluate.py phase2 \
  --run output/dev-phase2-m \
  --run output/dev-phase2-n \
  --run output/dev-phase2-a \
  --labels data/evaluation/a/development.labels.json \
  --questions data/evaluation/a/development.inputs.json \
  --support-annotations /local/path/support-units.json \
  --judgments output/dev-phase2-judgments.json \
  --tokenizer-cache data/tokenizer-cache \
  --out output/dev-phase2-evaluation
```

只有调用额度已登记并批准后，才显式加 `--judge-api` 运行固定裁判。脚本对每条成功回答只发一次裁判请求、不重试，并逐项保存进度；中断后保留裁判文件，评分与汇总可在另一次调用中读取这份文件完成。

## 输出口径

- 分母固定为 E 标签中的题数，并对每个方案补齐缺失行；分别统计生成状态、裁判状态、固定短语弃答、普通答错和裁判失败。
- 同时报告正确数 / 计划题数、已评分准确率和评分覆盖率；按题型、会话统计，并以共同成功评分的题计算 M/N/A 配对胜负，不据此给小样本显著性结论。
- 记录回答与裁判各自的实际 `usage`、缺失用量数及调用时长。美元费用留空待组内确认价格表，不从旧价格或估算值推算。
- 用量统计区分计划、已开始尝试、已尝试但缺用量和未发出；裁判复算核对完整固定请求、模型身份、自然结束状态及原始 yes/no 回答，人工改判只走独立 overrides。
- 开发集支持覆盖按 `answer_support`、`context_only` 分开，固定原 51 项分母；缺少预测上下文的题仍作为未覆盖计入。留出集的官方证据可定位性另按 A 冻结的 192/193 条引用、97 道完整可核查题记录，不与 51 项开发集标注混用。
- `summary.json` 和 `per-question.csv` 不包含问题文本、标准答案、模型回答、完整请求或支持原句，可用于后续撰写公开汇总；完整标签与裁判 JSON 保留本地。

F 的 PR #77 已合入 `main`，评分入口直接使用其中的 `qa-run-v2` 核验器。当前尚未运行阶段二模型回答或裁判，因此仓库里还没有阶段二准确率结果。
