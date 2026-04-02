"""
K-ZERO -- Council of 8 Web App
A magazine-style single-page deliberation viewer.

Run locally: python app.py
Deploy: Hugging Face Spaces, Render, Railway
"""

import json
import os
import random
import sys
import time
import traceback
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BG = "#0d1117"
CARD = "#161b22"
CARD_HOVER = "#1c2333"
BORDER = "#30363d"
TEXT = "#e6edf3"
MUTED = "#8b949e"
GOLD = "#f0c040"
GOLD_DIM = "#d4a017"
ACCENT_BLUE = "#58a6ff"
ACCENT_GREEN = "#3fb950"
ACCENT_RED = "#f85149"
ACCENT_PURPLE = "#bc8cff"

AGENT_COLORS: dict[str, str] = {
    "Elon Musk": "#f44336",
    "Richard Feynman": "#2196f3",
    "Kobe Bryant": "#ff9800",
    "Steve Jobs": "#e0e0e0",
    "Jean-Paul Sartre": "#9c27b0",
    "George Carlin": "#4caf50",
    "Bryan Johnson": "#1976d2",
    "Kevin (\uae40\uacbd\uc120)": "#90a4ae",
}

AGENT_ROLES: dict[str, str] = {
    "Elon Musk": "First-Principles Thinker",
    "Richard Feynman": "Curious Explorer",
    "Kobe Bryant": "Relentless Competitor",
    "Steve Jobs": "Visionary Designer",
    "Jean-Paul Sartre": "Existential Philosopher",
    "George Carlin": "Absurdist Comedian",
    "Bryan Johnson": "Biohacker Optimizer",
    "Kevin (\uae40\uacbd\uc120)": "The Moderator",
}

PROJECT_ROOT = Path(__file__).parent
TRANSCRIPTS_DIR = PROJECT_ROOT / "transcripts"
PREDICTIONS_DIR = PROJECT_ROOT / "predictions"

# ---------------------------------------------------------------------------
# Shared styles
# ---------------------------------------------------------------------------

PAGE_STYLE: dict[str, Any] = {
    "maxWidth": "920px",
    "margin": "0 auto",
    "padding": "0 20px 80px",
    "fontFamily": "'Inter', 'Segoe UI', 'Noto Sans KR', system-ui, sans-serif",
    "color": TEXT,
    "lineHeight": "1.6",
}

SECTION_GAP = "64px"


def _section_style(extra: dict | None = None) -> dict:
    base = {"marginTop": SECTION_GAP}
    if extra:
        base.update(extra)
    return base


def _card_style(extra: dict | None = None) -> dict:
    base: dict[str, Any] = {
        "backgroundColor": CARD,
        "border": f"1px solid {BORDER}",
        "borderRadius": "12px",
        "padding": "24px",
    }
    if extra:
        base.update(extra)
    return base


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def _extract_question_from_transcript(transcript_path: Path) -> str | None:
    """Extract the actual question from the transcript's opening message."""
    try:
        with transcript_path.open("r", encoding="utf-8") as f:
            transcript = json.load(f)
        for entry in transcript[:5]:
            if entry.get("type") in ("moderator", "god_mode") and len(entry.get("text", "")) > 30:
                text = entry["text"]
                # Find LAST question mark in first 300 chars (the main question)
                search_range = text[:300]
                idx = search_range.rfind("?")
                if idx > 0:
                    # Find sentence start
                    start = max(text.rfind(".", 0, idx), text.rfind(":", 0, idx))
                    start = start + 1 if start > 0 else 0
                    q = text[start:idx + 1].strip()
                    # Clean up common prefixes
                    for prefix in ["The question is", "The question"]:
                        if q.lower().startswith(prefix.lower()):
                            q = q[len(prefix):].lstrip(": ")
                    return q
                return text[:120]
    except Exception:
        pass
    return None


def _scan_analyses() -> list[dict[str, Any]]:
    """Return metadata dicts for every *_analysis.json, newest first."""
    results: list[dict[str, Any]] = []
    if not TRANSCRIPTS_DIR.exists():
        return results
    for p in sorted(TRANSCRIPTS_DIR.glob("*_analysis.json"), reverse=True):
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            meta = data.get("metadata", {})

            # Try to get actual question from transcript
            slug = p.stem.replace("_analysis", "")
            transcript_path = TRANSCRIPTS_DIR / f"{slug}.json"
            question = _extract_question_from_transcript(transcript_path)
            title = question or meta.get("scenario_title", p.stem)

            results.append({
                "path": str(p),
                "filename": p.name,
                "slug": slug,
                "title": title,
                "model": meta.get("model", "unknown"),
                "rounds": meta.get("total_rounds", 0),
                "messages": meta.get("total_messages", 0),
                "agents": meta.get("agent_names", []),
            })
        except Exception:
            continue
    return results


