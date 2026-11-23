import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'src')]
from export_development_memory import export
from structmem_retrieve import load_memory_index
from test_structmem_retrieve import make_index, save


class ExportTests(unittest.TestCase):
    def prepare(self, root):
        make_index(root)
        save(root / 'frozen.json', {'splits': {'development': ['conv-48']},
                                  'output_sha256': {'development.conversations.json': 'a' * 64}})

    def test_round_trip_preserves_native_bytes_vectors_and_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.prepare(root)
            result = export(root / 'index.json', root / 'frozen.json', root / 'out.zip')
            self.assertEqual(result['counts']['conv-48'], {'event': 2, 'synthesis': 1})
            with zipfile.ZipFile(root / 'out.zip') as packed:
                self.assertIsNone(packed.testzip())
                self.assertEqual(packed.read('conv-48/event.json'), (root / 'events.json').read_bytes())
                self.assertEqual(packed.read('conv-48/synthesis.json'), (root / 'summaries.json').read_bytes())
                packed.extractall(root / 'unpacked')
            loaded, _ = load_memory_index(root / 'unpacked/memory-index.json', ['conv-48'])
            self.assertEqual(loaded['conv-48']['event'], json.loads((root / 'events.json').read_text()))
            export(root / 'index.json', root / 'frozen.json', root / 'repeat.zip')
            self.assertEqual((root / 'out.zip').read_bytes(), (root / 'repeat.zip').read_bytes())

    def test_tamper_wrong_source_extra_file_and_overwrite_rejected(self):
        for case in ('tamper', 'source', 'scope', 'extra', 'overwrite'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.prepare(root)
                index = json.loads((root / 'index.json').read_text())
                if case == 'tamper':
                    (root / 'events.json').write_text('[]')
                elif case == 'source':
                    index['source_conversations_sha256'] = 'bad'
                elif case == 'scope':
                    index['conversations']['conv-49'] = index['conversations']['conv-48']
                elif case == 'extra':
                    index['conversations']['conv-48']['labels'] = {'path': 'frozen.json'}
                else:
                    (root / 'out.zip').write_bytes(b'keep')
                save(root / 'index.json', index)
                with self.assertRaises((ValueError, FileExistsError)):
                    export(root / 'index.json', root / 'frozen.json', root / 'out.zip')
                if case == 'overwrite':
                    self.assertEqual((root / 'out.zip').read_bytes(), b'keep')
                else:
                    self.assertFalse((root / 'out.zip').exists())


if __name__ == '__main__':
    unittest.main()
