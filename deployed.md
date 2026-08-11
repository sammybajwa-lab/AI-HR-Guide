# Deployment Record

**Submitted by:** Sammy Bajwa

Complete this file only after the final service is live.

## Application

**Platform:** Render / Railway / other: `____________________`

**Application URL:** `____________________________________________`

**Health URL:** `____________________________________________/health`

**Git commit used for the recording:** `____________________`

## Runtime configuration

Record the settings actually used during the final demo.

| Setting | Final value |
|---|---|
| `RAG_BACKEND` | `________________` |
| `MCP_TRANSPORT` | `________________` |
| `RAG_TOP_K` | `________________` |
| `LLM_ENABLED` | `________________` |
| `OPENAI_MODEL` | `________________` |
| `OPENAI_BASE_URL` | `default / __________________` |

Do not place API keys in this file.

## Health check

Paste the final `/health` response here after deployment:

```json
{
  "status": "TO_BE_REPLACED",
  "app": "TO_BE_REPLACED",
  "mcp": "TO_BE_REPLACED",
  "mcp_tool_count": 0,
  "rag_backend": "TO_BE_REPLACED",
  "llm_enabled": false
}
```

## Latency check

Record one cold request after the service has been idle and at least five warm requests.

**Cold request:** `________ ms / seconds`

**Warm requests:** `________, ________, ________, ________, ________`

**Warm median:** `________`

**Warm p95 or approximate upper bound:** `________`

## Final deployment checks

- [ ] Home page loads in a clean browser session.
- [ ] `/health` returns a healthy or expected status.
- [ ] MCP tool count matches the final server.
- [ ] Remote-work demo completes end-to-end.
- [ ] PTO demo completes end-to-end.
- [ ] Citations are visible in the UI.
- [ ] Tool-call trace is visible in the UI.
- [ ] No API key or secret appears in GitHub, browser output, logs shown in the video, or this file.