def _load_analysis(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_transcript(analysis_data: dict) -> list[dict]:
    """Load transcript JSON referenced by analysis metadata."""
    tp = analysis_data.get("metadata", {}).get("transcript_path", "")
    if tp:
        tp_path = Path(tp)
        if not tp_path.exists():
            # Try relative to transcripts dir
            tp_path = TRANSCRIPTS_DIR / tp_path.name
        if tp_path.exists():
            with tp_path.open("r", encoding="utf-8") as f:
                return json.load(f)
    # Fallback: try deriving from analysis path
    return []


def _find_prediction(slug: str) -> dict | None:
    """Try to find a prediction JSON that matches the slug."""
    if not PREDICTIONS_DIR.exists():
        return None
    for p in PREDICTIONS_DIR.glob("*.json"):
        if slug.split("_")[0] in p.stem.lower():
            try:
                with p.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue
    return None


def _agent_color(name: str) -> str:
    return AGENT_COLORS.get(name, "#8b949e")


def _agent_role(name: str) -> str:
    return AGENT_ROLES.get(name, "Council Member")


# ---------------------------------------------------------------------------
# Environment variables for live simulation
# ---------------------------------------------------------------------------

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
COUNCIL_MODEL = os.getenv("COUNCIL_MODEL", "llama-3.1-8b-instant")  # Fastest Groq model for web

PLACEHOLDER_QUESTIONS = [
    "What would you sacrifice everything for?",
    "Is consciousness an illusion?",
    "Should we colonize Mars before fixing Earth?",
    "Is the pursuit of immortality noble or foolish?",
    "Can AI ever truly understand human suffering?",
    "What is more important: freedom or security?",
    "Is ambition a virtue or a vice?",
    "Should we fear death or embrace it?",
]

# For/against keyword lists (from evolution.py _extract_position_local)
_FOR_KEYWORDS = [
    "yes", "absolutely", "should", "must", "pursue", "essential",
    "obviously", "of course", "agree", "support", "beneficial",
    "necessary", "important", "worth", "embrace", "create",
    "build", "advance", "progress", "opportunity",
]
_AGAINST_KEYWORDS = [
    "no", "shouldn't", "dangerous", "risk", "wrong", "foolish",
    "absurd", "meaningless", "pointless", "reject", "oppose",
    "refuse", "never", "death is", "hubris", "arrogant",
    "doomed", "failure", "destroy", "irrelevant",
]


def _score_position(text: str) -> float:
    """Score a response from -1 (against) to +1 (for) using keyword matching."""
    text_lower = text.lower()
    for_count = sum(1 for kw in _FOR_KEYWORDS if kw in text_lower)
    against_count = sum(1 for kw in _AGAINST_KEYWORDS if kw in text_lower)
    total = for_count + against_count
    if total > 0:
        return max(-1.0, min(1.0, (for_count - against_count) / total))
    return 0.0


# ---------------------------------------------------------------------------
# Streaming Council Simulation (background thread + polling)
# ---------------------------------------------------------------------------

import threading

# Shared state for streaming simulation
_sim_messages: list[dict[str, Any]] = []
_sim_running = False
_sim_done = False
_sim_error = ""
_sim_stop = False  # Flag to stop mid-deliberation


def _run_council_thread(question: str, n_steps: int = 3):
    """Run multi-step evolving deliberation in a background thread.

    Each STEP = one full Hegelian dialectic (4 rounds, all agents).
    Between steps, agents carry forward their revised positions.
    Thoughts compound and evolve across steps.

    Messages are appended to _sim_messages in real-time for streaming.
    """
    global _sim_messages, _sim_running, _sim_done, _sim_error, _sim_stop
    _sim_messages = []
    _sim_running = True
    _sim_done = False
    _sim_error = ""
    _sim_stop = False

    try:
        from runner.agent import load_agents, _create_client

        original_env = {
            k: os.environ.get(k, "")
            for k in ("LLM_API_KEY", "LLM_BASE_URL", "COUNCIL_MODEL", "COUNCIL_MAX_TOKENS")
        }
        if LLM_API_KEY:
            os.environ["LLM_API_KEY"] = LLM_API_KEY
        if LLM_BASE_URL:
            os.environ["LLM_BASE_URL"] = LLM_BASE_URL
        if COUNCIL_MODEL:
            os.environ["COUNCIL_MODEL"] = COUNCIL_MODEL
        os.environ["COUNCIL_MAX_TOKENS"] = "120"

        client = _create_client()
        agents = load_agents(PROJECT_ROOT, client=client)

        for k, v in original_env.items():
            if v:
                os.environ[k] = v

        agent_names = [n for n in agents.keys() if "Kevin" not in n]
        history: list[dict[str, Any]] = []

        def _add(speaker, text, round_num, msg_type="agent", phase=""):
            label = f"[{phase}] " if phase else ""
            entry = {"speaker": speaker, "text": text, "round": round_num,
                     "type": msg_type, "phase": phase}
            history.append(entry)
            _sim_messages.append(entry)

        def _agent_speak(name, topic, round_num, phase="", max_tok=100):
            """Speak with retry + rate limit backoff + pacing."""
            if _sim_stop:
                return
            agent = agents[name]
            for attempt in range(4):
                try:
                    text = agent.respond(history, current_topic=topic, max_tokens=max_tok)
                    if text and not text.startswith("["):
                        _add(name, text, round_num, phase=phase)
                        time.sleep(2)  # Pace between agents (stay under 30 req/min)
                        return
                except Exception as e:
                    err = str(e).lower()
                    if ("429" in err or "rate" in err or "quota" in err) and attempt < 3:
                        wait = 5 * (attempt + 1)  # 5s, 10s, 15s
                        _sim_messages.append({
                            "speaker": "[K-ZERO]",
                            "text": f"Rate limit hit. Waiting {wait}s before {name.split()[0]} speaks...",
                            "round": round_num, "type": "system", "phase": "",
                        })
                        time.sleep(wait)
                        # Rotate API key if available
                        try:
                            from runner.agent import _rotate_client
                            agent.client = _rotate_client()
                        except Exception:
                            pass
                        continue
                    else:
                        _add(name, f"[Error: {str(e)[:100]}]", round_num, "system", phase)
                        return
            _add(name, f"[{name.split()[0]} could not respond after retries]",
                 round_num, "system", phase)

        # ================================================================
        # MULTI-STEP HEGELIAN DIALECTIC
        # Each step = THESIS -> ANTITHESIS -> SYNTHESIS -> REVISION
        # Positions carry forward. Thoughts compound across steps.
        # ================================================================

        all_agents = list(agent_names)
        positions: dict[str, str] = {}
        round_counter = 0

        god_twists = [
            "What if the question itself is wrong? What is the REAL question?",
            "Assume your position is completely wrong. What changes?",
            "If only ONE idea from this debate survives, which should it be?",
            "200 years from now, which side will history vindicate?",
            "What would a child say that none of you have considered?",
        ]

        for step in range(1, n_steps + 1):
            if _sim_stop:
                _add("[K-ZERO]", "Deliberation stopped by user.", round_counter, "moderator")
                break
            random.shuffle(all_agents)

            # --- Step header ---
            if step == 1:
                _add("[K-ZERO]",
                     f"\u2501\u2501\u2501 THE COUNCIL CONVENES \u2501\u2501\u2501\n"
                     f"Question: \"{question}\"\n"
                     f"Evolution Steps: {n_steps} | Agents: {len(all_agents)}\n"
                     f"Each step: THESIS \u2192 ANTITHESIS \u2192 SYNTHESIS \u2192 REVISION",
                     round_counter, "moderator")
            else:
                _add("[K-ZERO]",
                     f"\u2501\u2501\u2501 EVOLUTION STEP {step}/{n_steps} \u2501\u2501\u2501\n"
                     f"Positions from Step {step-1} are carried forward. The dialectic deepens.",
                     round_counter, "moderator")

            # --- THESIS: ALL agents ---
            round_counter += 1
            thesis_label = f"S{step} THESIS"
            _add("[K-ZERO]",
                 f"Step {step} \u2014 THESIS: State your position." +
                 (" Your previous position is known \u2014 has your thinking evolved?" if step > 1 else ""),
                 round_counter, "moderator", thesis_label)

            for name in all_agents:
                prev = positions.get(name, "")
                ctx = f" Your position last step: \"{prev[:120]}\"." if prev else ""
                _agent_speak(name,
                    f"Question: \"{question}\".{ctx} State your position in 2 sentences MAX.",
                    round_counter, thesis_label, max_tok=100)

            # --- ANTITHESIS: ALL agents ---
            round_counter += 1
            anti_label = f"S{step} ANTITHESIS"
            _add("[K-ZERO]",
                 f"Step {step} \u2014 ANTITHESIS: Challenge the WEAKEST argument. Name them.",
                 round_counter, "moderator", anti_label)

            random.shuffle(all_agents)
            for name in all_agents:
                _agent_speak(name,
                    f"Question: \"{question}\". "
                    f"Name the weakest argument and who said it. 2 sentences MAX.",
                    round_counter, anti_label, max_tok=100)

            # --- SYNTHESIS: ALL agents ---
            round_counter += 1
            synth_label = f"S{step} SYNTHESIS"
            _add("[K-ZERO]",
                 f"Step {step} \u2014 SYNTHESIS: Reflect. What tension exists? What are you NOT seeing?",
                 round_counter, "moderator", synth_label)

            random.shuffle(all_agents)
            for name in all_agents:
                _agent_speak(name,
                    f"Question: \"{question}\". "
                    f"What tension exists between your view and the best counter-argument? 2 sentences.",
                    round_counter, synth_label, max_tok=100)

            # --- GOD twist (every step) ---
            round_counter += 1
            _add("[GOD]", random.choice(god_twists), round_counter, "god_mode")

            # --- REVISION: ALL agents ---
            round_counter += 1
            rev_label = f"S{step} REVISION"
            _add("[K-ZERO]",
                 f"Step {step} \u2014 REVISION: State your REVISED position. "
                 f"This carries into Step {step+1}." if step < n_steps else
                 f"Step {step} \u2014 FINAL REVISION: State your ultimate position.",
                 round_counter, "moderator", rev_label)

            random.shuffle(all_agents)
            for name in all_agents:
                prev = positions.get(name, "")
                ctx = f" Previous: \"{prev[:120]}\"." if prev else ""
                _agent_speak(name,
                    f"Question: \"{question}\".{ctx} "
                    f"Revised position in 2 sentences. Changed or held firm?",
                    round_counter, rev_label, max_tok=100)

            # Extract positions for next step
            for msg in _sim_messages:
                if msg.get("phase") == rev_label and msg["type"] == "agent":
                    positions[msg["speaker"]] = msg["text"][:200]

        # === KEVIN: FINAL SYNTHESIS across ALL steps ===
        kevin = agents.get("Kevin (\uae40\uacbd\uc120)")
        if kevin:
            try:
                synthesis = kevin.respond(history,
                    current_topic=(
                        f"In 4-5 sentences: Who evolved? Who held firm? "
                        f"What emerged that no one held at the start? "
                        f"End with ONE unanswered question."),
                    max_tokens=200)
                if synthesis and not synthesis.startswith("["):
                    _add("Kevin (\uae40\uacbd\uc120)", synthesis, round_counter + 1,
                         "moderator", "FINAL SYNTHESIS")
            except Exception as e:
                _add("Kevin (\uae40\uacbd\uc120)", f"[Error: {e}]", round_counter + 1, "system")

    except Exception as e:
        _sim_error = str(e)

    _sim_running = False
    _sim_done = True


def _analyze_responses(responses: list[dict]) -> dict:
    """Quick keyword-based analysis of simulation responses."""
    scores: dict[str, float] = {}
    for r in responses:
        if r.get("type") != "agent":
            continue
        name = r["speaker"]
        score = _score_position(r["text"])
        scores[name] = score

    if not scores:
        return {"verdict": "NO RESPONSES", "scores": {}}

    avg_score = sum(scores.values()) / len(scores)
    for_count = sum(1 for s in scores.values() if s > 0.1)
    against_count = sum(1 for s in scores.values() if s < -0.1)

    if abs(avg_score) > 0.3:
        verdict = "LEANS FOR" if avg_score > 0 else "LEANS AGAINST"
    elif for_count > 0 and against_count > 0:
        verdict = "SPLIT"
    else:
        verdict = "UNDECIDED"

    return {"verdict": verdict, "scores": scores, "avg_score": round(avg_score, 2)}


# ---------------------------------------------------------------------------
# Build the app
# ---------------------------------------------------------------------------


def build_app() -> Any:
    try:
        import plotly.graph_objects as go
        from dash import Dash, Input, Output, State, dcc, html, no_update
    except ImportError as exc:
        raise ImportError("Dash is required: pip install dash plotly") from exc

    analyses = _scan_analyses()

    app = Dash(
        __name__,
        title="K-ZERO",
        suppress_callback_exceptions=True,
    )

    # Inject CSS animations for the loading overlay
    app.index_string = '''<!DOCTYPE html>
<html>
<head>{%metas%}{%title%}{%favicon%}{%css%}
<style>
@keyframes pulse-orb {
    0%, 100% { transform: scale(1); opacity: 0.4; box-shadow: 0 0 20px rgba(243,156,18,0.2); }
    50% { transform: scale(1.4); opacity: 1; box-shadow: 0 0 40px rgba(243,156,18,0.6); }
}
@keyframes fade-agent {
    0%, 100% { opacity: 0.2; transform: translateY(0); }
    50% { opacity: 1; transform: translateY(-2px); }
}
@keyframes glow-btn:hover {
    box-shadow: 0 6px 30px rgba(243,156,18,0.5);
    transform: translateY(-1px);
}
@keyframes typing-dots {
    0%, 80%, 100% { opacity: 0.3; }
    40% { opacity: 1; }
}
.chat-scroll::-webkit-scrollbar { width: 6px; }
.chat-scroll::-webkit-scrollbar-track { background: transparent; }
.chat-scroll::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
.chat-scroll::-webkit-scrollbar-thumb:hover { background: #484f58; }
</style>
</head>
<body>{%app_entry%}{%config%}{%scripts%}{%renderer%}</body>
</html>'''

    # Dropdown options
    dropdown_options = [
        {"label": a["title"], "value": a["slug"]}
        for a in analyses
    ]
    default_slug = analyses[0]["slug"] if analyses else None

    # ------------------------------------------------------------------
    # Layout: thin nav bar + single content div
    # ------------------------------------------------------------------

    app.layout = html.Div([
        # Top nav bar
        html.Div([
            html.Div([
                html.Span("K", style={
                    "color": GOLD, "fontWeight": "800",
                    "fontSize": "1.3em",
                }),
                html.Span("-ZERO", style={
                    "color": TEXT, "fontWeight": "800",
                    "fontSize": "1.3em",
                }),
            ], style={"flexShrink": "0"}),

            # Dropdown for switching analyses (only if multiple)
            html.Div([
                dcc.Dropdown(
                    id="analysis-selector",
                    options=dropdown_options,
                    value=default_slug,
                    clearable=False,
                    style={
                        "width": "320px",
                        "backgroundColor": CARD,
                        "color": TEXT,
                        "border": "none",
                        "fontSize": "0.9em",
                    },
                ),
            ], style={
                "display": "flex" if len(analyses) > 1 else "none",
                "alignItems": "center",
            }),
        ], style={
            "backgroundColor": CARD,
            "borderBottom": f"1px solid {BORDER}",
            "padding": "10px 24px",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
            "position": "sticky",
            "top": "0",
            "zIndex": "1000",
        }),

        # ---- Ask the Council (chat interface) ----
        html.Div([
            html.Div([
                # Chat header bar
                html.Div([
                    html.Div([
                        html.Span("K", style={"color": GOLD, "fontWeight": "800", "fontSize": "1.2em"}),
                        html.Span("-ZERO", style={"color": TEXT, "fontWeight": "800", "fontSize": "1.2em"}),
                        html.Span(" Council Chat", style={"color": MUTED, "fontWeight": "400",
                                                          "fontSize": "0.9em", "marginLeft": "8px"}),
                    ]),
                    html.Div([
                        html.Span("8 minds", style={"color": MUTED, "fontSize": "0.75em"}),
                        html.Span(" \u00b7 ", style={"color": BORDER, "fontSize": "0.75em"}),
                        html.Span("Hegelian dialectic", style={"color": MUTED, "fontSize": "0.75em"}),
                    ]),
                ], style={
                    "backgroundColor": CARD,
                    "borderBottom": f"1px solid {BORDER}",
                    "padding": "12px 20px",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",
                    "borderRadius": "12px 12px 0 0",
                }),

                # Example question chips (above chat area)
                html.Div([
                    html.Span("Try: ", style={"color": MUTED, "fontSize": "0.75em", "marginRight": "6px"}),
                    *[html.Span(q, style={
                        "backgroundColor": "rgba(48, 54, 61, 0.5)", "color": MUTED,
                        "padding": "4px 12px", "borderRadius": "14px",
                        "fontSize": "0.72em", "cursor": "pointer",
                        "border": f"1px solid {BORDER}",
                        "display": "inline-block", "margin": "2px",
                    }) for q in [
                        "What is the point of life?",
                        "Should AI replace human jobs?",
                        "Is death the enemy or the teacher?",
                        "Should I quit my PhD?",
                    ]],
                ], style={
                    "padding": "10px 20px 6px",
                    "backgroundColor": "rgba(22, 27, 34, 0.5)",
                    "borderBottom": f"1px solid {BORDER}",
                }),

                # No API key message (inside chat area)
                html.Div(
                    "API key not configured. View pre-computed analyses below.",
                    id="no-api-key-msg",
                    style={
                        "color": ACCENT_RED,
                        "fontSize": "0.82em",
                        "padding": "8px 20px",
                        "textAlign": "center",
                        "display": "none" if LLM_API_KEY else "block",
                    },
                ),

                # Scrollable chat message area
                html.Div(id="sim-results", className="chat-scroll", style={
                    "height": "70vh",
                    "maxHeight": "70vh",
                    "overflowY": "auto",
                    "padding": "16px 20px",
                    "backgroundColor": BG,
                    "display": "flex",
                    "flexDirection": "column",
                }),

                # Typing indicator / status bar
                html.Div(id="sim-status", style={
                    "padding": "8px 20px",
                    "backgroundColor": CARD,
                    "borderTop": f"1px solid {BORDER}",
                    "minHeight": "20px",
                }),

                # Input bar at the BOTTOM (like WhatsApp/Discord)
                html.Div([
                    # Step selector (compact)
                    dcc.Dropdown(
                        id="step-selector",
                        options=[
                            {"label": "1", "value": 1},
                            {"label": "2", "value": 2},
                            {"label": "3", "value": 3},
                            {"label": "5", "value": 5},
                        ],
                        value=3,
                        clearable=False,
                        placeholder="Steps",
                        style={
                            "width": "58px", "backgroundColor": BG,
                            "color": TEXT, "border": "none",
                            "fontSize": "0.85em", "flexShrink": "0",
                        },
                    ),
                    # Single-line input
                    dcc.Input(
                        id="question-input",
                        type="text",
                        placeholder=random.choice(PLACEHOLDER_QUESTIONS),
                        debounce=False,
                        style={
                            "flex": "1",
                            "padding": "12px 16px",
                            "fontSize": "0.95em",
                            "backgroundColor": BG,
                            "color": TEXT,
                            "border": f"1px solid {BORDER}",
                            "borderRadius": "8px",
                            "outline": "none",
                            "fontFamily": "inherit",
                            "boxSizing": "border-box",
                        },
                    ),
                    # Send button
                    html.Button(
                        "\u25B6",
                        id="run-btn",
                        n_clicks=0,
                        style={
                            "width": "44px", "height": "44px",
                            "fontSize": "1.1em", "fontWeight": "700",
                            "backgroundColor": GOLD, "color": BG,
                            "border": "none", "borderRadius": "50%",
                            "cursor": "pointer", "flexShrink": "0",
                            "display": "flex", "alignItems": "center",
                            "justifyContent": "center",
                        },
                    ),
                    # (stop button is below the input bar)
                ], style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "10px",
                    "padding": "12px 16px",
                    "backgroundColor": CARD,
                    "borderTop": f"1px solid {BORDER}",
                    "borderRadius": "0 0 12px 12px",
                }),

                # Polling interval
                dcc.Interval(id="sim-poll", interval=2000, disabled=True),

                # Stop / Reset — plain link that reloads the page
                html.Div(
                    html.A("STOP / NEW QUESTION", href="/", style={
                        "display": "block", "textAlign": "center",
                        "padding": "10px", "fontSize": "0.82em",
                        "fontWeight": "700", "color": "#f85149",
                        "textDecoration": "none", "letterSpacing": "0.05em",
                        "cursor": "pointer",
                    }),
                    style={"borderTop": f"1px solid {BORDER}"},
                ),

                # Hidden stores
                dcc.Store(id="sim-timestamp", data=0),
                dcc.Store(id="sim-msg-count", data=0),
            ], style={
                "maxWidth": "780px",
                "margin": "0 auto",
                "border": f"1px solid {BORDER}",
                "borderRadius": "12px",
                "overflow": "hidden",
            }),
        ], style={
            "padding": "24px 20px 32px",
            "borderBottom": f"1px solid {BORDER}",
            "background": f"linear-gradient(180deg, {CARD} 0%, {BG} 100%)",
        }),

        # Page content (existing analysis viewer)
        html.Div(id="page-content"),

    ], style={
        "backgroundColor": BG,
        "minHeight": "100vh",
        "fontFamily": "'Inter', 'Segoe UI', 'Noto Sans KR', system-ui, sans-serif",
    })

    # ------------------------------------------------------------------
    # Callback: render entire page when analysis changes
    # ------------------------------------------------------------------

    analysis_lookup = {a["slug"]: a for a in analyses}

    @app.callback(
        Output("page-content", "children"),
        Input("analysis-selector", "value"),
    )
    def render_page(slug: str | None) -> Any:
        if not slug or slug not in analysis_lookup:
            if not analyses:
                return _build_empty_state(html)
            slug = analyses[0]["slug"]

        info = analysis_lookup[slug]
        analysis = _load_analysis(info["path"])
        transcript = _load_transcript(analysis)
        prediction = _find_prediction(slug)
        meta = analysis.get("metadata", {})

        return html.Div([
            _build_hero(html, meta, prediction, transcript),
            _build_verdict(html, dcc, go, meta, analysis, prediction),
            _build_who_said_what(html, analysis, transcript),
            _build_clash_map(html, dcc, go, analysis),
            _build_position_tracking(html, analysis),
            _build_topic_clusters(html, analysis),
            _build_conversation(html, transcript),
            _build_emergent_insights(html, analysis),
            _build_pipeline_info(html),
            _build_footer(html),
        ], style=PAGE_STYLE)

    # ------------------------------------------------------------------
    # Callback 1: START simulation (launches background thread, instant return)
    # ------------------------------------------------------------------

    @app.callback(
        Output("sim-status", "children"),
        Output("sim-timestamp", "data"),
        Output("sim-poll", "disabled"),
        Output("sim-msg-count", "data"),
        Input("run-btn", "n_clicks"),
        State("question-input", "value"),
        State("sim-timestamp", "data"),
        State("step-selector", "value"),
        prevent_initial_call=True,
    )
    def start_simulation(n_clicks, question, last_ts, n_steps):
        global _sim_running
        if not n_clicks or not question or not question.strip():
            return html.Div("Please type a question first.",
                           style={"color": ACCENT_RED, "fontSize": "0.9em"}), no_update, True, 0

        now = time.time()
        if last_ts and (now - last_ts) < 30:
            remaining = int(30 - (now - last_ts))
            return html.Div(f"Try again in {remaining}s.",
                           style={"color": GOLD, "fontSize": "0.9em"}), no_update, True, 0

        if not LLM_API_KEY:
            return html.Div("No API key. Set LLM_API_KEY as HF Space secret.",
                           style={"color": ACCENT_RED, "fontSize": "0.9em"}), no_update, True, 0

        if _sim_running:
            return html.Div("Council is already deliberating...",
                           style={"color": GOLD, "fontSize": "0.9em"}), no_update, False, 0

        # Launch simulation in background thread
        steps = int(n_steps) if n_steps else 3
        t = threading.Thread(target=_run_council_thread, args=(question.strip(), steps), daemon=True)
        t.start()

        return html.Div([
            html.Span("\u2022 ", style={"color": GOLD, "animation": "typing-dots 1.4s infinite",
                                        "fontSize": "1.4em", "lineHeight": "1"}),
            html.Span("\u2022 ", style={"color": GOLD, "animation": "typing-dots 1.4s infinite 0.2s",
                                        "fontSize": "1.4em", "lineHeight": "1"}),
            html.Span("\u2022 ", style={"color": GOLD, "animation": "typing-dots 1.4s infinite 0.4s",
                                        "fontSize": "1.4em", "lineHeight": "1"}),
            html.Span(" The Council is assembling...",
                      style={"color": MUTED, "fontSize": "0.82em", "marginLeft": "4px"}),
        ], style={"display": "flex", "alignItems": "center"}), now, False, 0  # Enable polling

    # ------------------------------------------------------------------
    # Callback 2: POLL for new messages (runs every 2 seconds)
    # ------------------------------------------------------------------

    @app.callback(
        Output("sim-results", "children"),
        Output("sim-poll", "disabled", allow_duplicate=True),
        Output("sim-status", "children", allow_duplicate=True),
        Input("sim-poll", "n_intervals"),
        State("sim-msg-count", "data"),
        prevent_initial_call=True,
    )
    def poll_messages(n_intervals, last_count):
        messages = list(_sim_messages)

        if not messages and not _sim_done:
            return no_update, no_update, no_update

        # Build chat bubbles for ALL messages so far
        cards: list[Any] = []
        for msg in messages:
            speaker = msg["speaker"]
            text = _clean_truncated_text(msg["text"])
            round_num = msg["round"]
            msg_type = msg.get("type", "agent")
            phase = msg.get("phase", "")
            color = _agent_color(speaker)

            if msg_type == "god_mode":
                # GOD messages: centered, dramatic red accent
                cards.append(html.Div([
                    html.Div([
                        html.Div("\u26A0", style={
                            "width": "28px", "height": "28px", "borderRadius": "50%",
                            "backgroundColor": ACCENT_RED, "color": "#fff",
                            "display": "flex", "alignItems": "center", "justifyContent": "center",
                            "fontWeight": "700", "fontSize": "0.75em", "margin": "0 auto 6px",
                        }),
                        html.Div("GOD MODE", style={
                            "color": ACCENT_RED, "fontWeight": "700", "fontSize": "0.7em",
                            "letterSpacing": "0.1em", "textAlign": "center", "marginBottom": "6px",
                        }),
                        html.P(text, style={
                            "color": TEXT, "fontSize": "0.92em", "lineHeight": "1.5",
                            "margin": "0", "textAlign": "center", "fontStyle": "italic",
                        }),
                    ], style={
                        "backgroundColor": "rgba(248, 81, 73, 0.06)",
                        "border": f"1px solid rgba(248, 81, 73, 0.25)",
                        "borderRadius": "12px", "padding": "14px 20px",
                        "maxWidth": "85%", "margin": "0 auto",
                    }),
                    html.Div(f"R{round_num}", style={
                        "color": MUTED, "fontSize": "0.65em", "textAlign": "center",
                        "marginTop": "4px", "opacity": "0.6",
                    }),
                ], style={"marginBottom": "12px"}))

            elif msg_type == "moderator":
                # K-ZERO / Kevin moderator: gold accent, full-width
                display_name = speaker.replace("[", "").replace("]", "")
                cards.append(html.Div([
                    html.Div([
                        html.Div(display_name[0] if display_name else "K", style={
                            "width": "28px", "height": "28px", "borderRadius": "50%",
                            "backgroundColor": GOLD, "color": BG,
                            "display": "inline-flex", "alignItems": "center", "justifyContent": "center",
                            "fontWeight": "700", "fontSize": "0.75em", "marginRight": "8px",
                            "verticalAlign": "middle",
                        }),
                        html.Span(display_name, style={
                            "color": GOLD, "fontWeight": "700", "fontSize": "0.85em",
                            "verticalAlign": "middle",
                        }),
                    ], style={"marginBottom": "6px"}),
                    html.P(text, style={
                        "color": TEXT, "fontSize": "0.88em", "lineHeight": "1.5",
                        "margin": "0", "whiteSpace": "pre-wrap", "opacity": "0.9",
                    }),
                    html.Div(f"R{round_num}", style={
                        "color": MUTED, "fontSize": "0.65em", "textAlign": "right",
                        "marginTop": "6px", "opacity": "0.5",
                    }),
                ], style={
                    "backgroundColor": "rgba(240, 192, 64, 0.04)",
                    "borderLeft": f"3px solid {GOLD}",
                    "borderRadius": "4px 12px 12px 4px",
                    "padding": "12px 16px", "marginBottom": "12px",
                }))

            else:
                # Agent messages: chat bubble style
                display_name = speaker
                role = _agent_role(speaker)
                # Subtle tint of the agent's color for bubble background
                bubble_bg = f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.06)"

                # Phase badge
                phase_badge = html.Span(phase.split()[-1] if phase else "", style={
                    "color": GOLD, "fontSize": "0.65em", "fontWeight": "600",
                    "backgroundColor": "rgba(240, 192, 64, 0.12)",
                    "padding": "2px 8px", "borderRadius": "10px",
                    "marginLeft": "8px",
                }) if phase else html.Span()

                cards.append(html.Div([
                    # Avatar + name row
                    html.Div([
                        html.Div(display_name[0] if display_name else "?", style={
                            "width": "32px", "height": "32px", "borderRadius": "50%",
                            "backgroundColor": color, "color": BG,
                            "display": "flex", "alignItems": "center", "justifyContent": "center",
                            "fontWeight": "700", "fontSize": "0.8em", "flexShrink": "0",
                        }),
                        html.Div([
                            html.Span(display_name, style={
                                "color": color, "fontWeight": "700", "fontSize": "0.9em",
                            }),
                            html.Span(f"  {role}", style={
                                "color": MUTED, "fontSize": "0.72em",
                            }),
                            phase_badge,
                        ]),
                    ], style={"display": "flex", "alignItems": "center", "gap": "10px",
                              "marginBottom": "6px"}),
                    # Message bubble
                    html.Div([
                        html.P(text, style={
                            "color": TEXT, "fontSize": "0.88em", "lineHeight": "1.55",
                            "margin": "0", "whiteSpace": "pre-wrap",
                        }),
                        html.Div(f"R{round_num}", style={
                            "color": MUTED, "fontSize": "0.6em", "textAlign": "right",
                            "marginTop": "6px", "opacity": "0.5",
                        }),
                    ], style={
                        "backgroundColor": bubble_bg,
                        "borderLeft": f"2px solid {color}",
                        "borderRadius": "4px 12px 12px 12px",
                        "padding": "10px 14px",
                        "marginLeft": "42px",
                    }),
                ], style={"marginBottom": "10px"}))

        # Status update
        if _sim_done:
            # Simulation complete — show verdict + disable polling
            analysis = _analyze_responses([m for m in messages if m.get("type") == "agent"])
            verdict = analysis["verdict"]
            verdict_color = ACCENT_GREEN if "FOR" in verdict else ACCENT_RED if "AGAINST" in verdict else GOLD

            # Add verdict card at the END (bottom of chat, like a final system message)
            scores = analysis.get("scores", {})
            pills = [html.Span(f"{n.split()[0]}: {s:+.1f}", style={
                "color": ACCENT_GREEN if s > 0.1 else ACCENT_RED if s < -0.1 else MUTED,
                "fontSize": "0.72em", "padding": "3px 10px",
                "border": f"1px solid {'#3fb950' if s > 0.1 else '#f85149' if s < -0.1 else MUTED}",
                "borderRadius": "12px", "display": "inline-block", "margin": "2px",
            }) for n, s in sorted(scores.items(), key=lambda x: x[1], reverse=True)]

            verdict_card = html.Div([
                html.Div(f"VERDICT: {verdict}", style={
                    "color": verdict_color, "fontWeight": "700", "fontSize": "1em",
                    "marginBottom": "8px",
                }),
                html.Div(pills),
            ], style={
                "backgroundColor": "rgba(240, 192, 64, 0.04)",
                "border": f"1px solid {verdict_color}",
                "borderRadius": "12px",
                "textAlign": "center", "padding": "14px 16px",
                "marginTop": "8px",
            })

            agent_count = len([m for m in messages if m.get("type") == "agent"])
            status = html.Div([
                html.Span("\u2713 ", style={"color": ACCENT_GREEN, "fontWeight": "700"}),
                html.Span(
                    f"Deliberation complete \u2014 {len(messages)} messages, {agent_count} agent responses.",
                    style={"color": ACCENT_GREEN, "fontSize": "0.82em"}),
            ], style={"display": "flex", "alignItems": "center"})

            return html.Div([*cards, verdict_card]), True, status

        # Still running — show typing indicator with last speaker context
        agent_msgs = [m for m in messages if m.get("type") == "agent"]
        last_speaker = agent_msgs[-1]["speaker"] if agent_msgs else "The Council"
        status = html.Div([
            html.Span("\u2022 ", style={"color": GOLD, "animation": "typing-dots 1.4s infinite",
                                        "fontSize": "1.4em", "lineHeight": "1"}),
            html.Span("\u2022 ", style={"color": GOLD, "animation": "typing-dots 1.4s infinite 0.2s",
                                        "fontSize": "1.4em", "lineHeight": "1"}),
            html.Span("\u2022 ", style={"color": GOLD, "animation": "typing-dots 1.4s infinite 0.4s",
                                        "fontSize": "1.4em", "lineHeight": "1"}),
            html.Span(f" {last_speaker} is formulating a response...",
                      style={"color": MUTED, "fontSize": "0.82em", "marginLeft": "4px"}),
            html.Span(f"  ({len(messages)} messages)",
                      style={"color": MUTED, "fontSize": "0.7em", "opacity": "0.5"}),
        ], style={"display": "flex", "alignItems": "center"})

        return html.Div(cards), no_update, status

    return app


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def _build_empty_state(html: Any) -> Any:
    return html.Div([
        html.Div([
            html.H1("K-ZERO", style={
                "color": GOLD, "fontSize": "3em",
                "fontWeight": "800", "margin": "0",
            }),
            html.P(
                "No deliberations found. Run your first council session:",
                style={"color": MUTED, "marginTop": "16px", "fontSize": "1.1em"},
            ),
            html.Pre(
                "python -m runner.demiurge",
                style={
                    "color": GOLD, "fontSize": "1.1em",
                    "backgroundColor": CARD, "padding": "16px",
                    "borderRadius": "8px", "display": "inline-block",
                    "marginTop": "12px",
                },
            ),
        ], style={"textAlign": "center", "padding": "120px 24px"}),
    ], style=PAGE_STYLE)


