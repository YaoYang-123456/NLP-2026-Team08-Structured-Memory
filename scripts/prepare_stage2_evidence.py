"""Prepare explicitly oracle-only evidence and label-free training histories offline."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from metamem_pilot.data import read, write, digest, file_hash, clean_session, retrieve

ROOT = Path(__file__).resolve().parents[1]
SELECTED = {
    '06f04340': ['answer_92d5f7cd:0:0', 'answer_92d5f7cd:4:0'],
    '9d25d4e0': ['answer_fcff2dc4_1:0:0', 'answer_fcff2dc4_2:0:0', 'answer_fcff2dc4_1:8:0'],
}


def array_records(path):
    """Incrementally decode JSON array; caller retains only whitelist records."""
    decoder = json.JSONDecoder()
    with path.open(encoding='utf-8') as stream:
        buf = ''
        eof = False
        while True:
            buf = buf.lstrip(' \r\n\t[,]')
            if not buf and eof:
                return
            try:
                row, end = decoder.raw_decode(buf)
            except json.JSONDecodeError:
                if eof:
                    raise
                part = stream.read(1024 * 1024)
                eof = not part
                buf += part
                continue
            yield row
            buf = buf[end:]


def sanitized(row):
    fields = ('question_id', 'question_type', 'question', 'question_date',
              'haystack_dates', 'haystack_session_ids')
    return {**{k: row[k] for k in fields},
            'haystack_sessions': [clean_session(s) for s in row['haystack_sessions']]}


def all_chunks(row):
    docs = {}
    for sid, date, session in zip(row['haystack_session_ids'], row['haystack_dates'], row['haystack_sessions']):
        for ti, turn in enumerate(session):
            words = turn['content'].split()
            for offset in range(0, len(words), 180):
                fid = f'{sid}:{ti}:{offset // 180}'
                docs[fid] = {'fact_id': fid, 'text': f"{date} {turn['role']}: " + ' '.join(words[offset:offset + 180]),
                             'session_id': sid, 'date': date, 'role': turn['role'],
                             'turn': ti, 'chunk': offset // 180, 'original_turn': turn['content']}
    return docs


def main():
    out = ROOT / 'output/stage2-preparation'
    if out.exists():
        raise FileExistsError('Do not overwrite preparation artifacts')
    validation = read(ROOT / 'output/stage1-evidence/validation-history.json')
    baseline = {r['question_id']: r for r in read(ROOT / 'data/pilot/validation.inputs.json')}
    oracles, diffs = [], []
    for qid, fids in SELECTED.items():
        row = next(r for r in validation if r['question_id'] == qid)
        assert retrieve(row) == baseline[qid], 'Original retrieval does not reproduce'
        chunks = all_chunks(row)
        candidates = [{'fact_id': fid, 'text': chunks[fid]['text'], 'score': None} for fid in fids]
        candidates.extend(f for f in baseline[qid]['facts'] if f['fact_id'] not in fids)
        facts, used = [], 0
        for f in candidates[:20]:
            text = f['text'][:12000-used]
            if not text:
                break
            facts.append({**f, 'text': text})
            used += len(text)
        oracle = {**baseline[qid], 'facts': facts}
        oracles.append(oracle)
        old_ids = [f['fact_id'] for f in baseline[qid]['facts']]
        new_ids = [f['fact_id'] for f in facts]
        diffs.append({'question_id': qid, 'selection': 'reference-assisted oracle, not automatic retrieval',
                      'baseline_facts_sha256': digest(baseline[qid]['facts']), 'oracle_facts_sha256': digest(facts),
                      'baseline_chars': sum(len(f['text']) for f in baseline[qid]['facts']), 'oracle_chars': used,
                      'baseline_count': len(old_ids), 'oracle_count': len(new_ids),
                      'added': [f for f in new_ids if f not in old_ids], 'removed': [f for f in old_ids if f not in new_ids],
                      'baseline_ids': old_ids, 'oracle_ids': new_ids,
                      'selected_sources': [chunks[fid] for fid in fids]})
    train_inputs = read(ROOT / 'data/pilot/train.inputs.json')
    train_ids = {r['question_id'] for r in train_inputs}
    train = []
    for row in array_records(ROOT / 'data/raw/longmemeval_s_cleaned.json'):
        if row['question_id'] in train_ids:
            train.append(row)
        # Other records are discarded; no questions/answers printed or inspected.
    by_id = {r['question_id']: r for r in train}
    assert len(train) == len(by_id) == len(train_ids) == 20
    train = [by_id[r['question_id']] for r in train_inputs]
    for row, saved in zip(train, train_inputs):
        assert retrieve(row) == saved, 'Training baseline mismatch'
        assert retrieve(sanitized(row)) == saved, 'Sanitization changed retrieval'
    write(out / 'oracle.inputs.json', oracles)
    write(out / 'oracle-diff.json', diffs)
    write(out / 'train-history.json', train)
    write(out / 'train.history-inputs.json', [sanitized(r) for r in train])
    write(out / 'oracle-quality-policy.json', {
        'version': 'stage2-oracle-quality-v1', 'frozen_before_generation': True,
        'scope': '06f04340 dinner oracle diagnostic only; independent quality metrics do not replace strict-v2 correctness',
        'reviewer_type': 'external_ai_app', 'human_gold': False,
        'evidence_use': {
            'fields': ['basil_or_mint_correctly_used', 'cherry_tomatoes_correctly_used', 'necessary_evidence_correctly_used'],
            'labels': ['yes', 'no', 'uncertain'],
            'rule': 'First two fields indicate whether a proposed dinner concretely uses each source ingredient group without contradiction; generic mention outside the actual dinner is insufficient. The combined field is yes only when both groups are correctly used, no when either is absent or misused, otherwise uncertain. This is content alignment, not proof the model causally read memory; original retrieval may produce the ingredients by coincidence.'},
        'unsupported_personal_attribution': {
            'labels': ['yes', 'no', 'uncertain'],
            'rule': 'yes if answer asserts unsupported user preferences, experiences, possession or food provenance. History supports cooking with basil/mint and harvesting cherry tomatoes from own garden; it does not establish growing basil/mint or liking a particular cuisine. Plain recipe suggestions and explicit conditional assumptions are not personal factual attribution. Give exact quoted claim and source rationale.'},
        'sources': next(d['selected_sources'] for d in diffs if d['question_id'] == '06f04340'),
        'human_review': None})
    write(out / 'verification.json', {
        'oracle_baseline_exact_reproduction': 2, 'train_baseline_exact_reproduction': 20,
        'sanitized_train_reproduction': 20, 'train_order_matches_inputs': True,
        'oracle_sources_exact_original_chunks': True, 'fact_limit': 20, 'character_limit': 12000,
        'test_boundary': 'Raw JSON parsed incrementally; only 20 training IDs retained; other records immediately discarded without displaying or inspecting contents. Existing validation cache used for oracle. No test inputs/labels opened.',
        'source_hashes': {str(p.relative_to(ROOT)): file_hash(p) for p in [ROOT/'data/raw/longmemeval_s_cleaned.json', ROOT/'data/pilot/train.inputs.json', ROOT/'data/pilot/validation.inputs.json', ROOT/'output/stage1-evidence/validation-history.json']},
        'outputs_sha256': {p.name: file_hash(p) for p in sorted(out.glob('*.json'))}})
    print(json.dumps({'directory': str(out), 'training_rows': len(train), 'oracle_rows': len(oracles), 'verification': 'passed'}))


def audit_improved():
    """Audit fixed candidate facts against already identified development sources."""
    from datetime import datetime
    out = ROOT / 'output/stage2-preparation/improved-evidence-audit.json'
    if out.exists():
        raise FileExistsError(out)
    baseline = {r['question_id']: r for r in read(ROOT / 'data/pilot/validation.inputs.json')}
    improved = read(ROOT / 'output/stage2-retrieval/validation.improved.inputs.json')
    histories = {r['question_id']: r for r in read(ROOT / 'output/stage1-evidence/validation-history.json')}
    known = read(ROOT / 'output/stage1-evidence/evidence-map.json')
    audited = []
    for new in improved:
        qid = new['question_id']
        old = baseline[qid]
        oldf = {f['fact_id']: f for f in old['facts']}
        newf = {f['fact_id']: f for f in new['facts']}
        chunks = all_chunks(histories[qid])
        assert len(newf) == len(new['facts'])
        for f in new['facts']:
            assert chunks[f['fact_id']]['text'].startswith(f['text'])
        dt = lambda x: datetime.strptime(x, '%Y/%m/%d (%a) %H:%M')
        qdate = dt(new['question_date'])
        entries = []
        for item in known:
            if item['question_id'] != qid:
                continue
            fid = item['fact_id']
            entries.append({'fact_id': fid, 'role': item['role'], 'date': item['date'],
                            'baseline_rank': next((i+1 for i,f in enumerate(old['facts']) if f['fact_id']==fid), None),
                            'candidate_rank': next((i+1 for i,f in enumerate(new['facts']) if f['fact_id']==fid), None),
                            'candidate_is_complete_chunk': fid in newf and newf[fid]['text']==chunks[fid]['text'],
                            'candidate_text': newf.get(fid, {}).get('text')})
        audited.append({'question_id': qid, 'known_evidence': entries,
                        'baseline_chars': sum(len(f['text']) for f in old['facts']),
                        'candidate_chars': sum(len(f['text']) for f in new['facts']),
                        'baseline_blocks': len(old['facts']), 'candidate_blocks': len(new['facts']),
                        'added_ids': [fid for fid in newf if fid not in oldf],
                        'removed_ids': [fid for fid in oldf if fid not in newf],
                        'changed_text': [{'fact_id':fid, 'before_chars':len(oldf[fid]['text']), 'after_chars':len(newf[fid]['text']), 'after_text':newf[fid]['text']} for fid in newf if fid in oldf and newf[fid]['text']!=oldf[fid]['text']],
                        'candidate_truncated_chunks': [fid for fid in newf if newf[fid]['text']!=chunks[fid]['text']],
                        'baseline_after_question': [fid for fid in oldf if dt(chunks[fid]['date'])>qdate],
                        'candidate_after_question': [fid for fid in newf if dt(chunks[fid]['date'])>qdate]})
    write(out, {'scope':'10 fixed development questions; targeted known-evidence audit, not recall; no generated answers or scores inspected',
                'source_consistency':'all candidate texts are prefixes of exact original chunks', 'rows':audited,
                'inputs_sha256':file_hash(ROOT/'output/stage2-retrieval/validation.improved.inputs.json')})
    print(json.dumps([{'id':r['question_id'],'chars':r['candidate_chars'],'known':[(e['fact_id'],e['baseline_rank'],e['candidate_rank'],e['candidate_is_complete_chunk']) for e in r['known_evidence']], 'changed':[(x['fact_id'],x['before_chars'],x['after_chars']) for x in r['changed_text']], 'future':(len(r['baseline_after_question']),len(r['candidate_after_question']))} for r in audited], indent=2))


if __name__ == '__main__':
    if sys.argv[1:] == ['--audit-improved']:
        audit_improved()
    elif not sys.argv[1:]:
        main()
    else:
        raise SystemExit('Only --audit-improved is accepted')
