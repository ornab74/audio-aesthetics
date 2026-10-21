"""Local-first FastAPI audio monitor, real WebSocket PCM feed, and optional hosted billing."""
from __future__ import annotations
import asyncio,io,json,os,logging,wave,time
from pathlib import Path
from typing import Any
from fastapi import FastAPI,WebSocket,WebSocketDisconnect,Request,HTTPException,Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from . import __version__
from .presets import PRESETS,CATALOG,selected_detections
from .chunker import MultiScaleChunker,AlertGate
from .dsp import pcm16,SignalAnalyzer
from .clef import ClefAdapter
from .osc import send_osc_alert
from . import billing
import numpy as np
log=logging.getLogger(__name__)
app=FastAPI(title='Audio Aesthetics // PRISM',version=__version__)
SITE=Path(__file__).resolve().parents[2]/'website'
if SITE.is_dir():app.mount('/assets',StaticFiles(directory=SITE),name='assets')

@app.get('/')
def home():return FileResponse(SITE/'index.html') if (SITE/'index.html').exists() else {'service':'Audio Aesthetics'}

@app.get('/api/health')
def health():return {'ok':True,'version':__version__,'engine':'dsp','clef_mode_default':'off',
    'cloud_configured':bool(os.getenv('CLOUDFLARE_ACCOUNT_ID') and os.getenv('CLOUDFLARE_API_TOKEN')),
    'local_clef_url':os.getenv('CLEF_LOCAL_URL','http://127.0.0.1:8088/v1/systemone'),
    'billing_configured':bool(os.getenv('STRIPE_SECRET_KEY') and os.getenv('STRIPE_PRICE_ID'))}

@app.get('/api/presets')
def presets():return {'presets':PRESETS,'detections':[d.json() for d in CATALOG.values()]}

class CheckoutBody(BaseModel):email:str=Field(min_length=5,max_length=254)
class ActivateBody(BaseModel):session_id:str=Field(min_length=5,max_length=255)

@app.post('/api/billing/checkout')
def checkout(b:CheckoutBody):
    if not __import__('re').fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',b.email):raise HTTPException(400,'Valid email required')
    return {'url':billing.checkout(b.email)}

@app.post('/api/billing/activate')
def activate(b:ActivateBody):return {'access_token':billing.activate(b.session_id),'message':'Store this Pro key safely; it is shown only once.'}

@app.post('/api/billing/portal')
def portal(authorization:str=Header(default='')):
    return {'url':billing.portal(authorization.removeprefix('Bearer ').strip())}

@app.post('/api/billing/webhook')
async def stripe_webhook(request:Request,stripe_signature:str=Header(default='')):
    if len(await request.body())>512_000:raise HTTPException(413,'Webhook oversized')
    return billing.webhook(await request.body(),stripe_signature)

def _settings(body:dict)->tuple:
    rate=int(body.get('sample_rate',16000));channels=int(body.get('channels',1))
    if rate not in (16000,22050,24000,32000,44100,48000):raise ValueError('Unsupported sample rate')
    if channels not in (1,2):raise ValueError('Only mono or stereo PCM16 supported')
    preset=str(body.get('preset','streamer'))
    checks=selected_detections(preset,body.get('enabled'),body.get('custom'))
    clef_mode=str(body.get('clef','off'))
    if clef_mode not in ('off','local','cloud'):raise ValueError('Invalid Clef mode')
    bpm=body.get('bpm');bpm=float(bpm) if bpm else None
    if bpm is not None and not 40<=bpm<=260:raise ValueError('BPM 40-260 only')
    reference_hz=body.get('reference_hz')
    reference_hz=float(reference_hz) if reference_hz else None
    if reference_hz is not None and not 35<=reference_hz<=2000:raise ValueError('Pitch reference 35-2000 Hz')
    quiet_db=float(body.get('quiet_db',-37))
    if not -75<=quiet_db<=-12:raise ValueError('Quiet threshold -75 to -12 dBFS')
    return rate,channels,preset,checks,clef_mode,bpm,reference_hz,quiet_db

async def _send(ws:WebSocket,lock:asyncio.Lock,item:dict):
    async with lock:await ws.send_json(item)