def _build_hero(html: Any, meta: dict, prediction: dict | None, transcript: list | None = None) -> Any:
    """Section 1: Full-bleed hero with title, question, and one-line verdict."""
    # Use the actual opening question from transcript, not the slug title
    title = meta.get("scenario_title", "Untitled Deliberation")
    if transcript:
        for entry in transcript[:3]:
            if entry.get("type") in ("moderator", "god_mode") and len(entry.get("text", "")) > 30:
                # Use the opening prompt as the title — truncate to first sentence
                opening = entry["text"]
                # Find first question mark or period as natural break
                for delim in ["?", ". "]:
                    idx = opening.find(delim)
                    if 20 < idx < 200:
                        title = opening[:idx + 1]
                        break
                else:
                    title = opening[:150]
                break

    # Build verdict line
    verdict_text = ""
    if prediction:
        dom = prediction.get("dominant_prediction", "")
        pct = prediction.get("dominance_pct", 0)
        qtype = prediction.get("question_type", "")
        conf = prediction.get("avg_confidence", 0)
        verdict_text = (
            f"The council {qtype} {dom} "
            f"with {int(conf * 100)}% confidence"
        )

    return html.Div([
        # K-ZERO brand
        html.Div([
            html.Span("K", style={"color": GOLD}),
            html.Span("-ZERO", style={"color": TEXT}),
        ], style={
            "fontSize": "1em", "fontWeight": "800",
            "letterSpacing": "0.15em", "marginBottom": "32px",
            "opacity": "0.5",
        }),

        # The question
        html.H1(f"\u201c{title}\u201d", style={
            "fontSize": "clamp(2em, 5vw, 3.2em)",
            "fontWeight": "800",
            "color": TEXT,
            "margin": "0",
            "lineHeight": "1.2",
            "maxWidth": "700px",
        }),

        # Verdict line
        html.P(verdict_text, style={
            "color": GOLD,
            "fontSize": "1.15em",
            "marginTop": "20px",
            "fontStyle": "italic",
            "letterSpacing": "0.02em",
            "opacity": "1" if verdict_text else "0",
        }) if verdict_text else html.Div(),

        # Model tag
        html.Div(
            meta.get("model", ""),
            style={
                "color": MUTED, "fontSize": "0.8em",
                "marginTop": "24px",
                "padding": "4px 12px",
                "border": f"1px solid {BORDER}",
                "borderRadius": "16px",
                "display": "inline-block",
            },
        ),
    ], style={
        "textAlign": "center",
        "padding": "80px 20px 60px",
        "background": f"linear-gradient(180deg, {CARD} 0%, {BG} 100%)",
        "borderRadius": "0 0 24px 24px",
        "marginTop": "-1px",
    })


