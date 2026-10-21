# HUMOID // PRISM OS — Quickstart

This is an **editable Flutter/Dart + Python source project**, not a compiled installer.

## 1. Start your private Python API

```bash
cd backend
python -m venv .venv
# activate .venv (Linux/macOS: source .venv/bin/activate; Windows: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt
python run.py
```

Copy the displayed bearer token. The API listens at `http://127.0.0.1:8765`.

## 2. Generate platform projects and run Flutter

Install a current stable Flutter SDK, then:

```bash
cd flutter
flutter create --platforms=android,ios,linux,macos,windows .
flutter pub get
flutter analyze
flutter test
flutter run -d <your-desktop-or-mobile-device>
```

Set API URL to `http://127.0.0.1:8765`, enter bearer token, and pick a NEW passphrase (10+ characters). If running on a physical phone, see the remote connection restrictions in `docs/SECURITY.md`.

## 3. Enable your preferred local model

**GGUF / llama-cpp-python:** In a separate environment:

```bash
pip install 'llama-cpp-python[server]'
python -m llama_cpp.server --model /absolute/path/model.gguf --host 127.0.0.1 --port 8081
```

Open **Local Models** in the app. Select `llama.cpp`, set server URL and model ID to match the actual local server.

**LiteRT-LM:** Install `litert-lm-api` on supported systems, supply a compatible `.litertlm` file, choose the LiteRT option in Local Models. These adapters have not been validated with actual model files in this build environment.

## 4. Verification

```bash
cd backend
PYTHONPATH=. python -m pytest -q tests
# 13 passed in this build environment
cd ../original
PYTHONPATH=src:. python -m pytest -q fusion_tests
# 18 passed in this build environment
```

## 5. Finding your source

- Flutter responsive navigation: `flutter/lib/screens/shell.dart`
- Flutter real screens: `flutter/lib/screens/pages.dart`
- UI color/type tokens: `flutter/lib/core/palette.dart`
- Python API routes: `backend/server/app.py`
- Python vault and original code: `backend/server/state.py`, `original/`
- llama.cpp and LiteRT runtime: `backend/server/inference.py`
- 15 implementation packages: `docs/15_PARTS.md`
- 1:1 parity / known missing functionality: `docs/PARITY.md`
- Security cautions: `docs/SECURITY.md`

The entire original user-provided Humoid project is included under `original/` with its GPL license. This does not imply every Tkinter/TUI functionality is wired to the new Flutter interface.
