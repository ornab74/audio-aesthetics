"""Preset configuration. Descriptive AI questions, not claims of measured ground truth."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import re

@dataclass(frozen=True)
class Detection:
    id: str
    label: str
    description: str
    layer: str = 'signal'  # signal or ai
    threshold: float = .68
    severity: str = 'warning'
    def json(self): return asdict(self)

SIGNAL = [
    Detection('clip','Clipping','Hard clip and flat-topped peaks',threshold=.005,severity='critical'),
    Detection('too_quiet','Too quiet','Program audio below configured RMS threshold',threshold=-37),
    Detection('too_loud','Too loud','Sustained excessive RMS level',threshold=-9),
    Detection('silence','Unexpected silence','Sustained near-silence',threshold=-55,severity='critical'),
    Detection('dropout','Dropouts','Near-zero segments interrupting active audio',severity='critical'),
    Detection('dc_offset','DC offset','Persistent bias off zero',threshold=.055),
    Detection('overcompressed','Overcompressed','Low crest factor during loud sustained audio',threshold=4.0),
    Detection('harsh','Harsh / brittle','High 3-8 kHz energy relative to mids'),
    Detection('muddy','Muddy / boomy','Excess low-mid energy relative to presence'),
    Detection('rumble','Low rumble','Unexpected sub-80 Hz energy'),
    Detection('phase','Stereo phase risk','Left/right anti-correlation can cancel in mono',threshold=-.2),
    Detection('smear','Transient smear proxy','Sustained sound with reduced transient contrast'),
    Detection('sibilance','Sibilance proxy','High-frequency burst / harshness proxy'),
    Detection('level_jump','Abrupt level jump','Sudden power jump compared with previous chunk',threshold=11),
    Detection('onset_grid','Beat grid drift proxy','Transients do not align to user-specified BPM'),
    Detection('tuning_reference','Pitch reference deviation','Isolated sustained note differs from selected note'),
]
AI = [
    Detection('buried_vocal','Buried vocals','Does the lead singing sound buried under the instruments?','ai'),
    Detection('vocal_hot','Vocals too high','Does the vocal dominate the mix unnaturally?','ai'),
    Detection('distorted_voice','Unwanted vocal distortion','Does spoken or sung voice sound unintentionally distorted?','ai'),
    Detection('detuned_guitar','Detuned guitar','Does a guitar audibly sound out of tune relative to the music?','ai'),
    Detection('offbeat','Performance off beat','Does a performer audibly lose the musical beat?','ai'),
    Detection('unbalanced_mix','Unbalanced mix','Does the mix have an obvious tonal or instrumental imbalance?','ai'),
    Detection('reverb_wash','Reverb wash','Does excessive reverb obscure clarity and articulation?','ai'),
    Detection('feedback','Feedback howl','Is there an unintended microphone/speaker feedback tone?','ai',severity='critical'),
    Detection('monitor_bleed','Monitor bleed','Is there distracting stage or monitor bleed?','ai'),
    Detection('click_pop','Clicks and pops','Are there audible glitches, clicks or pops?','ai'),
    Detection('room_resonance','Room resonance','Is strong resonant coloration making the sound worse?','ai'),
    Detection('crowd_swallow','Crowd masking','Is the main performance masked by crowd noise?','ai'),
    Detection('voice_fatigue','Harsh vocals','Does the vocal timbre sound strained or unpleasantly harsh?','ai'),
    Detection('noise_floor','Background noise','Is steady hiss or electrical hum distractingly audible?','ai'),
    Detection('echo','Unwanted echo','Is an echo or delayed duplicate of the voice audible?','ai'),
    Detection('music_aesthetics','Audio aesthetics warning','Does this audio contain a clear technical quality issue?','ai'),
]
CATALOG = {d.id:d for d in SIGNAL+AI}
PRESETS = {
    'streamer':['clip','too_quiet','too_loud','silence','dropout','level_jump','feedback','distorted_voice','echo','noise_floor','unbalanced_mix'],
    'artist':['clip','too_loud','harsh','muddy','smear','buried_vocal','vocal_hot','offbeat','unbalanced_mix','reverb_wash','music_aesthetics'],
    'guitar':['clip','tuning_reference','harsh','detuned_guitar','offbeat','reverb_wash','click_pop'],
    'vocals':['clip','too_quiet','too_loud','harsh','sibilance','buried_vocal','vocal_hot','distorted_voice','voice_fatigue','reverb_wash'],
    'levels':['clip','too_quiet','too_loud','silence','dropout','dc_offset','overcompressed','level_jump','phase','rumble'],
    'concert':['clip','silence','dropout','phase','level_jump','feedback','crowd_swallow','monitor_bleed','buried_vocal','room_resonance'],
    'podcast':['clip','too_quiet','too_loud','silence','dropout','noise_floor','echo','distorted_voice','click_pop'],
    'dj':['clip','too_loud','overcompressed','phase','smear','offbeat','unbalanced_mix','click_pop'],
    'mastering':['clip','overcompressed','harsh','muddy','rumble','phase','unbalanced_mix','music_aesthetics'],
    'custom':['clip','too_quiet','silence','dropout'],
}

def custom_detection(question: str, label: str='Custom detection', threshold:float=.70, custom_id:str='custom_0') -> Detection:
    question=question.strip()
    if not 12 <= len(question) <= 500: raise ValueError('Detection instruction must be 12-500 characters')
    if not 0.50 <= float(threshold) <= 0.99: raise ValueError('Threshold must be 0.50-0.99')
    if not re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}',custom_id): raise ValueError('Invalid identifier')
    return Detection(custom_id,label.strip()[:80] or 'Custom detection',question,'ai',float(threshold))

def selected_detections(preset:str, enabled:list[str]|None=None, custom:list[dict]|None=None) -> list[Detection]:
    if preset not in PRESETS: raise ValueError(f'Unknown preset: {preset}')
    ids=enabled if enabled is not None else PRESETS[preset]
    if len(ids)>64: raise ValueError('Up to 64 checks per session')
    ds=[CATALOG[k] for k in ids if k in CATALOG]
    for i,c in enumerate((custom or [])[:32]):
        if not isinstance(c,dict): continue
        ds.append(custom_detection(c.get('question',''),c.get('label','Custom check'),c.get('threshold',.70),f'custom_{i}'))
    if len([d for d in ds if d.layer=='ai'])>64: raise ValueError('Clef supports up to 64 questions')
    return ds
