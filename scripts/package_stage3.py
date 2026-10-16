"""Create the small tracked stage-three results from validated local artifacts."""
import argparse
import json
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from metamem_pilot.data import read,write,digest,file_hash
from summarize_stage3 import bind
from summarize_stability import validate_review
from stage3_quality import validate,validate_binding


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--audit',type=Path,required=True)
    a=p.parse_args();rows,queue,policy=bind(a.out)
    validate_review(queue,read(a.out/'reviews.json'),policy)
    validate_review(read(a.audit/'queue.hidden.json'),read(a.audit/'reviews.json'),policy)
    qq=read(a.out/'quality.queue.hidden.json');qp=read(a.out/'quality.policy.frozen.json')
    validate_binding(a.out,qq,rows);validate(qq,read(a.out/'quality.reviews.json'),qp)
    validate(read(a.audit/'quality.queue.hidden.json'),read(a.audit/'quality.reviews.json'),qp)
    result=read(a.out/'summary.reviewed.json');quality=read(a.out/'quality.summary.reviewed.json')
    result['quality']={k:v for k,v in quality.items() if k!='rows'}
    result['quality']['rows']=[{k:r[k] for k in ['sample_id','question_id','round','condition','dimensions','literal_citations','invalid_ids','human_acceptance']} for r in quality['rows']]
    result['verification']=read(a.out/'verification.json')
    result['session']=read(a.out.parent/'session.json')
    result['cleanup_independent']=read(a.out.parent/'cleanup-independent.json')
    samples=[json.loads(l) for l in (a.out.parent/'gpu-samples.jsonl').read_text(encoding='utf-8').splitlines()]
    result['gpu']={'sample_count':len(samples),'sampled_peak_mib':max(int(r['sample'].split(',')[0]) for r in samples),'sampling_note':'5-second samples started after service launch; not an exact instantaneous peak'}
    log=ROOT/'output/ollama-service/20261016-000746.stderr.log'
    trunc=[int(x) for x in re.findall(r'truncated = (\d+)',log.read_text(encoding='utf-8',errors='replace'))]
    assert len(trunc)==61 and not any(trunc)
    result['server_truncation']={'logged_calls':len(trunc),'nonzero':sum(x>0 for x in trunc),'log_sha256':file_hash(log)}
    paths=[a.out/n for n in ['answers.json','calls.jsonl','queue.hidden.json','reviews.json','quality.queue.hidden.json','quality.reviews.json','summary.reviewed.json','quality.summary.reviewed.json','verification.json']]+[a.audit/n for n in ['reviews.json','quality.reviews.json','scope.frozen.json']]
    result['source_hashes']={str(path.resolve().relative_to(ROOT)).replace('\\','/'):file_hash(path) for path in paths}
    result['ai_assessments']={'correctness':98,'quality':98,'unique_generated_answers':60,'human_gold':False,'exact_deployment_version':'unknown'}
    result['adoption']='Retain as optional research candidate/negative result; do not change default. Local quantity/verbosity benefits do not offset uncorrected abstention and dinner regression.'
    write(ROOT/'reports/metamem-stage3-results.json',result)
