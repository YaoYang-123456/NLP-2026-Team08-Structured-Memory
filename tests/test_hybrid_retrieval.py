import copy
import os
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hybrid_retrieval import canonical_units,hybrid_rank,select_contexts,validate_parents,render_selection

CFG={'bm25_k1':1.2,'bm25_b':0.75,'rrf_k':60,'mmr_relevance':0.7,'mmr_redundancy':0.3}


def event(uid='e1',text='A red apple.'):
    return {'id':uid,'kind':'event','text':text,'vector':[1.,0.],
            'source_ids':[uid+'/message'],'parent':None,'position':None}


def fixture():
    parents=[{'id':f'p{i}','text':'Time range: 2026-01-01\nRed apple. Green pear. Blue sky.',
              'source_ids':[f'p{i}/source']} for i in range(5)]
    units=[event(),event('e2','Another red apple.')]
    for p in parents:
        for i,text in enumerate(['Red apple.','Green pear.','Blue sky.']):
            units.append({'id':p['id']+f'/s{i}','kind':'synthesis_sentence','text':text,
                          'vector':[1.,0.],'source_ids':p['source_ids'],'parent':p['id'],'position':i})
    return units,parents


class HybridTests(unittest.TestCase):
    def test_identical_duplicate_logged_conflict_rejected(self):
        a=event();units,duplicates=canonical_units([a,copy.deepcopy(a)])
        self.assertEqual(len(units),1);self.assertEqual(duplicates,['e1'])
        b=copy.deepcopy(a);b['text']='changed'
        with self.assertRaises(ValueError):canonical_units([a,b])

    def test_same_text_different_ids_remains_distinct(self):
        self.assertEqual(len(canonical_units([event('a'),event('b')])[0]),2)

    def test_sources_labels_bad_vectors_rejected(self):
        for key,value in [('source_ids',[]),('vector',[0.,0.]),('vector',[float('nan'),0.])]:
            a=event();a[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):canonical_units([a])
        a=event();a['answer']='hidden'
        with self.assertRaises(ValueError):canonical_units([a])

    def test_ties_and_reordered_input_are_deterministic(self):
        units=[event('b'),event('a')]
        a=hybrid_rank(units,[1.,0.],'apple',CFG);b=hybrid_rank(units[::-1],[1.,0.],'apple',CFG)
        self.assertEqual(a,b);self.assertEqual(a['scores']['a']['dense_rank'],1)

    def test_empty_pool_and_topk_union(self):
        self.assertEqual(hybrid_rank([],[1.,0.],'apple',CFG)['units'],[])
        a=event('a','apple');b=event('b','pear');b['vector']=[0.,1.]
        r=hybrid_rank([a,b],[0.,1.],'apple',CFG,top_k=1)
        self.assertEqual({u['id'] for u in r['units']},{'a','b'})

    def test_parent_binding_and_original_order_omissions(self):
        units,parents=fixture();pb=validate_parents(units,parents)
        c=render_selection({'p0/s2','p0/s0'},units,pb)
        self.assertEqual(c[0]['text'],'Time range: 2026-01-01\nRed apple.\n[...]\nBlue sky.')
        self.assertEqual(c[0]['source_ids'],parents[0]['source_ids'])
        units[-1]['text']='invented'
        with self.assertRaises(ValueError):validate_parents(units,parents)

    def test_m_n_exact_budget_and_repeat(self):
        from evidence_budget import EvidenceBudget
        cache=Path(os.environ['QA_TOKENIZER_CACHE']);budget=EvidenceBudget(160,cache)
        units,parents=fixture();r=hybrid_rank(units,[1.,0.],'apple',CFG)
        for v in ('M','N'):
            a=select_contexts(r,parents,v,budget,CFG)
            self.assertEqual(a,select_contexts(r,parents,v,budget,CFG))
            self.assertLessEqual(budget.count(a['contexts']),160)
            self.assertEqual(len(a['steps']),len(units) if v=='N' else 2)
        m=select_contexts(r,parents,'M',EvidenceBudget(4096,cache),CFG)
        self.assertEqual(m['contexts'][:5],[{'kind':'synthesis','text':p['text'],'source_ids':p['source_ids']} for p in parents])
        with self.assertRaises(ValueError):select_contexts(r,parents,'M',EvidenceBudget(1,cache),CFG)
        with self.assertRaises(ValueError):select_contexts(r,parents[:4],'M',budget,CFG)

    def test_zero_lexical_overlap(self):
        r=hybrid_rank([event('a',''),event('b')],[1.,0.],'unmatched',CFG) if False else hybrid_rank([event()],[1.,0.],'unmatched',CFG)
        self.assertIsNone(r['scores']['e1']['lexical_rank'])


if __name__=='__main__':unittest.main()
