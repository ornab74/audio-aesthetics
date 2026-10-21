import asyncio
import numpy as np
import pytest
from aesthetics.clef import ClefAdapter
from aesthetics.presets import selected_detections
from aesthetics.osc import _osc_str
from aesthetics.light_bridge import decode_alert,LightBridge
import struct


def test_osc_roundtrip():
    raw=_osc_str('/aesthetics/alert')+_osc_str(',ssf')+_osc_str('clip')+_osc_str('critical')+struct.pack('>f',.82)
    event=decode_alert(raw)
    assert event=={'id':'clip','severity':'critical','probability':.82}
    with pytest.raises(ValueError):decode_alert(b'junk')
    with pytest.raises(ValueError):LightBridge('8.8.8.8',dry_run=False)

def test_real_model_payload_via_fake_endpoint(monkeypatch):
    monkeypatch.setenv('CLEF_LOCAL_URL','http://127.0.0.1:8088/v1/systemone')
    saved=[]
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'answers':{'buried_vocal':.88,'aesthetic_grade':3.2}}
    class Client:
        def __init__(self,timeout):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,url,json,headers):
            saved.append((url,json,headers));return Response()
    monkeypatch.setattr('aesthetics.clef.httpx.AsyncClient',Client)
    checks=selected_detections('artist',enabled=['buried_vocal','music_aesthetics'])
    out=asyncio.run(ClefAdapter('local').analyze(np.zeros(16000,dtype='float32'),16000,checks,{'rms_dbfs':-20.0}))
    assert saved[0][0]=='http://127.0.0.1:8088/v1/systemone'
    assert saved[0][1]['audio'][0].startswith('data:audio/wav;base64,')
    assert saved[0][1]['questions']['buried_vocal']['type']=='noul'
    assert saved[0][1]['questions']['aesthetic_grade']['type']=='score'
    assert next(d for d in out if d['id']=='buried_vocal')['positive']
    assert next(d for d in out if d['id']=='aesthetic_grade')['score_100']==80.0

def test_clef_off_is_no_model_call():
    x=np.zeros(16000,dtype='float32')
    assert asyncio.run(ClefAdapter('off').analyze(x,16000,selected_detections('artist')))==[]
