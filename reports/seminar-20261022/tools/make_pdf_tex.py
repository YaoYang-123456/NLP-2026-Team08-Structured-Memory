from pathlib import Path
import json,shutil,sys
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
r=Path.cwd();f=r/'reports/seminar-20261022';data=json.loads((f/'seminar-content.json').read_text(encoding='utf-8'));dest=Path(sys.argv[1])
dest.mkdir(parents=True,exist_ok=True)
(dest/'source/beamer').mkdir(parents=True,exist_ok=True)
# PDF is an exact visual preview of the editable PPTX; the Beamer source is separate.
pdf=canvas.Canvas(str(dest/'第8队-研讨候选-20261020.pdf'),pagesize=(960,540))
pdf.setTitle(data['title']);pdf.setAuthor('NLP Team08')
for png in sorted((dest/'preview').glob('slide-*.png')):pdf.drawImage(str(png),0,0,width=960,height=540);pdf.showPage()
pdf.save()
def esc(t):
 return ''.join({'\\':r'\textbackslash{}','&':r'\&','%':r'\%','_':r'\_','#':r'\#','$':r'\$','{':r'\{','}':r'\}','≠':r'$\ne$'}.get(c,c) for c in t)
tex=[r'\documentclass[aspectratio=169,10pt]{beamer}',r'\input{preamble}',r'\hypersetup{pdftitle={长对话结构化记忆复现与初步诊断},pdfauthor={NLP Team08}}',r'\begin{document}']
for i,s in enumerate(data['slides']):
 if i==9:tex.append(r'\appendix')
 tex += [r'\source{'+esc(s['source'])+'}',r'\begin{frame}{'+esc(s['title'])+'}',r'\small']
 if s.get('subtitle'):tex.append(esc(s['subtitle'])+r'\par\vspace{6mm}')
 if s.get('columns'):
  tex.append(r'\begin{columns}[T]')
  for c in s['columns']:
   tex += [r'\begin{column}{0.48\textwidth}',r'\textbf{'+esc(c['heading'])+r'}\par\vspace{3mm}',r'\begin{itemize}']+[r'\item '+esc(t) for t in c['body']]+[r'\end{itemize}\end{column}']
  tex.append(r'\end{columns}')
 elif s.get('rows'):
  if s['kind']=='team':
   # Keep long GitHub account names on one line and leave room for the source footer.
   tex.extend([r'{\footnotesize\setlength{\tabcolsep}{2pt}\renewcommand{\arraystretch}{1.02}',
               r'\begin{tabularx}{\linewidth}{@{}p{43mm}Yp{22mm}@{}}\toprule'])
   row_gap=r'\\[0.3mm]'
  else:
   tex.append(r'\begin{tabularx}{\linewidth}{@{}'+('Y'*len(s['rows'][0]))+r'@{}}\toprule')
   row_gap=r'\\[1.5mm]'
  for j,row in enumerate(s['rows']):
   tex.append(' & '.join(esc(v) for v in row)+row_gap+(r'\midrule' if j==0 else ''))
  tex.append(r'\bottomrule\end{tabularx}')
  if s['kind']=='team':tex.append(r'}')
  if s['kind']=='results':
   tex.append(r'\par\vspace{3mm}\textbf{S0：15/30（50.0\%）；S2：19/30（63.3\%）}\par 原始裁判为16/30与19/30；输入tokens约4.42倍。')
 else:
  tex += [r'\begin{itemize}']+[r'\item '+esc(t)+r'\vspace{4mm}' for t in s.get('lines',[])]+[r'\end{itemize}']
 if s.get('bottom'):tex.append(r'\aside{'+esc(s['bottom'])+'}')
 tex += [r'\note{'+esc(s['speech'])+'}',r'\end{frame}']
tex.append(r'\end{document}')
source='\n'.join(tex)+'\n';(f/'final-candidate.tex').write_text(source.replace(r'\input{preamble}',r'\input{../homework/slides/preamble}'),encoding='utf-8')
(dest/'source/beamer/main.tex').write_text(source,encoding='utf-8')
shutil.copy2(r/'reports/homework/slides/preamble.tex',dest/'source/beamer/preamble.tex')
print('PDF preview and Beamer source ready')
