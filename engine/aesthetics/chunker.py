"""Overlapping multi-timescale chunks + alert hysteresis and cooldown."""
from __future__ import annotations
import time
from .dsp import CircularAudio

class MultiScaleChunker:
    def __init__(self,rate=16000,channels=1,fast_s=.5,ai_s=8.,fast_window_s=2.,ai_window_s=10.):
        self.audio=CircularAudio(rate,channels,seconds=max(32,ai_window_s+2))
        self.fast_hop=int(fast_s*rate);self.ai_hop=int(ai_s*rate)
        self.fast_window_s=fast_window_s;self.ai_window_s=ai_window_s
        self.received=0;self.fast_done=0;self.ai_done=0;self.rate=rate
    def feed(self,chunk):
        self.audio.push(chunk);self.received+=len(chunk)
        fast=self.received-self.fast_done>=self.fast_hop and self.audio.count>=int(.2*self.rate)
        ai=self.received-self.ai_done>=self.ai_hop and self.audio.count>=int(self.ai_window_s*.75*self.rate)
        if fast:self.fast_done=self.received
        if ai:self.ai_done=self.received
        return (self.audio.tail(self.fast_window_s) if fast else None,
                self.audio.tail(self.ai_window_s) if ai else None)

class AlertGate:
    """Require N positive readings; reset only after clear readings, suppress repeat bursts."""
    def __init__(self,trigger=2,clear=2,cooldown=8.,clock=None):
        self.trigger=trigger;self.clear=clear;self.cooldown=cooldown;self.clock=clock or time.monotonic
        self.state={}
    def update(self,key:str,positive:bool)->bool:
        s=self.state.setdefault(key,{'hit':0,'miss':0,'active':False,'last':-1e12})
        if positive:
            s['hit']+=1;s['miss']=0
            if not s['active'] and s['hit']>=self.trigger and self.clock()-s['last']>=self.cooldown:
                s['active']=True;s['last']=self.clock();return True
        else:
            s['miss']+=1;s['hit']=0
            if s['miss']>=self.clear:s['active']=False
        return False
