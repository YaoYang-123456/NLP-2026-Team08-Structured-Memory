"""Repack a validated 4096-token D run at 2048; retain the infeasible fixed-five M result."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src')]
from context_packing import paired_s1, select_contexts
from evidence_budget import EvidenceBudget
from hybrid_retrieval import hybrid_rank, reject_annotations, select_contexts as select_control
from structmem_retrieve import file_hash, read_json
from run_context_packing import write_json


def run(base_run, out, cache):
    if out.exists():
        raise FileExistsError(out)
    manifest = read_json(base_run / 'manifest.json')
    bundle = base_run / 'controls/bundles.jsonl'
    spec = read_json(base_run / 'dependencies.json')
    if (manifest['status'] != 'offline_contexts_only' or manifest['budget'] != 4096
            or file_hash(bundle) != manifest['bundle_sha256']
            or file_hash(base_run / 'dependencies.json') != manifest['dependencies_sha256']
            or spec['bundle_sha256'] != manifest['bundle_sha256']):
        raise ValueError('Expected an unchanged completed 4096-token D run')
    for name, expected in manifest['code_sha256'].items():
        if file_hash(ROOT / name) != expected:
            raise ValueError('Base selection code changed; rebuild the baseline before ablation')
    rows = [json.loads(line) for line in bundle.read_text(encoding='utf-8').splitlines()]
    deps = {(row['sample_id'], row['qa_index']): row['dependencies'] for row in spec['rows']}
    if len(rows) != manifest['questions'] or set(deps) != {(r['sample_id'], r['qa_index']) for r in rows}:
        raise ValueError('Baseline question/dependency count differs')
    budget = EvidenceBudget(2048, cache)
    outputs, traces, infeasible = {v: [] for v in ('N', 'A', 'S1')}, [], []
    for row in rows:
        reject_annotations(row)
        key = row['sample_id'], row['qa_index']
        ranked = hybrid_rank(row['units'], row['query_vector'], row['question'], manifest['ranking'])
        a = select_contexts(ranked, row['parents'], deps[key], budget, manifest['ranking'])
        results = {'N': select_control(ranked, row['parents'], 'N', budget, manifest['ranking']),
                   'A': a, 'S1': paired_s1(a, ranked['units'], budget)}
        fixed = [{'kind': 'synthesis', 'text': p['text'], 'source_ids': p['source_ids']} for p in row['parents']]
        fixed_cost = budget.count(fixed)
        if fixed_cost > 2048:
            infeasible.append({'sample_id': key[0], 'qa_index': key[1], 'fixed_five_tokens': fixed_cost})
        identity = {k: row[k] for k in ('sample_id', 'qa_index', 'question', 'category')}
        for variant, result in results.items():
            outputs[variant].append({**identity, 'contexts': result['contexts']})
        traces.append({**identity, 'variants': results})
    out.mkdir(parents=True, exist_ok=False)
    for variant, values in outputs.items():
        (out / f'{variant}.inputs.jsonl').write_text(
            ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in values), encoding='utf-8', newline='\n')
    write_json(out / 'trace.json', traces)
    summary = {'questions': len(rows), 'budget': 2048, 'variants': ['N', 'A', 'S1'],
               'M': 'not run; fixed-five feasibility reported without trimming or deleting questions',
               'M_infeasible_questions': infeasible, 'bundle_sha256': manifest['bundle_sha256'],
               'dependencies_sha256': manifest['dependencies_sha256'],
               'dependency_status': spec['status'], 'answer_calls': 0, 'judge_calls': 0,
               'code_sha256': {**manifest['code_sha256'],
                               'scripts/run_d_budget_ablation.py': file_hash(Path(__file__))}}
    write_json(out / 'manifest.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('base-run', 'out', 'tokenizer-cache'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.base_run, args.out, args.tokenizer_cache), indent=2))
