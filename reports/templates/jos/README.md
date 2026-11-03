# 软件学报 LaTeX 模板

本目录保存 [CodingYuanLiu/JOS-Template](https://github.com/CodingYuanLiu/JOS-Template) 的模板快照，固定 commit 为 `7f1031f2ab948a8d778719da3159cfc532d27664`，获取日期为 2026-10-18。上游将其定位为对《软件学报》2025 年版 Word 样例的近似复现，**不是官方 LaTeX 模板**。[上游原说明](UPSTREAM-README.md)照录保留；来源、上游及本地校验值见 [sources.json](sources.json)。

官方 [Word 样例](../../../docs/course/软件学报排版样例2025年版.doc)供对照版式，小组实际使用 [LaTeX 阅读报告](../../homework/README.md)并导出 PDF。

## 文件与适配

- `jos.cls`：版式类；沿用上游纸张、正文区域、正文与标题字号、图表设置，按官方Word样例统一字体、页眉字号和文献标题。
- `jos.bst`：基于上游BibTeX样式，修正会议文献重复添加的“Proceedings of”前缀。
- `UPSTREAM-README.md`、`sources.json`：上游说明、固定版本、校验值和修改记录。

仅收录共用类文件和参考文献样式，不收录上游的缺陷预测示例论文、配图、字体包和生成 PDF。[本组报告入口](../../homework/main.tex)同时作为可编译示例。`UPSTREAM-README.md` 描述的是完整上游项目，其文件清单不代表本目录全部收录。

2026年10月29日按原始Word与LaTeX样例复核：字体齐备时使用已安装的宋体（SimSun）、黑体（SimHei）、楷体（KaiTi）、仿宋（FangSong）及Times New Roman；缺少其中任一字体时，继续使用原有Fandol与TeX Gyre字体。字体文件不随仓库分发。正文保持9pt、14.25pt行距和2em首行缩进；页眉按Word的9pt统一，文献标题使用不带冒号的References。会议文献前缀改为“In: ”，由BibTeX条目提供完整会议录名称。上游未声明独立许可证，保留原作者与来源，不将这些第三方文件重新授权为本项目原创代码。

查询、字段名、模型标识等技术字符串也使用正文的西文字体和字号；保留原始字符，并关闭其TeX引号及连字替换。模板不要求这些字符串必须使用等宽字体。

## 编译示例

需要带中文、XeLaTeX、BibTeX、latexmk 及上述字体的 TeX Live 环境。从仓库根目录执行：

```sh
cd reports/homework
latexmk -xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
```

输出为 `output/homework/main.pdf`，编译中间文件也在该忽略目录，共享类文件只有本目录一份。报告的 `.latexmkrc` 已设置类文件及参考文献样式的搜索路径；主稿使用 `\bibliographystyle{jos}`，`references.bib` 已收录六篇论文的参考文献条目。
