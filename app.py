"""
K-ZERO -- Council of 8
A live chat interface where 8 AI agents debate using Hegelian dialectic.

Run locally:  python app.py
Deploy:       Hugging Face Spaces, Render, Railway
"""

import json
import os
import random
import sys
import threading
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

BG = "#0d1117"
CARD = "#161b22"
BORDER = "#30363d"
TEXT = "#e6edf3"
MUTED = "#8b949e"
GOLD = "#f0c040"
RED = "#f85149"

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

PROJECT_ROOT = Path(__file__).parent

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
COUNCIL_MODEL = os.getenv("COUNCIL_MODEL", "llama-3.1-8b-instant")

# ---------------------------------------------------------------------------
# Shared state for thread communication
# ---------------------------------------------------------------------------

_sim_messages: list[dict[str, Any]] = []
_sim_running: bool = False
_sim_done: bool = False
_sim_stop: bool = False

# ---------------------------------------------------------------------------
# Background thread: multi-step Hegelian dialectic
# ---------------------------------------------------------------------------

GOD_TWISTS = [
    "What if the question itself is wrong? What is the REAL question?",
    "Assume your position is completely wrong. What changes?",
    "If only ONE idea from this debate survives, which should it be?",
    "200 years from now, which side will history vindicate?",
    "What would a child say that none of you have considered?",
]


