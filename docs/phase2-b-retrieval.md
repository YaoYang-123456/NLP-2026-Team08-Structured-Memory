# B/D共享排序与M/N离线接口

Refs #71、#72、#73、#75。B只实现M/N；A的依赖规则、闭包与正式打包由D负责。本入口不生成回答，也不读取评分注记。

## 版本与依赖

B分支从main `1a627bb`建立，不包含F全部改动。运行需要PR #77公共`evidence_budget.py`；Windows还需协作PR #78的POSIX路径键修复。B实施PR以main为base并保持draft，待公共接口审核合入后重新集成。隔离联调分支`YaoYang-123456/71-mn-integration`组合这两个依赖和B提交，仅供复核，不作为main的替代版本。

复用现有MiniLM规格（`configs/locomo-smoke.json`）；额外离线计数依赖沿用F的`requirements-qa.txt`，词法处理使用`nltk==3.9.2`。不安装训练框架、不新下载模型。原型的`words/bm25`已迁到共享模块，旧脚本改为导入；BM25查询项按排序顺序累加以消除Python哈希遍历差异。

## 候选输入

`scripts/run_mn.py`读取JSONL，每行恰有：

`sample_id, qa_index, question, category, query_vector, units, parents, embedding, scope`。

- 问题与类别必须匹配A已冻结的无标签题单文件，该文件SHA-256匹配原配置；只支持原30道开发题或其原5道子集。category只作输出元数据。
- embedding对象必须与A配置完全一致；query_vector与unit.vector为相同384维有限非零向量。正式输入需来自同一C/native导出或同版本缓存，不能混用本轮诊断重新编码的向量。
- scope说明实际候选范围及向量出处，必须非空。不能把每题原5条综合、归档69条称为原生91条全库。
- units逐项字段恰为`id, kind, text, vector, source_ids, parent, position`。kind为`event`或`synthesis_sentence`；event的parent/position为null；句子的parent为父综合ID，position为0起始句位。
- parents是按原检索顺序排列的综合级记录，逐项`id,text,source_ids`；类型隐含为synthesis。text必须保留`Time range: ...`首行及完整父文本。M严格要求原五条；N使用同一份父文本映射，不能为M另挑五条。
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

## 当前验收范围

本轮真实首样仅`conv-48/86`的已归档S2 top60事件及原五综合：60事件+60综合句，共120候选；使用本地固定MiniLM重新编码展示文本。它是受限候选接口诊断，**不是完整原生候选召回，也不是正式M/N准确率/覆盖实验**。M/N为4071/4095 tokens，五完整综合保留；两次选择及trace一致，两个mock官方核验通过。

首样包与来源见`reports/artifacts/phase2-b-contract-20261104.zip`及`reports/phase2-b-offline-20261104.md`。旧90份超额输入必须用正式共同池重新运行选择，本轮没有把90份都修好或用首样替代它们。5/30题完整正式验证仍需C/D原生事件向量、统一候选/原型缓存及父文本；完整91条综合到齐前明确限定同一原五条范围。E评分与留出工作仍由原负责人推进。
