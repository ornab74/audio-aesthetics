import io,wave
import numpy as np
from aesthetics.dsp import CircularAudio,SignalAnalyzer,pcm16
from aesthetics.chunker import MultiScaleChunker,AlertGate
from aesthetics.clef import get_noul_probability,to_wav_data_url
from aesthetics.presets import selected_detections
import pytest

def tone(sec=2,fs=16000,amp=.3,f=440):
    t=np.arange(int(sec*fs),dtype=np.float32)/fs
    return (amp*np.sin(2*np.pi*f*t)).astype(np.float32)

def test_clean_audio_and_metrics():
    metrics=SignalAnalyzer().analyze(tone())
    assert metrics['metrics']['rms_dbfs'] < -10
    assert metrics['metrics']['peak_dbfs'] < -9
    assert not metrics['issues']['clip']
    assert not metrics['issues']['silence']

def test_hard_clip():
    a=np.clip(3*tone(),-.7,.7) # below clip threshold
    assert not SignalAnalyzer().analyze(a)['issues']['clip']
    hard=np.clip(5*tone(),-1,1)
    assert SignalAnalyzer().analyze(hard)['issues']['clip']

def test_silence():
    x=np.zeros(32000,dtype=np.float32)
    result=SignalAnalyzer().analyze(x)
    assert result['issues']['silence']
    assert result['metrics']['rms_dbfs']==-120

def test_dropout():
    x=tone();x[4000:10000]=0
    assert SignalAnalyzer().analyze(x)['issues']['dropout']

def test_phase():
    x=tone();array=np.stack([x,-x],axis=1)
    assert SignalAnalyzer(channels=2).analyze(array)['issues']['phase']

def test_quiet_level_jump():
    s=SignalAnalyzer()
    assert s.analyze(tone(amp=.002))['issues']['too_quiet']
    assert s.analyze(tone(amp=.4))['issues']['level_jump']

def test_ring_buffer_and_chunk_boundaries():
    rb=CircularAudio(16000,1,seconds=2)
    rb.push(np.ones(16000,np.float32));rb.push(np.full(24000,2,np.float32))
    assert rb.count==32000
    assert len(rb.tail(.5))==8000
    assert rb.tail(.5).mean()==2
    c=MultiScaleChunker(fast_s=.5,ai_s=8.,ai_window_s=10.)
    fast,slow=c.feed(tone(sec=.5))
    assert fast is not None and slow is None
    for _ in range(15):fast,slow=c.feed(tone(sec=.5))
    assert slow is not None and len(slow)==128000

def test_alert_gate_hysteresis_and_rearm():
    now=[0]
    gate=AlertGate(trigger=2,clear=2,cooldown=8,clock=lambda:now[0])
    assert not gate.update('clip',True)
    assert gate.update('clip',True)
    assert not gate.update('clip',True)
    gate.update('clip',False);gate.update('clip',False)
    assert not gate.update('clip',True)
    assert not gate.update('clip',True) # still cooling down
    now[0]=12
    gate.update('clip',False);gate.update('clip',False)
    assert not gate.update('clip',True)
    assert gate.update('clip',True)

def test_preset_and_custom_validations():
    assert len(selected_detections('streamer'))>5
    detects=selected_detections('guitar',custom=[{'label':'Missing snare',
      'question':'Is the snare missing from the performance?'}])
    assert any(x.id=='custom_0' and x.layer=='ai' for x in detects)
    with pytest.raises(ValueError):selected_detections('nonexistent')
    with pytest.raises(ValueError):selected_detections('custom',custom=[{'question':'too short'}])

def test_pcm_and_wav_encoding():
    audio=tone(sec=.3)
    x=(audio*32767).astype('<i2').tobytes()
    assert len(pcm16(x))==4800
    url=to_wav_data_url(audio,16000)
    assert url.startswith('data:audio/wav;base64,')
    import base64
    data=base64.b64decode(url.split(',',1)[1]);w=wave.open(io.BytesIO(data),'rb')
    assert w.getnframes()==4800 and w.getframerate()==16000

def test_model_probability_parse():
    assert get_noul_probability(.77)==.77
    assert get_noul_probability({'probability':.62})==.62
    assert get_noul_probability({'garbage':'x'}) is None
