# Agora Agent Backend — SwiftUI Quickstart Recipe

FastAPI service that owns Agora token generation and agent session lifecycle for
the native iOS (SwiftUI) client quickstart. The iOS app reaches it directly at
`http://localhost:8000` (the Simulator shares the host network).

## What this service does

Starts a simple conversational AI agent using only Agora-managed vendors — **zero-key** —
and enables RTM so the iOS client's `ConversationalAIAPI` toolkit can render the
live transcript:

- `data_channel = "rtm"` — routes transcript/state/metrics over RTM
- `advanced_features = {"enable_rtm": True}` — required for the iOS toolkit
- `enable_metrics = True` / `enable_error_message = True` — stage metrics + errors

**Pipeline:** `DeepgramSTT(nova-3, en)` → `OpenAI` (Agora-managed, keyless) → `MiniMaxTTS`

The `OpenAI` vendor is Agora-managed (keyless by default). There is **no
separate `llm/` service** in this recipe.

## Run

```bash
cd server
uv venv venv && . venv/bin/activate
uv pip install -r requirements.txt -r requirements-dev.txt
python src/server.py
```

## Environment

Required:

- `AGORA_APP_ID` — Agora project App ID.
- `AGORA_APP_CERTIFICATE` — Agora project App Certificate.

Optional:

| Variable | Default | Notes |
| --- | :---: | --- |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model |
| `OPENAI_API_KEY` | — | BYO only — Agora manages the OpenAI key by default (keyless). Set only if your account requires it. |
| `AGENT_GREETING` | built-in | Optional opening line override |

## API

- `GET /get_config` — token + channel/UID config
- `POST /startAgent` — start an agent session
- `POST /stopAgent` — stop an agent session
