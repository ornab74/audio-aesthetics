"""Standalone adapter tests with an in-process fake local inference server."""
import asyncio
import json
import pytest
import httpx
from server.inference import Inference, validate_local_url


def test_rejects_nonlocal_inference_urls():
    for url in ('https://localhost:8081/v1','http://example.com:8081/v1',
                'http://127.0.0.1/v1','http://user:pw@localhost:8081/v1'):
        with pytest.raises(ValueError):
            validate_local_url(url)
    assert validate_local_url('http://127.0.0.1:8081/v1') == 'http://127.0.0.1:8081/v1'


def test_llama_cpp_completions_with_mocked_local_http(monkeypatch):
    seen=[]
    def handler(request):
        payload=json.loads(request.content)
        seen.append((request.url.path, payload['stream'], payload['messages'][0]['content']))
        if payload['stream']:
            events=[{'choices':[{'delta':{'content':'Hello'}}]},
                    {'choices':[{'delta':{'content':' orbit'}}]}]
            body=''.join('data: '+json.dumps(event)+'\n\n' for event in events)+'data: [DONE]\n\n'
            return httpx.Response(200,text=body,headers={'Content-Type':'text/event-stream'})
        return httpx.Response(200,json={'choices':[{'message':{'content':'Hello orbit'}}]})
    transport=httpx.MockTransport(handler)
    real_client=httpx.AsyncClient
    monkeypatch.setattr('server.inference.httpx.AsyncClient', lambda **k: real_client(transport=transport,**k))
    engine=Inference()
    message=[{'role':'user','content':'Hello'}]
    async def do_calls():
        assert await engine.complete(message)=='Hello orbit'
        assert ''.join([piece async for piece in engine.stream(message)])=='Hello orbit'
    asyncio.run(do_calls())
    assert seen==[('/v1/chat/completions',False,'Hello'),('/v1/chat/completions',True,'Hello')]
