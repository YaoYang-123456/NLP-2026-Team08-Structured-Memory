"""Validate stage-two provenance, produce paired statistics and a single audit queue."""
import argparse
import json
from collections import Counter
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"src"),str(ROOT/"scripts")]
from metamem_pilot.data import read,write_atomic,digest,file_hash
from summarize_stability import validate_review,score,conservative_label
from run_stage2 import prepare_slots
from run_pilot import call_events

PAIRS=[("C","A"),("D","B"),("B","A"),("D","C")]


def category(target, baseline):
    if target not in ("Yes","No") or baseline not in ("Yes","No"):
        return "incomparable"
    return "both_correct" if target==baseline=="Yes" else "both_wrong" if target==baseline=="No" else "only_target" if target=="Yes" else "only_baseline"


def bind(out):
    plan, frozen = read(out/"plan.frozen.json"),read(out/"inputs.frozen.json")
    for path,sha in frozen.items():
        if file_hash(ROOT/path)!=sha:raise ValueError("Inputs changed")
    indexed=lambda path:{r['question_id']:r for r in read(ROOT/path)}
    expected,by=prepare_slots(indexed('data/pilot/validation.inputs.json'),indexed('output/stage2-retrieval/validation.improved.inputs.json'),indexed('output/stage2-preparation/oracle.inputs.json'))
    rows,queue,policy=read(out/'answers.json'),read(out/'queue.hidden.json'),read(out/'policy.frozen.json')
    if digest(policy)!=plan['policy_sha256']:raise ValueError('Policy changed')
    cols=['phase','round','condition','question_id','retrieval','learned','facts_sha256']
    if [[r[k] for k in cols] for r in rows]!=[[r[k] for k in cols] for r in expected]:raise ValueError('Missing/duplicate/unexpected coordinates')
    if len({r['sample_id'] for r in rows})!=len(rows):raise ValueError('Duplicate sample ID')
    queued={r['sample_id']:r for r in queue}
    if len(queued)!=len(queue) or {r['sample_id'] for r in rows if r['status']=='generated'}!=set(queued):raise ValueError('Queue/output mismatch')
    learned=read(ROOT/plan['rules_file'])['rules']
    if file_hash(ROOT/plan['rules_file'])!=plan['rules_file_sha256']:raise ValueError('Rules changed')
    for r in rows:
        if r['rules_sha256']!=digest(learned if r['learned'] else []):raise ValueError('Rule binding changed')
        if r['status']!='generated':continue
        item=queued[r['sample_id']];source=by[r['retrieval']][r['question_id']]
        if item['response']!=r['response'] or item['question']!=source['question'] or item['applicable_strict_abstention']!=r['question_id'].endswith('_abs'):raise ValueError('Response/question binding changed')
    return rows,queue,policy


def statistics(rows):
    result={}
    for phase,conditions in [('oracle',['original','oracle']),('main',['A','B','C','D'])]:
        subset=[r for r in rows if r['phase']==phase]
        pairs=PAIRS if phase=='main' else [('oracle','original')]
        rounds,per_question,paired={},{},{}
        for repeat in range(3):
            rr=[r for r in subset if r['round']==repeat]
            rounds[str(repeat)]={c:score([r for r in rr if r['condition']==c]) for c in conditions}
            for qid in dict.fromkeys(r['question_id'] for r in rr):
                labels={r['condition']:r.get('label') for r in rr if r['question_id']==qid}
                per_question.setdefault(qid,{})[str(repeat)]=labels
                for target,baseline in pairs:
                    name=target+'-'+baseline
                    cat=category(labels.get(target),labels.get(baseline))
                    paired.setdefault(name,{}).setdefault(cat,[]).append({'question_id':qid,'round':repeat})
        result[phase]={'overall':{c:score([r for r in subset if r['condition']==c]) for c in conditions},'rounds':rounds,'per_question':per_question,'paired':paired,
                       'abstention':{c:score([r for r in subset if r['condition']==c and r['question_id'].endswith('_abs')]) for c in conditions}}
    return result


def primary(out):
    rows,queue,policy=bind(out)
    review=read(out/'reviews.json');labels=validate_review(queue,review,policy)
    linked=[{**r,**({'label':labels[r['sample_id']]['label'],'assessment':labels[r['sample_id']]} if r['sample_id'] in labels else {}),'human_acceptance':None} for r in rows]
    return linked,queue,policy,review


