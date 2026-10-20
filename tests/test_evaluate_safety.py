import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

spec = importlib.util.spec_from_file_location('evaluation_under_test', Path(__file__).parents[1]/'scripts/evaluate.py')
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)

class EvaluateSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.labels = self.root/'labels.json'
        self.pred = self.root/'pred.jsonl'
        self.judge = self.root/'judge.json'
        self.label = dict(sample_id='synthetic',qa_index=0,category=1,question='Capital?',answer='Paris')
        self.prediction = dict(sample_id='synthetic',qa_index=0,method='S0',status='ok',question='Capital?',prediction='Paris')
        self.saved = dict(status='scored',correct=True,judgment='yes',request={'messages':[{'role':'user','content':json.dumps(dict(question='Capital?',reference_answer='Paris',model_answer='Paris'))}]})
        self.write()
    def write(self):
        self.labels.write_text(json.dumps([self.label]),encoding='utf-8')
        self.pred.write_text(json.dumps(self.prediction)+'\n',encoding='utf-8')
        self.judge.write_text(json.dumps({'items':[dict(sample_id='synthetic',qa_index=0,methods={'S0':self.saved})]}),encoding='utf-8')
    def test_matching_legacy_request(self):
        summary,_=e.evaluate({'S0':self.pred},self.labels,self.judge)
        self.assertEqual(summary['methods']['S0']['correct'],1)
    def test_changed_prediction_reference_or_question_rejected(self):
        for field in ('prediction','reference','question'):
            with self.subTest(field=field):
                p=dict(self.prediction); label=dict(self.label)
                if field=='reference': label['answer']='London'
                else: p[field]="I don't know"
                with self.assertRaises(ValueError): e.validate_judgment_input(p,label,self.saved)
    def test_missing_request_and_contradictory_label_rejected(self):
        for saved in ({'status':'scored','correct':True,'judgment':'yes'},dict(self.saved,correct=False)):
            with self.assertRaises(ValueError): e.validate_judgment_input(self.prediction,self.label,saved)
    def test_interrupt_preserves_first_call_and_pending_status(self):
        second=dict(self.label,qa_index=1)
        self.labels.write_text(json.dumps([self.label,second]),encoding='utf-8')
        self.pred.write_text(json.dumps(self.prediction)+'\n'+json.dumps(dict(self.prediction,qa_index=1))+'\n',encoding='utf-8')
        result={'model':'fake','choices':[{'finish_reason':'stop','message':{'content':'yes'}}],'usage':{'total_tokens':5}}
        opener=Mock();opener.open.side_effect=[io.StringIO(json.dumps(result)),KeyboardInterrupt()]
        output=self.root/'new.json'
        with patch.dict(os.environ,{'DEEPSEEK_API_KEY':'synthetic-test-only'}),patch.object(e.urllib.request,'build_opener',return_value=opener):
            with self.assertRaises(KeyboardInterrupt):e.run_judge_api({'S0':self.pred},self.labels,output)
        saved=json.loads(output.read_text())
        self.assertEqual(saved['items'][0]['methods']['S0']['judgment'],'yes')
        self.assertEqual(saved['items'][1]['methods']['S0']['status'],'interrupted')
        self.assertEqual(saved['metadata']['status'],'interrupted')
        self.assertEqual(opener.open.call_count,2)
    def test_existing_direct_output_refused_before_network(self):
        old=self.judge.read_bytes()
        with patch.object(e.urllib.request,'build_opener') as connect:
            with self.assertRaises(ValueError):e.run_judge_api({'S0':self.pred},self.labels,self.judge)
            connect.assert_not_called()
        self.assertEqual(old,self.judge.read_bytes())
    def test_cli_existing_directory_refused(self):
        with patch.object(sys,'argv',['evaluate','--s0',str(self.pred),'--s2',str(self.pred),'--labels',str(self.labels),'--judge-api','--out',str(self.root)]),patch.object(e,'run_judge_api') as call:
            with self.assertRaises(SystemExit):e.main()
            call.assert_not_called()
    def test_failure_not_counted_as_wrong(self):
        self.saved.update(status='judge_failed',correct=None,judgment=None);self.write()
        summary,_=e.evaluate({'S0':self.pred},self.labels,self.judge)
        s=summary['methods']['S0'];self.assertEqual(s['scored'],0);self.assertEqual(s['judge_failed_or_missing'],1)
        self.assertIsNone(s['accuracy_on_scored'])

if __name__=='__main__':unittest.main()
