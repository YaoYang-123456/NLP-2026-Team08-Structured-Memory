# 本地执行记录：2026-10-15

负责人：YaoYang-123456。关联 issue #4；从最新 main `0ef241a` 新建任务分支。工作区 `NLP` 原本为空，直接克隆为根目录，没有覆盖现有仓库或组员文件。检查时没有未合并 PR。PR #3 的四份材料仍是历史准备记录，不回填为已完成实验。

## 本轮状态

| 层次 | 结论 |
| --- | --- |
| 环境可用 | Git 2.55.0，Python 3.14.7，独立 `.venv`；零新增第三方依赖。数据处理与程序验证可用 |
| 数据准备完成 | 官方真实 cleaned S，500 条审计完成；固定 20/10/20、检索结果和独立标签文件已生成 |
| 流程跑通 | 真实数据＋明确标记的模拟响应完成 smoke→learn→select→test；本地 HTTP 夹具验证参数传递 |
| 性能结果 | **没有**。真实 LLM 请求 0、付费 API 请求 0，没有真实规则学习和模型准确率 |

初次检测 GPU 为 RTX 5080 Laptop GPU，驱动 577.03，显存总量 16,303 MiB，空闲 15,599 MiB；D 盘约 182 GB 可用。仅检查 GPU/驱动，没有安装 CUDA、PyTorch 或验证张量计算。Ollama 客户端 0.34.0；初次查询自动启动已有服务，`/api/tags` 返回空模型列表，后续服务不可连接。常用 Hugging Face 缓存无模型目录、未发现 LM Studio 模型目录。另有本地 3080 代理监听，未检查其密钥、未调用模型、未把它当成免费服务。检查范围内没有适用模型；未扫描所有磁盘寻找权重。

## 数据来源和审计

[官方数据集](https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned)，由 MetaMem README 指向。固定 revision `98d7416c24c778c2fee6e6f3006e7a073259d48f`；下载于 `2026-10-15T10:06:01Z`（客户端纽约日期为 2026-10-15）。

- 文件：`data/raw/longmemeval_s_cleaned.json`，277,383,467 字节。
- SHA-256：`d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`；本地重新计算与官方该 revision 的 LFS 对象哈希一致。
- 来源记录：`data/raw/longmemeval_s_cleaned.source.json`；完整审计：`data/audit.json`。
- **请将该文件发送到小组微信群**。用途：真实数据与可复现试点；获取：运行下载脚本或官方固定 revision URL；群内发送人/日期：本轮未确认，不能记为已发送。文件不入 Git 或 PR 附件。

500 条均包含要求的九个字段，500 个唯一问题 ID；问题文本按小写、空白归一化后没有重复，完整有序历史也没有重复。答案为 468 个字符串、32 个整数，处理时明确转成字符串。六类数量：single-session-user 70、single-session-assistant 56、single-session-preference 30、multi-session 133、temporal-reasoning 133、knowledge-update 78；另有 30 条 `_abs` 拒答题。

发现 13 条题目的历史内存在重复会话 ID，7 条题目含空白消息（共 12 个空白 turn），均从本轮候选池排除，不改原数据。跨题出现 3,932 个重复会话 ID、4,366 个重复会话内容哈希；同一个会话 ID 没有多种内容版本。全部共享关系形成一个 500 条连通分量，因此不能声称把整套 500 条直接分成互不相关的训练/验证/测试。

实际做法是从未被排除条目中，按排序后 ID、seed 42、六类＋拒答七个桶轮转，交替向三个集合选题；遇到与其他集合已有题目共享问题/会话 ID/会话内容/完整历史的候选就跳过。选中题目保留全部原始历史，未选中的 450 条不用于任何学习或评价。这得到一个跨集合无直接共享的 50 条子集，不能推广为整套数据独立性证明，也不是用户级隔离：源数据没有稳定 user_id；语义近似和同一人物的未标注关联未被排除。

