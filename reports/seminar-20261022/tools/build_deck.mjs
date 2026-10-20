import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
const root=process.argv[2], dir=path.join(root,'reports/seminar-20261022');
const data=JSON.parse(await fs.readFile(path.join(dir,'seminar-content.json'),'utf8'));
const dest=process.argv[3];
if(!root||!dest)throw new Error('Usage: node build_deck.mjs REPO OUTPUT_DIRECTORY');
await fs.mkdir(path.join(dest,'preview'),{recursive:true});
await fs.mkdir(path.join(root,'output/build'),{recursive:true});
await fs.mkdir(path.join(root,'output/final'),{recursive:true});
const skill='C:/Users/hp/.codex/plugins/cache/openai-primary-runtime/presentations/26.1017.22135/skills/presentations';
const {finalizePresentation,applyPresentationChartFont}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')));
const font='Microsoft YaHei', ink='#17334F', blue='#28649A', muted='#596B7B', line='#C7D9E9';
const p=Presentation.create({slideSize:{width:1280,height:720}});
p.theme.defaultFont=font;
function txt(s,t,x,y,w,h,size=28,bold=false,color=ink){let o=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});o.text=t;o.text.style={typeface:font,fontSize:size,bold,color};return o;}
function rule(s,y,x=60,w=1160){s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:2},fill:line,line:{fill:'none',width:0}});}
function tab(s,rows,x,y,w,h,widths,size=25){let t=s.tables.add({rows:rows.length,columns:rows[0].length,left:x,top:y,width:w,height:h,values:rows,columnWidths:widths});t.borders.assign({fill:line,width:0.6});for(let i=0;i<rows.length;i++)for(let j=0;j<rows[0].length;j++){let c=t.getCell(i,j);c.fill=i===0?'#EAF2F8':'#FFFFFF';c.text.style={typeface:font,fontSize:size,bold:i===0,color:ink};}return t;}
for(const [i,d] of data.slides.entries()){
 let s=p.slides.add();s.background.fill='#FFFFFF';
 txt(s,d.title,60,35,1160,70,36,true);rule(s,112);
 if(d.kind==='cover'){
  txt(s,d.subtitle,62,160,1130,50,25,false,blue);
  d.lines.forEach((t,j)=>txt(s,t,62,252+j*82,1140,64,j===0?32:27,j===0));
 }else if(['columns','cases'].includes(d.kind)){
  d.columns.forEach((c,k)=>{let x=60+k*600;txt(s,c.heading,x,152,555,70,29,true,blue);c.body.forEach((t,j)=>txt(s,t,x,245+j*(d.kind==='cases'?74:90),548,78,27));});
 }else if(d.kind==='flow'){
  d.lines.forEach((t,j)=>{txt(s,['01','02','03','04'][j],60,148+j*100,58,55,25,true,blue);txt(s,t,132,143+j*100,1070,82,29);if(j<3)rule(s,232+j*100,132,1060);});
 }else if(d.kind==='results'){
  txt(s,'S0  50.0%',65,145,350,58,40,true,blue);txt(s,'S2  63.3%',445,145,350,58,40,true,ink);
  txt(s,'复核后；原始为 53.3% / 63.3%',65,206,900,37,22,false,muted);
  let ch=s.charts.add('bar',{position:{left:55,top:260,width:690,height:310},categories:['1 多跳','2 时间','3 开放域','4 单跳'],series:[{name:'S0',values:[50,62.5,28.6,57.1],fill:'#91B6D1'},{name:'S2',values:[50,87.5,42.9,71.4],fill:blue}],hasLegend:true,legend:{position:'bottom',textStyle:{fontSize:20}},barOptions:{direction:'column',grouping:'clustered',gapWidth:100},xAxis:{textStyle:{fontSize:20}},yAxis:{min:0,max:100,majorUnit:25,numberFormatCode:'0"%"',textStyle:{fontSize:18},majorGridlines:{fill:'#E6EDF3',width:1}},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.0',textStyle:{fontSize:17}},chartFill:'#FFFFFF'});applyPresentationChartFont(ch,{fontFamily:font});
  txt(s,'输入成本',790,270,400,42,28,true,blue);txt(s,'132,531 → 586,282 tokens\n约 4.42 倍\n回答费用约 ¥0.27 → ¥1.17',790,335,410,180,26);
  txt(s,'分母：8 / 8 / 7 / 7；每组共 30 题',65,569,1080,32,22,false,muted);
 }else if(d.rows){
  tab(s,d.rows,60,150,1160,d.kind==='team'?405:380,d.kind==='team'?[320,610,230]:[300,520,340],d.kind==='team'?23:25);
 }else{d.lines.forEach((t,j)=>txt(s,t,65,160+j*98,1140,82,30,j===0));}
 if(d.bottom)txt(s,d.bottom,60,603,1160,57,20,false,muted);
 txt(s,d.source,60,675,1100,26,14,false,muted);txt(s,`${i+1} / 11`,1160,675,90,26,15,false,muted);
 s.speakerNotes.text=`${d.seconds?`计划 ${d.seconds} 秒。`:'答辩备用页。'}\n${d.speech}\n来源：${d.source}\nAI辅助编制，成员人工验收未填写。`;
 if(i>=9)s.hidden=true;
}
for(const [i,s] of p.slides.items.entries()){const blob=await p.export({slide:s,format:'png',scale:1});await fs.writeFile(path.join(dest,'preview',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await blob.arrayBuffer()));}
// PDF preview is assembled from the checked PNGs; this runtime's PDF font package is unavailable.
const candidate=path.join(root,'output/build/candidate.pptx');await (await PresentationFile.exportPptx(p)).save(candidate);
const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:path.join(root,'output/final/第8队-研讨候选-20261020.pptx'),pythonExecutable:'C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit','--require-native-table-slide','4','--require-native-table-slide','8','--require-native-table-slide','10'],explicitTotalSlideCount:11,requiredNativeTableOwnerSlides:[4,8,10],requiredNativeChartOwnerSlides:[5],materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,receiptPath:path.join(root,'output/build/pptx-validation.json')});
await fs.copyFile(path.join(root,'output/final/第8队-研讨候选-20261020.pptx'),path.join(dest,'第8队-研讨候选-20261020.pptx'));
await fs.writeFile(path.join(root,'output/build/inspect.ndjson'),(await p.inspect({kind:'slide,textbox,table,chart,notes',maxChars:100000})).ndjson);
console.log(JSON.stringify({slides:p.slides.items.length,destination:dest,result}));
