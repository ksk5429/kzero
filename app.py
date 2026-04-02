"""
K-ZERO -- Council of 8 Web App
A magazine-style single-page deliberation viewer.

Run locally: python app.py
Deploy: Hugging Face Spaces, Render, Railway
"""

import json
import os
import sys
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
# Build the app
# ---------------------------------------------------------------------------


def build_app() -> Any:
    try:
        import plotly.graph_objects as go
        from dash import Dash, Input, Output, dcc, html
    except ImportError as exc:
        raise ImportError("Dash is required: pip install dash plotly") from exc

    analyses = _scan_analyses()

    app = Dash(
        __name__,
        title="K-ZERO",
        suppress_callback_exceptions=True,
    )

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

        # Page content
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
            _build_who_said_what(html, analysis),
            _build_clash_map(html, dcc, go, analysis),
            _build_conversation(html, transcript),
            _build_emergent_insights(html, analysis),
            _build_footer(html),
        ], style=PAGE_STYLE)

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


def _build_who_said_what(html: Any, analysis: dict) -> Any:
    """Section 3: Pull-quote cards for each agent, alternating layout."""
    key_quotes = analysis.get("key_quotes", {})
    if not key_quotes:
        return html.Div()

    cards: list[Any] = []
    names = list(key_quotes.keys())

    for i, (agent, qinfo) in enumerate(key_quotes.items()):
        color = _agent_color(agent)
        role = _agent_role(agent)
        quote = qinfo.get("quote", "")
        why = qinfo.get("why_it_matters", qinfo.get("why_impactful", ""))
        round_num = qinfo.get("round", "?")
        align_right = (i % 2 == 1)

        card = html.Div([
            # Agent name + role
            html.Div([
                html.Span(agent, style={
                    "color": color,
                    "fontWeight": "700",
                    "fontSize": "1.1em",
                }),
                html.Span(f"  \u00b7  {role}", style={
                    "color": MUTED,
                    "fontSize": "0.85em",
                }),
                html.Span(f"  \u00b7  Round {round_num}", style={
                    "color": MUTED,
                    "fontSize": "0.8em",
                }),
            ]),

            # The quote (pull-quote style)
            html.Blockquote(
                f"\u201c{quote}\u201d",
                style={
                    "fontSize": "1.15em",
                    "lineHeight": "1.6",
                    "color": TEXT,
                    "margin": "16px 0",
                    "padding": "0 0 0 20px",
                    "borderLeft": f"3px solid {color}",
                    "fontStyle": "italic",
                },
            ),

            # Why it matters
            html.P(why, style={
                "color": MUTED,
                "fontSize": "0.88em",
                "margin": "0",
            }) if why else html.Div(),
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


def _build_footer(html: Any) -> Any:
    """Section 7: Footer with GitHub link."""
    return html.Div([
        html.Hr(style={"border": "none", "borderTop": f"1px solid {BORDER}"}),
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
                "Ask your own question:  python -m runner.demiurge",
                style={
                    "margin": "8px 0 0", "color": MUTED,
                    "fontSize": "0.8em", "fontFamily": "monospace",
                },
            ),
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