@app.websocket('/ws/audio')
async def monitor(ws:WebSocket):
    # Local-only deployment. For external deployments, configure HTTPS reverse proxy,
    # Origin allowlist, authentication and trusted-forwarder rules before use.
    await ws.accept();tasks=set();send_lock=asyncio.Lock()
    try:
        first=await asyncio.wait_for(ws.receive_json(),timeout=10)
        if first.get('type')!='start':raise ValueError('First message must start a session')
        token=os.getenv('AESTHETICS_ACCESS_TOKEN','')
        if token and not __import__('hmac').compare_digest(str(first.get('token','')),token):
            await _send(ws,send_lock,{'type':'error','message':'Invalid server access token'});await ws.close(code=1008);return
        rate,channels,preset,checks,clef_mode,bpm,ref,quiet_db=_settings(first)
        if clef_mode=='cloud' and not billing.active(first.get('pro_token')):
            await _send(ws,send_lock,{'type':'error','message':'Cloud Clef requires an active Pro key'});await ws.close(code=1008);return
        adapter=ClefAdapter(clef_mode)
        if clef_mode!='off' and not adapter.available:
            await _send(ws,send_lock,{'type':'error','message':'Clef credentials / endpoint not configured'});await ws.close(code=1008);return
        chunker=MultiScaleChunker(rate,channels);analyzer=SignalAnalyzer(rate,channels);gate=AlertGate()
        ai_gate=AlertGate(trigger=1,clear=2,cooldown=16.)
        signal_checks=[d for d in checks if d.layer=='signal'];ai_checks=[d for d in checks if d.layer=='ai']
        ai_task=None;last_metrics={};frames=0;last_ai_frame=-rate*10;started=time.monotonic()
        await _send(ws,send_lock,{'type':'ready','preset':preset,'sample_rate':rate,'checks':[d.json() for d in checks],
            'clef':clef_mode,'mode':'microphone / loopback depending on input source'})
        async def call_ai(window,metrics):
            try:
                out=await adapter.analyze(window,rate,ai_checks,metrics)
                for ev in out:
                    if ev['id']=='aesthetic_grade':
                        await _send(ws,send_lock,{'type':'ai_score',**ev});continue
                    await _send(ws,send_lock,{'type':'decision',**ev})
                    if ai_gate.update(ev['id'],ev['positive']):
                        event={'type':'alert',**ev,'message':f'{ev["label"]} detected (AI estimate)'}
                        await _send(ws,send_lock,event)
                        try:send_osc_alert(event)
                        except Exception:log.exception('OSC failure')
            except (WebSocketDisconnect,RuntimeError):pass
            except Exception as exc:
                log.warning('CLEF unavailable: %s',exc)
                try:await _send(ws,send_lock,{'type':'ai_error','message':f'CLEF request failed: {type(exc).__name__}'})
                except Exception:pass
        while True:
            received=await ws.receive()
            if received.get('type')=='websocket.disconnect':break
            raw=received.get('bytes')
            if raw is None:
                if received.get('text'):
                    try:
                        msg=json.loads(received['text'])
                        if msg.get('type')=='ping':await _send(ws,send_lock,{'type':'pong'})
                    except json.JSONDecodeError:pass
                continue
            if len(raw)>rate*channels*2*3:await _send(ws,send_lock,{'type':'error','message':'PCM packet exceeds 3 seconds'});continue
            values=pcm16(raw,channels)
            if len(values)==0:continue
            frames+=len(values)
            fast,long=chunker.feed(values)
            if fast is not None:
                result=analyzer.analyze(fast,bpm=bpm,reference_hz=ref,quiet_db=quiet_db)
                last_metrics=result.get('metrics',{})
                await _send(ws,send_lock,{'type':'meters','seconds':round(frames/rate,2),
                                         'metrics':last_metrics,'uptime':round(time.monotonic()-started,1)})
                for d in signal_checks:
                    flag=bool(result.get('issues',{}).get(d.id,False))
                    if gate.update(d.id,flag):
                        event={'type':'alert','id':d.id,'label':d.label,'severity':d.severity,
                               'source':'dsp','message':d.description,'probability':1.0}
                        await _send(ws,send_lock,event)
                        try:send_osc_alert(event)
                        except Exception:log.exception('OSC failure')
            # Adaptive AI scheduling: use the long overlapping context normally.
            # After a severe local fault, dispatch an earlier 4s window (at most
            # once per 4s) rather than waiting for the next 8-second model hop.
            urgent=bool(fast is not None and result.get('issues',{}).get('clip') or
                        fast is not None and result.get('issues',{}).get('dropout') or
                        fast is not None and result.get('issues',{}).get('level_jump'))
            early=urgent and chunker.audio.count>=rate*4 and frames-last_ai_frame>=rate*4
            if (long is not None or early) and ai_checks and clef_mode!='off' and (ai_task is None or ai_task.done()):
                ai_window=long if long is not None else chunker.audio.tail(4.)
                last_ai_frame=frames
                ai_task=asyncio.create_task(call_ai(ai_window.copy(),last_metrics.copy()))
                tasks.add(ai_task);ai_task.add_done_callback(tasks.discard)
    except WebSocketDisconnect:pass
    except asyncio.TimeoutError:
        try:await _send(ws,send_lock,{'type':'error','message':'Session start timed out'})
        except Exception:pass
    except ValueError as err:
        try:await _send(ws,send_lock,{'type':'error','message':str(err)})
        except Exception:pass
    except Exception as err:log.exception('Audio session failed')
    finally:
        for task in tasks:task.cancel()
        if tasks:await asyncio.gather(*tasks,return_exceptions=True)
        try:await ws.close()
        except Exception:pass

@app.post('/api/analyze-wav')
async def analyze_wav(request:Request,preset:str='streamer',bpm:float|None=None,reference_hz:float|None=None):
    """Local diagnostic upload endpoint: WAV PCM16 up to 60 s / 8 MiB; no AI calls."""
    secret=os.getenv('AESTHETICS_ACCESS_TOKEN','')
    if secret and not __import__('hmac').compare_digest(request.headers.get('x-aesthetics-token',''),secret):
        raise HTTPException(401,'Unauthorized')
    raw=await request.body()
    if len(raw)>8*1024*1024:raise HTTPException(413,'WAV too large')
    try:
        with wave.open(io.BytesIO(raw),'rb') as w:
            if w.getsampwidth()!=2 or w.getnchannels() not in (1,2):raise ValueError('16-bit mono/stereo WAV required')
            rate=w.getframerate();channels=w.getnchannels()
            if rate not in (16000,22050,24000,32000,44100,48000):raise ValueError('Unsupported rate')
            frames=w.readframes(min(w.getnframes(),rate*60))
        checks=selected_detections(preset)
        signal=SignalAnalyzer(rate,channels).analyze(pcm16(frames,channels),bpm,reference_hz)
        return {'preset':preset,'metrics':signal.get('metrics',{}),
                'issues':[d.json() for d in checks if d.layer=='signal' and signal.get('issues',{}).get(d.id)]}
    except (wave.Error,ValueError,EOFError) as err:raise HTTPException(400,str(err))

