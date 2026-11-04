"""Shared label-free BM25/RRF/MMR and complete-context M/N packing for B/D."""
import math
import re
from collections import Counter

FORBIDDEN = {'answer', 'reference_answer', 'reference_evidence', 'labels', 'label', 'score',
             'prediction', 'judge', 'gold', 'evidence'}


def reject_annotations(value):
    if isinstance(value, dict):
        if FORBIDDEN.intersection(value):
            raise ValueError('Scoring annotations are not candidate inputs')
        for child in value.values():
            reject_annotations(child)
    elif isinstance(value, list):
        for child in value:
            reject_annotations(child)


def normalize(vector):
    if not isinstance(vector, list) or not vector or any(type(x) not in (int, float) or not math.isfinite(x) for x in vector):
        raise ValueError('Expected a finite vector')
    norm = math.sqrt(sum(x*x for x in vector))
    if not norm:
        raise ValueError('Zero vector')
    return [x/norm for x in vector]


def canonical_units(units):
    """Merge only identical IDs with identical payload; never merge equal text across IDs."""
    reject_annotations(units)
    bank, duplicates = {}, []
    for unit in units:
        if set(unit) != {'id', 'kind', 'text', 'vector', 'source_ids', 'parent', 'position'}:
            raise ValueError('Candidate fields differ from the shared contract')
        if not isinstance(unit['id'], str) or not unit['id'] or unit['kind'] not in ('event', 'synthesis_sentence'):
            raise ValueError('Invalid candidate ID/kind')
        if not isinstance(unit['text'], str) or not unit['text'].strip():
            raise ValueError('Missing candidate text')
        ids = unit['source_ids']
        if not isinstance(ids, list) or not ids or any(not isinstance(s, str) or not s for s in ids) or len(set(ids)) != len(ids):
            raise ValueError('Missing or duplicate source IDs')
        if unit['kind'] == 'event':
            if unit['parent'] is not None or unit['position'] is not None:
                raise ValueError('Event cannot have a synthesis parent')
            if unit['id'] != ids[0]:
                raise ValueError('Event ID must be its primary source ID')
        elif not isinstance(unit['parent'], str) or not unit['parent'] or type(unit['position']) is not int or unit['position'] < 0:
            raise ValueError('Sentence needs parent and position')
        normalize(unit['vector'])
        if unit['id'] in bank:
            if bank[unit['id']] != unit:
                raise ValueError('Conflicting duplicate candidate ID')
            duplicates.append(unit['id'])
        bank[unit['id']] = unit
    if len({len(u['vector']) for u in bank.values()}) > 1:
        raise ValueError('Candidate vector dimensions differ')
    return [bank[k] for k in sorted(bank)], duplicates


def hybrid_rank(units, query_vector, question, config, top_k=None):
    """All methods share this pool and scores. top_k optionally performs dense/lex recall."""
    from nltk.stem import PorterStemmer
    units, duplicates = canonical_units(units)
    query = normalize(query_vector)
    if not units:
        return {'units': [], 'scores': {}, 'duplicates': duplicates, 'similarity': {}}
    if len(query) != len(units[0]['vector']):
        raise ValueError('Query/corpus dimension mismatch')
    vectors = {u['id']: normalize(u['vector']) for u in units}
    dense = {uid: sum(a*b for a,b in zip(v, query)) for uid,v in vectors.items()}
    stemmer = PorterStemmer()
    lexical = dict(zip([u['id'] for u in units], bm25([words(u['text'],stemmer) for u in units], words(question,stemmer),config)))
    dense_order = sorted(dense, key=lambda uid:(-dense[uid], uid))
    lexical_order = sorted((uid for uid in lexical if lexical[uid]>0),key=lambda uid:(-lexical[uid],uid))
    if top_k is not None:
        if type(top_k) is not int or top_k<1:
            raise ValueError('Invalid recall limit')
        dense_order,lexical_order=dense_order[:top_k],lexical_order[:top_k]
    dr,lr=({uid:i+1 for i,uid in enumerate(order)} for order in (dense_order,lexical_order))
    ids=set(dr)|set(lr)
    rrf={uid:sum(1/(config['rrf_k']+r[uid]) for r in (dr,lr) if uid in r) for uid in ids}
    maximum=max(rrf.values())
    scores={uid:{'dense':dense[uid],'bm25':lexical[uid],'dense_rank':dr.get(uid),'lexical_rank':lr.get(uid),'rrf':rrf[uid],'relevance':rrf[uid]/maximum} for uid in sorted(ids)}
    similarity={uid:{other:max(0,min(1,sum(a*b for a,b in zip(vectors[uid],vectors[other])))) for other in ids} for uid in ids}
    return {'units':[u for u in units if u['id'] in ids],'scores':scores,'duplicates':duplicates,'similarity':similarity}


def summary_parts(text):
    header,body=text.split('\n',1)
    if not header.startswith('Time range:'):
        raise ValueError('Missing synthesis time range')
    return header,[s for s in re.split(r'(?<=[.!?])\s+|\n+',body) if s]