def _run_council(question: str, n_steps: int = 3) -> None:
    """Run multi-step evolving deliberation. Appends messages to _sim_messages."""
    global _sim_messages, _sim_running, _sim_done, _sim_stop
    _sim_messages = []
    _sim_running = True
    _sim_done = False
    _sim_stop = False

    try:
        from runner.agent import _create_client, _rotate_client, load_agents

        # Set env vars for agent module
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

        # Restore env
        for k, v in original_env.items():
            if v:
                os.environ[k] = v

        agent_names = [n for n in agents if "Kevin" not in n]
        history: list[dict[str, Any]] = []

        def _add(speaker: str, text: str, rnd: int,
                 msg_type: str = "agent", phase: str = "") -> None:
            entry = {
                "speaker": speaker, "text": text,
                "round": rnd, "type": msg_type, "phase": phase,
            }
            history.append(entry)
            _sim_messages.append(entry)

        def _agent_speak(name: str, topic: str, rnd: int,
                         phase: str = "", max_tok: int = 100) -> None:
            if _sim_stop:
                return
            agent = agents[name]
            for attempt in range(4):
                try:
                    text = agent.respond(
                        history, current_topic=topic, max_tokens=max_tok)
                    if text and not text.startswith("["):
                        _add(name, text, rnd, "agent", phase)
                        time.sleep(2)
                        return
                except Exception as e:
                    err = str(e).lower()
                    if ("429" in err or "rate" in err or "quota" in err) and attempt < 3:
                        wait = 5 * (attempt + 1)
                        _sim_messages.append({
                            "speaker": "[K-ZERO]",
                            "text": f"Rate limit hit. Waiting {wait}s...",
                            "round": rnd, "type": "system", "phase": "",
                        })
                        time.sleep(wait)
                        try:
                            agent.client = _rotate_client()
                        except Exception:
                            pass
                        continue
                    else:
                        _add(name, f"[Error: {str(e)[:100]}]", rnd, "system", phase)
                        return
            _add(name, f"[{name.split()[0]} could not respond]", rnd, "system", phase)

        # ==============================================================
        # MULTI-STEP HEGELIAN DIALECTIC
        # ==============================================================

        all_agents = list(agent_names)
        positions: dict[str, str] = {}
        rnd = 0

        for step in range(1, n_steps + 1):
            if _sim_stop:
                _add("[K-ZERO]", "Deliberation stopped.", rnd, "moderator")
                break

            random.shuffle(all_agents)

            # --- Step header ---
            if step == 1:
                _add("[K-ZERO]",
                     f"\u2501\u2501\u2501 THE COUNCIL CONVENES \u2501\u2501\u2501\n"
                     f'Question: "{question}"\n'
                     f"Steps: {n_steps} | Agents: {len(all_agents)}\n"
                     f"THESIS \u2192 ANTITHESIS \u2192 SYNTHESIS \u2192 REVISION",
                     rnd, "moderator")
            else:
                _add("[K-ZERO]",
                     f"\u2501\u2501\u2501 STEP {step}/{n_steps} \u2501\u2501\u2501\n"
                     f"Positions carry forward. The dialectic deepens.",
                     rnd, "moderator")

            # --- THESIS ---
            rnd += 1
            phase = f"S{step} THESIS"
            _add("[K-ZERO]", f"Step {step} \u2014 THESIS: State your position."
                 + (" Has your thinking evolved?" if step > 1 else ""),
                 rnd, "moderator", phase)
            for name in all_agents:
                prev = positions.get(name, "")
                ctx = f' Previous: "{prev[:120]}".' if prev else ""
                _agent_speak(
                    name,
                    f'Question: "{question}".{ctx} State your position in 2 sentences MAX.',
                    rnd, phase)

            # --- ANTITHESIS ---
            rnd += 1
            phase = f"S{step} ANTITHESIS"
            _add("[K-ZERO]",
                 f"Step {step} \u2014 ANTITHESIS: Challenge the WEAKEST argument. Name them.",
                 rnd, "moderator", phase)
            random.shuffle(all_agents)
            for name in all_agents:
                _agent_speak(
                    name,
                    f'Question: "{question}". '
                    f"Name the weakest argument and who said it. 2 sentences MAX.",
                    rnd, phase)

            # --- SYNTHESIS ---
            rnd += 1
            phase = f"S{step} SYNTHESIS"
            _add("[K-ZERO]",
                 f"Step {step} \u2014 SYNTHESIS: What tension exists? What are you NOT seeing?",
                 rnd, "moderator", phase)
            random.shuffle(all_agents)
            for name in all_agents:
                _agent_speak(
                    name,
                    f'Question: "{question}". '
                    f"What tension exists between your view and the best counter? 2 sentences.",
                    rnd, phase)

            # --- GOD twist ---
            rnd += 1
            _add("[GOD]", random.choice(GOD_TWISTS), rnd, "god_mode")

            # --- REVISION ---
            rnd += 1
            phase = f"S{step} REVISION"
            header = (f"Step {step} \u2014 FINAL REVISION: State your ultimate position."
                      if step == n_steps else
                      f"Step {step} \u2014 REVISION: Revised position carries into Step {step + 1}.")
            _add("[K-ZERO]", header, rnd, "moderator", phase)
            random.shuffle(all_agents)
            for name in all_agents:
                prev = positions.get(name, "")
                ctx = f' Previous: "{prev[:120]}".' if prev else ""
                _agent_speak(
                    name,
                    f'Question: "{question}".{ctx} '
                    f"Revised position in 2 sentences. Changed or held firm?",
                    rnd, phase)

            # Carry positions forward
            for msg in _sim_messages:
                if msg.get("phase") == phase and msg["type"] == "agent":
                    positions[msg["speaker"]] = msg["text"][:200]

        # === KEVIN: FINAL SYNTHESIS ===
        kevin = agents.get("Kevin (\uae40\uacbd\uc120)")
        if kevin and not _sim_stop:
            try:
                synthesis = kevin.respond(
                    history,
                    current_topic=(
                        "In 4-5 sentences: Who evolved? Who held firm? "
                        "What emerged that no one held at the start? "
                        "End with ONE unanswered question."),
                    max_tokens=200)
                if synthesis and not synthesis.startswith("["):
                    _add("Kevin (\uae40\uacbd\uc120)", synthesis,
                         rnd + 1, "moderator", "FINAL SYNTHESIS")
            except Exception as e:
                _add("Kevin (\uae40\uacbd\uc120)", f"[Error: {e}]",
                     rnd + 1, "system")

    except Exception as e:
        _sim_messages.append({
            "speaker": "[K-ZERO]",
            "text": f"Fatal error: {e}",
            "round": 0, "type": "system", "phase": "",
        })

    _sim_running = False
    _sim_done = True


