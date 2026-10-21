# HUMOID // PRISM OS

**Flutter desktop/mobile client + authenticated Python backend + original Humoid Fusion sources.**

A retro-futurist Material 3 implementation inspired by the supplied Humoid Ring posters and concept galleries. Original PRISM and encryption modules are imported **unchanged** for authoritative data operations; Flutter widgets are real, interactive controls.

> **Status — working source project, not a verified 1:1 production port.** The backend has been exercised with automated tests. Flutter SDK is not installed in the build environment, so Flutter compilation, Android/iOS packaging, live llama.cpp inference, and live LiteRT inference have **not** been validated. The original high-privilege AgentHarness, entire historical CustomTkinter GUI, and model-encrypted LiteRT download flow are preserved under `original/` but are **not** all exposed in the Flutter API. See `docs/PARITY.md` and `docs/SECURITY.md`.

## What is included

```
Humoid_PRISM_Flutter_Source/
├── flutter/
│   ├── pubspec.yaml                Flutter package & assets
│   ├── lib/main.dart               App entry point
│   ├── lib/core/                   PRISM design system, HTTP/SSE client, state
│   ├── lib/screens/                Adaptive desktop/mobile shell & live workspaces
│   ├── lib/widgets/                Retro Material 3 panels, orbits, stars, badges
│   ├── assets/                     Supplied visual-art references
│   └── test/widget_test.dart       Flutter connection screen smoke test
├── backend/
│   ├── server/app.py               FastAPI routes
│   ├── server/state.py             AgentVault + PrismStore integration
│   ├── server/security.py          Password-derived vault key / identity
│   ├── server/inference.py         llama.cpp and LiteRT-LM adapters
│   ├── run.py                      Safe localhost-only runner
│   ├── migrate_legacy.py           Optional read-only PRISM importer
│   ├── requirements.txt
│   └── tests/test_api.py           FastAPI tests
├── original/                       Original supplied code + GPLv3 license
└── docs/                           Parity, 15 stages, API, security
```

## Run — step 1: Python service

Python 3.11+ recommended, tested here with FastAPI and Python 3.11/3.12 compatible packages.

```bash
cd Humoid_PRISM_Flutter_Source/backend
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

The service prints an **API token** and listens at `http://127.0.0.1:8765`. Keep the token secret; the server requires it even to unlock the vault. To reuse a token between launches, set a long random `HUMOID_API_TOKEN` in your host environment. The service does **not** accept public LAN traffic by default.

The vault's **first** successful unlock creates a **new** Scrypt-derived passphrase identity in `~/.humoid-prism-flutter`; choose and remember a password of 10+ characters. It intentionally will not open or overwrite the Tkinter GUI's existing vault. Persistent data uses the original `AgentVault` AES-256-GCM sealed snapshots, with the original PRISM SQLite database mounted only while unlocked.

## Run — step 2: local inference model

### Option A: llama-cpp-python GGUF

In a **second** environment/terminal with a compatible Python version and native toolchain:

```bash
pip install 'llama-cpp-python[server]'
python -m llama_cpp.server --model /absolute/path/to/your/model.gguf --host 127.0.0.1 --port 8081
```

The Flutter settings page defaults to `http://127.0.0.1:8081/v1` and model ID `local-gguf`. If your llama.cpp server exposes another ID, update **Local Models**. Model weights are not included. `llama-cpp-python` native builds differ by OS/GPU and may require extra installation steps.

### Option B: Google's LiteRT-LM Python SDK

On a supported host:

```bash
pip install litert-lm-api
```

In **Local Models** choose **LiteRT-LM** and enter an existing absolute `.litertlm` model path. This adapter uses `litert_lm.Engine(path)` and the Python Conversation API to produce text. It is **not** a direct replacement for the original GUI's **encrypted model-at-rest loader**: original encrypted weights require a separate migration/decryption bridge, which this release deliberately does not pretend to provide.

## Run — step 3: Flutter

Flutter stable and Dart 3.4+ are required; newer Flutter stable is recommended for the Material 3 APIs used here.

```bash
cd Humoid_PRISM_Flutter_Source/flutter
flutter create --platforms=android,ios,linux,macos,windows .
flutter pub get
flutter run -d linux     # or -d windows, -d macos, -d android, -d ios
```