def _build_verdict(
    html: Any, dcc: Any, go: Any,
    meta: dict, analysis: dict, prediction: dict | None,
) -> Any:
    """Section 2: Stats and optional prediction pie chart."""
    agents = meta.get("agent_names", [])
    rounds_ = meta.get("total_rounds", 0)
    messages = meta.get("total_messages", 0)

    # Classification from position tracking
    shifted = sum(
        1 for v in analysis.get("position_tracking", {}).values()
        if v.get("shifted")
    )
    total_agents = len(agents)
    if total_agents == 0:
        classification = "EMPTY"
    elif shifted == 0:
        classification = "DEADLOCKED"
    elif shifted < total_agents / 2:
        classification = "POLARIZED"
    else:
        classification = "CONVERGENT"

    # Stats cards
    stats = [
        ("Agents", str(len(agents)), ACCENT_BLUE),
        ("Rounds", str(rounds_), GOLD),
        ("Messages", str(messages), ACCENT_GREEN),
        ("Shifted", f"{shifted}/{total_agents}", ACCENT_PURPLE),
        ("Pattern", classification, ACCENT_RED),
    ]

    stat_elements = []
    for label, value, color in stats:
        stat_elements.append(
            html.Div([
                html.Div(value, style={
                    "fontSize": "1.8em", "fontWeight": "700",
                    "color": color, "lineHeight": "1",
                }),
                html.Div(label, style={
                    "fontSize": "0.8em", "color": MUTED,
                    "marginTop": "6px", "textTransform": "uppercase",
                    "letterSpacing": "0.08em",
                }),
            ], style={
                "textAlign": "center",
                "flex": "1",
                "minWidth": "100px",
            })
        )

    children = [
        html.Div(
            stat_elements,
            style={
                "display": "flex",
                "flexWrap": "wrap",
                "gap": "16px",
                "justifyContent": "center",
            },
        ),
    ]

    # Prediction pie chart if available
    if prediction and prediction.get("prediction_distribution"):
        dist = prediction["prediction_distribution"]
        labels = list(dist.keys())
        values = list(dist.values())
        colors = [ACCENT_GREEN if "FOR" in l.upper() else ACCENT_RED for l in labels]

        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.55,
            marker={"colors": colors, "line": {"color": BG, "width": 2}},
            textinfo="label+percent",
            textfont={"color": TEXT, "size": 14},
            hoverinfo="label+value",
        )])
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            margin={"l": 0, "r": 0, "t": 0, "b": 0},
            height=260,
            width=260,
        )
        fig.add_annotation(
            text=f"<b>{prediction.get('dominant_prediction', '?')}</b>",
            x=0.5, y=0.5, showarrow=False,
            font={"size": 20, "color": GOLD},
        )

        children.append(
            html.Div([
                dcc.Graph(
                    figure=fig,
                    config={"displayModeBar": False},
                    style={"margin": "0 auto"},
                ),
            ], style={"textAlign": "center", "marginTop": "32px"}),
        )

    return html.Div(
        children,
        style=_section_style({
            **_card_style(),
            "padding": "32px",
        }),
    )