# ---------------------------------------------------------------------------
# Dash app
# ---------------------------------------------------------------------------

from dash import Dash, Input, Output, State, dcc, html, no_update

app = Dash(__name__, title="K-ZERO")
app.config.suppress_callback_exceptions = True

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------


def _make_layout() -> html.Div:
    return html.Div([

        # --- Header bar ---
        html.Div([
            html.Span("K", style={"color": GOLD, "fontWeight": "800"}),
            html.Span("-ZERO", style={"color": TEXT, "fontWeight": "800"}),
            html.Span(" \u00b7 Council of 8", style={
                "color": MUTED, "fontWeight": "400", "fontSize": "0.85em",
                "marginLeft": "6px",
            }),
        ], style={
            "padding": "12px 20px",
            "borderBottom": f"1px solid {BORDER}",
            "fontSize": "1.1em",
            "fontFamily": "'Inter', 'Segoe UI', system-ui, sans-serif",
        }),

        # --- Chat area ---
        html.Div(
            id="chat-area",
            children=[
                html.Div("Ask a question to begin.", style={
                    "color": MUTED, "textAlign": "center",
                    "paddingTop": "40vh", "fontSize": "0.95em",
                }),
            ],
            style={
                "height": "calc(100vh - 120px)",
                "overflowY": "auto",
                "padding": "20px",
                "display": "flex",
                "flexDirection": "column",
                "gap": "12px",
            },
        ),

        # --- Input bar (always visible at bottom) ---
        html.Div([
            # Step dropdown
            dcc.Dropdown(
                id="step-dropdown",
                options=[
                    {"label": "1", "value": 1},
                    {"label": "2", "value": 2},
                    {"label": "3", "value": 3},
                    {"label": "5", "value": 5},
                ],
                value=3,
                clearable=False,
                style={
                    "width": "54px",
                    "backgroundColor": BG,
                    "color": TEXT,
                    "border": "none",
                    "fontSize": "0.85em",
                    "flexShrink": "0",
                },
            ),
            # Question input
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
                },
            ),
            # Send button
            html.Button(
                "\u25b6", id="send-btn", n_clicks=0,
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
            # Stop / New Question (plain link, avoids Dash button serialization bug)
            html.A(
                "\u21bb New", href="/",
                style={
                    "color": RED, "fontSize": "0.8em", "fontWeight": "700",
                    "textDecoration": "none", "padding": "8px 10px",
                    "flexShrink": "0", "letterSpacing": "0.03em",
                },
            ),
        ], style={
            "display": "flex",
            "alignItems": "center",
            "gap": "10px",
            "padding": "10px 16px",
            "backgroundColor": CARD,
            "borderTop": f"1px solid {BORDER}",
            "position": "fixed",
            "bottom": "0",
            "left": "0",
            "right": "0",
            "zIndex": "100",
        }),

        # --- Status line ---
        html.Div(id="status-line", style={
            "display": "none",
        }),

        # --- Polling interval ---
        dcc.Interval(id="sim-poll", interval=2000, disabled=True),

        # --- Hidden stores ---
        dcc.Store(id="sim-timestamp", data=0),

    ], style={
        "backgroundColor": BG,
        "minHeight": "100vh",
        "fontFamily": "'Inter', 'Segoe UI', 'Noto Sans KR', system-ui, sans-serif",
        "color": TEXT,
        "margin": "0",
        "paddingBottom": "60px",
    })


app.layout = _make_layout


# ---------------------------------------------------------------------------
# Chat bubble builders
# ---------------------------------------------------------------------------


def _bubble_moderator(text: str) -> html.Div:
    """K-ZERO moderator message: gold left border, full width."""
    return html.Div([
        html.Div("[K-ZERO]", style={
            "color": GOLD, "fontWeight": "700", "fontSize": "0.8em",
            "marginBottom": "4px", "letterSpacing": "0.05em",
        }),
        html.Div(text, style={
            "color": TEXT, "fontSize": "0.9em",
            "whiteSpace": "pre-wrap", "lineHeight": "1.5",
        }),
    ], style={
        "borderLeft": f"3px solid {GOLD}",
        "padding": "12px 16px",
        "backgroundColor": CARD,
        "borderRadius": "0 8px 8px 0",
    })


