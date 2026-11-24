# B/D共享排序与M/N离线接口

Refs #71、#72、#73、#75。B只实现M/N；A的依赖规则、闭包与正式打包由D负责。本入口不生成回答，也不读取评分注记。

## 版本与依赖

B 的 [PR #79](https://github.com/YaoYang-123456/NLP-2026-Team08-Structured-Memory/pull/79) 已接入 main `f658cc7`。该版本包含 F 的公共预算与请求核验接口（#77）和 Windows 路径键修复（#78）。Windows 与其他平台使用同一入口。此前的隔离集成分支和受限单题记录保留为 11 月 4 日快照。

复用现有MiniLM规格（`configs/locomo-smoke.json`）；额外离线计数依赖沿用F的`requirements-qa.txt`，词法处理使用`nltk==3.9.2`。不安装训练框架、不新下载模型。原型的`words/bm25`已迁到共享模块，旧脚本改为导入；BM25查询项按排序顺序累加以消除Python哈希遍历差异。

## 候选输入

`scripts/run_mn.py`读取JSONL，每行恰有：

`sample_id, qa_index, question, category, query_vector, units, parents, embedding, scope`。

- 问题与类别必须匹配A已冻结的无标签题单文件，该文件SHA-256匹配原配置；只支持原30道开发题或其原5道子集。category只作输出元数据。
- embedding对象必须与A配置完全一致；query_vector与unit.vector为相同384维有限非零向量。正式输入需来自同一C/native导出或同版本缓存，不能混用本轮诊断重新编码的向量。
- scope说明实际候选范围及向量出处，必须非空。不能把每题原5条综合、归档69条称为原生91条全库。
- units逐项字段恰为`id, kind, text, vector, source_ids, parent, position`。kind为`event`或`synthesis_sentence`；event的parent/position为null；句子的parent为父综合ID，position为0起始句位。
- parents是按原检索顺序排列的综合级记录，逐项`id,text,source_ids`；类型隐含为synthesis。text必须保留`Time range: ...`首行及完整父文本。CLI核对冻结S2交接包哈希并逐题验证原五条完整文本、来源和顺序，拒绝换父文本；M严格要求原五条；N使用同一份父文本映射，不能为M另挑五条。
- 主ID为source_ids首项；所有ID限定在本题sample_id命名空间。同ID同内容的完全重复候选合并并记日志，同ID冲突报错；同文不同ID不合并。父ID+句位重复报错，不将相似度当成身份去重。
- `summary_parts`沿用原型完整句切分；每句必须逐字匹配父文本对应句位及来源。引用原父文本不等于已证实原始对话蕴含。

拒绝answer/reference_answer/reference_evidence/label/score/judge/prediction等标注字段；C/E评分文件不得传入此接口。完整bundle快照只保留本地，不作为全库公开数据。

## D可复用函数

`canonical_units(units)`返回稳定ID顺序的唯一候选及重复ID记录。

`hybrid_rank(units, query_vector, question, config, top_k=None)`返回共同候选、dense/BM25分数及名次、RRF与归一化相关性、相似度矩阵及去重trace。BM25为k1=1.2/b=0.75，RRF k=60；排序平分使用ID。默认对提供的共同池全部排序，与anchor原型共同池重排一致；可用top_k=120在完整事件银行上做dense/lex并集召回，然后和综合句组成共同池重排。正式上游必须记录召回池及向量哈希，不能三组各自截取不同候选。

`select_contexts(ranked, parents, variant, budget, config)`实现M/N，MMR为0.7 relevance−0.3 max similarity，包含非正效用的候选也按顺序尝试，整块超预算则跳过。M先固定五条完整综合、只对事件作选择；N事件与句子联合选择。M和N共享相关性与相似度，但可选类型/预占额度不同。固定综合不计入M事件MMR冗余，沿用原型定义。

`validate_parents`和`render_selection(selected_ids, units, parents_by_id, fixed=())`可供D使用。D计算依赖闭包后，调用同一个渲染函数与F预算器试算整包。包内按原句位合并，省略处`[...]`；父综合和事件展示均有稳定顺序。A新增依赖后的已选集合会改变后续MMR冗余，不要求N/A最终序列相同。

F.count在每次完整试选上计算，包含短编号、kind、完整正文和省略标记。M五条先过prepare，放不下明确失败；最终再prepare，不自动删证据、不截断文本。输出contexts严格只含`source_ids/kind/text`。

## 运行与重建

```powershell
python scripts/run_mn.py --bundle <无标签共同候选.jsonl> `
  --questions <A的development.inputs.json或smoke.inputs.json> `
  --tokenizer-cache <固定cl100k缓存> --out output/mn-new
python scripts/run_qa.py --mock --method S2 --variant M `
  --input output/mn-new/M.inputs.jsonl --config configs/qa-phase2.json `
  --tokenizer-cache <固定cl100k缓存> --out output/mn-mock-M
python scripts/verify_qa_run.py --run output/mn-mock-M --tokenizer-cache <固定cl100k缓存>
```

N同理使用N文件和variant N。输出目录必须全新。选择输出含两个公共输入、完整bundle快照、trace、manifest；trace含每个候选来源/父级/句位/分数、每步效用/冗余、接受/拒绝和完整试选tokens。manifest记录代码、候选输入哈希、实际scope和零模型调用。相同bundle重跑应逐字节一致；QA run_id每次独立，比较请求哈希而非整个QA目录。

## 原生开发集联调

11 月 23 日使用 D 的原生开发包复核了三会话的 3,712 条事件及 91 条综合。对每题在完整同会话事件库取 dense 120 与 lexical 120 的并集，复用事件原生向量，把题目和原五父综合的完整句交给固定 MiniLM 编码。M/N/A 使用同一份 bundle 与排序配置，综合范围仍为每题原五条。数据来源、1/5/30 题验证和预算结果见[原生联调报告](../reports/phase2-b-native-20261123.md)。

11 月 4 日 [受限首样](../reports/artifacts/phase2-b-contract-20261104.zip) 使用归档 top-60 事件并重新编码展示文本，结果见[历史报告](../reports/phase2-b-offline-20261104.md)。开发集主预算结果以新的原生联调为准。C/E 仍需审核原型依赖，E 负责正式评价。
