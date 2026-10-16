"""Offline provenance verification for the completed stage-three session chain."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
from metamem_pilot.data import read,write,digest,file_hash
from run_stage3 import stage3_prompt
from run_pilot import call_events
from summarize_stage3 import bind

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
rows,queue,policy=bind(a.out)
assert len(rows)==60 and all(r['status']=='generated' for r in rows)
byid={r['sample_id']:r for r in rows}
sources={r['question_id']:r for r in read(ROOT/'data/pilot/validation.inputs.json')}
config=read(ROOT/'configs/qwen-stability-sampling.json')
events=call_events(a.out/'calls.inherited.jsonl')+call_events(a.out/'calls.jsonl')
answers=[e for e in events if e['question_id']!='__warmup__']
assert len(answers)==60 and len({e['question_id'] for e in answers})==60
for e in answers:
    row=byid[e['question_id']];source=sources[row['question_id']]
    expected=stage3_prompt(source,row['condition'])
    assert e['prompt']==expected and e['response']==row['response']
    assert e['settings']==config['stages']['answer_eval'] and e['stage']=='answer_eval'
    payload={'model':config['answer']['model'],'messages':[{'role':'user','content':expected}],**e['settings'],'stream':False}
    assert digest(payload)==e['prompt_sha256']
assert all(e['status']=='ok' and e.get('finish_reason')=='stop' for e in events)
old=read(ROOT/'output/strict-abstention-v2-20261015/source-hashes.before.json')
assert all(file_hash(ROOT/'output/external-ai-experiment-20261015-2143'/name)==sha for name,sha in old.items())
stage1=read(ROOT/'reports/metamem-stage1-results.json')['source_hashes']
assert all(file_hash(ROOT/name)==sha for name,sha in stage1.items())
stage2=read(ROOT/'reports/metamem-stage2-results.json')['source_hashes']
assert all(file_hash(ROOT/name)==sha for name,sha in stage2.items())
from stage3_quality import validate,validate_binding,citation_existence
quality_queue=read(a.out/'quality.queue.hidden.json');quality_policy=read(a.out/'quality.policy.frozen.json')
validate_binding(a.out,quality_queue,rows)
for item in quality_queue:
    row=byid[item['sample_id']]
    assert item['facts']==sources[row['question_id']]['facts'] and item['response']==row['response']
if (a.out/'quality.reviews.json').exists():
    reviewed=validate(quality_queue,read(a.out/'quality.reviews.json'),quality_policy)
    assert all(citation_existence(item)[0]==reviewed[item['sample_id']]['dimensions']['citation_existence'] for item in quality_queue)
assert read(a.out/'initial-four-operational-check.json')['passed']
record={'answers':60,'prompts_reconstructed_exactly':60,'local_requests':len(events),'warmups':len(events)-60,'generation_failures':0,'finish_length':0,'reported_prompt_tokens':sum(e['usage']['prompt_tokens'] for e in events),'reported_completion_tokens':sum(e['usage']['completion_tokens'] for e in events),'call_seconds':sum(e['seconds'] for e in events),'max_input_tokens_plus_output_budget':max(e['usage']['prompt_tokens']+e['settings']['max_tokens'] for e in events),'historical_v1_files_unchanged':len(old),'stage1_critical_files_unchanged':len(stage1),'stage2_critical_files_unchanged':len(stage2),'human_acceptance':None}
write(a.out/'verification.json',record);print(record)
