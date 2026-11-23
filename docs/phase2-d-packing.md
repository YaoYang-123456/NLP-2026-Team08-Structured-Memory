# D：上下文保留与配对删除接口

关联 #73、#71、#72、#75。实现采用 B 的 `hybrid_rank` / `render_selection` 和 F 的 `EvidenceBudget`，没有独立计数器、检索器或生成式压缩。

## 依赖与范围

任务分支从 main `1a627bb` 创建；运行依赖尚未合并的 #79（B `7126895`）和 #77（F `9e7a8e8`，包含 Windows 路径修复）。本 PR 只包含 D 的新增文件，不把 B/F 的未审核代码带入 main。公共依赖合入后需重新集成验证。

当前支持原开发题单/原五条综合的契约，与 B 的入口一致。已补交完整原生 3,712 事件和 91 综合，并以原生事件向量、全会话 dense120/lexical120 并集候选完成固定 1/5/30 题离线验证。综合仍使用每题原五条；C/E 审核后的依赖规则尚待交接。旧原型规则标记 `provisional`，不能视为 C/E 已冻结规则。最新交付见[原生离线报告](../reports/phase2-d-native-20261123.md)。

## 选择与消融

`src/context_packing.py` 接收 B 返回的共同排序结果，以及单独的句子依赖映射。每个综合句必须显式有一项，即使其依赖为空；事件不出现在该映射。依赖必须指向同一父综合的更早原句，拒绝缺失目标、自环、前向边、重复依赖和跨父综合边；此限制保证无环，并保留原型的前文依赖范围。

每轮按共同 MMR 分数与稳定 ID 选种子，求传递闭包，再用已选集合去重；调用 B 的渲染器按原句序合并、省略处保留 `[...]`、保留原来源。F 对整份试选计数，超预算则跳过整个包。成功加入的依赖参与后续 MMR 冗余计算，不再重复作为种子选择；先前因预算拒绝的种子仍可作为其他种子的必要依赖重新试算。

trace 保存种子、闭包、增量与依赖 ID、MMR 效用/冗余、接受或拒绝原因、试选 token、最终选择/未选 ID 和 F 的完整证据与来源映射。未选 ID 表示候选损失，不等于答案支持丢失；后者由 E 另行评价。

配对 S1 直接从 A 的最终 contexts 删除所有综合块，事件集合、原文和顺序保持一致，不补满释放的预算。它是 **A 的删除综合消融**，不是重新检索的事件强基线，也不与历史 S0/S2 成绩直接并表。

## 无标签依赖文件

`scripts/run_context_packing.py` 接收 B 同格式的 JSONL bundle 和独立 JSON 依赖文件：

```json
{
  "version": "C提供的规则版本",
  "status": "provisional",
  "bundle_sha256": "候选JSONL原始字节SHA-256",
  "rows": [
    {
      "sample_id": "conv-48",
      "qa_index": 86,
      "dependencies": {"conv-48/synthesis/example/sentence/0": []}
    }
  ]
}
```

`status` 为 `provisional` 或 `reviewed`；后者只能在实际审核后由交接方填写，程序不进行语义审核。每题映射完整覆盖候选综合句，题目身份集合与 bundle 完全相同，重复题目拒绝。文件不包含评分注记；规则不得依据参考答案制定。

CLI 复用 B 的 `run_mn.run` 完成冻结题单哈希、嵌入、会话命名空间及原五综合的身份/顺序校验，生成共同 M/N 对照；D 同时核对共同排序指纹。错误在写入正式上下文之前暴露；输出目录必须全新。

```powershell
python scripts/run_context_packing.py --bundle <bundle.jsonl> `
  --questions data/locomo/smoke.inputs.json --dependencies <dependencies.json> `
  --tokenizer-cache <固定cl100k缓存> --out output/d-packing-new
python scripts/run_qa.py --mock --method S2 --variant A `
  --input output/d-packing-new/A.inputs.jsonl --config configs/qa-phase2.json `
  --tokenizer-cache <固定cl100k缓存> --out output/d-qa-A
python scripts/verify_qa_run.py --run output/d-qa-A --tokenizer-cache <固定cl100k缓存>
```

输出包括 `A.inputs.jsonl`、`S1.inputs.jsonl`、`trace.json`、依赖快照、manifest 和 `controls/` 下的 M/N。S1 的 mock 使用 `--method S1 --variant A`，表示 A 的配对删除条件；F 当前 variant 枚举不含 S1，未为此更改公共接口。评价时联合使用 method/variant/run_id，不能混为 A 的 S2 回答。

主预算为 4,096。固定五条综合在 26/30 题上已超过 2,048，因此不能强行把 M 缩到该预算。`scripts/run_d_budget_ablation.py` 从已验证的 4,096 运行读取绑定的候选/依赖快照，核对基线代码与输入哈希，输出 2,048 的 N/A/S1 和 M 的不可行题目；不截断 M 或更换分母。该条件下 90 条 mock 请求已重建，未运行付费回答。

```powershell
python scripts/run_d_budget_ablation.py --base-run output/d-packing-new `
  --tokenizer-cache <固定cl100k缓存> --out output/d-2048-new
```

2,048 的 QA 需另用 `evidence_budget.max_tokens=2048` 的配置，模型与提示词保持一致；原 4,096 配置不覆盖。

## 原生记忆交接与候选准备

`scripts/export_development_memory.py` 核对冻结开发会话、输入源、全部点的向量与来源、六个原生导出文件的 SHA-256，输出可移动索引与原字节导出。它不加载原始数据库、不运行记忆构建。现成包见[原生记忆清单](../reports/phase2-native-memory-20261123.json)，约 14.69 MB，可直接从仓库获取。

```powershell
python scripts/export_development_memory.py `
  --memory-index output/structmem-live-20261020/memory-index.json `
  --archive output/native-development-export.zip
python scripts/prepare_d_candidates.py --memory-index <解包后的memory-index.json> `
  --questions data/locomo/development.inputs.json --model-cache data/model-cache `
  --out output/d-candidates-new
```

候选准备复用 B 的共享召回，对完整会话事件做 dense120/lexical120 并集；事件向量逐项保留原生值，不重新编码。固定 MiniLM 只编码问题和完整综合句，超长句沿用已有错误通道拒绝，不暗中截断。原五综合须逐字匹配完整 91 条原生库中的对应父文本。输出共同 bundle、原型依赖、召回记录及源哈希；正式选择仍由同一个 B/D 排序器完成。

原生首样包另含全 91 父综合的 1,144 原句和 315 条原型依赖，供 C/E 核对指代、相对日期和过度扩展；审核状态全部保持待核对。完整 30 题缓存、原始响应与数据库继续留在本地。

验证结果及可读取首样见[离线报告](../reports/phase2-d-offline-20261123.md)。
