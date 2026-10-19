# 上游来源

固定来源：[OpenBMB/MetaMem](https://github.com/OpenBMB/MetaMem/tree/66232c1cb33d3d7939d323b431f21c741785142e)，提交 `66232c1cb33d3d7939d323b431f21c741785142e`，2026-10-15 核对。许可证 Apache-2.0，原文件保存在 [MetaMem-LICENSE](MetaMem-LICENSE)。

- `metamem_templates.py`：从 `src/train_metamem.py` 抽取四个纯字符串模板（回答、轨迹反思、规则提议、批量合并），仅清除两处空白行上的行尾空格，保留提示内容。
- `metamem_judge.py`：从同一文件原样抽取 `get_anscheck_prompt`，保持六类任务和拒答评判口径。
- 本地 `MetaMem/` 为完整上游浅克隆，已被 Git 忽略；没有改写上游源码或安装其依赖。运行试点仅需上述两个随仓库提供的纯 Python 文件，不依赖此克隆。

抽取纯模板与函数是为了复用官方提示词而避免导入上游模块时初始化全局模型客户端。我们自己的数据选择、BM25、HTTP 调用、训练编排和测试均在 `src/metamem_pilot/`，并未声称它们是上游实现。

如需重新检查完整源码：

```powershell
git clone https://github.com/OpenBMB/MetaMem.git third_party/MetaMem
git -C third_party/MetaMem checkout 66232c1cb33d3d7939d323b431f21c741785142e
```

接口核对：上游 `construct_memory.py` 用 LightMem 建事实并检索；`process_train_data.py` 合并为 `question_id/problem/memories/groundtruth/task`；`train_metamem.py` 多次回答、judge、部分正确筛选、反思、提出 add/update/delete、批量合并；验证选择检查点后，推理使用固定规则。试点保留这一训练逻辑，将标签与回答输入分文件存放，不直接导入上游会将失败变成零分的调用包装器。
