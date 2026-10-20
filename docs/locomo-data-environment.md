# A：LoCoMo 数据与环境交接

负责人：`ngocnamd93-spec`；任务 [#26](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/26)。本交付只覆盖数据与环境，不运行回答、抽取、综合或评分 API。

## 1. 固定来源和划分

官方数据为 [snap-research/locomo 的 locomo10.json](https://github.com/snap-research/locomo/blob/cbfbc1dba6bc53d00625212a0f22d55ffee7c1fc/data/locomo10.json)，版本 `cbfbc1dba6bc53d00625212a0f22d55ffee7c1fc`。原文件 2,805,274 字节，SHA-256 为 `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`，Git blob SHA-1 为 `d95b872480b413d935821fdc3c84f8a8f5f29e73`。下载后不格式化、不改换行。

StructMem 固定使用 [LightMem 8449d574](https://github.com/zjunlp/LightMem/tree/8449d574df6bae1bdf3314a1564da65e2f37e046)。本交付记录版本并核对其数据入口，未安装或运行完整 LightMem；完整上游依赖和构建适配仍由 C/D 负责。

`configs/locomo-smoke.json` 保存全部会话 ID、原始题目索引、模型版本和输出哈希，不保存题目正文或答案。使用种子 42：

- 开发会话：`conv-48`、`conv-42`、`conv-41`，每个选 10 题。
- 留出会话：`conv-49`、`conv-44`、`conv-47`、`conv-50`、`conv-43`、`conv-26`、`conv-30`。本次不抽正式留出题、不产生留出模型结果。
- 30 题按原始 category 1/2/3/4 分别为 8/8/7/7，排除 category 5；前 5 题是联调子集，覆盖四类和三个开发会话。
- 选题仅按会话 ID、题型和固定随机顺序，不依据答案或模型表现；这是均衡开发样本，不代表全量分布。

沿用 F 的 [PR #35](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/35) 交接约定：`sample_id` 保持官方原始会话 ID，**题目主键是 `(sample_id, qa_index)`**。例如 `("conv-48", 86)`；`qa_index` 是官方 `qa` 数组从 0 开始的索引，未过滤或重排后重新编号。同一会话的多题不能仅按 sample_id 关联。

## 2. 准备数据

数据准备只需要 Python 3.11 或更新版本，不需要 GPU、API Key 或第三方包。从仓库根目录执行：

```powershell
python scripts/prepare_locomo.py --download
python -m unittest discover -s tests -p test_prepare_locomo.py -v
```

如果已有同版本文件，将其放到 `data/raw/locomo10.json` 后省略 `--download`。直连下载不可用时，可从上面的固定版本链接手动下载相同原文件；脚本会核对精确字节哈希，不接受从网页复制后重新格式化的 JSON。

默认读取已提交的冻结配置，输出 `data/locomo/`。重复执行仅允许输出字节完全相同；不同文件会明确报错，先调查原因，不通过覆盖或重新选题消除差异。`--freeze` 是首次建立清单的维护入口，已有配置时拒绝覆盖；组员复跑不要加它。

重新生成到独立目录检查：

```powershell
python scripts/prepare_locomo.py --output-dir output/locomo-recheck
```

两个目录对应文件的 SHA-256 应与配置中的 `output_sha256` 一致。标准答案和证据文件也属于本地数据，不提交到 Git。

## 3. 交接文件与边界

- `development.conversations.json`：B/C/D 使用的三个完整开发会话。每项仅有 `sample_id` 和 `conversation`；后者保留 `speaker_a/b`、按数字排序的 `session_N`、原始 `session_N_date_time`。消息保留 `dia_id`、`speaker`、`text`、可选 `blip_caption`，不附带 `qa`、事件总结、observation 或评分证据。
- `development.inputs.json`：30 题；`smoke.inputs.json`：其中 5 题。每题严格只有 `sample_id`、`qa_index`、原始数字 `category`、`question`。
- `development.labels.json` / `smoke.labels.json`：只交 E 做评分和人工核查，保存 `sample_id`、`qa_index`、`category` 及原始类型的 `answer`、原始 `evidence` 列表。E 按 `(sample_id, qa_index)` 关联，区分方法时再加 method，不能仅按会话 ID 或结果数组顺序关联。

问答输入示例（仅结构，正文占位，不是新增实验题）：

```json
{
  "sample_id": "conv-48",
  "qa_index": 86,
  "category": 1,
  "question": "<原始题目正文>"
}
```

B/C 的记忆与检索只使用当前问题对应的完整会话，不能把三个会话混成同一个人的历史。`D1:1` 等消息 ID 仅在单会话内唯一；跨会话索引可使用 `conv-48/D1:1`，同时保留原始 ID。时间字符串未经重解析或时区转换；会话时间不是每条消息的独立时间。

图片不下载。为保持与固定版 `add_locomo.py` 一致，使用已有 `blip_caption` 时按上游的 `(image description: ...)` 附在文本后，B/C 应使用同一文本口径；不使用标注的 session_summary、event_summary 或 observation 作为记忆输入。

F 负责回答结果接口，A 不替 F 实现客户端。B/D 读取本清单后，为每题添加真实检索的 `contexts`，按 F 的约定写成 JSONL；保留其余四个字段不变，不添加 conversation_id 等额外字段，不把标签文件拼进上下文。本交接格式已按 F 的现有实现做离线检查，仍须由相关成员审核后共同采用，当前不能声称全组已确认。

本机用 PR #35 的固定提交 `4206096a2929256b4be55d28c105e441e367ad63` 做了 5 题模拟：仅在忽略目录的副本中添加空 `contexts`，调用 `--mock`；5 题均为 simulated，真实成功回答数为 0。此检查证明身份字段和输入白名单兼容，不证明检索或模型回答效果。

## 4. 嵌入环境

固定候选为 [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/1110a243fdf4706b3f48f1d95db1a4f5529b4d41)，revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`、384 维、归一化向量、模型最大长度 256 tokens。固定版 LightMem 的本地嵌入路径是占位符、索引为 384 维；此模型是本项目的明确选择，不是论文 OpenAI 嵌入配置的严格复现。

B/C/D 在真实运行前需统一模型版本、维度、归一化和文本处理。B 的分块必须考虑模型长度限制，不能把任意长度会话直接编码后忽略截断。若组内决定改用其他模型，要在首次真实运行前集中更新配置并重建所有相关索引，不单独替换某一方法。

使用已有可工作的 PyTorch 环境时，避免覆盖 CUDA 安装，可创建隔离环境复用它：

```powershell
python -m venv --system-site-packages tmp/locomo-venv
tmp/locomo-venv/Scripts/python.exe -m pip install -r requirements-locomo.txt
tmp/locomo-venv/Scripts/python.exe scripts/check_locomo_environment.py
```

没有 PyTorch 时，在独立虚拟环境安装 CPU 版本再装依赖，不为 A 下载回答模型：

```powershell
python -m venv tmp/locomo-venv
tmp/locomo-venv/Scripts/python.exe -m pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cpu
tmp/locomo-venv/Scripts/python.exe -m pip install -r requirements-locomo.txt
tmp/locomo-venv/Scripts/python.exe scripts/check_locomo_environment.py
```

加载脚本先核验冻结数据，再用真实消息计算两个 384 维向量，检查有限值、单位长度与同输入一致性；记录实际 Python、依赖版本和设备。CPU 验证不代表 CUDA 或完整 StructMem 构建通过。首次下载模型缓存到 `data/model-cache/`；有缓存后可离线运行：

```powershell
tmp/locomo-venv/Scripts/python.exe scripts/check_locomo_environment.py --local-files-only
```

失败会保留非零退出和 traceback，同时将失败类型记录在 `output/locomo/environment.json`；不把失败写成通过，不自行换模型或调用远端嵌入。

## 5. 验收与后续

实际检查汇总见 `reports/locomo-a-verification.json`，个人进展见 `reports/locomo-a-progress.md`。本机自动验证与另一位成员的独立复验分开记录。

另一位成员需在自己的环境按第 2/4 节加载数据和模型，提供 GitHub 用户名、实际命令、依赖版本、结果与输出哈希。尚未发生时，#26 的“至少另一位成员能照说明加载”保持未勾选；AI 自查不代替此项。

原始数据 2,805,274 字节，小于大文件阈值；仍留在本地，由固定官方链接获取。模型文件若达到 20 MB，请将该文件发送到小组微信群；不加入 Git 或 PR 附件。群内发送尚未发生时不填写发送日期。密钥、数据、环境、模型与运行原始产物均不入 Git，公开材料只使用 GitHub 用户名。
