import copy
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from context_packing import paired_s1, select_contexts, validate_dependencies
from evidence_budget import EvidenceBudget
from hybrid_retrieval import hybrid_rank, render_selection, select_contexts as select_controls, validate_parents

CONFIG = {'rrf_k': 60, 'bm25_k1': 1.2, 'bm25_b': .75,
          'mmr_relevance': .7, 'mmr_redundancy': .3}


def fixture():
    spans = ['Alex arrived on January 1, 2026.', 'He joined the club.',
             'The next day he bought an apple.', 'A separate detail.']
    parent = {'id': 'p', 'text': 'Time range: 2026-01-01\n' + ' '.join(spans), 'source_ids': ['p']}
    units = [{'id': f's{i}', 'kind': 'synthesis_sentence', 'text': text,
              'parent': 'p', 'position': i, 'source_ids': ['p'], 'vector': [1., i / 10]}
             for i, text in enumerate(spans)]
    units.append({'id': 'e', 'kind': 'event', 'text': 'Alex likes apples.',
                  'parent': None, 'position': None, 'source_ids': ['e'], 'vector': [0., 1.]})
    return units, [parent], {'s0': [], 's1': ['s0'], 's2': ['s1'], 's3': []}


class ContextPackingTests(unittest.TestCase):
    def setUp(self):
        self.units, self.parents, self.dependencies = fixture()
        self.ranked = hybrid_rank(self.units, [1., 0.], 'club apple', CONFIG)

    def budget(self, maximum=4096):
        return EvidenceBudget(maximum, Path(os.environ['QA_TOKENIZER_CACHE']))

    def test_transitive_closure_and_no_duplicate_fragments(self):
        result = select_contexts(self.ranked, self.parents, self.dependencies, self.budget(), CONFIG)
        step = next(s for s in result['steps'] if s['id'] == 's2')
        self.assertEqual(step['closure_ids'], ['s0', 's1', 's2'])
        text = result['contexts'][0]['text']
        for unit in self.units[:4]:
            self.assertEqual(text.count(unit['text']), 1)
        self.assertEqual(result['selected_ids'], ['e', 's0', 's1', 's2', 's3'])

    def test_empty_dependencies_match_n_exactly(self):
        dependencies = {uid: [] for uid in self.dependencies}
        a = select_contexts(self.ranked, self.parents, dependencies, self.budget(45), CONFIG)
        n = select_controls(self.ranked, self.parents, 'N', self.budget(45), CONFIG)
        self.assertEqual(a['contexts'], n['contexts'])
        self.assertEqual(a['selected_ids'], n['selected_ids'])
        self.assertEqual(a['evidence'], n['evidence'])
        self.assertEqual([s['id'] for s in a['steps']], [s['id'] for s in n['steps']])

    def test_package_cannot_be_partially_accepted(self):
        # Make the dependent sentence rank first, while its closure cannot fit.
        ranked = copy.deepcopy(self.ranked)
        for uid in ranked['scores']:
            ranked['scores'][uid]['relevance'] = 1. if uid == 's2' else 0.
        result = select_contexts(ranked, self.parents, self.dependencies, self.budget(20), CONFIG)
        step = result['steps'][0]
        self.assertEqual(step['id'], 's2')
        self.assertFalse(step['accepted'])
        self.assertEqual(step['added_ids'], ['s0', 's1', 's2'])
        self.assertNotIn('s2', result['selected_ids'])
        self.assertLessEqual(result['evidence']['proxy_tokens'], 20)

    def test_accepted_dependencies_change_remaining_mmr(self):
        ranked = copy.deepcopy(self.ranked)
        for uid in ranked['scores']:
            ranked['scores'][uid]['relevance'] = 1. if uid == 's2' else .1
        result = select_contexts(ranked, self.parents, self.dependencies, self.budget(), CONFIG)
        self.assertEqual(result['steps'][0]['added_ids'], ['s0', 's1', 's2'])
        self.assertNotIn('s0', [s['id'] for s in result['steps']])
        self.assertGreater(result['steps'][1]['redundancy'], 0)

    def test_invalid_dependency_boundary_rejected(self):
        for dependencies in ({}, {**self.dependencies, 's2': ['missing']},
                             {**self.dependencies, 's2': ['e']},
                             {**self.dependencies, 's1': ['s2']},
                             {**self.dependencies, 's0': ['s0']},
                             {**self.dependencies, 's1': ['s0', 's0']},
                             {**self.dependencies, 'answer': []}):
            with self.subTest(dependencies=dependencies), self.assertRaises(ValueError):
                validate_dependencies(self.units, dependencies)

    def test_cross_parent_dependency_rejected(self):
        extra = {**self.units[0], 'id': 'other', 'parent': 'other-parent'}
        with self.assertRaises(ValueError):
            validate_dependencies(self.units + [extra],
                                  {**self.dependencies, 'other': [], 's1': ['other']})

    def test_render_retains_order_omissions_and_source(self):
        contexts = render_selection({'s0', 's2'}, self.units,
                                    validate_parents(self.units, self.parents))
        self.assertEqual(contexts[0]['source_ids'], ['p'])
        self.assertIn('2026.\n[...]\nThe next', contexts[0]['text'])
        self.assertTrue(contexts[0]['text'].endswith('[...]'))

    def test_paired_s1_deletes_without_refill(self):
        a = select_contexts(self.ranked, self.parents, self.dependencies, self.budget(), CONFIG)
        s1 = paired_s1(a, self.units, self.budget())
        self.assertEqual(s1['contexts'], [c for c in a['contexts'] if c['kind'] == 'event'])
        self.assertEqual(s1['selected_ids'], ['e'])
        self.assertEqual(s1['removed_ids'], ['s0', 's1', 's2', 's3'])

    def test_reordered_inputs_repeat_and_budget(self):
        a = select_contexts(self.ranked, self.parents, self.dependencies, self.budget(45), CONFIG)
        ranked = hybrid_rank(self.units[::-1], [1., 0.], 'club apple', CONFIG)
        self.assertEqual(a, select_contexts(ranked, self.parents, self.dependencies, self.budget(45), CONFIG))
        self.assertLessEqual(a['evidence']['proxy_tokens'], 45)


if __name__ == '__main__':
    unittest.main()
