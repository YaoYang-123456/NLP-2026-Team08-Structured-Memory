"""Prepare native development candidates for B/D, using shared B recall and exact sentences."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src')]
from flat_rag import SentenceTransformerEmbeddings, json_hash, load_questions
from hybrid_retrieval import hybrid_rank, summary_parts, validate_parents
from structmem_retrieve import file_hash, load_memory_index, memory_text, original_source_ids, read_json
from anchor_context_pilot import dependencies


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def prepare(memory_index, questions_path, model_cache, out):
    if out.exists():
        raise FileExistsError(out)
    frozen = read_json(ROOT / 'configs/locomo-smoke.json')
    if file_hash(questions_path) != frozen['output_sha256'].get(questions_path.name):
        raise ValueError('Expected an unchanged frozen smoke/development question file')
    questions = load_questions(questions_path)
    index = read_json(memory_index)
    if index.get('source_conversations_sha256') != frozen['output_sha256']['development.conversations.json']:
        raise ValueError('Native memory source differs from the development freeze')
    memories, hashes = load_memory_index(memory_index, frozen['splits']['development'])
    ranking = read_json(ROOT / 'configs/phase2-anchor-pilot.json')['ranking']
    recall = read_json(ROOT / 'configs/phase2-coverage-pilot.json')
    if recall['dense_top_k'] != recall['lexical_top_k']:
        raise ValueError('Shared B recall expects equal dense/lexical limits')
    archive = ROOT / 'reports/artifacts/s2-predictions-for-E-20261020.zip'
    expected = read_json(ROOT / 'reports/phase2-memory-audit-20261103.json')['inputs']['prediction_archives'][archive.name]
    if file_hash(archive) != expected:
        raise ValueError('Frozen S2 archive hash mismatch')
    with zipfile.ZipFile(archive) as packed:
        # Read only the original synthesis contexts; never use predictions or scoring annotations.
        fixed = {(r['sample_id'], r['qa_index']): [c for c in r['contexts'] if c['kind'] == 'synthesis']
                 for r in map(json.loads, packed.read('predictions30.jsonl').splitlines())}
    events, summaries = {}, {}
    for sid, bank in memories.items():
        events[sid] = [{'id': f"{sid}/event/{p['id']}", 'kind': 'event',
                        'text': memory_text(p, 'event'), 'vector': p['vector'],
                        'source_ids': [f"{sid}/event/{p['id']}"] + original_source_ids(sid, p),
                        'parent': None, 'position': None} for p in bank['event']]
        summaries[sid] = {f"{sid}/synthesis/{p['id']}": p for p in bank['synthesis']}
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    encoder = SentenceTransformerEmbeddings(frozen['embedding'], model_cache)
    query_vectors = encoder.encode([q['question'] for q in questions])
    # Embed complete original sentences once. Native event vectors are preserved, never re-encoded.
    sentence_texts = sorted({s for q in questions for c in fixed[q['sample_id'], q['qa_index']]
                             for s in summary_parts(c['text'])[1]})
    sentence_vectors = dict(zip(sentence_texts, encoder.encode(sentence_texts)))
    rows, dependency_rows, diagnostics = [], [], []
    for question, query in zip(questions, query_vectors):
        started = time.perf_counter()
        sid, qi = question['sample_id'], question['qa_index']
        recalled = hybrid_rank(events[sid], query, question['question'], ranking,
                               top_k=recall['dense_top_k'])
        units, parents, edges = list(recalled['units']), [], {}
        for context in fixed[sid, qi]:
            pid = context['source_ids'][0]
            if pid not in summaries[sid] or memory_text(summaries[sid][pid], 'synthesis') != context['text']:
                raise ValueError('Original five synthesis text does not match native export')
            parents.append({'id': pid, 'text': context['text'], 'source_ids': context['source_ids']})
            _, spans = summary_parts(context['text'])
            local_edges = dependencies(spans)
            for position, text in enumerate(spans):
                uid = f'{pid}/sentence/{position}'
                units.append({'id': uid, 'kind': 'synthesis_sentence', 'text': text,
                              'vector': sentence_vectors[text], 'source_ids': context['source_ids'],
                              'parent': pid, 'position': position})
                edges[uid] = [f'{pid}/sentence/{i}' for i in local_edges[position]]
        validate_parents(units, parents)
        rows.append({**question, 'query_vector': query, 'units': units, 'parents': parents,
                     'embedding': frozen['embedding'],
                     'scope': 'native full development event-bank dense120/lexical120 union; original five synthesis parents; pinned MiniLM sentence/query vectors; provisional legacy dependencies'})
        dependency_rows.append({'sample_id': sid, 'qa_index': qi, 'dependencies': edges})
        diagnostics.append({**{k: question[k] for k in ('sample_id', 'qa_index')},
                            'native_events': len(events[sid]), 'recalled_events': len(recalled['units']),
                            'synthesis_sentences': len(units) - len(recalled['units']),
                            'candidate_sha256': json_hash(units), 'recall_scores': recalled['scores']})
        print(json.dumps({'sample_id': sid, 'qa_index': qi, 'candidates': len(units),
                          'recall_seconds': round(time.perf_counter() - started, 2)}), flush=True)
    out.mkdir(parents=True, exist_ok=False)
    bundle = out / 'bundle.jsonl'
    bundle.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8', newline='\n')
    dump(out / 'dependencies.json', {'version': 'legacy-anchor-pilot-20261103-unreviewed',
                                    'status': 'provisional', 'bundle_sha256': file_hash(bundle),
                                    'rows': dependency_rows})
    dump(out / 'recall.json', diagnostics)
    manifest = {'questions': len(rows), 'memory_index_sha256': file_hash(memory_index),
                'memory_sha256': hashes, 'questions_sha256': file_hash(questions_path),
                'bundle_sha256': file_hash(bundle), 'embedding': frozen['embedding'],
                'recall_top_k': recall['dense_top_k'], 'parent_scope': 'original_five_per_question',
                'native_synthesis_counts': {sid: len(bank['synthesis']) for sid, bank in memories.items()},
                'dependency_status': 'provisional', 'answer_calls': 0, 'judge_calls': 0,
                'code_sha256': {p.relative_to(ROOT).as_posix(): file_hash(p) for p in
                               (Path(__file__), ROOT / 'src/hybrid_retrieval.py',
                                ROOT / 'src/flat_rag.py', ROOT / 'scripts/anchor_context_pilot.py')}}
    dump(out / 'manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('memory-index', 'questions', 'model-cache', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.memory_index, args.questions, args.model_cache, args.out), indent=2))