def _bubble_god(text: str) -> html.Div:
    """GOD mode message: red border, centered, dramatic."""
    return html.Div([
        html.Div("\u26a1 GOD MODE", style={
            "color": RED, "fontWeight": "800", "fontSize": "0.75em",
            "letterSpacing": "0.1em", "marginBottom": "4px",
            "textAlign": "center",
        }),
        html.Div(text, style={
            "color": TEXT, "fontSize": "0.9em",
            "textAlign": "center", "fontStyle": "italic",
        }),
    ], style={
        "border": f"1px solid {RED}",
        "padding": "12px 20px",
        "borderRadius": "8px",
        "backgroundColor": "#1a0a0a",
        "maxWidth": "600px",
        "margin": "8px auto",
    })


def _bubble_system(text: str) -> html.Div:
    """System / error message: muted, small."""
    return html.Div(text, style={
        "color": MUTED, "fontSize": "0.8em",
        "fontStyle": "italic", "padding": "4px 16px",
    })


def _bubble_agent(name: str, text: str, phase: str) -> html.Div:
    """Agent chat bubble with colored avatar dot and phase badge."""
    color = AGENT_COLORS.get(name, MUTED)
    role = AGENT_ROLES.get(name, "")

    # Parse phase for badge display
    badge_text = ""
    if phase:
        parts = phase.split()
        if len(parts) >= 2:
            badge_text = parts[-1]  # e.g. "THESIS", "ANTITHESIS"
        else:
            badge_text = phase

    badge_color = {
        "THESIS": "#2196f3",
        "ANTITHESIS": "#f44336",
        "SYNTHESIS": "#9c27b0",
        "REVISION": "#4caf50",
    }.get(badge_text.upper(), MUTED)

    # Extract step number from phase like "S1 THESIS"
    step_label = ""
    if phase and phase[0] == "S" and len(phase) > 1 and phase[1].isdigit():
        step_label = phase.split()[0]  # "S1"

    return html.Div([
        # Header: dot + name + role + phase badge
        html.Div([
            # Avatar dot
            html.Span("\u25cf ", style={
                "color": color, "fontSize": "0.9em",
            }),
            # Name
            html.Span(name, style={
                "color": color, "fontWeight": "700", "fontSize": "0.85em",
            }),
            # Role
            html.Span(f" \u00b7 {role}", style={
                "color": MUTED, "fontSize": "0.75em",
            }) if role else None,
            # Phase badge
            html.Span(f"  {badge_text}", style={
                "color": badge_color, "fontSize": "0.7em",
                "fontWeight": "700", "letterSpacing": "0.05em",
                "marginLeft": "auto",
            }) if badge_text else None,
            # Step label
            html.Span(f" {step_label}", style={
                "color": MUTED, "fontSize": "0.65em",
            }) if step_label else None,
        ], style={
            "display": "flex", "alignItems": "center",
            "gap": "2px", "marginBottom": "4px",
        }),
        # Message body
        html.Div(text, style={
            "color": TEXT, "fontSize": "0.9em",
            "lineHeight": "1.5",
        }),
    ], style={
        "borderLeft": f"3px solid {color}",
        "padding": "10px 14px",
        "backgroundColor": CARD,
        "borderRadius": "0 8px 8px 0",
    })


def _build_chat(messages: list[dict]) -> list:
    """Convert message list to chat bubble components."""
    bubbles = []
    for msg in messages:
        msg_type = msg.get("type", "agent")
        speaker = msg.get("speaker", "")
        text = msg.get("text", "")
        phase = msg.get("phase", "")

        if msg_type == "moderator" or speaker == "[K-ZERO]":
            bubbles.append(_bubble_moderator(text))
        elif msg_type == "god_mode" or speaker == "[GOD]":
            bubbles.append(_bubble_god(text))
        elif msg_type == "system":
            bubbles.append(_bubble_system(f"{speaker}: {text}" if speaker else text))
        else:
            bubbles.append(_bubble_agent(speaker, text, phase))

    return bubbles


