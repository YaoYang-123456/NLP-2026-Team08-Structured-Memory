# C：事件记忆最小构建入口

负责人：oioioi-521；技术任务 [#32](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/issues/32)。

本页保留合成 smoke 阶段的复跑说明：对话读取 → 官方事实/关系双路抽取 → 官方事件绑定与向量入库 → 关闭数据库 → 独立重新读取核对。该阶段用六条自拟对话验证接口，结果不作为数据集成绩。当前三个真实开发会话已完成，最新结果和交接状态见 [开发会话接入](structmem-development.md) 与 [个人进展定稿](../reports/structmem-progress-20261019.md)。

## 实现与边界

- 上游固定为 zjunlp/LightMem 的 `8449d574df6bae1bdf3314a1564da65e2f37e046`，运行前核对提交及源码/提示词未修改。
- 复用 `LightMemory.add_memory()`、LoCoMo 官方 factual/relational 提示词、来源时间绑定和 Qdrant 入库。适配集中在 `src/structmem_build.py`，不改上游和旧 MetaMem 试点。
- 这是 **session smoke 配置**：关闭预压缩和话题切分，将一个完整 session 作为一个片段，最后强制抽取；本地 CPU 使用 384 维 all-MiniLM-L6-v2。与论文/团队最终预处理配置存在差异，不能称为完整 StructMem 复现，不能直接作为 S2 正式对照结果。
- 抽取使用 `deepseek-flash`，非思考、temperature=0、top_p=1、输出上限 2048。2026-10-19 已通过账号 models 接口与[官方模型文档](https://api-docs.deepseek.com/quick_start/pricing/)核对；[非思考模式](https://api-docs.deepseek.com/guides/thinking_mode/)显式设置 `thinking.type=disabled`。Flash 非思考模式的 top_p 固定为 1；实际部署精确版本不能仅凭返回别名推断。
- 原上游 OpenAI 管理器初始化会创建关闭证书验证的客户端；入口在任何生成请求前关闭并替换为默认校验证书的客户端。密钥只从环境变量或本地 `.env` 读取，不打印、不写入结果或配置。
- 每个 session 最多两次生成请求，不自动重试；空提取、调用失败、JSON 错误、输出截断、来源 ID 越界或转换条目缺失均报错。失败运行保留 `status=failed`，不能交作完整记忆。
- 原上游入库载荷不保留 `entry_type`、原始消息 ID；入口保持原有字段，并补充类型、来源样本/session/消息 ID。来源 ID 是上游输出的锚点，不代表已人工核实整条关系的所有证据。
- 两次提取均验证成功后才开始插入。插入失败可能留下部分数据库，必须依据 summary 状态判断完成；不自动续写或覆盖。每次使用新的运行目录。

## 本机直接运行

本机已在独立 Python 3.11 环境安装固定上游依赖，实际运行路径保存在 Git 忽略的 `output/structmem/local-runtime.json`。本地 `.env` 已配置 `DEEPSEEK_API_KEY`；后续更换密钥只修改该文件。

从仓库根目录在 PowerShell 执行以下命令。它会发起两次真实 API 调用，仅处理自拟样例：

```powershell
.\scripts\run_structmem_smoke.ps1 -RunName synthetic-check
```

需要回放已保存的真实响应、验证入库而不再次调用模型时：

```powershell
.\scripts\run_structmem_smoke.ps1 -RunName replay-check -ReplayPath output\structmem\synthetic-run-02
```

回放要求输入、配置、上游版本、提示词文件哈希及逐次生成的实际提示词一致；结果标记 `execution=replay`。回放中记录的 usage 属于原请求，不是新的消费，不得重复计费或当成新的模型实验。

## 换电脑准备

1. 安装 Python 3.10/3.11，创建独立虚拟环境。
2. 克隆官方 LightMem 并切换上述固定提交；在环境里执行 `python -m pip install -e <LightMem目录>`。该版本固定了全部依赖，包含 torch 2.8.0；不修改系统环境。首次安装/导入耗时不计作模型推理耗时。
3. 下载 `sentence-transformers/all-MiniLM-L6-v2` 为本地完整模型。此次下载的 revision 为 `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`。本地权重、环境、上游克隆不提交。
4. 预备上游分词器：`python -c "import tiktoken; tiktoken.get_encoding('o200k_base')"`。构建入口不会主动下载嵌入权重。
5. 在本地 `.env` 填写 `DEEPSEEK_API_KEY=你的密钥`。在忽略目录创建 `output/structmem/local-runtime.json`，填写 `python`、`upstream`、`embedding_model` 三个绝对路径。共享配置不含密钥。

## 后续接入 A 的真实数据

先确认正式开发会话与预处理配置。以下命令只准备显式指定的一个完整 session，不读 QA 进入构建；将占位内容替换为 A 提供的实际路径与 ID：

```powershell
python src/structmem_build.py prepare --data data/locomo10.json --sample-id SAMPLE_ID --session 1 --output output/structmem/real-input.json
python src/structmem_build.py build --input output/structmem/real-input.json --config configs/structmem-smoke.json --upstream LIGHTMEM_PATH --embedding-model LOCAL_MODEL_PATH --output output/structmem/real-session-01
```

输入超过 smoke 上限时会停止，不裁剪 session。完整开发会话构建及与团队预压缩/切分策略的适配仍需继续完成；不要把关闭这些步骤的 smoke 结果直接交作最终数据。

## 结果与交接

每次结果保存在 `output/structmem/<运行名>/`：

| 文件 | 含义 |
| --- | --- |
| `input.json` | 不含 QA 的会话输入，含原时间和消息 ID |
| `factual/relational-prompt.json` | 两次实际模型输入 |
| `factual/relational-response.json` | 原始模型响应、返回模型名和 usage |
| `qdrant/` | 独立数据库，collection 为 `structmem_events` |
| `memories.json` | 关闭数据库后重新读取的载荷与向量 |
| `summary.json` | 状态、输入/提示词哈希、配置、调用失败、耗时及读回结果 |

交给 D 的应是成功运行的独立副本、summary、输入映射和复跑命令，并明确 smoke/正式配置差异。关闭数据库后才复制，不同时写一个 Qdrant 目录。包含向量的导出只是核对资料，后续综合与检索应优先复用上游数据库结构。

原始产物均留在忽略目录；Git 仅提交入口、配置、自拟测试和说明。单文件达到 20 MB 时，请将该文件发送到小组微信群，仓库只记录获取方式和校验信息。

## 离线检查

```powershell
python -m unittest discover -s tests -p test_structmem_build.py -v
```

覆盖 QA 隔离、消息 ID、重复 ID、异常来源 ID、畸形/截断 JSON、官方关系字段兼容。完整验证记录见 `reports/structmem-smoke-20261019.json`。
