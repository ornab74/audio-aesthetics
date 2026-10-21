from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from server.app import app
from server.state import state

@pytest.fixture
def client(tmp_path):
    if state.unlocked: state.close()
    state.root = tmp_path / 'encrypted-vault'
    with TestClient(app) as c:
        yield c
        if state.unlocked: state.close()

@pytest.fixture
def authed(client):
    headers={'Authorization':'Bearer '+state.token}
    assert client.post('/vault/unlock',headers=headers,json={'passphrase':'correct horse battery staple'}).status_code==200
    return client,headers

def test_rejects_missing_token(client):
    assert client.get('/memories').status_code==401
    assert client.get('/vault/status').status_code==401
    assert client.get('/health').status_code==200

def test_vault_roundtrip_and_encrypted_files(authed):
    c,h=authed
    created=c.post('/memories',headers=h,json={'text':'A solar memory from another time','ring':5,'project':'global'})
    assert created.status_code==200,created.text
    result=c.get('/memories/search',headers=h,params={'q':'solar'}).json()['results']
    assert any(x['id']==created.json()['id'] for x in result)
    assert c.post('/vault/lock',headers=h).json()['unlocked'] is False
    path=state.root/'agent_prism.sqlite3.aes'
    assert path.exists()
    assert b'solar memory' not in path.read_bytes()
    assert c.post('/vault/unlock',headers=h,json={'passphrase':'not the actual password'}).status_code==400
    assert c.post('/vault/unlock',headers=h,json={'passphrase':'correct horse battery staple'}).status_code==200
    assert c.get('/memories',headers=h).json()[0]['text']=='A solar memory from another time'

def test_task_requires_explicit_approval(authed):
    c,h=authed
    resp=c.post('/tasks',headers=h,json={'title':'Orbit review','instructions':'Read this note',
                                          'due_at':'2020-01-01T12:00:00Z','kind':'memory_review'})
    assert resp.status_code==200
    t=resp.json()
    assert t['status']=='scheduled'
    assert any(x['id']==t['id'] for x in c.get('/tasks/due',headers=h).json())
    completed=c.post('/tasks/'+t['id']+'/approve',headers=h)
    assert completed.status_code==200,completed.text
    assert completed.json()['status']=='completed'
    events=c.get('/tasks/'+t['id']+'/events',headers=h).json()
    assert any(e['event']=='completed' for e in events)

def test_session_history_with_fake_model(authed,monkeypatch):
    c,h=authed
    async def fake_complete(messages):return 'Hello from the encrypted orbit.'
    monkeypatch.setattr(state.inference,'complete',fake_complete)
    result=c.post('/chat',headers=h,json={'session':'Hello','text':'tell me about memory'})
    assert result.status_code==200,result.text
    chats=c.get('/sessions',headers=h).json()['chats']
    assert chats['Hello'][-1]['role']=='assistant'
    assert 'encrypted orbit' in chats['Hello'][-1]['content']
    assert c.delete('/sessions/Hello',headers=h).status_code==200
    assert 'Hello' not in c.get('/sessions',headers=h).json()['chats']

def test_context_scope_and_delete(authed):
    c,h=authed
    saved=c.post('/memories',headers=h,json={'text':'Mission starflower technical observation','project':'missionA','ring':3}).json()
    r=c.get('/memories/search',headers=h,params={'q':'starflower','project':'missionA','strict':True})
    assert r.status_code==200
    assert any(m['id']==saved['id'] for m in r.json()['results'])
    assert c.delete('/memories/'+saved['id'],headers=h).status_code==200
    assert all(m['id']!=saved['id'] for m in c.get('/memories',headers=h).json())


def test_agent_profiles_and_inference_restrictions(authed):
    c,h=authed
    assert c.post('/agents',headers=h,json={'name':'Navigator','role':'Planner','instructions':'Help prioritize tasks.'}).status_code==200
    assert c.post('/agents',headers=h,json={'name':'Navigator'}).status_code==409
    assert len(c.get('/agents',headers=h).json())==1
    before=c.get('/config',headers=h).json()['inference']
    invalid=c.put('/config/inference',headers=h,json={'backend':'llama_cpp','base_url':'http://evil.example:8080/v1'})
    assert invalid.status_code==400
    assert c.delete('/agents/Navigator',headers=h).status_code==200
    assert c.get('/agents',headers=h).json()==[]


def test_road_scan_mocked_model(authed,monkeypatch):
    c,h=authed
    async def mock_complete(messages):return 'High'
    monkeypatch.setattr(state.inference,'complete',mock_complete)
    r=c.post('/road-scan',headers=h,json={'weather':'blizzard','traffic':'high'})
    assert r.status_code==200
    assert r.json()['label']=='High'
    assert 'not a live' in r.json()['disclaimer']


def test_streamed_chat_persists_after_completion(authed,monkeypatch):
    c,h=authed
    async def mock_stream(messages):
        yield 'Star'
        yield ' light'
    monkeypatch.setattr(state.inference,'stream',mock_stream)
    with c.stream('POST','/chat/stream',headers=h,json={'session':'Stream','text':'Hello'}) as r:
        assert r.status_code==200
        text=''.join(r.iter_text())
        assert 'Star' in text and 'light' in text
        assert '"done": true' in text
    chats=c.get('/sessions',headers=h).json()['chats']
    assert chats['Stream'][-1]['content']=='Star light'


def test_legacy_hmk2_key_roundtrip(tmp_path):
    import os,struct
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from migrate_legacy import gui_master_key
    password='some-unlock-password'
    salt,nonce,key=os.urandom(16),os.urandom(12),os.urandom(32)
    wrapped=PBKDF2HMAC(algorithm=hashes.SHA256(),length=32,salt=salt,iterations=350000).derive(password.encode())
    record=b'HMK2'+bytes([2])+struct.pack('>I',350000)+salt+nonce+AESGCM(wrapped).encrypt(nonce,key,b'HMK2')
    p=tmp_path/'.enc_key';p.write_bytes(record)
    assert gui_master_key(p,password)==key
    with pytest.raises(Exception):gui_master_key(p,'wrongpassword')


def test_rejected_model_configuration_is_atomic(authed):
    client, headers = authed
    original = client.get('/config', headers=headers).json()['inference']
    response = client.put('/config/inference', headers=headers, json={
        'backend': 'litert_lm', 'base_url': 'https://outside.invalid/v1',
        'model': 'should-not-save', 'max_tokens': 2048,
    })
    assert response.status_code == 400
    assert client.get('/config', headers=headers).json()['inference'] == original


def test_workspace_ast_scan_is_read_only(authed, tmp_path, monkeypatch):
    client, headers = authed
    root = tmp_path / 'workspace'
    root.mkdir()
    source = root / 'sample.py'
    source.write_text('class SpaceNavigator:\n    def route(self): pass\n')
    monkeypatch.setenv('HUMOID_WORKSPACE', str(root))
    before = source.read_bytes()
    result = client.get('/workspace/scan', headers=headers, params={'q': 'Space'}).json()
    assert any(symbol['name'] == 'SpaceNavigator' for symbol in result['symbols'])
    assert source.read_bytes() == before