# ---------------------------------------------------------------------------
# Callback 1: Start simulation
# ---------------------------------------------------------------------------

@app.callback(
    Output("status-line", "children"),
    Output("sim-timestamp", "data"),
    Output("sim-poll", "disabled"),
    Input("send-btn", "n_clicks"),
    State("question-input", "value"),
    State("step-dropdown", "value"),
    prevent_initial_call=True,
)
def start_simulation(n_clicks, question, n_steps):
    if not n_clicks or not question or not question.strip():
        return no_update, no_update, no_update

    if _sim_running:
        return "Simulation already running.", no_update, no_update

    if not LLM_API_KEY:
        return "No API key. Set LLM_API_KEY.", no_update, True

    n_steps = n_steps or 3
    t = threading.Thread(
        target=_run_council,
        args=(question.strip(), n_steps),
        daemon=True,
    )
    t.start()

    return "Council convened...", time.time(), False


# ---------------------------------------------------------------------------
# Callback 2: Poll for messages
# ---------------------------------------------------------------------------

@app.callback(
    Output("chat-area", "children"),
    Output("sim-poll", "disabled", allow_duplicate=True),
    Output("status-line", "children", allow_duplicate=True),
    Input("sim-poll", "n_intervals"),
    prevent_initial_call=True,
)
def poll_messages(n_intervals):
    messages = list(_sim_messages)

    if not messages and not _sim_done:
        return [html.Div(
            "\u25cf Convening the council...",
            style={"color": GOLD, "textAlign": "center", "paddingTop": "20vh"},
        )], False, "Waiting for first response..."

    bubbles = _build_chat(messages)

    # Typing indicator
    if _sim_running:
        # Find last speaker to show "X is thinking..."
        thinking_name = "An agent"
        for msg in reversed(messages):
            if msg.get("type") == "agent":
                thinking_name = msg["speaker"].split()[0]
                break
        bubbles.append(html.Div(
            f"\u25cf {thinking_name} is thinking...",
            style={
                "color": MUTED, "fontSize": "0.8em",
                "fontStyle": "italic", "padding": "8px 16px",
                "animation": "pulse 1.5s infinite",
            },
        ))

    # Auto-scroll anchor
    bubbles.append(html.Div(id="scroll-anchor"))

    if _sim_done:
        status = f"Done. {len(messages)} messages."
        return bubbles, True, status

    status = f"{len(messages)} messages..."
    return bubbles, False, status


# ---------------------------------------------------------------------------
# Inject auto-scroll JS + global CSS
# ---------------------------------------------------------------------------

app.index_string = """<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
    <style>
        body { margin: 0; background: #0d1117; }
        * { box-sizing: border-box; }
        /* Dropdown text color fix */
        .Select-value-label, .Select-option { color: #e6edf3 !important; }
        .Select-menu-outer { background: #161b22 !important; border-color: #30363d !important; }
        .Select-control { background: #0d1117 !important; border-color: #30363d !important; }
        /* Pulse animation for typing indicator */
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #0d1117; }
        ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
    </style>
</head>
<body>
    {%app_entry%}
    <footer>
        {%config%}
        {%scripts%}
        {%renderer%}
    </footer>
    <script>
        // Auto-scroll to bottom when new messages arrive
        const observer = new MutationObserver(function() {
            const anchor = document.getElementById('scroll-anchor');
            if (anchor) anchor.scrollIntoView({behavior: 'smooth'});
        });
        const chatCheck = setInterval(function() {
            const chat = document.getElementById('chat-area');
            if (chat) {
                observer.observe(chat, {childList: true, subtree: true});
                clearInterval(chatCheck);
            }
        }, 500);
    </script>
</body>
</html>"""

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860, debug=False)