def _extract_best_sentences(text: str, max_sentences: int = 3) -> list[str]:
    """Extract the best standalone sentences from agent text."""
    text = text.strip()
    # Split into sentences
    sentences = []
    current = ""
    for char in text:
        current += char
        if char in ".!?" and len(current.strip()) > 20:
            s = current.strip()
            # Filter out meta-text, narration, and broken sentences
            if not any(skip in s.lower() for skip in ["[", "*", "as i", "in my view", "i think that"]):
                sentences.append(s)
            current = ""
    # Return the longest, most substantive sentences
    sentences.sort(key=len, reverse=True)
    return sentences[:max_sentences]


def _build_who_said_what(html: Any, analysis: dict, transcript: list | None = None) -> Any:
    """Section 3: Multiple quote cards per agent from both analysis and transcript."""
    key_quotes = analysis.get("key_quotes", {})

    # Also extract quotes directly from transcript for richer content
    transcript_quotes: dict[str, list[dict]] = {}
    if transcript:
        for msg in transcript:
            if msg.get("type") != "agent":
                continue
            speaker = msg.get("speaker", "")
            text = _clean_truncated_text(msg.get("text", ""))
            rnd = msg.get("round", 0)
            if len(text) < 30:
                continue

            if speaker not in transcript_quotes:
                transcript_quotes[speaker] = []

            best = _extract_best_sentences(text, max_sentences=2)
            for sentence in best:
                transcript_quotes[speaker].append({"quote": sentence, "round": rnd})

    # Merge: key_quotes (from analysis) + transcript quotes
    all_agents = set(list(key_quotes.keys()) + list(transcript_quotes.keys()))

    if not all_agents:
        return html.Div()

    cards: list[Any] = []
    card_idx = 0

    for agent in sorted(all_agents):
        color = _agent_color(agent)
        role = _agent_role(agent)
        quotes_for_agent: list[dict] = []

        # Add key quote first (from analysis — highest quality)
        if agent in key_quotes:
            kq = key_quotes[agent]
            quotes_for_agent.append({
                "quote": _clean_truncated_text(kq.get("quote", "")),
                "round": kq.get("round", "?"),
                "why": kq.get("why_it_matters", kq.get("why_impactful", "")),
                "is_key": True,
            })

        # Add transcript quotes (supplementary)
        if agent in transcript_quotes:
            seen_texts = {q["quote"][:50] for q in quotes_for_agent}
            for tq in transcript_quotes[agent]:
                if tq["quote"][:50] not in seen_texts and len(quotes_for_agent) < 4:
                    quotes_for_agent.append({
                        "quote": tq["quote"],
                        "round": tq["round"],
                        "why": "",
                        "is_key": False,
                    })
                    seen_texts.add(tq["quote"][:50])

        if not quotes_for_agent:
            continue

        # Build agent section
        agent_quotes: list[Any] = []
        for q in quotes_for_agent:
            quote_text = q["quote"]
            # Skip empty or very short quotes
            if len(quote_text) < 15:
                continue

            quote_style = {
                "fontSize": "1.1em" if q.get("is_key") else "0.95em",
                "lineHeight": "1.6",
                "color": TEXT,
                "margin": "12px 0",
                "padding": "0 0 0 16px",
                "borderLeft": f"3px solid {color}",
                "fontStyle": "italic",
            }

            agent_quotes.append(html.Div([
                html.Blockquote(f"\u201c{quote_text}\u201d", style=quote_style),
                html.Div(style={"display": "flex", "gap": "12px", "alignItems": "center"}, children=[
                    html.Span(f"Round {q['round']}", style={
                        "color": MUTED, "fontSize": "0.75em",
                        "backgroundColor": CARD, "padding": "2px 8px",
                        "borderRadius": "4px",
                    }),
                    html.Span(q["why"], style={
                        "color": MUTED, "fontSize": "0.82em",
                    }) if q.get("why") else html.Span(),
                ]),
            ]))

        align_right = (card_idx % 2 == 1)
        card_idx += 1

        card = html.Div([
            html.Div([
                html.Span(agent, style={
                    "color": color, "fontWeight": "700", "fontSize": "1.1em",
                }),
                html.Span(f"  \u00b7  {role}", style={
                    "color": MUTED, "fontSize": "0.85em",
                }),
                html.Span(f"  \u00b7  {len(agent_quotes)} quotes", style={
                    "color": MUTED, "fontSize": "0.8em",
                }),
            ]),
            *agent_quotes,
        ], style={
            **_card_style(),
            "marginBottom": "20px",
            "marginLeft": "48px" if align_right else "0",
            "marginRight": "0" if align_right else "48px",
            "borderLeft": f"3px solid {color}" if not align_right else "none",
            "borderRight": f"3px solid {color}" if align_right else "none",
        })

        cards.append(card)

    return html.Div([
        html.H2("Who Said What", style={
            "color": TEXT, "fontSize": "1.6em",
            "fontWeight": "700", "marginBottom": "8px",
        }),
        html.P(
            "The defining moments from each voice in the council.",
            style={"color": MUTED, "marginBottom": "32px", "fontSize": "0.95em"},
        ),
        *cards,
    ], style=_section_style())


