# From working MVP to a real $20/mo product

## Shipped in this source bundle

- PRISM-inspired cross-platform Flutter audio monitor (mic PCM16 and configurable detectors)
- Python FastAPI engine, WebSockets, 32 built-in detectors, 10 presets, custom AI questions
- Multi-scale ring buffer: 80ms diagnostics, 2s/0.5s signal windows, 10s/8s AI windows, earlier 4s reviews for severe faults
- Rule-based technical signal-health index and optional Clef-Omni AI aesthetic rating
- Local/cloud Clef-Omni adapter with audio WAV and typed decision questions
- Hysteresis/cooldowns, OSC alerts, optional LAN-only WLED visual warnings
- Offline WAV diagnostic endpoint and known-fault fixture
- Responsive product website, real Stripe session/webhook/license/portal paths (credentials required)
- License verification gates hosted cloud decision mode, not local FOSS functionality
- Backend unit/integration tests

## Required before a paid public launch

1. Train and validate against recordings labeled by sound engineers across streaming hardware, untreated rooms, live venues and content genres. Measure precision/recall, detection latency, false-alarm rates, calibration and fairness. Identify failure causes, not only subjective AI scores.
2. Run Clef-Omni locally on target GPU hardware and confirm the deployed SystemOne audio endpoint returns the official numeric/structured answers. Measure throughput under concurrent sessions; add workers, Redis queue, and long-job shedding if needed.
3. Test real Cloudflare Workers AI credentials and hosted APIs including rate-limiting, rejection, provider outages, network jitter and data retention. Introduce consent and explicit privacy disclosures.
4. Test Flutter on physical Windows, macOS, Linux, Android, iOS and browser devices. Add native system-audio capture for platforms where OBS/loopback integration matters; review sample-rate and channel normalization.
5. Build authenticated SaaS accounts, secure login/recovery, an organization model, customer support, observability, business disclosures and licensing recovery. Unit-test all Stripe lifecycle events and entitlement reconciliation.
6. Deploy with HTTPS/WSS, Origin allowlist, token rotation, signup rate limiting, payments fraud controls, abuse throttling, database backups and proper CSP. Confirm $20/mo cloud costs under heavy use and define fair-use controls.
7. Add alerts integrations for OBS WebSocket v5 and common lighting consoles with explicit safeguards and opt-in. Never let the model autonomously change console gain or strobe lights at a live event.
8. Add local calibration data: input-device profiles, baseline noise floor, latency budgets, dynamic thresholds, optional stems for objective vocal-level differences, and event-replay tools (with audio retention consent).

## Product differentiation

Treat this as *audible anomaly observability*: not generative music, and not a replacement for a live engineer. Explain which check produced a signal, show evidence and calibrated confidence, keep humans in control, and make the FOSS localhost experience worth using even without a cloud account.
