"""Offline check of existing F handoffs. Never calls a model or opens held-out data."""
import argparse, hashlib, json, sys
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from src.llm_client import build_messages

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def key(x): return x['sample_id'],x['qa_index']

def verify(s0,s2,selection):
    expected=read(selection); keys=[key(x) for x in expected]; assert len(keys)==len(set(keys))==30
    assert Counter(x['category'] for x in expected)=={1:8,2:8,3:7,4:7}
    result={'new_model_calls':0,'selection_sha256':sha(selection),'methods':{},'judge_rows_independently_recomputed':False}
    for name,d,pname,cname,config_name in [('S0',s0,'predictions.jsonl','calls.jsonl','qa-s0-20261019.json'),('S2',s2,'predictions30.jsonl','calls30.jsonl','qa-structmem-20261020.json')]:
        manifest=read(d/('manifest.json' if name=='S0' else 'files.sha256.json'))
        files=manifest['files'] if name=='S0' else manifest
        for file,v in files.items():
            assert sha(d/file)==(v['sha256'] if isinstance(v,dict) else v),(name,file)
        ps=rows(d/pname);cs=rows(d/cname);config=read(d/config_name)
        assert [key(x) for x in ps]==keys==[key(x) for x in cs]
        for p,c,q in zip(ps,cs,expected):
            assert p['question']==q['question'] and p['category']==q['category']
            assert p['method']==c['method']==name
            assert p['status']==c['status']=='ok' and p['simulated'] is False and c['simulated'] is False
            assert p['finish_reason']==c['finish_reason']=='stop'
            assert c['request']['messages']==build_messages(config,name,p)
            for f in ['model','temperature','top_p','max_tokens']:assert c['request'][f]==config[f]
            assert c['request']['thinking']=={'type':'disabled'}
            response=c['raw_response'];assert response['choices'][0]['message']['content']==p['prediction']==c['prediction']
            assert response['usage']==p['usage']==c['usage']
            assert response['model']==p['returned_model']==c['returned_model']
            assert Counter(x['kind'] for x in p['contexts'])==({'raw':60} if name=='S0' else {'event':60,'synthesis':5})
            assert all(src.startswith(p['sample_id']) for x in p['contexts'] for src in x['source_ids'])
            assert not {'answer','reference_answer','evidence','gold_answer'} & set(p)
        usage={f:sum(p['usage'][f] for p in ps) for f in ['prompt_tokens','completion_tokens','total_tokens']}
        result['methods'][name]={'questions':len(ps),'successful':len(ps),'truncated':0,'usage':usage,'call_seconds':sum(p['seconds'] for p in ps),'prediction_sha256':sha(d/pname),'call_sha256':sha(d/cname),'verified_request_response_pairs':len(ps),'abstentions':sum("don't know" in p['prediction'].lower() for p in ps),'manifest_files_verified':len(files)}
    assert result['methods']['S0']['usage']['total_tokens']==132952
    assert result['methods']['S2']['usage']['total_tokens']==586460
    result['answer_input_ratio']=586282/132531
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--s0-dir',type=Path,required=True);p.add_argument('--s2-dir',type=Path,required=True);p.add_argument('--selection',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=verify(a.s0_dir,a.s2_dir,a.selection)
    with a.out.open('x',encoding='utf-8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(r,indent=2))