def validate_parents(units, parents):
    reject_annotations(parents)
    bank={}
    for p in parents:
        if set(p) != {'id','text','source_ids'} or p['id'] in bank or not p['source_ids'] or any(not isinstance(x,str) or not x for x in p['source_ids']):
            raise ValueError('Invalid/duplicate parent synthesis')
        if p['source_ids'][0] != p['id']:
            raise ValueError('Parent ID must be its primary source ID')
        header,spans=summary_parts(p['text'])
        bank[p['id']]={**p,'header':header,'spans':spans}
    positions=set()
    for u in units:
        if u['kind']=='synthesis_sentence':
            p=bank.get(u['parent']);position=u['position']
            if p is None or position>=len(p['spans']) or p['spans'][position]!=u['text'] or p['source_ids']!=u['source_ids']:
                raise ValueError('Sentence is not bound to parent text/source')
            if (u['parent'],position) in positions:
                raise ValueError('Same parent position has multiple candidate IDs')
            positions.add((u['parent'],position))
    return bank


def render_selection(selected, units, parents, fixed=()):
    """D may reuse this renderer after computing its own dependency closure."""
    bank={u['id']:u for u in units}
    if not set(selected)<=set(bank):
        raise ValueError('Unknown selected candidate')
    contexts=[{'source_ids':parents[uid]['source_ids'],'kind':'synthesis','text':parents[uid]['text']} for uid in fixed]
    groups={}
    for uid in selected:
        u=bank[uid]
        if u['kind']=='synthesis_sentence':
            groups.setdefault(u['parent'],set()).add(u['position'])
    for parent in sorted(groups):
        p=parents[parent];positions=sorted(groups[parent]);pieces=[];prev=-1
        for pos in positions:
            if pos>prev+1:pieces.append('[...]')
            pieces.append(p['spans'][pos]);prev=pos
        if prev<len(p['spans'])-1:pieces.append('[...]')
        contexts.append({'source_ids':p['source_ids'],'kind':'synthesis','text':p['header']+'\n'+'\n'.join(pieces)})
    for uid in sorted(selected):
        u=bank[uid]
        if u['kind']=='event':contexts.append({'source_ids':u['source_ids'],'kind':'event','text':u['text']})
    return contexts


def select_contexts(ranked, parents, variant, budget, config):
    if variant not in ('M','N'):
        raise ValueError('B implements M/N only; A dependency closure belongs to D')
    units=ranked['units'];pb=validate_parents(units,parents)
    fixed=[p['id'] for p in parents] if variant=='M' else []
    if variant=='M' and len(fixed)!=5:
        raise ValueError('M requires exactly five complete fixed syntheses')
    selected=set();steps=[]
    contexts=render_selection(selected,units,pb,fixed)
    budget.prepare(contexts)  # Fixed five must fit intact.
    remaining={u['id'] for u in units if variant=='N' or u['kind']=='event'}
    while remaining:
        values={}
        for uid in remaining:
            red=max((ranked['similarity'][uid][other] for other in selected),default=0)
            values[uid]=(config['mmr_relevance']*ranked['scores'][uid]['relevance']-config['mmr_redundancy']*red,red)
        uid=min(remaining,key=lambda u:(-values[u][0],u));remaining.remove(uid)
        proposed=render_selection(selected|{uid},units,pb,fixed)
        cost=budget.count(proposed)
        accepted=cost<=budget.max_tokens
        steps.append({'id':uid,'utility':values[uid][0],'redundancy':values[uid][1],'accepted':accepted,'reason':'selected' if accepted else 'whole_selection_exceeds_budget','proposed_tokens':cost})
        if accepted:selected.add(uid)
    contexts=render_selection(selected,units,pb,fixed)
    evidence=budget.prepare(contexts)
    return {'contexts':contexts,'selected_ids':sorted(selected),'fixed_parent_ids':fixed,'steps':steps,'evidence':evidence}


STOP = set("a an the is are was were be been being do does did has have had can could would should will may might to of in on at by for from with and or but as it its his her their them he she they you your i me my we our what which who when where why how both any kind around currently recently recent get got go went use instead together".split())

def words(text, stemmer):
    return [stemmer.stem(w) for w in re.findall(r"[a-z]+|\d+", text.lower()) if w not in STOP]


def bm25(documents, query, config):
    counts = [Counter(d) for d in documents]
    df = Counter(w for d in documents for w in set(d))
    average = sum(map(len, documents)) / len(documents)
    if average == 0:
        return [0.0] * len(documents)
    scores = []
    for terms, doc in zip(counts, documents):
        score = 0.0
        for word in sorted(set(query)):
            frequency = terms[word]
            idf = math.log(1 + (len(documents) - df[word] + 0.5) / (df[word] + 0.5))
            denominator = frequency + config["bm25_k1"] * (1 - config["bm25_b"] + config["bm25_b"] * len(doc) / average)
            score += idf * frequency * (config["bm25_k1"] + 1) / denominator
        scores.append(score)
    return scores