`flutter create` supplies the machine/platform-specific Android, iOS, macOS, Windows, and Linux runner/host projects. These generated platform directories are **not** checked into this source bundle because the Flutter SDK was unavailable to generate and validate them in the build environment. Keep the existing `lib`, `assets`, `pubspec.yaml` and `test` files when scaffolding.

In the app, enter the API URL and bearer token printed by the Python service. Unlock with the vault passphrase. Choose and start an inference backend for AI chat. Python and Flutter are separate processes; the Python service must keep running.

**Mobile:** The Python process does not run inside the APK/IPA in this version. On a phone `127.0.0.1` means **the phone**, not your desktop. A VPN / TLS reverse proxy plus explicit device authentication is required to connect remotely. Do **not** simply modify the Python backend to bind to `0.0.0.0` without appropriate security work. Android/iOS native model inference is not yet implemented.

## Native features covered by this release

- Mission Control dashboard with live PRISM ring and task counts.
- Adaptive desktop sidebar, mobile navigation, Material 3 controls, original space-art assets.
- Local GGUF chat completion & SSE text streaming, LiteRT blocking chat, encrypted chat sessions and history.
- PRISM memory create/search/forget/distill; all 7 original memory rings.
- CTX scoped recall with original `summary_packet` retrieval.
- ChronoOrbit task creation, recurrence, due/review, **explicit user approval**, task event history.
- Custom agent persona profiles injected into text chat (not full original AgentHarness tool execution).
- Read-only AST symbol scanner for configured Python workspace.
- New memory constellation graph derived from project/ring topology. This is exploratory, **not** a trained semantic map.
- Editable llama.cpp/LiteRT settings and local model file inventory.
- Text-only Road Scanner risk category (local AI estimate, not for driving decisions).
- Vault unlock/lock and encrypted PRISM state.
- Optional **read-only** PRISM memory import from original Humoid Fusion.

## Test

```bash
cd backend
python -m pip install pytest
PYTHONPATH=. pytest -q tests
# Test original (included) PRISM separately:
cd ../original
PYTHONPATH=src:. python -m pytest -q fusion_tests

# After Flutter is installed:
cd ../flutter
flutter analyze
flutter test
```

Tests in this environment: **13 backend tests pass; 18 original fusion tests pass**. A static delimiter-balance check was run on Flutter source, but **there was no Dart compiler available**, so no Flutter build or widget test execution is claimed.

## Data migration

From a closed original Humoid installation:

```bash
cd backend
python migrate_legacy.py /path/to/humoid-ring-main --target ~/.humoid-prism-flutter
```

The importer requests your original GUI and new Flutter-vault passwords interactively, reads the original encrypted PRISM SQLite snapshot **without writing to the old vault**, and adds memory entries to the new vault idempotently (with index consent disabled). It does **not** migrate original tasks, GUI chat-history database, encrypted models, or TUI tool settings. Back up both vaults before migrating. Do not run while either GUI/backend is writing to its vault.

## License and attribution

The `original/` directory contains user-provided GPLv3 licensed source; **the original GPLv3 license is retained**. This combined derivative source package is distributed under GPLv3 (see `LICENSE`). No pretrained models, native Python wheels, or system font files are redistributed.

See `docs/SECURITY.md` for additional cautions. Interface concept art is a UI design reference, not evidence of tested machine-learning performance.

## Status at handoff (October 2026)

- **Backend tests:** 13 passed, including scoped memory, encryption, explicit approval, read-only tools, streamed chat and the mocked local HTTP inference adapter.
- **Original fusion tests:** 18 passed. These tests don't prove that every original GUI workflow has been ported.
- **Dart:** structural delimiter checks pass. The Flutter SDK is not available in this build environment, so compilation and widget tests must be run locally.
- **Model weights:** not bundled, no live hardware inference performed. You must provide a compatible `.gguf` or `.litertlm` and follow the corresponding runtime's instructions.
- **Parity:** see `docs/PARITY.md`; especially agent tool execution, old GUI migration, encrypted model loading, and embedded mobile runtimes remain incomplete.