def _build_clash_map(html: Any, dcc: Any, go: Any, analysis: dict) -> Any:
    """Section 4: Network graph + ranked relationship cards."""
    import math

    am = analysis.get("agreement_matrix", {})
    labels = am.get("labels", [])
    matrix = am.get("matrix", [])

    if not labels or not matrix:
        return html.Div()

    short = [n.split(" ")[0] if "(" not in n else n.split("(")[0].strip()
             for n in labels]
    n = len(labels)

    # --- Network Graph ---
    # Arrange agents in a circle
    positions = []
    for i in range(n):
        angle = 2 * math.pi * i / n - math.pi / 2
        positions.append((math.cos(angle), math.sin(angle)))

    fig = go.Figure()

    # Draw edges (connections between agents)
    all_pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            score = matrix[i][j]
            if abs(score) < 0.05:
                continue
            all_pairs.append((i, j, score))

            # Edge color and width
            if score > 0.2:
                color = ACCENT_GREEN
                dash = "solid"
            elif score < -0.2:
                color = ACCENT_RED
                dash = "solid"
            else:
                color = MUTED
                dash = "dot"

            width = max(1, abs(score) * 6)

            fig.add_trace(go.Scatter(
                x=[positions[i][0], positions[j][0]],
                y=[positions[i][1], positions[j][1]],
                mode="lines",
                line={"color": color, "width": width, "dash": dash},
                hoverinfo="text",
                text=f"{short[i]} {'<->' if score > 0 else 'vs'} {short[j]}: {score:+.1f}",
                showlegend=False,
            ))

    # Draw nodes (agents)
    node_x = [p[0] for p in positions]
    node_y = [p[1] for p in positions]
    node_colors = [AGENT_COLORS.get(name, "#888") for name in labels]
    node_text = [f"<b>{s}</b>" for s in short]

    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        marker={"size": 40, "color": node_colors, "line": {"width": 2, "color": "#0d1117"}},
        text=node_text,
        textposition="top center",
        textfont={"size": 13, "color": TEXT},
        hovertemplate="%{text}<extra></extra>",
        showlegend=False,
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 20, "r": 20, "t": 10, "b": 10},
        height=420,
        xaxis={"visible": False, "range": [-1.5, 1.5]},
        yaxis={"visible": False, "range": [-1.5, 1.5], "scaleanchor": "x"},
    )

    # --- Ranked Relationship Cards ---
    raw = am.get("raw_pairwise", {})

    def _find_evidence(a: str, b: str) -> str:
        for key in [f"{a} -> {b}", f"{b} -> {a}"]:
            if key in raw:
                return raw[key].get("evidence", "")
        return ""

    # Sort all pairs by score
    sorted_pairs = sorted(all_pairs, key=lambda x: x[2])

    relationship_cards: list[Any] = []

    # Top 3 clashes (most negative)
    clashes = [p for p in sorted_pairs if p[2] < -0.1][:3]
    for i_idx, j_idx, score in clashes:
        ev = _find_evidence(labels[i_idx], labels[j_idx])
        relationship_cards.append(html.Div([
            html.Div(style={"display": "flex", "alignItems": "center", "gap": "12px"}, children=[
                html.Span(f"{score:+.1f}", style={
                    "color": ACCENT_RED, "fontWeight": "800", "fontSize": "1.5em",
                    "minWidth": "55px",
                }),
                html.Div([
                    html.Div(
                        f"{short[i_idx]} vs {short[j_idx]}",
                        style={"color": TEXT, "fontWeight": "600", "fontSize": "1.05em"},
                    ),
                    html.Div(
                        f"\u201c{ev[:200]}\u201d" if ev else "",
                        style={"color": MUTED, "fontSize": "0.85em", "fontStyle": "italic", "marginTop": "4px"},
                    ),
                ]),
            ]),
        ], style={**_card_style(), "borderLeft": f"4px solid {ACCENT_RED}", "marginBottom": "10px"}))

    # Top 3 alliances (most positive)
    alliances = [p for p in reversed(sorted_pairs) if p[2] > 0.1][:3]
    for i_idx, j_idx, score in alliances:
        ev = _find_evidence(labels[i_idx], labels[j_idx])
        relationship_cards.append(html.Div([
            html.Div(style={"display": "flex", "alignItems": "center", "gap": "12px"}, children=[
                html.Span(f"{score:+.1f}", style={
                    "color": ACCENT_GREEN, "fontWeight": "800", "fontSize": "1.5em",
                    "minWidth": "55px",
                }),
                html.Div([
                    html.Div(
                        f"{short[i_idx]} + {short[j_idx]}",
                        style={"color": TEXT, "fontWeight": "600", "fontSize": "1.05em"},
                    ),
                    html.Div(
                        f"\u201c{ev[:200]}\u201d" if ev else "",
                        style={"color": MUTED, "fontSize": "0.85em", "fontStyle": "italic", "marginTop": "4px"},
                    ),
                ]),
            ]),
        ], style={**_card_style(), "borderLeft": f"4px solid {ACCENT_GREEN}", "marginBottom": "10px"}))

    return html.Div([
        html.H2("Alliances & Conflicts", style={
            "color": TEXT, "fontSize": "1.6em",
            "fontWeight": "700", "marginBottom": "8px",
        }),
        html.P(
            "Green lines = agreement. Red lines = conflict. Thicker = stronger.",
            style={"color": MUTED, "marginBottom": "24px", "fontSize": "0.95em"},
        ),

        # Network graph
        html.Div([
            dcc.Graph(
                figure=fig,
                config={"displayModeBar": False},
            ),
        ], style={
            **_card_style(),
            "padding": "16px",
            "marginBottom": "24px",
        }),

        # Relationship cards
        html.Div(style={"display": "flex", "gap": "20px", "flexWrap": "wrap"}, children=[
            # Clashes column
            html.Div(style={"flex": "1", "minWidth": "280px"}, children=[
                html.Div("CLASHES", style={
                    "color": ACCENT_RED, "fontWeight": "700",
                    "fontSize": "0.8em", "letterSpacing": "0.1em",
                    "marginBottom": "12px",
                }),
                *[c for c in relationship_cards if ACCENT_RED in str(c)],
            ]) if clashes else html.Div(),
            # Alliances column
            html.Div(style={"flex": "1", "minWidth": "280px"}, children=[
                html.Div("ALLIANCES", style={
                    "color": ACCENT_GREEN, "fontWeight": "700",
                    "fontSize": "0.8em", "letterSpacing": "0.1em",
                    "marginBottom": "12px",
                }),
                *[c for c in relationship_cards if ACCENT_GREEN in str(c)],
            ]) if alliances else html.Div(),
        ]),
    ], style=_section_style())


