# API reference (initial v0.1)

## REST

- `GET /api/health`: engine version, feature availability, provider readiness.
- `GET /api/presets`: preset mappings and 32 built-in detector definitions.
- `POST /api/analyze-wav?preset=streamer`: binary PCM16 WAV, response with DSP metrics + matching checks (maximum file size 8MiB, 60s decoded).
- `POST /api/billing/checkout`: `{ "email": "..." }` returns `{ "url": "https://checkout.stripe.com/..." }` if configured.
- `POST /api/billing/activate`: `{ "session_id": "cs_..." }` returns one-time `access_token` for an active paid subscription.
- `POST /api/billing/portal`: `Authorization: Bearer ae_...` returns Stripe customer portal URL.
- `POST /api/billing/webhook`: Stripe webhook body with signed `Stripe-Signature` header.

## WebSocket streaming

Connect to `ws://127.0.0.1:8788/ws/audio`. Send the first **JSON text** message:

```json
{
  "type": "start",
  "token": "optional-local-api-token",
  "pro_token": "optional-pro-license",
  "preset": "streamer",
  "sample_rate": 16000,
  "channels": 1,
  "clef": "off",
  "quiet_db": -37,
  "bpm": 120,
  "reference_hz": 440,
  "enabled": ["clip", "silence", "dropout", "buried_vocal"],
  "custom": [{
    "label": "Missing snare",
    "question": "Does the snare disappear unexpectedly from this track?",
    "threshold": 0.75
  }]
}
```

Then send **binary little-endian signed PCM16 audio**, as mono or interleaved stereo at the declared rate. Data must match the declared sample rate/channels. Keep packets at ~0.1 seconds, at most 3 seconds. The socket pushes events:

```json
{"type":"ready","preset":"streamer","sample_rate":16000,"checks":[],"clef":"off"}
{"type":"meters","seconds":1.0,"metrics":{"peak_dbfs":-9.2,"rms_dbfs":-20.7}}
{"type":"alert","id":"clip","label":"Clipping","severity":"critical","source":"dsp","message":"Hard clipping","probability":1.0}
{"type":"decision","id":"buried_vocal","probability":0.77,"threshold":0.68,"positive":true,"source":"clef-local"}
{"type":"ai_error","message":"CLEF request failed: ConnectError"}
{"type":"error","message":"Invalid server access token"}
```

`type=ai_score` carries the optional 0–100 uncalibrated Clef aesthetics score when requested. `signal_health_score` is a rule-based technical index in meters. `type=decision` means an AI estimate; `type=alert` is gated by hysteresis/cooldown. Not all decisions trigger an alert. A severe DSP fault can trigger an earlier ~4-second AI review instead of waiting for the normal 8-second AI hop. The signal engine runs independently if the model is unavailable. Observed amplitude values are in **dBFS** (not LUFS); audio is not source separated. Soundcard loopback CLI uses the same protocol.

## OSC output

`AESTHETICS_OSC_PORT=9000` sends to `127.0.0.1:9000` at `/aesthetics/alert` with type string,string,float: `fault_id`, `severity`, `probability`.

### Optional WLED lighting bridge

To prove the event-to-light pipeline works without hardware, run:

```bash
# Terminal A: receives alert OSC and prints actions; no physical light change
cd engine
python -m aesthetics.light_bridge --dry-run

# Terminal B: restart engine with OSC enabled
export AESTHETICS_OSC_PORT=9000
python run.py
```

For a WLED device on your private LAN (for example, `192.168.1.48`), run `python -m aesthetics.light_bridge --ip 192.168.1.48`. A warning shows a static amber color (critical: muted red), without a strobe, for three seconds before attempting to restore the previous state. **Never rely on this as an emergency or venue-safety light.** On Windows PowerShell, use `$env:AESTHETICS_OSC_PORT='9000'` instead of `export`.
