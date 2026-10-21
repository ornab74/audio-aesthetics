"""Cloudflare Clef-Omni and local SystemOne-compatible decision endpoint adapter."""
from __future__ import annotations
import base64,io,os,struct,wave
import numpy as np
import httpx
from .presets import Detection

CLOUDFLARE_MODEL='@cf/cloudflare/clef-omni'

def to_wav_data_url(audio:np.ndarray,rate:int,channels:int=1)->str:
    pcm=np.clip(audio,-1,1);pcm=(pcm*32767).astype('<i2').tobytes()
    out=io.BytesIO()
    with wave.open(out,'wb') as wav:
        wav.setnchannels(channels);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(pcm)
    return 'data:audio/wav;base64,'+base64.b64encode(out.getvalue()).decode('ascii')

def get_noul_probability(answer):
    if isinstance(answer,(float,int)) and not isinstance(answer,bool): return max(0.,min(1.,float(answer)))
    if isinstance(answer,dict):
        for k in ('probability','score','value','yes','true','confidence'):
            if isinstance(answer.get(k),(float,int)):return max(0.,min(1.,float(answer[k])))
    return None

class ClefAdapter:
    def __init__(self,mode='off',local_url:str|None=None):
        self.mode=mode
        self.local_url=local_url or os.getenv('CLEF_LOCAL_URL','http://127.0.0.1:8088/v1/systemone')
        if mode not in ('off','local','cloud'):raise ValueError('Bad CLEF mode')
    @property
    def available(self):
        if self.mode=='local':return True
        if self.mode=='cloud':return bool(os.getenv('CLOUDFLARE_ACCOUNT_ID') and os.getenv('CLOUDFLARE_API_TOKEN'))
        return False
    async def analyze(self,audio:np.ndarray,rate:int,checks:list[Detection],state:dict|None=None)->list[dict]:
        if not self.available or not checks:return []
        if self.mode=='cloud':
            url=f"https://api.cloudflare.com/client/v4/accounts/{os.environ['CLOUDFLARE_ACCOUNT_ID']}/ai/run/{CLOUDFLARE_MODEL}"
            token=os.environ['CLOUDFLARE_API_TOKEN']
        else:
            # Restrict private-local endpoint by default; deliberate remote configs require secure TLS.
            parsed=httpx.URL(self.local_url)
            if parsed.scheme!='https' and parsed.host not in ('127.0.0.1','localhost','::1'):
                raise ValueError('Remote CLEF endpoints require HTTPS')
            url=self.local_url;token=os.getenv('CLEF_LOCAL_API_KEY','')
        questions={d.id:{'type':'noul','instructions':d.description} for d in checks[:64]}
        if any(d.id=='music_aesthetics' for d in checks) and len(questions)<64:
            questions['aesthetic_grade']={
                'type':'score',
                'instructions':'Rate perceptual sound quality of this sample, focusing on balance, clarity, dynamics and audible artifacts rather than genre preference.',
                'criteria':['Severely impaired','Clear technical flaws','Acceptable mix','Strong mix','Exceptional mix']}
        payload={'model':'clef-omni','state':{'purpose':'Live audio quality diagnosis; answer based on actually audible evidence.','signal_features':state or {}},
                 'audio':[to_wav_data_url(audio,rate,1 if audio.ndim==1 else audio.shape[1])],
                 'questions':questions}
        headers={'Authorization':f'Bearer {token}'} if token else {}
        async with httpx.AsyncClient(timeout=30) as client:
            response=await client.post(url,json=payload,headers=headers)
            response.raise_for_status();data=response.json()
        if 'result' in data:data=data['result']
        answers=data.get('answers',{})
        events=[]
        for d in checks:
            prob=get_noul_probability(answers.get(d.id))
            if prob is not None:
                events.append({'id':d.id,'label':d.label,'probability':round(prob,3),
                               'threshold':d.threshold,'positive':prob>=d.threshold,
                               'source':f'clef-{self.mode}','severity':d.severity})
        if 'aesthetic_grade' in answers:
            grade=answers['aesthetic_grade']
            # Clef score: probability-weighted index 0..4 for five ordered criteria.
            # Unknown response schema? Do not invent a rating.
            if isinstance(grade,(int,float)) and not isinstance(grade,bool):
                normalized=max(0.,min(100.,float(grade)*25.))
                events.append({'id':'aesthetic_grade','label':'AI mix aesthetics',
                    'score_100':round(normalized,1),'positive':False,
                    'source':f'clef-{self.mode}','severity':'info'})
        return events