def _build_clash_map_legacy(html: Any, dcc: Any, go: Any, analysis: dict) -> Any:
    """LEGACY heatmap — kept for reference."""
    return html.Div()  # Disabled — replaced by network graph


# Keep the old callouts section for the return
def _dummy_callouts():
    """Legacy placeholder — unused."""
    pass


def _clean_truncated_text(text: str) -> str:
    """Fix truncated LLM output — find the last complete sentence."""
    if not text:
        return text
    text = text.strip()
    # If it ends with proper punctuation, it's fine
    if text and text[-1] in ".!?\"'":
        return text
    # Find last sentence-ending punctuation
    for i in range(len(text) - 1, max(0, len(text) - 200), -1):
        if text[i] in ".!?" and (i + 1 >= len(text) or text[i + 1] in " \n\"'"):
            return text[:i + 1]
    # No good break found — add ellipsis
    return text.rstrip() + "..."


def _build_conversation(html: Any, transcript: list[dict]) -> Any:
    """Section 5: Chat-style transcript."""
    if not transcript:
        return html.Div()

    messages: list[Any] = []
    for msg in transcript:
        speaker = msg.get("speaker", "Unknown")
        text = _clean_truncated_text(msg.get("text", ""))
        round_num = msg.get("round", 0)
        msg_type = msg.get("type", "agent")

        # Determine styling by type
        if msg_type == "god_mode":
            name_color = ACCENT_RED
            bubble_border = f"1px solid {ACCENT_RED}"
            bubble_bg = "rgba(248, 81, 73, 0.08)"
            avatar_bg = ACCENT_RED
            avatar_letter = "!"
            display_name = "GOD MODE"
        elif msg_type == "moderator":
            clean_name = speaker.replace("[", "").replace("]", "")
            name_color = GOLD
            bubble_border = f"1px solid {BORDER}"
            bubble_bg = "rgba(240, 192, 64, 0.05)"
            avatar_bg = GOLD
            avatar_letter = "M"
            display_name = clean_name
        else:
            name_color = _agent_color(speaker)
            bubble_border = f"1px solid {BORDER}"
            bubble_bg = CARD
            avatar_bg = _agent_color(speaker)
            avatar_letter = speaker[0] if speaker else "?"
            display_name = speaker

        messages.append(html.Div([
            # Avatar circle
            html.Div(
                avatar_letter,
                style={
                    "width": "36px",
                    "height": "36px",
                    "borderRadius": "50%",
                    "backgroundColor": avatar_bg,
                    "color": BG if avatar_bg != "#90a4ae" else TEXT,
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "fontWeight": "700",
                    "fontSize": "0.85em",
                    "flexShrink": "0",
                },
            ),
            # Name + round + text
            html.Div([
                html.Div([
                    html.Span(display_name, style={
                        "color": name_color,
                        "fontWeight": "600",
                        "fontSize": "0.9em",
                    }),
                    html.Span(f"  R{round_num}", style={
                        "color": MUTED,
                        "fontSize": "0.75em",
                        "marginLeft": "8px",
                    }),
                ]),
                html.Div(
                    text,
                    style={
                        "color": TEXT if msg_type == "agent" else MUTED,
                        "fontSize": "0.9em",
                        "marginTop": "6px",
                        "lineHeight": "1.65",
                        "whiteSpace": "pre-wrap",
                    },
                ),
            ], style={
                "flex": "1",
                "minWidth": "0",
            }),
        ], style={
            "display": "flex",
            "gap": "12px",
            "padding": "16px",
            "backgroundColor": bubble_bg,
            "border": bubble_border,
            "borderRadius": "8px",
            "marginBottom": "8px",
        }))

    return html.Div([
        html.H2("The Conversation", style={
            "color": TEXT, "fontSize": "1.6em",
            "fontWeight": "700", "marginBottom": "8px",
        }),
        html.P(
            "The full deliberation, unedited.",
            style={"color": MUTED, "marginBottom": "24px", "fontSize": "0.95em"},
        ),
        html.Div(
            messages,
            style={
                "maxHeight": "700px",
                "overflowY": "auto",
                "padding": "4px",
            },
        ),
    ], style=_section_style())


def _build_emergent_insights(html: Any, analysis: dict) -> Any:
    """Section 6: Emergent insight cards."""
    insights = analysis.get("emergent_insights", [])
    if not insights:
        return html.Div()

    cards: list[Any] = []
    for ins in insights:
        contributors = ins.get("contributing_agents", [])
        contributor_tags = []
        for c in contributors:
            color = _agent_color(c)
            contributor_tags.append(html.Span(
                c.split(" ")[0] if "(" not in c else c.split("(")[0].strip(),
                style={
                    "color": color,
                    "fontSize": "0.8em",
                    "padding": "2px 10px",
                    "border": f"1px solid {color}",
                    "borderRadius": "12px",
                    "marginRight": "6px",
                    "display": "inline-block",
                    "marginBottom": "4px",
                },
            ))

        cards.append(html.Div([
            html.Div(
                f"Round {ins.get('emerged_in_round', '?')}",
                style={
                    "color": ACCENT_PURPLE,
                    "fontSize": "0.75em",
                    "textTransform": "uppercase",
                    "letterSpacing": "0.08em",
                    "fontWeight": "600",
                    "marginBottom": "8px",
                },
            ),
            html.P(ins.get("insight", ""), style={
                "color": TEXT,
                "fontSize": "1.05em",
                "fontWeight": "500",
                "margin": "0 0 12px",
                "lineHeight": "1.5",
            }),
            html.P(
                ins.get("evidence", ""),
                style={
                    "color": MUTED,
                    "fontSize": "0.85em",
                    "fontStyle": "italic",
                    "margin": "0 0 12px",
                },
            ) if ins.get("evidence") else html.Div(),
            html.Div(contributor_tags),
        ], style={
            **_card_style(),
            "borderTop": f"3px solid {ACCENT_PURPLE}",
            "marginBottom": "16px",
        }))

    return html.Div([
        html.H2("Emergent Insights", style={
            "color": TEXT, "fontSize": "1.6em",
            "fontWeight": "700", "marginBottom": "8px",
        }),
        html.P(
            "Ideas that didn't exist in any single mind. "
            "They emerged from the collision.",
            style={"color": MUTED, "marginBottom": "32px", "fontSize": "0.95em"},
        ),
        *cards,
    ], style=_section_style())


