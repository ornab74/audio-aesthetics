"""Fast signal checks. Values are engineered heuristics; no false source separation claims."""
from __future__ import annotations
from collections import deque
import math
import numpy as np

EPS=1e-10

def db(x:float)->float:
    return max(-120.0,20*math.log10(max(float(x),EPS)))

def pcm16(data:bytes,channels:int=1)->np.ndarray:
    if len(data)%2: data=data[:-1]
    values=np.frombuffer(data,dtype='<i2').astype(np.float32)/32768
    if channels>1:
        values=values[:len(values)//channels*channels].reshape(-1,channels)
    return values

class CircularAudio:
    def __init__(self,sample_rate=16000,channels=1,seconds=32):
        self.rate=sample_rate;self.channels=channels;self.max_samples=int(sample_rate*seconds)
        self.parts:deque[np.ndarray]=deque();self.count=0
    def push(self,chunk:np.ndarray):
        chunk=chunk.copy();self.parts.append(chunk);self.count+=len(chunk)
        while self.count>self.max_samples and self.parts:
            front=self.parts[0]; trim=min(self.count-self.max_samples,len(front))
            if trim==len(front): self.parts.popleft()
            else:self.parts[0]=front[trim:]
            self.count-=trim
    def tail(self,seconds:float)->np.ndarray:
        if not self.parts:return np.zeros((0,self.channels) if self.channels>1 else (0,),np.float32)
        need=min(int(self.rate*seconds),self.count);pieces=[]
        for p in reversed(self.parts):
            if need<=0:break
            take=min(len(p),need);pieces.append(p[-take:]);need-=take
        return np.concatenate(list(reversed(pieces)))

class SignalAnalyzer:
    def __init__(self,sample_rate:int=16000,channels:int=1):
        self.rate=sample_rate;self.channels=channels;self.prev_rms_db=None
    def analyze(self,array:np.ndarray,bpm:float|None=None,reference_hz:float|None=None,quiet_db=-37.0):
        if len(array)<int(self.rate*.2):return {}
        mono=array.mean(axis=1) if array.ndim==2 else array
        n=len(mono); peak=float(np.max(np.abs(mono)));rms=float(np.sqrt(np.mean(mono**2)))
        rms_db=db(rms);peak_db=db(peak); crest_db=peak_db-rms_db
        clip_rate=float(np.mean(np.abs(mono)>=.998))
        dc=float(np.mean(mono))
        frames=int(self.rate*.08)
        powers=np.array([np.sqrt(np.mean(mono[i:i+frames]**2)) for i in range(0,n-frames+1,frames)])
        tiny=powers<10**(-58/20)
        silent_run=int(max((sum(1 for _ in g) for v,g in __import__('itertools').groupby(tiny) if v),default=0))
        dropout=bool(silent_run>=2 and np.any(powers>10**(-35/20)))
        # FFT energy bands and temporal onset proxy.
        frame_len=min(2048,n);hop=max(256,frame_len//4)
        starts=range(0,max(1,n-frame_len+1),hop)
        w=np.hanning(frame_len).astype(np.float32)
        specs=np.array([np.abs(np.fft.rfft(mono[s:s+frame_len]*w)) for s in starts],np.float32)
        freqs=np.fft.rfftfreq(frame_len,1/self.rate)
        def energy(lo,hi):
            mask=(freqs>=lo)&(freqs<hi)
            return float(np.mean(np.sum(specs[:,mask]**2,axis=1)))+EPS if mask.any() else EPS
        sub=energy(20,80);low=energy(80,300);mid=energy(300,2500);high=energy(3000,7500)
        top=energy(4800,7500)
        high_ratio=high/(mid+high+EPS)
        low_ratio=(sub+low)/(sub+low+mid+high+EPS)
        rumble_ratio=sub/(sub+low+mid+high+EPS)
        centroid=float(np.mean(np.sum(specs*freqs[None,:],axis=1)/(np.sum(specs,axis=1)+EPS)))
        diff=np.maximum(0,np.diff(specs,axis=0));flux=float(np.mean(np.sum(diff,axis=1))) if len(diff) else 0
        mid_mags=np.sum(specs[:,(freqs>=100)&(freqs<6000)],axis=1)+EPS
        spread=float(np.std(mid_mags)/(np.mean(mid_mags)+EPS))
        if array.ndim==2 and array.shape[1]>1:
            l=array[:,0];r=array[:,1]
            corr=float(np.corrcoef(l,r)[0,1]) if np.std(l)>EPS and np.std(r)>EPS else 1.
        else:corr=None
        old=self.prev_rms_db
        self.prev_rms_db=rms_db
        onset_grid=None
        if bpm and 40<=bpm<=260 and len(powers)>10:
            diffp=np.diff(powers,prepend=powers[0]); cuts=np.where((diffp>max(.012,float(np.std(diffp)*1.5))) & (powers>0.017))[0]
            if len(cuts)>=5:
                times=cuts*.08; period=60./bpm
                # Calculate alignment modulo beat without assuming an offset/phase.
                phases=(times%period)/period;concentration=float(abs(np.mean(np.exp(2j*np.pi*phases))))
                onset_grid=round(1-concentration,3)
        pitch_hz=None;pitch_deviation=None
        if reference_hz and 35<=reference_hz<=2000 and rms_db>-43:
            # Autocorrelation pitch is useful ONLY for isolated monophonic notes.
            sample=mono[-min(n,int(self.rate*.35)):];sample=sample-np.mean(sample)
            if len(sample)>600:
                # FFT-based autocorrelation avoids O(N²) on continuous live streams.
                fft_n=1 << ((len(sample)*2-1).bit_length())
                spectrum=np.fft.rfft(sample,n=fft_n)
                corrp=np.fft.irfft(spectrum*spectrum.conj(),n=fft_n)[:len(sample)]
                lag_min=max(1,int(self.rate/1600));lag_max=min(len(corrp)-1,int(self.rate/55))
                cand=corrp[lag_min:lag_max]
                if len(cand) and max(cand)>float(corrp[0])*.43:
                    lag=int(np.argmax(cand))+lag_min
                    pitch_hz=round(self.rate/lag,2)
                    # Compare pitch to closest octave-equivalent specified reference.
                    pitch_deviation=round(1200*math.log2(pitch_hz/reference_hz) - 1200*round(math.log2(pitch_hz/reference_hz)),1)
        issues={
          'clip':clip_rate>=.005,
          'too_quiet':rms_db<quiet_db and rms_db>-65,
          'too_loud':rms_db>-9,
          'silence':rms_db<-55,
          'dropout':dropout,
          'dc_offset':abs(dc)>.055,
          'overcompressed':crest_db<4 and rms_db>-23,
          'harsh':high_ratio>.68 and rms_db>-42,
          'muddy':low_ratio>.80 and rms_db>-42,
          'rumble':rumble_ratio>.55 and rms_db>-42,
          'phase':corr is not None and corr<-.2,
          'smear':spread<.08 and crest_db<6 and rms_db>-25,
          'sibilance':top/(mid+top+EPS)>.79 and rms_db>-40,
          'level_jump':old is not None and rms_db-old>11 and rms_db>-40,
          'onset_grid':onset_grid is not None and onset_grid>.55,
          'tuning_reference':pitch_deviation is not None and abs(pitch_deviation)>25,
        }
        values={'peak_dbfs':round(peak_db,1),'rms_dbfs':round(rms_db,1),'crest_db':round(crest_db,1),
            'clipping_pct':round(clip_rate*100,3),'dc_offset':round(dc,4),
            'spectral_centroid_hz':round(centroid,0),'transient_flux':round(flux,2),
            'high_frequency_ratio':round(high_ratio,3),'low_band_ratio':round(low_ratio,3),
            'rumble_ratio':round(rumble_ratio,3),'stereo_correlation':None if corr is None else round(corr,3),
            'pitch_hz':pitch_hz,'pitch_cents_offset':pitch_deviation,'onset_grid_error':onset_grid}
        # 0-100 is a rule-of-thumb TECHNICAL signal-health index, not an aesthetic judgment.
        penalties={'clip':32,'silence':28,'dropout':30,'too_loud':12,'too_quiet':12,
                   'dc_offset':10,'overcompressed':9,'harsh':6,'muddy':5,
                   'rumble':6,'phase':18,'smear':4,'sibilance':4,'level_jump':6}
        health=100-sum(weight for key,weight in penalties.items() if issues.get(key))
        values['signal_health_score']=max(0,min(100,health))
        return {'metrics':values,'issues':issues}
