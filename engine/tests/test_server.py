import os,io,wave
import numpy as np
from fastapi.testclient import TestClient
from aesthetics.server import app
from aesthetics import billing
from aesthetics.dsp import pcm16

client=TestClient(app)

def test_api_catalog_and_static_site():
    assert client.get('/api/health').json()['ok']
    p=client.get('/api/presets').json()
    assert 'streamer' in p['presets'] and len(p['detections'])>=25
    html=client.get('/')
    assert html.status_code==200 and 'HEAR THE' in html.text

def test_wav_analyze():
    x=np.zeros(16000,dtype='<i2');buf=io.BytesIO()
    with wave.open(buf,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(x.tobytes())
    r=client.post('/api/analyze-wav?preset=streamer',content=buf.getvalue(),headers={'content-type':'audio/wav'})
    assert r.status_code==200
    assert any(x['id']=='silence' for x in r.json()['issues'])
    assert client.post('/api/analyze-wav',content=b'no').status_code==400

def test_ws_streaming_and_alerts():
    with client.websocket_connect('/ws/audio') as ws:
        ws.send_json({'type':'start','preset':'streamer','sample_rate':16000,'channels':1,'clef':'off'})
        assert ws.receive_json()['type']=='ready'
        data=np.ones(16000,dtype='<i2')*32767
        # Streaming in chunks tests overlap, hysteresis and no fake provider calls.
        for _ in range(3):ws.send_bytes(data.tobytes())
        types=[]
        for _ in range(9):
            msg=ws.receive_json();types.append(msg['type'])
            if msg['type']=='meters' and msg['seconds']>=2.5:break
        assert 'meters' in types and 'alert' in types

def test_ws_invalid_mode():
    with client.websocket_connect('/ws/audio') as ws:
        ws.send_json({'type':'start','preset':'streamer','sample_rate':16000,'clef':'bad'})
        assert ws.receive_json()['type']=='error'

def test_cloud_rejects_unpaid_key():
    with client.websocket_connect('/ws/audio') as ws:
        ws.send_json({'type':'start','preset':'streamer','sample_rate':16000,'clef':'cloud'})
        assert 'Pro' in ws.receive_json()['message']

def test_subscription_requires_provider_configuration(monkeypatch):
    monkeypatch.delenv('STRIPE_SECRET_KEY',raising=False)
    resp=client.post('/api/billing/checkout',json={'email':'sample@example.com'})
    assert resp.status_code==503

def test_license_not_active_when_absent(tmp_path,monkeypatch):
    monkeypatch.setenv('AESTHETICS_DB',str(tmp_path/'billing.db'))
    assert not billing.active('bogus')
