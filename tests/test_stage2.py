import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/"src"), str(ROOT/"scripts")]
from metamem_pilot.role_retrieval import retrieve_balanced
from metamem_pilot.data import digest
from run_stage2 import prepare_slots, recover_logged_answers, write_atomic
from metamem_pilot.pipeline import answer_prompt
from unittest.mock import patch
from summarize_stage2 import statistics, category


class Stage2Tests(unittest.TestCase):
    def test_role_budget_preserves_assistant_and_ignores_labels(self):
        row = {"question_id":"q", "question_type":"single-session-user", "question":"target", "question_date":"2023/01/02", "haystack_session_ids":["s"], "haystack_dates":["2023/01/01"],
               "haystack_sessions":[[{"role":"assistant", "content":"target "*100}, {"role":"user", "content":"target real fact"}]], "answer":"secret", "answer_session_ids":["secret"]}
        a = retrieve_balanced(row, top_k=2, max_chars=120)
        row['answer'] = 'changed'; row['answer_session_ids'] = ['changed']
        self.assertEqual(a, retrieve_balanced(row, top_k=2, max_chars=120))
        self.assertEqual(len(a['facts']),2)
        self.assertTrue(any('assistant:' in f['text'] for f in a['facts']))
        self.assertTrue(any('user:' in f['text'] for f in a['facts']))
        self.assertTrue(all(len(f['text'])<=60 for f in a['facts']))
        self.assertNotIn('secret', str(a))

    def test_completed_call_recovered_without_regeneration(self):
        row={'question_id':'q','question':'Q','question_date':'today','facts':[]}
        slots=[{'sample_id':'s','question_id':'q','retrieval':'original','learned':False,'status':'generating'}]
        event={'question_id':'s','prompt':answer_prompt(row,[]),'status':'ok','finish_reason':'stop','response':'saved'}
        self.assertEqual(recover_logged_answers(slots,[event],{'original':{'q':row}},[]),['s'])
        self.assertEqual(slots[0]['status'],'generated')
        self.assertEqual(slots[0]['response'],'saved')
        with patch('run_stage2._write_atomic',side_effect=[PermissionError(),None]) as save, patch('run_stage2.time.sleep'):
            write_atomic('unused',{})
            self.assertEqual(save.call_count,2)
        with patch('run_stage2._write_atomic',side_effect=ValueError('bad')):
            with self.assertRaises(ValueError):write_atomic('unused',{})

    def test_statistics_preserve_uncertain_and_missing(self):
        rows=[{'phase':'main','round':0,'question_id':'q','condition':c,**({'label':v} if v else {})} for c,v in [('A','Yes'),('B','No'),('C','uncertain'),('D',None)]]
        result=statistics(rows)['main']
        self.assertEqual(result['overall']['C']['uncertain'],1)
        self.assertEqual(result['overall']['D']['No'],0)
        self.assertEqual(result['overall']['D']['missing_or_failed'],1)
        self.assertEqual(result['paired']['C-A']['incomparable'],[{'question_id':'q','round':0}])
        self.assertEqual(category('Yes','No'),'only_target')
        self.assertEqual(category('No','Yes'),'only_baseline')

    def test_factorial_inputs_and_coordinates(self):
        original={str(i):{'facts':[{'text':'base'}]} for i in range(10)}
        improved={str(i):{'facts':[{'text':'improved'}]} for i in range(10)}
        oracle={str(i):{'facts':[{'text':'oracle'}]} for i in range(2)}
        slots, by = prepare_slots(original,improved,oracle)
        self.assertEqual(len(slots),132)
        self.assertEqual(len({s['sample_id'] for s in slots}),132)
        self.assertEqual(len({(s['phase'],s['round'],s['question_id'],s['condition']) for s in slots}),132)
        for repeat in range(3):
            for qid in original:
                rows={s['condition']:s for s in slots if s['phase']=='main' and s['round']==repeat and s['question_id']==qid}
                self.assertEqual(rows['A']['facts_sha256'],rows['B']['facts_sha256'])
                self.assertEqual(rows['C']['facts_sha256'],rows['D']['facts_sha256'])
                self.assertNotEqual(rows['A']['facts_sha256'],rows['C']['facts_sha256'])
                self.assertFalse(rows['A']['learned']);self.assertTrue(rows['B']['learned'])


if __name__=='__main__':
    unittest.main()
