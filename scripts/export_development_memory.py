"""Export D's hash-bound native development memories, without rebuilding them."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from structmem_retrieve import file_hash, load_memory_index, read_json


def export(memory_index, frozen_config, archive):
    if archive.exists():
        raise FileExistsError(archive)
    frozen, index = read_json(frozen_config), read_json(memory_index)
    if index.get('source_conversations_sha256') != frozen['output_sha256']['development.conversations.json']:
        raise ValueError('Memory source is not the frozen development conversations')
    if set(index['conversations']) != set(frozen['splits']['development']):
        raise ValueError('Export must cover exactly the frozen development conversations')
    if any(set(kinds) != {'event', 'synthesis'} for kinds in index['conversations'].values()):
        raise ValueError('Only native event/synthesis exports may be shared')
    memories, hashes = load_memory_index(memory_index, frozen['splits']['development'])
    entries, conversations = {}, {}
    for sid, kinds in index['conversations'].items():
        conversations[sid] = {}
        for kind, spec in kinds.items():
            name = f'{sid}/{kind}.json'
            data = (memory_index.parent / spec['path']).read_bytes()
            if hashlib.sha256(data).hexdigest() != hashes[sid][kind]:
                raise ValueError('Native export changed while packaging')
            entries[name] = data
            conversations[sid][kind] = {'path': name, 'sha256': hashes[sid][kind]}
    portable = {**index, 'conversations': conversations}
    manifest = {'source_memory_index_sha256': file_hash(memory_index),
                'frozen_config_sha256': file_hash(frozen_config),
                'counts': {sid: {kind: len(points) for kind, points in kinds.items()}
                           for sid, kinds in memories.items()},
                'files': {name: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                          for name, data in entries.items()},
                'scope': 'Native derived development memories and vectors, not raw databases or QA labels',
                'answer_calls': 0, 'judge_calls': 0, 'memory_build_calls': 0}
    for name, value in [('memory-index.json', portable), ('manifest.json', manifest)]:
        entries[name] = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    entries['README.txt'] = (
        'Native development event/synthesis point exports, original bytes and vectors.\n'
        'Read memory-index.json and manifest.json; validate hashes before loading.\n'
        f"Counts: {sum(len(m['event']) for m in memories.values())} events, "
        f"{sum(len(m['synthesis']) for m in memories.values())} syntheses. No new model calls.\n"
        'No raw Qdrant databases, original conversations, QA answers, predictions or API records.\n'
        'Source bindings are provenance, not a proof of semantic entailment.\n'
        'Sentence indexes and reviewed dependency rules remain C/E responsibilities.\n'
    ).encode('utf-8')
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as packed:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 23, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            packed.writestr(info, data)
    with zipfile.ZipFile(archive) as packed:
        if packed.testzip() is not None:
            raise ValueError('Export archive CRC failed')
    return {**manifest, 'archive_bytes': archive.stat().st_size, 'archive_sha256': file_hash(archive)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--memory-index', type=Path, required=True)
    parser.add_argument('--frozen-config', type=Path, default=ROOT / 'configs/locomo-smoke.json')
    parser.add_argument('--archive', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.memory_index, args.frozen_config, args.archive), indent=2))
