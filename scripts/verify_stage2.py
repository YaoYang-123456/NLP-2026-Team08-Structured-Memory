"""Offline provenance verification for the completed stage-two session chain."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
from metamem_pilot.data import read,write,digest,file_hash
from metamem_pilot.pipeline import answer_prompt
from run_pilot import call_events
from summarize_stage2 import bind

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
rows,queue,policy=bind(a.out)
assert len(rows)==132 and all(r['status']=='generated' for r in rows)
byid={r['sample_id']:r for r in rows}
sources={name:{r['question_id']:r for r in read(ROOT/path)} for name,path in {'original':'data/pilot/validation.inputs.json','oracle':'output/stage2-preparation/oracle.inputs.json','role-balanced':'output/stage2-retrieval/validation.improved.inputs.json'}.items()}
learned=read(ROOT/'configs/rules-stage1-frozen.json')['rules']
config=read(ROOT/'configs/qwen-stability-sampling.json')
events=call_events(a.out/'calls.inherited.jsonl')+call_events(a.out/'calls.jsonl')
answers=[e for e in events if e['question_id']!='__warmup__']
assert len(answers)==132 and len({e['question_id'] for e in answers})==132
for e in answers:
    row=byid[e['question_id']];source=sources[row['retrieval']][row['question_id']]
    expected=answer_prompt(source,learned if row['learned'] else [])
    assert e['prompt']==expected and e['response']==row['response']
    assert e['settings']==config['stages']['answer_eval'] and e['stage']=='answer_eval'
    payload={'model':config['answer']['model'],'messages':[{'role':'user','content':expected}],**e['settings'],'stream':False}
    assert digest(payload)==e['prompt_sha256']
assert all(e['status']=='ok' and e.get('finish_reason')=='stop' for e in events)
old=read(ROOT/'output/strict-abstention-v2-20261015/source-hashes.before.json')
assert all(file_hash(ROOT/'output/external-ai-experiment-20261015-2143'/name)==sha for name,sha in old.items())
stage1=read(ROOT/'reports/metamem-stage1-results.json')['source_hashes']
assert all(file_hash(ROOT/name)==sha for name,sha in stage1.items())
quality=read(ROOT/'output/stage2-quality/reviews.json');q=read(ROOT/'output/stage2-quality/queue.hidden.json');qp=read(ROOT/'output/stage2-quality/policy.frozen.json')
assert quality['queue_sha256']==digest(q) and quality['policy_sha256']==digest(qp)
expected={r['sample_id']:r for r in q};seen=set()
original_queue={r['sample_id']:r for r in queue}
for item in q:
    original=original_queue[item['sample_id']]
    assert all(item[k]==original[k] for k in ['sample_id','input_sha256','question','response'])
    assert digest({k:v for k,v in original.items() if k!='input_sha256'})==original['input_sha256']
quality_counts={c:{} for c in ['original','oracle']}
from collections import Counter
for r in quality['results']:
    assert r['sample_id'] in expected and r['sample_id'] not in seen;seen.add(r['sample_id'])
    assert r['input_sha256']==expected[r['sample_id']]['input_sha256'] and r['human_review'] is None
    for quote in r['attribution_quotes']:assert quote in expected[r['sample_id']]['response']
    condition=byid[r['sample_id']]['condition']
    for field in ['basil_or_mint_correctly_used','cherry_tomatoes_correctly_used','necessary_evidence_correctly_used','unsupported_personal_attribution']:
        assert r[field] in ['yes','no','uncertain']
        quality_counts[condition].setdefault(field,Counter())[r[field]]+=1
assert seen==set(expected)
record={'answers':132,'prompts_reconstructed_exactly':132,'local_requests':len(events),'warmups':len(events)-132,'generation_failures':0,'finish_length':0,'inherited_requests':len(call_events(a.out/'calls.inherited.jsonl')),'reported_prompt_tokens':sum(e['usage']['prompt_tokens'] for e in events),'reported_completion_tokens':sum(e['usage']['completion_tokens'] for e in events),'call_seconds':sum(e['seconds'] for e in events),'max_input_tokens_plus_output_budget':max(e['usage']['prompt_tokens']+e['settings']['max_tokens'] for e in events),'historical_v1_files_unchanged':len(old),'stage1_critical_files_unchanged':len(stage1),'dinner_quality_counts':quality_counts,'human_acceptance':None}
write(a.out/'verification.json',record);print(record)
