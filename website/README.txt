AUDIO AESTHETICS // RUN LOCALLY
================================
1. Install Python 3.11+ and Flutter stable (Flutter is optional for command-line loopback monitoring).
2. cd engine
3. python -m venv .venv
4. Activate your virtual environment.
5. pip install -r requirements.txt
6. python run.py
7. Open http://127.0.0.1:8788 for the website.
8. For Flutter: cd ../flutter ; flutter create --platforms=android,ios,linux,macos,windows,web . ; python tool/enable_audio_permissions.py ; flutter pub get ; flutter run -d <device>
9. For OBS / system output: pip install soundcard ; python -m aesthetics.capture --list-devices ; python -m aesthetics.capture --device N
10. For optional local CLEF: start a separately installed Clef-Omni SystemOne server at http://127.0.0.1:8088/v1/systemone.

IMPORTANT: No automatic subscription charges. Stripe requires operator setup of a live $20/month recurring Price, API key and webhook.
Cloud CLEF requires provider credentials and an activated Pro license. The default engine is local/offline.
License: GPLv3; original PRISM reference sources are preserved in prism_reference/.
Read README.md in the package root for full instructions and security guidance.