| 类型 | 训练 | 验证 | 测试 |
| --- | ---: | ---: | ---: |
| knowledge-update | 5 | 2 | 3 |
| multi-session | 4 | 4 | 4 |
| single-session-assistant | 3 | 1 | 3 |
| single-session-preference | 3 | 1 | 3 |
| single-session-user | 3 | 1 | 4 |
| temporal-reasoning | 2 | 1 | 3 |
| 总数 | 20 | 10 | 20 |
| 其中拒答（不额外计数） | 3 | 2 | 3 |

三个集合两两在问题 ID、归一化问题文本、会话 ID、去掉 has_answer 标记的会话内容哈希、有序完整历史哈希上均为 0 重叠。只检查字节/规范化文本层面，不宣称已消除所有潜在语义泄漏。最初顺序选择版本会使测试无拒答，故在没有查看测试答案内容或调用模型前改为交替选题；旧产物仅留在忽略的 `data/pilot-sequential-draft/`。另将生成 JSON 统一为 UTF-8/LF，验证全部题目、事实和标签内容不变；此前 CRLF 产物在 `data/pilot-crlf-draft/`。正式清单是 `data/pilot/manifest.json`，SHA-256 `057be7b8d131e56df62d2884c89463ad485a378b88c6f53f67288705526f6936`。

## 实际运行与验证

执行过：Git clone/fetch/status、Python 版本与 venv、pip list、nvidia-smi、磁盘检查、Ollama 模型列表；`scripts/download_data.py`、`scripts/audit_data.py`、`scripts/prepare_data.py`；`python -m unittest discover -s tests -v`；`scripts/run_pilot.py` 的四个 --mock 阶段；`git diff --check`。完整可复跑命令在 [入口说明](metamem-local-pilot.md)。

模拟日志：五题 smoke 36 个模拟调用；20 题 learn 144；验证 40（规则内容去重后 2 个候选）；三组测试 120。所有 real_requests 都为 0；token 字段为 null；测试每组 valid_model_scores=0、accuracy_on_valid=null。模拟 judge 故意产生同题有对有错以覆盖编辑分支，不能据此称本机小模型能够学习元记忆。验证同分选最早空规则，本次模拟也不代表真实 B2 有无收益。

必要测试覆盖答案与证据标记隔离、先回答后读取标签、规则缺失/错误类型/空人工规则、服务失败和判分解析、同文不同 ID、无部分正确时不替换人工规则、规则编辑预算、划分重叠、配置/阶段隔离、三组 facts 一致、模拟不计模型分数、真实 HTTP 夹具中六阶段参数与 usage、未配置服务禁止调用。HTTP 夹具只在临时目录和回环端口运行，回复是合成的，不是模型。

最终代码的 14 项必要测试通过，日志在 `output/verification-tests.txt`；未配置模型时的失败检查通过，记录在 `output/disabled-service-check.json`。最终四阶段模拟产物分别在 `output/release-mock-smoke/`、`output/release-mock-learn/`、`output/release-mock-select/`、`output/release-mock-test/`，每个目录保存实际命令及配置，正式成绩仍为空。更早的模拟目录是实现期间的流程检查，不用于继续当前指纹的实验。重新从原数据计算 50 个 ID、全部检索结果和跨集合重叠也通过，记录在 `output/data-reproduction-check.json`。

输出保存在 `output/`：环境记录、各阶段 run.json/calls.jsonl/规则/逐题输出/summary。代码和文档纳入任务分支；数据、上游完整克隆、环境和逐题结果不提交。未运行 LightMem、真实推理、真实 judge、真实元记忆学习、性能评测、全量五折或最终报告制作。

## 继续条件

缺少已加载且使用条件明确的本地回答模型与 judge。五题试跑预计 20–36 次请求；真实 token、速度、服务上下文上限和 judge 可靠性仍未测。选择/下载模型或启用付费服务需要后续明确条件，不以聊天订阅替代 API 预算。此次新数据接口和运行约定涉及共享代码，PR 应由一位相关成员集中审核后合并；本轮不自动合并、不安排组员期限。