def _build_position_tracking(html: Any, analysis: dict) -> Any:
    """Section: Who shifted their position during deliberation."""
    tracking = analysis.get("position_tracking", {})
    if not tracking:
        return html.Div()

    cards: list[Any] = []
    for name, data in tracking.items():
        shifted = data.get("shifted", False)
        initial = data.get("initial_position", "")
        final = data.get("final_position", "")
        reason = data.get("shift_description", "")
        color = _agent_color(name)
        short = name.split()[0] if "(" not in name else name.split("(")[0].strip()

        if shifted:
            badge = html.Span("SHIFTED", style={
                "color": BG, "backgroundColor": "#f85149", "padding": "2px 8px",
                "borderRadius": "4px", "fontSize": "0.75em", "fontWeight": "700"})
        else:
            badge = html.Span("HELD FIRM", style={
                "color": MUTED, "backgroundColor": CARD, "padding": "2px 8px",
                "borderRadius": "4px", "fontSize": "0.75em", "border": f"1px solid {BORDER}"})

        cards.append(html.Div([
            html.Div(style={"display": "flex", "alignItems": "center", "gap": "10px",
                             "marginBottom": "8px"}, children=[
                html.Span(short, style={"color": color, "fontWeight": "700", "fontSize": "1.05em"}),
                badge,
            ]),
            html.Div([
                html.Div("Initial:", style={"color": MUTED, "fontSize": "0.75em"}),
                html.P(initial[:150], style={"color": TEXT, "fontSize": "0.85em", "margin": "0 0 8px"}),
            ]) if initial else html.Div(),
            html.Div([
                html.Div("Final:", style={"color": MUTED, "fontSize": "0.75em"}),
                html.P(final[:150], style={"color": TEXT, "fontSize": "0.85em", "margin": "0 0 8px"}),
            ]) if final else html.Div(),
            html.P(reason, style={"color": GOLD, "fontSize": "0.8em", "fontStyle": "italic",
                                   "margin": "0"}) if reason else html.Div(),
        ], style={**_card_style(), "borderLeft": f"3px solid {color}", "marginBottom": "10px"}))

    return html.Div([
        html.H2("Position Evolution", style={
            "color": TEXT, "fontSize": "1.6em", "fontWeight": "700", "marginBottom": "8px"}),
        html.P("How each mind moved during the deliberation.",
               style={"color": MUTED, "marginBottom": "20px", "fontSize": "0.95em"}),
        html.Div(cards, style={"display": "grid",
                                "gridTemplateColumns": "repeat(auto-fill, minmax(280px, 1fr))",
                                "gap": "12px"}),
    ], style=_section_style())


def _build_topic_clusters(html: Any, analysis: dict) -> Any:
    """Section: Topic clusters identified in the deliberation."""
    clusters = analysis.get("topic_clusters", [])
    if not clusters:
        return html.Div()

    cards: list[Any] = []
    for cluster in clusters:
        theme = cluster.get("theme", "Unknown")
        desc = cluster.get("description", "")
        agents_engaged = cluster.get("engaged_agents", [])
        round_range = cluster.get("round_range", [])

        agent_pills = [html.Span(a.split()[0], style={
            "backgroundColor": _agent_color(a), "color": BG,
            "padding": "2px 8px", "borderRadius": "12px",
            "fontSize": "0.75em", "fontWeight": "600", "marginRight": "4px",
        }) for a in agents_engaged]

        round_text = f"Rounds {round_range[0]}-{round_range[1]}" if len(round_range) == 2 else ""

        cards.append(html.Div([
            html.Div(theme, style={"color": TEXT, "fontWeight": "700", "fontSize": "1.1em",
                                    "marginBottom": "6px"}),
            html.P(desc, style={"color": MUTED, "fontSize": "0.85em", "margin": "0 0 8px"}),
            html.Div(agent_pills, style={"marginBottom": "6px"}),
            html.Span(round_text, style={"color": MUTED, "fontSize": "0.75em"}) if round_text else html.Div(),
        ], style={**_card_style(), "borderTop": f"3px solid {GOLD}"}))

    return html.Div([
        html.H2("Topic Clusters", style={
            "color": TEXT, "fontSize": "1.6em", "fontWeight": "700", "marginBottom": "8px"}),
        html.P("Themes that dominated the discussion.",
               style={"color": MUTED, "marginBottom": "20px", "fontSize": "0.95em"}),
        html.Div(cards, style={"display": "grid",
                                "gridTemplateColumns": "repeat(auto-fill, minmax(260px, 1fr))",
                                "gap": "12px"}),
    ], style=_section_style())


def _build_pipeline_info(html: Any) -> Any:
    """Section: Show the full K-ZERO pipeline with commands."""
    steps = [
        ("1. Simulate", "8 agents debate across N rounds",
         "python -m runner.council_runner --rounds 5",
         "Available: 3 sample transcripts included in this demo"),
        ("2. Analyze", "LLM extracts positions, clashes, insights",
         "python -m runner.analyze transcripts/*.json",
         "Available: analysis data powering this page"),
        ("3. Predict", "Run 1000x, get probability distribution",
         "python -m runner.predict \"Your question\" --runs 100",
         "Classifies questions as CONVERGENT / CONTESTED / OPEN"),
        ("4. Report", "Quarto book with embedded charts",
         "python -m runner.report predictions/*.json --format pdf",
         "Generates HTML, PDF, or DOCX via Quarto"),
        ("5. Artifacts", "NotebookLM: podcast, quiz, study guide",
         "python -m runner.artifacts reports/*.pdf --all",
         "7 learning materials from one report"),
        ("6. Dialectic", "Hegelian thesis/antithesis/synthesis",
         "python -m runner.dialectic \"Your question\" --rounds 5",
         "Agents explicitly revise positions each round"),
        ("7. Share", "Auto-format for Twitter/X",
         "python -m runner.thread transcripts/*.json",
         "280-char tweets with key quotes and clashes"),
    ]

    cards = []
    for title, desc, cmd, note in steps:
        cards.append(html.Div([
            html.Div(title, style={"color": GOLD, "fontWeight": "700", "fontSize": "1.05em",
                                    "marginBottom": "6px"}),
            html.P(desc, style={"color": TEXT, "fontSize": "0.85em", "margin": "0 0 8px"}),
            html.Code(cmd, style={
                "display": "block", "backgroundColor": "#0d1117",
                "color": "#7ee787", "padding": "8px 10px", "borderRadius": "4px",
                "fontSize": "0.78em", "marginBottom": "8px", "overflowX": "auto",
            }),
            html.Div(note, style={"color": MUTED, "fontSize": "0.75em", "fontStyle": "italic"}),
        ], style={**_card_style(), "padding": "16px"}))

    return html.Div([
        html.H2("The K-ZERO Pipeline", style={
            "color": TEXT, "fontSize": "1.6em", "fontWeight": "700", "marginBottom": "8px"}),
        html.P("One question in. Seven artifacts out. Each command runs locally for free.",
               style={"color": MUTED, "marginBottom": "20px", "fontSize": "0.95em"}),
        html.Div(cards, style={"display": "grid",
                                "gridTemplateColumns": "repeat(auto-fill, minmax(280px, 1fr))",
                                "gap": "12px"}),
        html.Div([
            html.P([
                "Get started: ",
                html.Code("pip install the-council", style={"color": "#7ee787"}),
                " or ",
                html.A("clone from GitHub", href="https://github.com/ksk5429/kzero",
                       target="_blank", style={"color": GOLD}),
            ], style={"color": MUTED, "fontSize": "0.9em", "textAlign": "center", "marginTop": "20px"}),
        ]),
    ], style=_section_style())


def _build_footer(html: Any) -> Any:
    """Footer with local run CTA + GitHub link."""
    return html.Div([
        # "Run Locally" banner
        html.Div([
            html.Div([
                html.Div("Want unlimited deliberation?", style={
                    "color": GOLD, "fontWeight": "700", "fontSize": "1.1em",
                    "marginBottom": "8px",
                }),
                html.P(
                    "This demo runs on a free API with rate limits. "
                    "For unlimited sessions with deep multi-step evolution, "
                    "run K-ZERO locally with Ollama (free, no API key needed).",
                    style={"color": MUTED, "fontSize": "0.88em", "margin": "0 0 16px",
                           "lineHeight": "1.5"},
                ),
                html.Pre(
                    "git clone https://github.com/ksk5429/kzero.git && cd kzero\n"
                    "pip install -r requirements.txt\n"
                    "# Install Ollama: https://ollama.com\n"
                    "ollama pull qwen2.5:7b\n"
                    "python -m runner.demiurge          # Interactive god-mode\n"
                    "python -m runner.overnight \"Your question\" --runs 50 --steps 5",
                    style={
                        "backgroundColor": "#0d1117", "color": "#7ee787",
                        "padding": "14px 16px", "borderRadius": "8px",
                        "fontSize": "0.82em", "overflowX": "auto",
                        "border": f"1px solid {BORDER}", "margin": "0",
                    },
                ),
            ], style={
                "backgroundColor": CARD, "padding": "24px",
                "borderRadius": "12px", "border": f"1px solid {GOLD}40",
                "maxWidth": "680px", "margin": "0 auto",
            }),
        ], style={"padding": "40px 20px 20px"}),

        html.Hr(style={"border": "none", "borderTop": f"1px solid {BORDER}",
                        "marginTop": "32px"}),
        html.Div([
            html.P([
                "Powered by ",
                html.Span("K-ZERO", style={"color": GOLD, "fontWeight": "600"}),
                " \u2014 Multi-Agent Philosophical Deliberation System",
            ], style={"margin": "0", "color": MUTED, "fontSize": "0.9em"}),
            html.P([
                html.A(
                    "github.com/ksk5429/kzero",
                    href="https://github.com/ksk5429/kzero",
                    target="_blank",
                    style={"color": GOLD, "textDecoration": "none"},
                ),
                "  \u2014  MIT License  \u2014  Free & Open Source",
            ], style={
                "margin": "10px 0 0", "color": MUTED, "fontSize": "0.85em",
            }),
            html.P(
                "The book is the translation layer between swarm intelligence and individual human understanding.",
                style={
                    "margin": "16px 0 0", "color": MUTED,
                    "fontSize": "0.75em", "fontStyle": "italic", "opacity": "0.6",
                },
            ),
        ], style={"textAlign": "center", "padding": "32px 0 48px"}),
    ], style={"marginTop": SECTION_GAP})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

app = build_app()
server = app.server  # For WSGI deployment (gunicorn, etc.)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    print(f"\n  K-ZERO: http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
