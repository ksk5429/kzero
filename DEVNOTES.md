# K-ZERO Developer Notes

> Running log of decisions, bugs, fixes, and learnings. Updated every session.

---

## 2026-04-03

### Bugs Fixed
- **Zombie processes**: Background `python app.py &` from Claude Code created unkillable orphan processes. **Fix**: Always run in foreground in user's terminal. Never use `&` from Claude Code.
- **`_sim_stop` UnboundLocalError**: Nested function `_agent_speak` wrote to `_sim_stop` without `global` declaration. Python treated it as local. **Fix**: Added `global _sim_stop`.
- **Stuck simulation state**: `_sim_running=True` persisted after failed Groq API calls, blocking all future simulations. **Fix**: Auto-reset on new request + `/stop` route clears state.
- **Thinking indicator invisible on Groq**: Groq responds in ~1s, poll interval is 2s, so thinking message was added and removed before poll caught it. **Fix**: Minimum 3-second display time for thinking indicators.
- **Dash 4 button serialization bug**: `html.Button` with `id="stop-btn"` was not serialized into `_dash-layout` JSON when used as `Input` in callbacks. **Workaround**: Use `html.A(href="/stop")` instead of `html.Button`.
- **HF Spaces 30s timeout**: Synchronous callbacks that ran simulations hit the HF proxy timeout. **Fix**: Background thread + `dcc.Interval` polling every 2s.

### Architecture Decisions
- **Callable layout** (`app.layout = _make_layout`): Fresh layout on each page load. Means `_dash-layout` API returns minimal data but browser renders correctly.
- **5-minute auto-timeout**: Simulations killed after 300s to prevent zombie threads on HF Spaces.
- **Rate limit resilience**: 4 retries with exponential backoff (5s/10s/15s) + API key rotation + 2s pacing between agents.
- **`/stop` Flask route**: Plain HTML link instead of Dash callback to stop simulation. Resets all state and clears messages.

### Performance Benchmarks (Qwen 2.5 7B on RTX 2060)
- 1-step dialectic (4 rounds × 7 agents = 28 messages): ~24 min
- 3-step dialectic (84 messages): ~71 min
- Overnight capacity: ~7 runs × 3 steps in 9 hours

### Key Files
| File | Lines | Purpose |
|------|-------|---------|
| `app.py` | ~500 | Dash chat interface (HF Spaces + local) |
| `launcher.py` | ~230 | Windows .exe launcher with auto Ollama setup |
| `runner/overnight.py` | ~330 | Multi-run batch for overnight Ollama execution |
| `runner/dialectic.py` | ~392 | Hegelian dialectic engine (CLI) |

### Tokens/Costs
- Groq free: 100K tokens/day, 30 req/min — good for ~1 demo session
- Groq free with `llama-3.1-8b-instant`: faster, higher rate limits
- Google Gemini free: 20 req/day/model/key — too limited
- Ollama local: unlimited, ~5 min per agent response on CPU

### Known Issues
- 4 unkillable orphan Python processes from earlier `&` background launches (die on reboot)
- Overnight batch killed early due to Ollama being slow on CPU (~70 min per 3-step run)
- HF Spaces Dash dropdown styling doesn't match dark theme perfectly
