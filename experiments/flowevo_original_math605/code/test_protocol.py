from common import *
from native import runner, task_for, score, assert_local_extractors_unchanged
from generate import request_for, Generator, consume
from replay_native import ReplayClient
from runtime.llm_client import LLMClientError
import pytest

PUBLIC = dict(task_id='test_native', problem='What is 2+3?', subject='Prealgebra',
              level='Level 5', split='validation', official_row_index=0)

def cfg():
    return dict(model='deepseek-flash', max_tokens=2048, gold_reflection=False,
        condition_config=dict(runner.CONDITIONS['ours'], retry=False),
        max_http_attempts=2, max_total_tokens=20000, max_transport_attempts_per_task=2)

def response(content='The answer is 5.', finish='stop'):
    return dict(model='deepseek-flash', choices=[dict(message=dict(content=content,reasoning_content='think'),finish_reason=finish)],
        usage=dict(prompt_tokens=30,completion_tokens=10,total_tokens=40,
                   completion_tokens_details=dict(reasoning_tokens=6)))

def test_exact_upstream_extractors():
    assert assert_local_extractors_unchanged()
    assert score(PUBLIC, r'Correct: \boxed{5}', 'The answer is 5.')['passed']
    # Deliberately retain nested-brace defect, rather than replacing with V3.
    result=score(PUBLIC,r'\boxed{\frac{1}{3}}',r'\boxed{\frac{1}{7}}')
    assert result['passed'] and result['extracted_prediction']==r'\frac{1'

def test_public_request_rejects_gold():
    with pytest.raises(AssertionError):
        request_for(dict(PUBLIC,gold_answer='5'),cfg())
    request=request_for(PUBLIC,cfg())
    assert request['max_tokens']==2048
    assert request['messages'][1]['content']=='Problem: What is 2+3?\n\nSolve step by step. End with: The answer is [your answer].'

def test_completed_job_never_resends(tmp_path):
    calls=[]
    def transport(req):
        calls.append(req);return response()
    generator=Generator(cfg(),tmp_path,transport)
    first=generator.call(PUBLIC)
    assert generator.call(PUBLIC)==first and len(calls)==1
    assert generator.tokens==40

def test_empty_content_retains_usage_without_retry(tmp_path):
    generator=Generator(cfg(),tmp_path,lambda req:response('', 'length'))
    record=generator.call(PUBLIC)
    assert generator.calls==1 and generator.tokens==40
    client=ReplayClient([PUBLIC],{PUBLIC['task_id']:record})
    with pytest.raises(LLMClientError):
        client.generate(instructions=record['request']['messages'][0]['content'],
            input_text=record['request']['messages'][1]['content'],settings=runner._GEN_SETTINGS)
    assert record['total_tokens']==40

def test_native_runner_no_gold_retries(tmp_path):
    generator=Generator(cfg(),tmp_path,lambda req:response('The answer is 4.'))
    record=generator.call(PUBLIC)
    client=ReplayClient([PUBLIC],{PUBLIC['task_id']:record})
    episodes=runner.run_condition('math','ours',cfg()['condition_config'],client,[task_for(PUBLIC,r'\boxed{5}')])
    assert len(episodes)==1 and not episodes[0]['passed']
    assert client.calls==1 and episodes[0]['retries']==0

def test_math_library_cannot_change_other_task_prompt():
    library=runner.CodeSkillLibrary()
    library.add(task_for(dict(PUBLIC,task_id='earlier'),r'\boxed{5}'),'The answer is 5.')
    assert library.retrieve(task_for(PUBLIC))=={'type':'none'}

def test_stream_usage_includes_reasoning_and_empty_content(tmp_path):
    class Stream:
        def iter_lines(self,decode_unicode=True):
            yield 'data: '+json.dumps({'choices':[{'delta':{'reasoning_content':'think'},'finish_reason':None}]})
            yield 'data: '+json.dumps({'choices':[{'delta':{},'finish_reason':'length'}],'usage':response()['usage']})
            yield 'data: [DONE]'
    result=consume(Stream(),tmp_path/'response.sse.gz')
    assert result['usage']['total_tokens']==40
    assert result['choices'][0]['message']['content']==''
    assert result['choices'][0]['message']['reasoning_content']=='think'

def test_incomplete_stream_rejected(tmp_path):
    class Stream:
        def iter_lines(self,decode_unicode=True):
            yield 'data: '+json.dumps({'choices':[{'delta':{'content':'5'},'finish_reason':'stop'}]})
    with pytest.raises(RuntimeError):
        consume(Stream(),tmp_path/'response.sse.gz')
