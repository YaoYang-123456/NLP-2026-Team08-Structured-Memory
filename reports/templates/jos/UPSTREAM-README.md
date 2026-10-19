# 软件学报 Latex 模板

## 中文

本目录提供一个 XeLaTeX 模板，用于近似复现 `软件学报排版样例2025年版.docx` 中的
《软件学报》官方 Word 模板格式。

### 文件说明

- `jos.tex`：根据官方 Word 模板整理的示例论文。
- `jos.cls`：《软件学报》版式对应的 LaTeX class 文件。
- `jos.bst`：示例论文使用的 BibTeX 参考文献样式。
- `ref.bib`：示例论文使用的占位参考文献条目。
- `figures/`：从 `软件学报排版样例2025年版.docx` 中提取的示例图片。
- `fonts/`：用于尽量贴近 Word 模板显示效果的中文字体。
- `软件学报排版样例2025年版.docx`：作为格式参考的官方 Word 模板。

### 编译方法

使用 XeLaTeX 编译：

```sh
make
```

也可以直接运行：

```sh
latexmk -xelatex jos.tex
```

生成的示例 PDF 文件为 `jos.pdf`。

### 说明

本模板是对官方 Word 版式的实用性 LaTeX 近似复现。正式投稿前，请将生成的
PDF 与官方 DOCX 模板进行对照，并根据自己的论文修改元信息、参考文献和作者
信息。本模板主要由 codex + gpt 5.5 生成。



## English

This directory contains a XeLaTeX template that approximates the official
Journal of Software (`软件学报`) Word template in `软件学报排版样例2025年版.docx`.

### Files

- `jos.tex`: sample paper adapted from the official Word template.
- `jos.cls`: LaTeX class file for the Journal of Software layout.
- `jos.bst`: bibliography style used by the sample.
- `ref.bib`: placeholder bibliography entries for the sample paper.
- `figures/`: figures extracted from `软件学报排版样例2025年版.docx` for the sample paper.
- `fonts/`: Chinese fonts used for closer visual matching.
- `软件学报排版样例2025年版.docx`: original Word template used as the reference.

### Build

Compile with XeLaTeX:

```sh
make
```

or directly:

```sh
latexmk -xelatex jos.tex
```

The sample PDF is generated as `jos.pdf`.

### Notes

The template is intended as a practical LaTeX approximation of the official
Word layout. Please compare the generated PDF with the official DOCX before
submission and adjust metadata, bibliography, and author information for your
own manuscript.
