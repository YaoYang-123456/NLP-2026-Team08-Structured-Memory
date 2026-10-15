# MetaMem 本地最小试点入口

本入口是杨垚的 **BM25 RAG＋元记忆小规模验证**，不是 LightMem 主实验复现，也不是全组已确定的最终方案。实际运行证据见 [2026-10-15 记录](metamem-local-run-20261015.md)，原方案见 [metamem-pilot.md](metamem-pilot.md)。

## 路线和接口

[论文 §3、Figure 2](https://aclanthology.org/2026.findings-acl.270.pdf) 区分事实记忆 M 与学习得到的经验 E；本入口遵循多次回答、评判、反思、规则编辑的链条。官方提示词与 judge 函数直接复用，版本、许可证和复用边界见 [third_party](../third_party/README.md)。

| 阶段 | 本入口的输入 → 输出 | 标签访问 |
| --- | --- | --- |
| 数据准备 | 官方 cleaned S → 审计、分组清单 | 只做字段完整性及标签文件分离，不按答案筛选 |
| 事实检索 | 带时间的原始会话片段、问题 → 固定 facts | 丢弃 `has_answer`、`answer_session_ids`，不用答案检索 |
| 回答 | 问题、日期、facts、规则 → response | 提示构造函数不接收标准答案 |
| judge | 问题、答案、response、任务 → yes/no | 单独调用；拒答按 `_abs` 识别 |
| 学习 | 训练集多次回答及判分 → 反思、编辑、检查点 | 只加载训练标签 |
| 选择 | 各候选规则在验证集的完整评分 → 冻结 B0/B1/B2 | 只加载验证标签，不反思、不更新规则 |
| 测试 | 同一测试清单、固定 facts 和三份规则 → 汇总 | 回答之后才加载测试标签给 judge；没有学习接口 |

与论文主实验的差异：不进行 LightMem 压缩、话题聚合、事实提取或 Qdrant 向量存储；使用标准库实现的 BM25（k1=1.5、b=0.75），原始单条消息每 180 个空白分词分块，top-k 20，事实正文总预算 12,000 字符。它也不是论文向量 RAG 消融的等配置复现。检索效果未经模型评测，可能漏掉关键证据；不能将模型失误全部归因于规则。

训练固定为 1 epoch、batch 5、每题 2 次。只用全部采样有效且有对有错的题目反思；全对、全错、调用不完整分别记录。学不到规则时保留显式空的 learned 检查点，记录 `no_rules_learned`，不会替换成人工规则。初始空检查点也参与验证；同分选择最早版本，避免无证据地偏向更复杂规则。只有全部验证题都得到有效判分的候选才能被选择。

规则采用最多 8 条、渲染后 UTF-8 2,048 字节的共同预算；学习规则每条最多 30 个空白分词。**这是本试点明确的字节预算，不冒称精确 tokenizer token 上限**；模型实际 token 由响应 usage 记录。B1/B2 都不因规则长度改变 facts。事实字符预算及规则字节预算是减少本轮依赖的调整。

## 环境与数据

在仓库根目录运行 PowerShell；本轮验证 Python 3.14.7。代码只用标准库，没有需要安装的第三方包。不要在其他课程虚拟环境中安装。

```powershell
python -m venv .venv
.venv/Scripts/python.exe scripts/download_data.py
.venv/Scripts/python.exe scripts/prepare_data.py
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

下载脚本固定官方 Hugging Face revision 与 LFS SHA-256，已存在的数据不会被覆盖；失败的 `.partial` 文件需检查后处理，不自动重试计费或覆盖。准备脚本同样拒绝覆盖 `data/pilot/`。当前机器已完成上述步骤，应复用现有文件。

`data/pilot/manifest.json` 保存原始哈希、选择协议、逐题 ID/类型、检索参数、输入和标签文件哈希及 B1 哈希。`*.inputs.json` 只有问题、日期、任务和检索 facts；`*.labels.json` 单独存标准答案。数据与逐题输出均被 Git 忽略。原始数据 277,383,467 字节：**请将该文件发送到小组微信群**；群内发送状态本轮未确认。

## 不需要模型的完整流程检查

```powershell
.venv/Scripts/python.exe scripts/run_pilot.py smoke --mock --out output/mock-smoke
.venv/Scripts/python.exe scripts/run_pilot.py learn --mock --out output/mock-learn
.venv/Scripts/python.exe scripts/run_pilot.py select --mock --training-run output/mock-learn --out output/mock-select
.venv/Scripts/python.exe scripts/run_pilot.py test --mock --selection-run output/mock-select --out output/mock-test
```

输出目录必须是新目录；已有上述目录时请换一个名字。`smoke` 只取前 5 条训练题，不可作为正式 `learn` 输入给 `select`。模拟响应是硬编码流程夹具，非模型生成；所有逐题结果和运行均带 simulated 标记，汇总准确率/正确数/token 均为 null，`valid_model_scores=0`。模拟训练产物与真实运行的指纹不同，不得混用。

## 接入真实本地服务后的五题试跑

配置模板 [local.example.json](../configs/local.example.json) 默认 `backend=disabled`、模型名为空，故不能误发实验调用。确认是本机实际加载的免费模型服务后，将模板复制到 `output/local-config.json`，填写 answer/judge 模型名，将 backend 改为 local。记录服务版本、模型权重来源/版本、量化、上下文长度等启动信息到运行目录旁。当前入口只支持 loopback 上的 OpenAI 兼容 HTTP 服务；禁用代理转发和 HTTP 重定向，不读取环境中的 API 密钥。**localhost 代理本身不证明免费；不要将付费转发服务填成 local。**

```powershell
.venv/Scripts/python.exe scripts/run_pilot.py smoke --config output/local-config.json --out output/real-smoke-01
```

五题试跑用于生成、judge、部分正确筛选、规则更新和日志连通性，不是测试成绩。确认日志里的服务错误、截断、judge 解析、规则更新和成本均可解释，再决定是否运行 learn/select/test。用同一配置分别运行上节后三条命令，去掉 `--mock`、加入 `--config output/local-config.json`，并换用新输出目录即可。本轮未执行这些真实调用。

可选的 `--max-tokens`、`--temperature`、`--top-p` 都覆盖全部六个调用阶段；默认则使用配置中各阶段独立值。改变任何阶段配置、模型、代码、数据清单或人工规则，都会改变指纹，原来的学习/选择目录会被拒绝复用。没有模型响应缓存，也没有静默重试。

## 结果和错误口径

- `run.json`：实际命令、有效配置、代码/数据/规则指纹、开始时间、状态、耗时、请求数和 usage。
- `calls.jsonl`：每次请求的阶段、题目 ID、模型、参数、完整本地提示、提示哈希、响应、finish_reason、usage、耗时和错误类型。不要把该日志外发或提交 Git。
- 学习目录：逐批 rollout、各规则文件、`learning.json`；包括保留题目、全对/全错/调用失败跳过原因和编辑失败。
- 选择目录：逐候选验证输出、`selection.json`、冻结的 B0/B1/B2；测试会核验文件哈希。
- 测试目录：各组逐题输出、`summary.json`；列总数、生成数、有效评分数、覆盖率、分类分数以及 B0/B2 配对 ID。

`accuracy_on_valid` 分母只含有效评分；`correct_over_planned` 是预定题目中已确认正确的比例，是包含未完成题目的下界，不能把服务失败解释为能力错误。生成失败、judge 失败、judge 输出不严格为 yes/no、非 stop 结束（含截断）均单独记录。缺失 token 是 unknown/null；已报告 token 的合计与缺失计数一起看，不拿缺失调用当零成本。

## 调用量与未决条件

五题、每题两次：生成 10＋judge 10；若五组均部分正确，则再反思 10＋提议 5＋批合并 1，**20–36 次**，无重试。全对或全错时只有前 20 次且学不到规则。

20 题学习最多 144 次。含初始空规则与四个批检查点，最多 5 个不同候选，验证最多 100 次；冻结后三组各 20 题最多 120 次。完整试点合计最多 **364 次**（不含额外五题 smoke），重复规则版本自动去重可减少验证调用。这比原建议 344 多出的 20 次来自新增的初始空规则候选。还没有真实 token/耗时样本，无法给出可信费用。

当前缺少实际模型。可行选择：用户指定已有本地权重及加载方式；或确认后下载一款适合本机显存的 7B–8B 四位量化指令模型并以本地服务运行；或提供明确允许用途、模型及预算的 API，届时另做受控适配。小模型自判的偏差需单独报告，不能等同于论文 235B judge。本轮没有下载模型，也没有开启付费调用。
