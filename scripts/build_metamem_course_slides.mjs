// Run with the Codex bundled Node after build_metamem_course_materials.py.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const build = path.join(root, 'tmp/metamem-materials-20261019');
const skill = process.argv[2];
const python = process.argv[3];
if (!skill || !python) throw new Error('Supply presentation skill directory and bundled Python executable');
const require = createRequire(path.join(build, 'loader.cjs'));
process.env.RUNTIME_NODE_MODULES = await fs.realpath(path.join(build, 'node_modules'));
process.env.RUNTIME_NODE = process.execPath;
const {Presentation, PresentationFile} = await import(pathToFileURL(require.resolve('@oai/artifact-tool')).href);
const {finalizePresentation, applyPresentationChartFont} = await import(pathToFileURL(path.join(skill, 'container_tools/artifact_tool_utils.mjs')).href);
const content = JSON.parse(await fs.readFile(path.join(root, 'reports/metamem-course-slides.json'), 'utf8'));
const FONT = content.font;
const pres = Presentation.create({slideSize: {width: 1280, height: 720}});
const color = {ink: '#172C3C', body: '#304452', accent: '#087E8B', other: '#A85532', gray: '#667788'};

function text(slide, value, x, y, w, h, size=28, bold=false, fill=color.body, name='body') {
  const shape = slide.shapes.add({geometry:'textbox', name,
    position:{left:x,top:y,width:w,height:h}, fill:'none', line:{fill:'none',width:0}});
  shape.text = value;
  shape.text.style = {typeface:FONT,fontSize:size,bold,color:fill,wrap:'word',autoFit:'none',insets:0,
    verticalAlignment:'top'};
  return shape;
}

const chartSlides=[], tableSlides=[];
for (let i=0; i<content.slides.length; i++) {
  const item=content.slides[i], s=pres.slides.add();
  s.background.fill='#FFFFFF';
  s.speakerNotes.text = item.notes+'\n\n来源：'+item.source+'\n论文：https://aclanthology.org/2026.findings-acl.270/\n仓库真实试点贡献：杨垚；整理与汇报署名待本人填写。';
  if (item.kind==='cover') {
    text(s,'MetaMem',76,140,1128,100,76,true,color.ink,'deck-title');
    text(s,'论文阅读与个人试点',80,262,1120,75,48,true,color.ink,'cover-topic');
    text(s,item.body.join('\n\n'),84,400,1110,210,28,false,color.body,'cover-subtitle');
  } else {
    text(s,item.title,64,45,1152,84,44,true,color.ink,'slide-title');
    if (item.kind==='figure') {
      const bytes=await fs.readFile(path.join(root,content.figure));
      s.images.add({blob:bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),contentType:'image/png',
        alt:'MetaMem 原论文 Figure 2 的完整方法图',fit:'contain',position:{left:192,top:145,width:896,height:524}});
    } else if (item.chart) {
      const spec=item.chart;
      text(s,spec.unit,72,143,720,35,21,false,color.gray,'chart-unit');
      const chart=s.charts.add('bar', {
        position:{left:54,top:192,width:768,height:414},
        categories:spec.categories,
        series:spec.series.map((ser,n)=>({...ser,fill:n===0?color.accent:color.other})),
        hasLegend:spec.series.length>1,
        legend:{position:'bottom',textStyle:{fontSize:21,typeface:FONT}},
        barOptions:{direction:'column',grouping:'clustered',gapWidth:120},
        dataLabels:{showValue:true,position:'outEnd',textStyle:{fontSize:22,typeface:FONT}},
        xAxis:{textStyle:{fontSize:20,typeface:FONT}},
        yAxis:{min:0,max:spec.max,textStyle:{fontSize:19,typeface:FONT},
          majorGridlines:{fill:'#E4E9ED',width:1}},
        chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF',
      });
      applyPresentationChartFont(chart,{fontFamily:FONT});
      text(s,item.body.join('\n\n'),870,190,342,420,27,false,color.body,'chart-explanation');
      chartSlides.push(i+1);
    } else if (item.table) {
      const vals=[item.table.headers,...item.table.rows];
      const height=vals.length===5?250:vals.length===4?220:170;
      const table=s.tables.add({rows:vals.length,columns:vals[0].length,left:78,top:158,width:1124,height,
        values:vals,columnWidths:vals[0].length===2?[470,654]:vals[0].length===3?[520,302,302]:[390,260,260,214]});
      table.borders.assign({fill:'#D3DEE5',width:1,style:'solid'});
      for(let r=0;r<vals.length;r++)for(let c=0;c<vals[0].length;c++){
        const cell=table.getCell(r,c);
        cell.fill=r===0?'#E7F0F3':r%2===0?'#F5F8FA':'#FFFFFF';
        cell.text.style={typeface:FONT,fontSize:26,bold:r===0,color:color.ink,verticalAlignment:'middle',
          alignment:c===0?'left':'center',insets:{left:15,right:12,top:8,bottom:8}};
      }
      text(s,item.body.join('\n\n'),80,185+height,1120,455-height,27,false,color.body,'table-explanation');
      tableSlides.push(i+1);
    } else {
      text(s,item.body.join('\n\n'),82,170,1108,445,31,false,color.body,'main-explanation');
    }
  }
  text(s,item.source,66,679,1080,26,15,false,color.gray,'source-footer');
  text(s,String(i+1).padStart(2,'0'),1168,679,50,26,16,false,color.gray,'slide-number');
}

const finalPath=path.join(root,'reports/metamem-reading-and-pilot-20261019-v2.pptx');
const candidate=path.join(build,'candidate.pptx');
const existingChartDrafts=new Set((await fs.readdir(root)).filter(n=>n.startsWith('.chart-data-')));
await (await PresentationFile.exportPptx(pres)).save(candidate);
const previews=path.join(build,'slide-previews');
await fs.mkdir(previews,{recursive:true});
for(const [i,s] of pres.slides.items.entries()) {
  const png=await pres.export({slide:s,format:'png',scale:1.2});
  await fs.writeFile(path.join(previews,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
  const layout=await s.export({format:'layout'});
  await fs.writeFile(path.join(previews,`slide-${String(i+1).padStart(2,'0')}.layout.json`),await layout.text());
}
const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath,
  pythonExecutable:python,
  integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',
    ...tableSlides.flatMap(n=>['--require-native-table-slide',String(n)])],
  explicitTotalSlideCount:content.slides.length,
  requiredNativeTableOwnerSlides:tableSlides,requiredNativeChartOwnerSlides:chartSlides,
  materializeLiteralChartWorkbooks:true,
  fontPolicy:{basis:'design',families:[FONT]},verifyArtifactToolImport:true,
  receiptPath:path.join(build,'presentation-validation-v2.json')});
for(const name of (await fs.readdir(root)).filter(n=>n.startsWith('.chart-data-')&&!existingChartDrafts.has(n))) {
  const source=path.resolve(root,name), target=path.resolve(build,name);
  if(path.dirname(source)!==root || path.dirname(target)!==build) throw new Error('Chart draft outside build scope');
  await fs.rename(source,target);
}
console.log(JSON.stringify({finalPath,slides:content.slides.length,tableSlides,chartSlides,result}));
