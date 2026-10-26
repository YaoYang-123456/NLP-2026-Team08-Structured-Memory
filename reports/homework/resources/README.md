# HyMEM PDF 字符映射

`Adobe-GB1-UCS2` 是 Adobe 的 GB1 CID → Unicode 标准映射，版本9.000，来自本机随Poppler分发的CMap资源。文件原样保留Adobe版权及BSD式再分发许可，许可全文在文件开头；生成PDF时也将整个资源（含许可）嵌入。

上游项目：[Adobe mapping-resources-pdf](https://github.com/adobe-type-tools/mapping-resources-pdf)。资源仅用于HyMEM两份个人PDF的兼容性修复，读者无需安装字体或下载外部CMap。

Tectonic将Fandol标为标准Adobe-GB1字体，省略内嵌ToUnicode；部分预览器未配置外部CMap，会跳过全部中文。`scripts/fix_hymem_pdf_unicode.py` 给这些Identity-H字体补充映射，保留原嵌入字体、矢量图、文字及版式。
