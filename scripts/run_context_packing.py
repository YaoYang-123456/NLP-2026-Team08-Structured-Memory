"""Offline M/N/A and paired S1 inputs using the same frozen development bundle."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src')]
from context_packing import paired_s1, select_contexts
from flat_rag import json_hash
from hybrid_retrieval import hybrid_rank, reject_annotations
from run_mn import run as run_controls


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n',
                    encoding='utf-8', newline='\n')


def run(bundle, questions, dependencies_path, out, cache, config_path=None, max_tokens=4096):
    from evidence_budget import EvidenceBudget
    if out.exists():
        raise FileExistsError(out)
    rows = [json.loads(line) for line in bundle.read_text(encoding='utf-8').splitlines()]
    spec = json.loads(dependencies_path.read_text(encoding='utf-8'))
    reject_annotations(spec)
    if (set(spec) != {'version', 'status', 'bundle_sha256', 'rows'}
            or not isinstance(spec['version'], str) or not spec['version'].strip()
            or spec['status'] not in ('provisional', 'reviewed')
            or spec['bundle_sha256'] != hashlib.sha256(bundle.read_bytes()).hexdigest()):
        raise ValueError('Dependency specification/version must bind the exact candidate bundle')
    dependency_rows = {}
    for row in spec['rows']:
        if set(row) != {'sample_id', 'qa_index', 'dependencies'}:
            raise ValueError('Unexpected dependency row fields')
        key = row['sample_id'], row['qa_index']
        if key in dependency_rows:
            raise ValueError('Duplicate dependency question')
        dependency_rows[key] = row['dependencies']
    if set(dependency_rows) != {(r['sample_id'], r['qa_index']) for r in rows}:
        raise ValueError('Dependency questions must exactly match the candidate bundle')
    config_path = config_path or ROOT / 'configs/phase2-anchor-pilot.json'
    ranking = json.loads(config_path.read_text(encoding='utf-8'))['ranking']
    budget = EvidenceBudget(max_tokens, cache)
    results, traces = {'A': [], 'S1': []}, []
    # Validate D's entire input before producing the controls or any output files.
    for row in rows:
        reject_annotations(row)
        ranked = hybrid_rank(row['units'], row['query_vector'], row['question'], ranking)
        selection = select_contexts(ranked, row['parents'],
                                    dependency_rows[row['sample_id'], row['qa_index']], budget, ranking)
        ablation = paired_s1(selection, ranked['units'], budget)
        identity = {key: row[key] for key in ('sample_id', 'qa_index', 'question', 'category')}
        for variant, value in (('A', selection), ('S1', ablation)):
            results[variant].append({**identity, 'contexts': value['contexts']})
        traces.append({**identity, 'scope': row['scope'],
                       'common_ranking_sha256': json_hash(ranked),
                       'dependencies': dependency_rows[row['sample_id'], row['qa_index']],
                       'variants': {'A': selection, 'S1': ablation}})
    # B owns frozen question, namespace, embedding and original-five validation.
    controls = run_controls(bundle, questions, out / 'controls', cache, config_path, max_tokens)
    control_traces = json.loads((out / 'controls/trace.json').read_text(encoding='utf-8'))
    if [t['common_ranking_sha256'] for t in traces] != [t['common_ranking_sha256'] for t in control_traces]:
        raise ValueError('A and M/N rankings differ')
    for variant, values in results.items():
        (out / f'{variant}.inputs.jsonl').write_text(
            ''.join(json.dumps(value, ensure_ascii=False) + '\n' for value in values),
            encoding='utf-8', newline='\n')
    (out / 'dependencies.json').write_bytes(dependencies_path.read_bytes())
    write_json(out / 'trace.json', traces)
    manifest = {**controls, 'variants': ['M', 'N', 'A', 'S1'],
                'controls_directory': 'controls', 'dependency_version': spec['version'],
                'dependency_status': spec['status'],
                'dependencies_sha256': hashlib.sha256(dependencies_path.read_bytes()).hexdigest(),
                'questions_sha256': hashlib.sha256(questions.read_bytes()).hexdigest(),
                'config_sha256': hashlib.sha256(config_path.read_bytes()).hexdigest(),
                'pairing': 'delete_synthesis_from_A_without_refill'}
    manifest['code_sha256'] = {**controls['code_sha256'], **{
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (Path(__file__), ROOT / 'src/context_packing.py', ROOT / 'scripts/run_mn.py')}}
    write_json(out / 'manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bundle', 'questions', 'dependencies', 'out', 'tokenizer-cache'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--max-tokens', type=int, default=4096)
    args = parser.parse_args()
    print(json.dumps(run(args.bundle, args.questions, args.dependencies, args.out,
                         args.tokenizer_cache, args.config, args.max_tokens)))
