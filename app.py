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
            results.append({
                "path": str(p),
                "filename": p.name,
                "slug": p.stem.replace("_analysis", ""),
                "title": meta.get("scenario_title", p.stem),
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
            _build_hero(html, meta, prediction),
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


def _build_hero(html: Any, meta: dict, prediction: dict | None) -> Any:
    """Section 1: Full-bleed hero with title, question, and one-line verdict."""
    title = meta.get("scenario_title", "Untitled Deliberation")

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
    """Section 4: Agreement heatmap + clash/alliance callouts."""
    am = analysis.get("agreement_matrix", {})
    labels = am.get("labels", [])
    matrix = am.get("matrix", [])

    if not labels or not matrix:
        return html.Div()

    # Short labels for display
    short = [n.split(" ")[0] if "(" not in n else n.split("(")[0].strip()
             for n in labels]

    # Build heatmap
    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=short,
        y=short,
        colorscale=[
            [0.0, ACCENT_RED],
            [0.5, BG],
            [1.0, ACCENT_GREEN],
        ],
        zmin=-1,
        zmax=1,
        text=[[f"{v:.1f}" for v in row] for row in matrix],
        texttemplate="%{text}",
        textfont={"size": 13, "color": TEXT},
        hovertemplate="%{y} vs %{x}: %{z:.2f}<extra></extra>",
        showscale=False,
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 80, "r": 20, "t": 20, "b": 80},
        height=380,
        xaxis={
            "tickfont": {"color": MUTED, "size": 12},
            "side": "bottom",
        },
        yaxis={
            "tickfont": {"color": MUTED, "size": 12},
            "autorange": "reversed",
        },
    )

    # Find biggest clash and strongest alliance
    min_score, max_score = 0.0, 0.0
    clash_pair, alliance_pair = ("", ""), ("", "")

    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            v = matrix[i][j]
            if v < min_score:
                min_score = v
                clash_pair = (labels[i], labels[j])
            if v > max_score:
                max_score = v
                alliance_pair = (labels[i], labels[j])

    # Get evidence from raw_pairwise
    raw = am.get("raw_pairwise", {})

    def _find_evidence(a: str, b: str) -> str:
        for key in [f"{a} -> {b}", f"{b} -> {a}"]:
            if key in raw:
                return raw[key].get("evidence", "")
        return ""

    callouts: list[Any] = []
    if min_score < 0:
        ev = _find_evidence(clash_pair[0], clash_pair[1])
        callouts.append(html.Div([
            html.Span("Biggest Clash", style={
                "color": ACCENT_RED, "fontWeight": "700",
                "fontSize": "0.9em", "textTransform": "uppercase",
                "letterSpacing": "0.05em",
            }),
            html.Div(
                f"{clash_pair[0].split(' ')[0]} vs "
                f"{clash_pair[1].split(' ')[0]}  ({min_score:+.1f})",
                style={"color": TEXT, "fontWeight": "600", "marginTop": "4px"},
            ),
            html.P(
                f"\u201c{ev}\u201d" if ev else "",
                style={
                    "color": MUTED, "fontSize": "0.85em",
                    "fontStyle": "italic", "marginTop": "8px",
                },
            ) if ev else html.Div(),
        ], style=_card_style({"flex": "1", "borderTop": f"3px solid {ACCENT_RED}"})))

    if max_score > 0:
        ev = _find_evidence(alliance_pair[0], alliance_pair[1])
        callouts.append(html.Div([
            html.Span("Strongest Alliance", style={
                "color": ACCENT_GREEN, "fontWeight": "700",
                "fontSize": "0.9em", "textTransform": "uppercase",
                "letterSpacing": "0.05em",
            }),
            html.Div(
                f"{alliance_pair[0].split(' ')[0]} + "
                f"{alliance_pair[1].split(' ')[0]}  ({max_score:+.1f})",
                style={"color": TEXT, "fontWeight": "600", "marginTop": "4px"},
            ),
            html.P(
                f"\u201c{ev}\u201d" if ev else "",
                style={
                    "color": MUTED, "fontSize": "0.85em",
                    "fontStyle": "italic", "marginTop": "8px",
                },
            ) if ev else html.Div(),
        ], style=_card_style({"flex": "1", "borderTop": f"3px solid {ACCENT_GREEN}"})))

    return html.Div([
        html.H2("The Clash Map", style={
            "color": TEXT, "fontSize": "1.6em",
            "fontWeight": "700", "marginBottom": "8px",
        }),
        html.P(
            "Agreement and tension between council members. "
            "Green means alignment, red means conflict.",
            style={"color": MUTED, "marginBottom": "24px", "fontSize": "0.95em"},
        ),

        # Heatmap
        html.Div([
            dcc.Graph(
                figure=fig,
                config={"displayModeBar": False},
            ),
        ], style={
            **_card_style(),
            "padding": "16px",
            "marginBottom": "20px",
        }),

        # Clash / Alliance callouts
        html.Div(
            callouts,
            style={
                "display": "flex",
                "gap": "16px",
                "flexWrap": "wrap",
            },
        ),
    ], style=_section_style())


def _build_conversation(html: Any, transcript: list[dict]) -> Any:
    """Section 5: Chat-style transcript."""
    if not transcript:
        return html.Div()

    messages: list[Any] = []
    for msg in transcript:
        speaker = msg.get("speaker", "Unknown")
        text = msg.get("text", "")
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
    """Section 7: Footer."""
    return html.Div([
        html.Hr(style={"border": "none", "borderTop": f"1px solid {BORDER}"}),
        html.Div([
            html.P([
                "Powered by ",
                html.Span("K-ZERO", style={"color": GOLD, "fontWeight": "600"}),
            ], style={"margin": "0", "color": MUTED, "fontSize": "0.85em"}),
            html.P(
                "Ask your own question:  python -m runner.demiurge",
                style={
                    "margin": "6px 0 0", "color": MUTED,
                    "fontSize": "0.8em", "fontFamily": "monospace",
                },
            ),
        ], style={"textAlign": "center", "padding": "32px 0"}),
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
