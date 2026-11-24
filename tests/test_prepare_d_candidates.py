import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'src')]
import prepare_d_candidates as command
from structmem_retrieve import file_hash, memory_text
from test_structmem_retrieve import make_index, save


class CandidateTests(unittest.TestCase):
    def prepare_fixture(self, root):
        for folder in ('configs', 'reports/artifacts', 'src', 'scripts'):
            (root / folder).mkdir(parents=True, exist_ok=True)
        make_index(root)
        questions = [{'sample_id': 'conv-48', 'qa_index': 86, 'category': 1, 'question': 'Who joined?'}]
        save(root / 'smoke.inputs.json', questions)
        spec = json.loads((ROOT / 'configs/locomo-smoke.json').read_text(encoding='utf-8'))['embedding']
        save(root / 'configs/locomo-smoke.json', {
            'embedding': spec, 'splits': {'development': ['conv-48']},
            'output_sha256': {'smoke.inputs.json': file_hash(root / 'smoke.inputs.json'),
                              'development.conversations.json': 'a' * 64}})
        ranking = {'rrf_k': 60, 'bm25_k1': 1.2, 'bm25_b': .75,
                   'mmr_relevance': .7, 'mmr_redundancy': .3}
        save(root / 'configs/phase2-anchor-pilot.json', {'ranking': ranking})
        save(root / 'configs/phase2-coverage-pilot.json', {'dense_top_k': 120, 'lexical_top_k': 120})
        summary = json.loads((root / 'summaries.json').read_text(encoding='utf-8'))[0]
        text = memory_text(summary, 'synthesis')
        archived = {**questions[0], 'prediction': 'POISON_PREDICTION', 'contexts': [
            {'source_ids': ['conv-48/synthesis/s1', 'conv-48/event/e1'], 'kind': 'synthesis', 'text': text}]}
        archive = root / 'reports/artifacts/s2-predictions-for-E-20261020.zip'
        with zipfile.ZipFile(archive, 'w') as packed:
            packed.writestr('predictions30.jsonl', json.dumps(archived) + '\n')
        save(root / 'reports/phase2-memory-audit-20261103.json', {
            'inputs': {'prediction_archives': {archive.name: file_hash(archive)}}})
        for relative in ('scripts/prepare_d_candidates.py', 'src/hybrid_retrieval.py',
                         'src/flat_rag.py', 'scripts/anchor_context_pilot.py'):
            (root / relative).write_text('fixture code')
        encoder = Mock()
        encoder.encode.side_effect = lambda texts: [[1.] + [0.] * 383 for _ in texts]
        return encoder

    def test_native_vectors_preserved_and_predictions_never_reach_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            encoder = self.prepare_fixture(root)
            with patch.object(command, 'ROOT', root), patch.object(command, '__file__', str(root / 'scripts/prepare_d_candidates.py')), patch.object(command, 'SentenceTransformerEmbeddings', return_value=encoder):
                result = command.prepare(root / 'index.json', root / 'smoke.inputs.json', root / 'cache', root / 'out')
            row = json.loads((root / 'out/bundle.jsonl').read_text(encoding='utf-8'))
            native = {str(p['id']): p['vector'] for p in json.loads((root / 'events.json').read_text(encoding='utf-8'))}
            for unit in row['units']:
                if unit['kind'] == 'event':
                    self.assertEqual(unit['vector'], native[unit['id'].split('/')[-1]])
            self.assertNotIn('POISON_PREDICTION', (root / 'out/bundle.jsonl').read_text(encoding='utf-8'))
            self.assertEqual(encoder.encode.call_args_list[0].args[0], ['Who joined?'])
            self.assertEqual(encoder.encode.call_args_list[1].args[0], ['Alex joined the club.'])
            self.assertEqual(result['questions'], 1)
            dependencies = json.loads((root / 'out/dependencies.json').read_text(encoding='utf-8'))
            self.assertEqual(dependencies['bundle_sha256'], file_hash(root / 'out/bundle.jsonl'))
            self.assertEqual(dependencies['status'], 'provisional')

    def test_changed_question_or_native_parent_rejected(self):
        for case in ('question', 'parent'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                encoder = self.prepare_fixture(root)
                if case == 'question':
                    (root / 'smoke.inputs.json').write_text('[]')
                else:
                    summary = json.loads((root / 'summaries.json').read_text(encoding='utf-8'))
                    summary[0]['payload']['summary'] = 'Changed parent.'
                    save(root / 'summaries.json', summary)
                    index = json.loads((root / 'index.json').read_text(encoding='utf-8'))
                    index['conversations']['conv-48']['synthesis']['sha256'] = file_hash(root / 'summaries.json')
                    save(root / 'index.json', index)
                with patch.object(command, 'ROOT', root), patch.object(command, 'SentenceTransformerEmbeddings', return_value=encoder):
                    with self.assertRaises(ValueError):
                        command.prepare(root / 'index.json', root / 'smoke.inputs.json', root / 'cache', root / 'out')
                self.assertFalse((root / 'out').exists())


if __name__ == '__main__':
    unittest.main()