def save_summary(out,audit=None):
    linked,queue,policy,review=primary(out)
    suffix='.reviewed' if audit else ''
    if (out/('summary'+suffix+'.json')).exists():raise FileExistsError('Preserve previous summary')
    changes=[];extra=0
    if audit:
        aq,ar=read(audit/'queue.hidden.json'),read(audit/'reviews.json')
        originals={r['sample_id']:r for r in queue}
        if any(r!=originals.get(r['sample_id']) for r in aq):raise ValueError('Audit must be an exact original subset')
        scope=read(audit/'scope.frozen.json')
        if scope['queue_sha256']!=digest(aq):raise ValueError('Audit scope mismatch')
        reviewed=validate_review(aq,ar,policy);extra=len(reviewed)
        for row in linked:
            sid=row['sample_id']
            if sid not in reviewed:continue
            row['primary_label']=row['label'];row['audit_assessment']=reviewed[sid]
            row['label']=conservative_label(row['label'],reviewed[sid]['label'])
            if row['primary_label']!=reviewed[sid]['label']:
                changes.append({k:row[k] for k in ['sample_id','phase','question_id','round','condition','primary_label','label','assessment','audit_assessment']})
    usage_by_condition={}
    coordinates={r['sample_id']:r for r in linked}
    for call in call_events(out/'calls.inherited.jsonl')+call_events(out/'calls.jsonl'):
        row=coordinates.get(call['question_id'])
        key=row['phase']+':'+row['condition'] if row else 'warmup'
        cost=usage_by_condition.setdefault(key,{'requests':0,'seconds':0,'prompt_tokens':0,'completion_tokens':0,'failures':0})
        cost['requests']+=1;cost['seconds']+=call['seconds'];cost['failures']+=call['status']!='ok'
        for token in ['prompt_tokens','completion_tokens']:cost[token]+=(call.get('usage') or {}).get(token,0)
    summary={**statistics(linked),'cost_by_condition':usage_by_condition,'scoring_version':policy['version'],'primary_reviews':len(review['results']),'audit_reviews':extra,'disagreements':changes,'human_acceptance':None,'independent_main_questions':10,'generation_usage':read(out/'run.json'),'source_review_sha256':file_hash(out/'reviews.json')}
    if audit:summary['audit_review_sha256']=file_hash(audit/'reviews.json')
    write_atomic(out/('assessed-answers'+suffix+'.json'),linked)
    write_atomic(out/('summary'+suffix+'.json'),summary)
    print({p:summary[p]['overall'] for p in ['oracle','main']})


def prepare_audit(out,dest):
    dest.mkdir(parents=True,exist_ok=False)
    linked,queue,policy,review=primary(out)
    selected={(r['question_id'],r['round']) for r in linked if r['phase']=='main' and (r['question_id'].endswith('_abs') or r['question_id'] in ['0a995998','cc6d1ec1'])}
    for repeat in range(3):
        for qid in dict.fromkeys(r['question_id'] for r in linked if r['phase']=='main'):
            labels={r['condition']:r.get('label') for r in linked if r['phase']=='main' and r['round']==repeat and r['question_id']==qid}
            if any(labels.get(a)!=labels.get(b) for a,b in PAIRS):selected.add((qid,repeat))
    ids={r['sample_id'] for r in linked if r['phase']=='oracle' or (r['question_id'],r['round']) in selected}
    aq=[r for r in queue if r['sample_id'] in ids]
    write_atomic(dest/'queue.hidden.json',aq);write_atomic(dest/'policy.frozen.json',policy)
    write_atomic(dest/'scope.frozen.json',{'queue_sha256':digest(aq),'count':len(aq),'selection':'all oracle; all main abstention/clothing/bird; every main qid-round with any discordant planned pair; no label shown to reviewer','resolution':'Label disagreement -> uncertain, raw primary preserved','frozen_before_audit':True})
    print({'audit_count':len(aq)})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--audit',type=Path);p.add_argument('--prepare-audit',type=Path)
    args=p.parse_args()
    if args.prepare_audit:prepare_audit(args.out,args.prepare_audit)
    else:save_summary(args.out,args.audit)
