"""Bind the separate evidence-quality review to the actual supplied facts."""
import argparse
import sys
import re
from pathlib import Path
from collections import Counter
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from metamem_pilot.data import read, write_atomic, digest
from summarize_stage3 import bind


def citation_existence(item):
    # IDs in this frozen corpus use a session:turn:chunk form; inspect literal IDs anywhere in the answer.
    cited=re.findall(r'[A-Za-z0-9_-]+:\d+:\d+',item['response'])
    for bracket in re.findall(r'\[([^\]\n]+)\]',item['response']):
        for token in bracket.split(','):
            token=re.sub(r'^Fact ID\s*:\s*','',token.strip(),flags=re.I)
            if re.fullmatch(r'[A-Za-z0-9_-]+(?::\d+)*',token) and re.search(r'[0-9_]',token):
                cited.append(token)
    cited=list(dict.fromkeys(cited))
    known={f['fact_id'] for f in item['facts']}
    invalid=[c for c in cited if c not in known]
    return ('invalid' if invalid else 'valid' if cited else 'none'), cited, invalid


def validate_binding(out, queue, rows):
    by={r['sample_id']:r for r in rows if r['status']=='generated'}
    sources={r['question_id']:r for r in read(ROOT/'data/pilot/validation.inputs.json')}
    if len(queue)!=len(by) or {r['sample_id'] for r in queue}!=set(by):raise ValueError('Quality/generated IDs mismatch')
    for item in queue:
        row=by[item['sample_id']];source=sources[row['question_id']]
        if any(item[k]!=source[k] for k in ['question','question_date','facts']) or item['response']!=row['response']:
            raise ValueError('Quality source binding changed')


def validate(queue, review, policy):
    if review['version'] != policy['version'] or review['queue_sha256'] != digest(queue) or review['policy_sha256'] != digest(policy):
        raise ValueError('Quality version/queue mismatch')
    if review['reviewer']['type'] != 'external_ai_app' or review['reviewer']['human_gold'] is not False:
        raise ValueError('External AI provenance required')
    items = {r['sample_id']:r for r in queue}
    results = {r['sample_id']:r for r in review['results']}
    if len(items)!=len(queue) or len(results)!=len(review['results']) or set(items)!=set(results):
        raise ValueError('Missing/duplicate quality rows')
    for sid, item in items.items():
        payload={k:v for k,v in item.items() if k!='input_sha256'}
        if digest(payload)!=item['input_sha256'] or results[sid]['input_sha256']!=item['input_sha256']:
            raise ValueError('Quality input mismatch')
        dimensions=results[sid]['dimensions']
        if set(dimensions)!=set(policy['dimensions']) or any(v not in policy['dimensions'][k] for k,v in dimensions.items()):
            raise ValueError('Invalid quality dimension')
        if not results[sid]['reason'].strip():raise ValueError('Missing quality basis')
    return results


def export(out):
    rows,queue,_=bind(out)
    by={r['sample_id']:r for r in rows}
    sources={r['question_id']:r for r in read(ROOT/'data/pilot/validation.inputs.json')}
    policy=read(ROOT/'configs/evidence-quality-v1.json')
    quality=[]
    for item in queue:
        row=by[item['sample_id']];source=sources[row['question_id']]
        q={'sample_id':item['sample_id'],'question':item['question'],'question_date':source['question_date'],
           'response':item['response'],'facts':source['facts'],'policy_sha256':digest(policy)}
        q['input_sha256']=digest(q);quality.append(q)
    for name,obj in [('quality.queue.hidden.json',quality),('quality.policy.frozen.json',policy)]:
        if (out/name).exists():raise FileExistsError(name)
        write_atomic(out/name,obj)


def summarize(out,audit):
    rows,_,_=bind(out);queue=read(out/'quality.queue.hidden.json');policy=read(out/'quality.policy.frozen.json')
    validate_binding(out,queue,rows)
    items={r['sample_id']:r for r in queue}
    primary=validate(queue,read(out/'quality.reviews.json'),policy)
    extra={}
    if audit:
        aq=read(audit/'quality.queue.hidden.json')
        originals={r['sample_id']:r for r in queue}
        if any(r!=originals.get(r['sample_id']) for r in aq):raise ValueError('Audit quality queue differs')
        extra=validate(aq,read(audit/'quality.reviews.json'),policy)
    assessed=[];disagreements=[]
    for row in rows:
        if row['status']!='generated':continue
        sid=row['sample_id'];initial=primary[sid];dims=dict(initial['dimensions'])
        if sid in extra:
            for key,value in dims.items():
                other=extra[sid]['dimensions'][key]
                if value!=other:
                    disagreements.append({'sample_id':sid,'dimension':key,'primary':value,'audit':other})
                    dims[key]='uncertain' if key!='citation_existence' else value
        existence,cited,invalid=citation_existence(items[sid])
        if dims['citation_existence']!=existence:
            raise ValueError('Citation existence requires manual inspection of notation: '+sid)
        assessed.append({**{k:row[k] for k in ['sample_id','question_id','round','condition']},'dimensions':dims,'literal_citations':cited,'invalid_ids':invalid,'primary':initial,'audit':extra.get(sid),'human_acceptance':None})
    totals={c:{d:dict(Counter(r['dimensions'][d] for r in assessed if r['condition']==c)) for d in policy['dimensions']} for c in ['baseline','candidate']}
    result={'version':policy['version'],'totals':totals,'rows':assessed,'disagreements':disagreements,'primary_reviews':len(primary),'audit_reviews':len(extra),'missing_or_failed':sum(r['status']!='generated' for r in rows),'human_acceptance':None}
    dest=out/('quality.summary.reviewed.json' if audit else 'quality.summary.json')
    if dest.exists():raise FileExistsError(dest)
    write_atomic(dest,result)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--export',action='store_true');p.add_argument('--audit',type=Path)
    a=p.parse_args()
    if a.export:export(a.out)
    else:summarize(a.out,a.audit)
