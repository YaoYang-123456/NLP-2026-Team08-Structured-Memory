# 真实五题试跑记录：2026-10-15

负责人：杨垚 / YaoYang-123456。延续 issue #6 / PR #7，在用户明确授权后运行；未合并 PR #5 或 #7。本次仅运行现有训练清单前五题，没有完整训练、验证选择、测试评价、下载或付费调用。

## 结果

| 项目 | 实际结果 |
| --- | --- |
| 模型 | Ollama 0.34.0；qwen2.5:7b-instruct-q4_K_M；answer/judge 共用 |
| 模型摘要 | 845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e |
| 成功进入五题的会话耗时 | 54.685 秒，含服务启动、加载/预热、五题及收尾尝试；worker 47.082 秒 |
| 真实生成请求 | 22：预热 1、回答 10、judge 9、反思 2；提案/合并 0；另有元数据和卸载请求 |
| 调用状态 | 20 个 stop 正常结束；2 个 length 结束，均记录为失败而非能力错误；没有自动重试 |
| 有效判分 | 9/10 次回答获得有效 judge 判分；其中 yes 3、no 6，覆盖率 90% |
| 规则学习 | 没有学出规则；rules-00 / rules-01 均为空，不替换为人工规则 |
| token | 服务报告输入 40,349、输出 3,863；22 次均有 usage，包含预热与失败请求 |
| 上下文 | 实际加载容量 8192；最大输入 3310，最大输入＋输出 3822；服务日志未发现输入截断或 context shift |
| 显存 | Ollama size_vram 5,133,943,438 字节；5 秒采样观察到整卡峰值 5151 MiB（约 5.03 GiB），不是连续采样的绝对峰值 |
| 释放 | 卸载接口 done_reason=unload，随后 /api/ps 为空；独立检查服务/runner 已消失、11436 无监听；GPU 回落至 10 MiB、0% |

3/9 是同一个 7B judge 给出的训练 smoke 判定比例，**不是正式测试准确率，也不是人工确认的正确率**。原始回答、截断片段、judge 输出、反思和规则快照全部保留。尚未进行人工正确性判定；human-review.json 的人工字段保持空值。

## 时间窗口与真实故障

全轮窗口从 `2026-10-15T14:50:21Z` 开始（客户端纽约时间 10:50:21），停止推理截止 `15:40:21Z`、总截止 `15:50:21Z`。启动前发现 Endfield 进程与约 5976 MiB / 46% GPU 使用；用户自行退出游戏后，GPU 为 280 MiB / 0%，再开始加载模型。没有擅自结束游戏。

第一次入口 `output/evening-smoke-20261015-1452/` 于 14:52:04Z 启动，未发送生成请求。Windows 下 detached Ollama 继承了 subprocess.run(capture_output=True) 的输出管道，导致 Python 等待管道 EOF；45 秒超时后仍等待继承句柄。手动按已保存进程身份停止该服务后，入口记录 startup_or_runtime_error / not_started，约 115 秒结束。保留该目录，没有覆盖。

只修复 `scripts/evening_smoke.py` 的服务控制调用：stdin 使用 DEVNULL，stdout/stderr 写 `output/ollama-service/control.log`，避免用 PIPE 接收后台服务继承的句柄。没有修改模型、数据或生成参数。

第二次入口 `output/evening-smoke-20261015-1454/` 于 14:54:14Z 启动，原窗口剩余秒数传给现有入口，截止时间没有顺延。14:55:08Z 完成卸载，整个真实五题会话提前结束，不补跑失败调用。

停止阶段 taskkill /T /F 对已经消失的 runner 报非零，入口如实保留 server_stop_error 并以非零退出；worker 自身 completed / exit 0。随后独立确认原 server PID 16408、runner PID 27188 均不存在，端口无监听，模型已卸载，GPU 10 MiB / 0%。不将原始错误记录改写成无错误；补充核验见 cleanup-verification.json。本轮不再启动模型以重测这个退出竞争现象。

14:59:23Z 保存补充核验时，用户已重新打开 Endfield，整卡显存为 5938 MiB / 33%；本次 Ollama 服务和 runner 仍不存在、端口无监听。这一游戏使用量不算作模型未释放，模型释放后的 10 MiB / 0% 证据见 14:55:12Z 的采样及此前独立检查。

## 输出上限与规则学习

- 回答 `8a2466db` 的 attempt 0 用满 512 输出 token，finish_reason=length，保留片段但不送 judge，不记答错。
- `6aeb4375_abs` 两次判分一对一错，符合上游默认更新条件。第二次反思也用满 512 输出 token，导致该组反思/提案失败；没有调用 propose 或 merge，没有生成新规则。
- 其余题目：两题两次全错、一题两次全对；另有一题调用不完整。全部按既有规则跳过。

因此不能把本次结果解释为“小模型完全没有更新机会”，也不能把没有学出规则直接归因于模型能力：有一个合格组，但被反思输出上限阻断。之后若调整输出预算或模型，应新建明确的实验记录；本轮没有临时增大预算重跑，也没有读取验证/测试答案。

## 产物与实际验证

主目录：`output/evening-smoke-20261015-1454/`。

- `session.json` / `model.json` / `worker.log`：实际命令、配置、截止时间、耗时和清理状态。
- `smoke/calls.jsonl` / `run.json` / `rollouts-00.json` / `learning.json` / `rules-*.json`：全部真实调用、判分和学习状态。
- `review.txt` / `review-inputs.json` / `human-review.json`：仅五条训练题的人工复核入口；截断回答保留并标为 generation_failed。review 汇总中的 generated=10 包含该保留片段；有效完整回答为 9，不能将 10 当作完整成功回答数。
- `gpu-samples.jsonl` / `diagnostics.json` / `cleanup-verification.json`：显存采样、输入/输出截断检查和独立收尾核验。
- 服务推理日志：`output/ollama-service/20261015-105415.stderr.log`；启动/停止控制日志：`output/ollama-service/control.log`。

运行使用现有 evening_smoke.start 入口，外层仅将 ACTIVE_SECONDS / TOTAL_SECONDS 设为上述原窗口的剩余时间，拒绝已有输出目录。原始数据、模型、B0/B1 和检索配置未更改；所有真实运行产物保留本地，不纳入 Git。

本次修复新增一项 mock 检查，确认服务控制用文件而不是 PIPE。执行 `python -m unittest discover -s tests -p test_evening.py -v`：12 项专项检查通过，未运行完整数据审计或其他实验。真实入口第二次成功越过原阻塞点并完成五题，另验证了实际卸载、端口和 GPU 状态。
