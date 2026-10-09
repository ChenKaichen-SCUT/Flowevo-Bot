import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from code_math.runner import CONDITIONS,CodeSkillLibrary,build_goldfree_math_prompt,run_condition,verify
from core.schemas import CodeTaskInstance

class FakeLLM:
    def __init__(self): self.prompts=[]
    def generate(self,**kw):
        self.prompts.append(kw['input_text'])
        return SimpleNamespace(text='The answer is 7.',prompt_tokens=20,completion_tokens=6)

class GoldFreeTest(unittest.TestCase):
    def test_gold_does_not_affect_calls_or_prompts(self):
        runs=[]
        for gold in ('7','CANARY_GOLD_123'):
            llm=FakeLLM()
            tasks=[CodeTaskInstance(task_id=f'math_{i}',benchmark='math',prompt='Compute the sum of integers 3 and 4.',metadata={'gold_answer':gold}) for i in range(2)]
            result=run_condition('math','ours',CONDITIONS['ours'],llm,tasks)
            self.assertEqual(len(llm.prompts),2)
            self.assertTrue(all(e['retries']==0 and e['library_size']==0 for e in result))
            self.assertTrue(all('CANARY' not in e['feedback'] for e in result))
            runs.append(llm.prompts)
        self.assertEqual(*runs)
    def test_frozen_history_injects_in_both_math_benchmarks(self):
        for benchmark in ('math','gsm8k'):
            library=CodeSkillLibrary()
            task=CodeTaskInstance(task_id='train',benchmark=benchmark,prompt='Compute the sum of integers 2 and 5.')
            library.add(task,'The answer is 7.')
            target=CodeTaskInstance(task_id='test',benchmark=benchmark,prompt='Compute the sum of integers 3 and 4.',metadata={'gold_answer':'CANARY'})
            prompt=build_goldfree_math_prompt(target,library)
            self.assertIn('similar solved problem',prompt)
            self.assertNotIn('CANARY',prompt)
            self.assertEqual(library.size,1)
            llm=FakeLLM()
            result=run_condition(benchmark,'ours',CONDITIONS['ours'],llm,[target],math_library=library)
            self.assertEqual(llm.prompts,[prompt])
            self.assertEqual(result[0]['retries'],0)
            self.assertEqual(result[0]['library_size'],1)

if __name__=='__main__':unittest.main()
