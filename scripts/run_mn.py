"""Offline M/N selection from label-free, precomputed common candidate bundles."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src')]
from hybrid_retrieval import hybrid_rank,select_contexts,reject_annotations
from flat_rag import load_questions,json_hash


def run(bundle, questions, out, cache, config_path=None, max_tokens=4096):
    from evidence_budget import EvidenceBudget
    if out.exists():raise FileExistsError(out)
    config_path=config_path or ROOT/'configs/phase2-anchor-pilot.json'
    config=json.loads(config_path.read_text(encoding='utf-8'))['ranking']
    frozen=json.loads((ROOT/'configs/locomo-smoke.json').read_text(encoding='utf-8'))
    if hashlib.sha256(questions.read_bytes()).hexdigest()!=frozen['output_sha256'].get(questions.name):
        raise ValueError('Question file does not match A frozen input hash')
    allowed={(q['sample_id'],q['qa_index']):q for q in load_questions(questions)}
    devkeys={(q['sample_id'],q['qa_index']) for q in frozen['questions']}
    if not set(allowed)<=devkeys:raise ValueError('Only frozen development questions are supported')
    rows=[json.loads(line) for line in bundle.read_text(encoding='utf-8').splitlines()]
    if not rows:raise ValueError('Empty candidate bundle')
    budget=EvidenceBudget(max_tokens,cache);outputs={'M':[],'N':[]};traces=[];seen=set()
    for row in rows:
        reject_annotations(row)
        if set(row)!={'sample_id','qa_index','question','category','query_vector','units','parents','embedding','scope'}:
            raise ValueError('Unexpected bundle fields')
        key=row['sample_id'],row['qa_index']
        if key in seen or key not in allowed:raise ValueError('Duplicate/unknown development identity')
        seen.add(key)
        identity={k:row[k] for k in ('sample_id','qa_index','question','category')}
        if identity!=allowed[key] or row['embedding']!=frozen['embedding']:
            raise ValueError('Frozen question/embedding mismatch')
        if not isinstance(row['scope'],str) or not row['scope'].strip():raise ValueError('Candidate scope required')
        for item in row['units']+row['parents']:
            if not item['id'].startswith(row['sample_id']+'/') or any(not sid.startswith(row['sample_id']+'/') for sid in item['source_ids']):
                raise ValueError('Cross-conversation candidate/source')
        if len(row['query_vector'])!=frozen['embedding']['dimensions']:raise ValueError('Embedding dimension mismatch')
        ranked=hybrid_rank(row['units'],row['query_vector'],row['question'],config)
        results={v:select_contexts(ranked,row['parents'],v,budget,config) for v in outputs}
        for v,result in results.items():outputs[v].append({**identity,'contexts':result['contexts']})
        traces.append({**identity,'scope':row['scope'],'candidate_sha256':json_hash(row['units']),
                       'common_ranking_sha256':json_hash(ranked),'duplicates':ranked['duplicates'],
                       'scores':ranked['scores'],'units':[{k:v for k,v in u.items() if k!='vector'} for u in ranked['units']],
                       'parents':row['parents'],'variants':results})
    out.mkdir(parents=True,exist_ok=False)
    for v,values in outputs.items():
        (out/f'{v}.inputs.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in values),encoding='utf-8',newline='\n')
    (out/'bundles.jsonl').write_bytes(bundle.read_bytes())
    (out/'trace.json').write_text(json.dumps(traces,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    manifest={'status':'offline_contexts_only','questions':len(rows),'variants':['M','N'],'budget':max_tokens,
              'ranking':config,'bundle_sha256':hashlib.sha256(bundle.read_bytes()).hexdigest(),
              'scopes':sorted({r['scope'] for r in rows}),'embedding':frozen['embedding'],
              'code_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in
                             [Path(__file__),ROOT/'src/hybrid_retrieval.py',ROOT/'src/evidence_budget.py']},
              'answer_calls':0,'judge_calls':0,'accuracy':None}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['bundle','questions','out','tokenizer-cache']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--config',type=Path);p.add_argument('--max-tokens',type=int,default=4096)
    a=p.parse_args();print(json.dumps(run(a.bundle,a.questions,a.out,a.tokenizer_cache,a.config,a.max_tokens)))
