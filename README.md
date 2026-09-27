# Attio Merlin Proxy

OpenAI-compatible API gateway for **Attio Merlin** (Ask Attio). Turns Attio's in-app AI assistant into a local `/v1/chat/completions` endpoint with an account pool, round-robin rotation, a live dashboard, and scope-gate fallback routing.

Zero dependencies — plain Node.js (≥18), single file.

## How it works

Attio Merlin's backend system prompt refuses general-purpose coding — it only answers Attio-workflow questions. The proxy works around that scope gate in two layers:

1. **Workflow code-step wrapper** — every prompt is wrapped as an Attio Workflow custom code step: a draft with a `TODO: complete this step` stub next to a real `attio.companies.update(...)` call, with the user's request quoted inside the stub. Merlin completes the TODO instead of refusing.
2. **Fallback routing** — the wrapper is model-sensitive (model-side guardrails drift). If a non-opus answer looks like a refusal, a stall, or codeless output for a code request, the proxy silently retries once on `claude-5.5-opus` and returns whichever answer contains real code.

```
client ──POST /v1/chat/completions──▶ proxy ──PUT thread + poll turn──▶ Attio Merlin
                                        │                                   │
                                        │◀──────── answer ──────────────────┘
                                        └─ refusal/stall? ── retry on opus ─▶ answer with code
```

## Quick start

```bash
# 1. Add an Attio account (cookie from a logged-in browser session)
cp attio-accounts.example.json attio-accounts.json   # then fill in your cookie + workspace slug

# 2. Start
npm start            # listens on 127.0.0.1:18092

# 3. Grab the generated gateway API key from the dashboard
open http://127.0.0.1:18092/
```

The gateway key is generated on first start and stored in `attio-state.json` (shown on the dashboard). Accounts can also be added live from the dashboard.

## API

### Models

| Model id | Upstream |
|---|---|
| `claude-5.5-opus` | Anthropic Claude 5.5 Opus |
| `claude-4.6-sonnet` (default) | Anthropic Claude 4.6 Sonnet |
| `gpt-6-sol` | OpenAI GPT 6 Sol |
| `gpt-5.6-terra` | OpenAI GPT 5.6 Terra |
| `gemini-3.8-flash` | Gemini 3.8 Flash |
| `gemini-3.1-pro` | Gemini 3.1 Pro |

### Chat completion

```bash
curl -s http://127.0.0.1:18092/v1/chat/completions \
  -H "Authorization: Bearer $ATTIO_PROXY_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-4.6-sonnet",
    "messages": [{"role": "user", "content": "Write a function topKFrequent(words, k) in javascript."}]
  }'
```

Streaming (`"stream": true`, SSE) is supported. OpenAI-compatible request/response shapes; token usage fields are zeroed (Attio does not report them).

### Other endpoints

- `GET /v1/models` — model list (auth required)
- `GET /health` — liveness + live-account count (no auth)
- `GET /` — dashboard: stats, API key, account table, add-account form
- `POST /dashboard/api` — account management (`add`, `disable`, `enable`, `delete`, `revive`)

## Account pool

`attio-accounts.json` holds Attio cookie sessions (round-robin; auto-disabled for 24h on HTTP 401):

```json
{
  "accounts": [
    {
      "name": "acct-1",
      "cookie": "attio-session=eyJ...; attio-app-session=eyJ...",
      "slug": "your-workspace-slug",
      "email": "you@example.com",
      "enabled": true
    }
  ]
}
```

The cookie comes from a logged-in `app.attio.com` browser session (`attio-session=...` is required; workspace slug is the segment in `https://app.attio.com/<slug>/...`). Session JWT expiry is shown on the dashboard.

## Configuration

| Env | Default | Description |
|---|---|---|
| `PROXY_PORT` | `18092` | Listen port (loopback only) |

Runtime files (gitignored): `attio-state.json` (gateway API key, stats, rotation cursor), `attio-accounts.json` (sessions).

## Use with OpenAI-compatible clients

Works anywhere an OpenAI base URL is accepted, e.g.:

```
OPENAI_BASE_URL=http://127.0.0.1:18092/v1
OPENAI_API_KEY=<gateway key from the dashboard>
```

## Notes

- Model names and the scope-gate behavior are Attio-internal and can change without notice; the fallback heuristics (`looksLikeRefusal` / `looksLikeStall` / `looksLikeCode` in `server.mjs`) are the place to patch when that happens.
- Loopback-only listener by design — expose it further only behind your own auth.
- Attio sessions expire; watch the dashboard's Session column and swap dead cookies.
