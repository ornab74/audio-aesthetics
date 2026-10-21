# Clef-Omni model integration / local inference

The product uses Cloudflare **Clef-Omni**, not non-audio Clef/Flash and not a generic chat-completion model. It emits structured, typed yes/no decision scores. On first use, model-specific endpoints must be configured by the operator.

Reference API: https://developers.cloudflare.com/workers-ai/models/clef-omni/
Original weights: https://huggingface.co/Cloudflare/clef-omni
Apple Silicon 4-bit alternative: https://huggingface.co/mlx-community/clef-omni-4bit

## Audio-bearing SystemOne payload

```json
{
  "model": "clef-omni",
  "state": {
    "purpose": "Live audio quality diagnosis; answer based on audible evidence.",
    "signal_features": {"peak_dbfs": -9.2, "rms_dbfs": -20.7}
  },
  "audio": ["data:audio/wav;base64,<VALID_WAV_BASE64>"],
  "questions": {
    "buried_vocal": {
      "type": "noul",
      "instructions": "Does the lead singing sound buried under the instruments?"
    }
  }
}
```

The engine writes a real WAV container, not a bare byte array, and accepts numeric decision outputs. It ignores malformed/unknown answers rather than calling everything a match. The model sends up to 64 questions per pass, bounded by the official schema.

### Hosted configuration

- `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` must exist in the Python engine environment.
- Hosted endpoint: `https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/@cf/cloudflare/clef-omni`.
- Choose `cloud` in Flutter with a valid active subscription token. The backend handles secrets and TLS requests.
- This is **not** a direct client-to-provider integration, so no secret Cloudflare key is embedded in the Flutter app.

### Truly local AI configuration

Set `CLEF_LOCAL_URL=http://127.0.0.1:8088/v1/systemone` (or your compatible HTTPS endpoint). Launch a **third-party or self-compiled server that explicitly supports Clef-Omni audio** with the request format above. Local inference is heavy: one available MLX variant is approximately 20GB and recommends 32GB+ RAM. Generic llama.cpp OpenAI `/v1/chat/completions`, text-only Clef-Flash endpoints, and common generative audio models **are not drop-in substitutes** for this API. No model weights or GPU runtimes are bundled.

For a pure CPU laptop without the large model, select **DSP-only**; the deterministic offline feature set remains fully operational. For a lighter local language-audio option, one could add a LAION CLAP adapter, but CLAP zero-shot similarity is not calibrated Clef-style yes/no decision probability. It is deliberately **not silently substituted** here.

## Aesthetic score caveats

- Vocal prominence from a mixed stereo program isn't directly measurable without vocal separation, stems, or a supervised model. It is a **Clef opinion** here.
- Guitar detuning without a reference score/stems can be ambiguous; use isolated-input reference pitch to get stronger numerical evidence.
- Beat drift requires explicit tempo and robust onset detection, and this DSP implementation is only a coarse proxy.
- AI decisions may be wrong or inconsistent in chaotic live environments. Calibrate alerts with labeled examples before relying on a critical show.
- **No automatic mixing, patching, gain riding, or FOH control** is permitted in this MVP. Alerts are informational only.
