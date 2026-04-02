"""
K-ZERO -- Council of 8 Web App
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

from runner.visualize import create_app  # noqa: E402 -- reuse existing Dash builder

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BG = "#1a1a2e"
CARD = "#16213e"
ACCENT = "#0f3460"
TEXT = "#e0e0e0"
MUTED = "#8a8a9a"
GOLD = "#f39c12"

PROJECT_ROOT = Path(__file__).parent
TRANSCRIPTS_DIR = PROJECT_ROOT / "transcripts"
DIALECTICS_DIR = PROJECT_ROOT / "dialectics"
PREDICTIONS_DIR = PROJECT_ROOT / "predictions"


# ---------------------------------------------------------------------------
# Scan available artifacts
# ---------------------------------------------------------------------------

def _scan_analyses() -> list[dict[str, Any]]:
    """Return metadata dicts for every *_analysis.json found."""
    results = []
    for p in sorted(TRANSCRIPTS_DIR.glob("*_analysis.json")):
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            meta = data.get("metadata", {})
            results.append({
                "path": str(p),
                "filename": p.name,
                "title": meta.get("scenario_title", p.stem),
                "model": meta.get("model", "unknown"),
                "rounds": meta.get("total_rounds", 0),
                "messages": meta.get("total_messages", 0),
                "agents": meta.get("agent_names", []),
            })
        except Exception:
            continue
    return results


def _count_artifacts() -> dict[str, int]:
    """Count files in each artifact directory."""
    counts: dict[str, int] = {}
    for name, d in [("analyses", TRANSCRIPTS_DIR), ("dialectics", DIALECTICS_DIR),
                    ("predictions", PREDICTIONS_DIR)]:
        if d.exists():
            counts[name] = len([f for f in d.iterdir() if f.suffix == ".json"])
        else:
            counts[name] = 0
    counts["transcripts"] = len(list(TRANSCRIPTS_DIR.glob("*.json"))) if TRANSCRIPTS_DIR.exists() else 0
    return counts


# ---------------------------------------------------------------------------
# Build the enhanced Dash app
# ---------------------------------------------------------------------------

def build_app() -> Any:
    """Build the full K-ZERO app with landing page + analysis dashboard."""
    try:
        from dash import Dash, Input, Output, State, dcc, html, no_update
    except ImportError as exc:
        raise ImportError("Dash is required: pip install dash plotly") from exc

    analyses = _scan_analyses()
    counts = _count_artifacts()

    if not analyses:
        # Fallback: no analyses at all -- show a static info page
        app = Dash(__name__, title="K-ZERO -- Council of 8")
        app.layout = html.Div([
            html.H1("K-ZERO", style={"color": TEXT, "textAlign": "center", "marginTop": "80px"}),
            html.P("No analysis files found. Run a simulation first.",
                   style={"color": MUTED, "textAlign": "center"}),
            html.Pre(
                "python -m runner.council_runner --rounds 5\n"
                "python -m runner.analyze transcripts/<latest>.json",
                style={"color": GOLD, "textAlign": "center", "fontSize": "1em"},
            ),
        ], style={"backgroundColor": BG, "minHeight": "100vh",
                   "fontFamily": "'Segoe UI', 'Noto Sans KR', sans-serif"})
        return app

    # Build dropdown options
    dropdown_options = [
        {"label": f"{a['title']}  ({a['rounds']}R / {a['messages']}M)", "value": a["path"]}
        for a in analyses
    ]
    default_path = analyses[-1]["path"]  # latest

    # Pre-load the default analysis dashboard
    default_dash_app = create_app(default_path)
    default_layout = default_dash_app.layout

    # Collect all unique agents across all analyses
    all_agents = sorted({name for a in analyses for name in a["agents"]})

    # System modes
    modes = []
    if counts["analyses"] > 0:
        modes.append("Deliberation Analysis")
    if counts["dialectics"] > 0:
        modes.append("Dialectic Evolution")
    if counts["predictions"] > 0:
        modes.append("Prediction Aggregation")

    # ---------------------------------------------------------------
    # App shell
    # ---------------------------------------------------------------
    app = Dash(
        __name__,
        title="K-ZERO -- Council of 8",
        suppress_callback_exceptions=True,
    )

    # Stat card helper
    def _stat_card(label: str, value: str, color: str = GOLD) -> html.Div:
        return html.Div([
            html.Div(value, style={
                "fontSize": "2.2em", "fontWeight": "bold", "color": color,
                "lineHeight": "1",
            }),
            html.Div(label, style={
                "fontSize": "0.85em", "color": MUTED, "marginTop": "4px",
            }),
        ], style={
            "backgroundColor": CARD, "padding": "20px 24px",
            "borderRadius": "8px", "textAlign": "center",
            "minWidth": "120px", "flex": "1",
        })

    # Agent pill helper
    def _agent_pill(name: str) -> html.Span:
        return html.Span(name, style={
            "backgroundColor": ACCENT, "color": TEXT,
            "padding": "4px 12px", "borderRadius": "16px",
            "fontSize": "0.85em", "display": "inline-block",
            "margin": "3px",
        })

    # Analysis card helper
    def _analysis_card(a: dict) -> html.Div:
        return html.Div([
            html.Div(a["title"], style={
                "fontSize": "1.15em", "fontWeight": "bold", "color": TEXT,
                "marginBottom": "6px",
            }),
            html.Div([
                html.Span(f"{a['rounds']} rounds", style={"color": GOLD, "marginRight": "16px"}),
                html.Span(f"{a['messages']} messages", style={"color": MUTED, "marginRight": "16px"}),
                html.Span(f"{len(a['agents'])} agents", style={"color": MUTED}),
            ], style={"fontSize": "0.9em", "marginBottom": "8px"}),
            html.Div(
                [_agent_pill(n) for n in a["agents"]],
                style={"lineHeight": "2"},
            ),
        ], style={
            "backgroundColor": CARD, "padding": "16px 20px",
            "borderRadius": "8px", "borderLeft": f"4px solid {GOLD}",
            "marginBottom": "12px",
        })

    # ---------------------------------------------------------------
    # Landing page content
    # ---------------------------------------------------------------
    landing_page = html.Div([
        # Hero
        html.Div([
            html.H1([
                html.Span("K", style={"color": GOLD}),
                html.Span("-ZERO", style={"color": TEXT}),
            ], style={
                "fontSize": "3.5em", "fontWeight": "800", "margin": "0",
                "letterSpacing": "0.05em",
            }),
            html.P(
                "Council of 8 -- Multi-Agent Philosophical Deliberation System",
                style={"color": MUTED, "fontSize": "1.2em", "margin": "8px 0 4px"},
            ),
            html.P(
                "Eight distinct minds. One question. Emergent insight.",
                style={"color": GOLD, "fontSize": "1em", "fontStyle": "italic",
                       "margin": "0 0 24px"},
            ),
        ], style={"textAlign": "center", "padding": "48px 32px 24px"}),

        # Stats row
        html.Div([
            _stat_card("Agents", str(len(all_agents))),
            _stat_card("Analyses", str(counts["analyses"])),
            _stat_card("Dialectics", str(counts["dialectics"]), "#3498db"),
            _stat_card("Predictions", str(counts["predictions"]), "#2ecc71"),
            _stat_card("Modes", str(len(modes)), "#9b59b6"),
        ], style={
            "display": "flex", "gap": "16px", "justifyContent": "center",
            "padding": "0 32px 24px", "flexWrap": "wrap",
        }),

        # Modes bar
        html.Div([
            html.Span(m, style={
                "backgroundColor": ACCENT, "color": TEXT,
                "padding": "6px 16px", "borderRadius": "20px",
                "fontSize": "0.9em", "margin": "4px",
            }) for m in modes
        ], style={"textAlign": "center", "marginBottom": "24px"}),

        # Roster
        html.Div([
            html.H3("The Council", style={"color": TEXT, "marginBottom": "12px"}),
            html.Div(
                [_agent_pill(name) for name in all_agents],
                style={"lineHeight": "2.2"},
            ),
        ], style={
            "backgroundColor": CARD, "padding": "20px 28px",
            "borderRadius": "8px", "margin": "0 32px 24px",
        }),

        # Available analyses
        html.Div([
            html.H3("Available Deliberations", style={"color": TEXT, "marginBottom": "16px"}),
            html.Div([_analysis_card(a) for a in analyses]),
        ], style={"padding": "0 32px 16px"}),

        # Selector
        html.Div([
            html.H3("Launch Dashboard", style={"color": TEXT, "marginBottom": "12px"}),
            html.Div([
                dcc.Dropdown(
                    id="analysis-selector",
                    options=dropdown_options,
                    value=default_path,
                    clearable=False,
                    style={
                        "backgroundColor": CARD, "color": "#000",
                        "flex": "1", "minWidth": "300px",
                    },
                ),
                html.Button(
                    "View Analysis",
                    id="launch-btn",
                    n_clicks=0,
                    style={
                        "backgroundColor": GOLD, "color": "#1a1a2e",
                        "border": "none", "padding": "10px 28px",
                        "borderRadius": "6px", "fontWeight": "bold",
                        "fontSize": "1em", "cursor": "pointer",
                        "marginLeft": "12px",
                    },
                ),
            ], style={"display": "flex", "alignItems": "center", "gap": "8px",
                       "flexWrap": "wrap"}),
        ], style={
            "backgroundColor": CARD, "padding": "20px 28px",
            "borderRadius": "8px", "margin": "0 32px 32px",
        }),
    ])

    # ---------------------------------------------------------------
    # Full layout: landing + dashboard container
    # ---------------------------------------------------------------
    app.layout = html.Div([
        dcc.Store(id="current-view", data="landing"),
        dcc.Store(id="current-analysis-path", data=default_path),

        # Navigation bar (always visible)
        html.Div([
            html.Span([
                html.Span("K", style={"color": GOLD, "fontWeight": "800"}),
                html.Span("-ZERO", style={"color": TEXT, "fontWeight": "800"}),
            ], style={"fontSize": "1.3em", "cursor": "pointer"}, id="nav-home"),
            html.Span(
                "Council of 8",
                style={"color": MUTED, "fontSize": "0.9em", "marginLeft": "16px"},
            ),
        ], style={
            "backgroundColor": CARD, "padding": "12px 24px",
            "borderBottom": f"1px solid {ACCENT}",
            "display": "flex", "alignItems": "center",
        }),

        # Landing page
        html.Div(id="landing-container", children=landing_page),

        # Dashboard container (hidden initially)
        html.Div(id="dashboard-container", children=default_layout,
                 style={"display": "none"}),
    ], style={
        "backgroundColor": BG, "minHeight": "100vh",
        "fontFamily": "'Segoe UI', 'Noto Sans KR', sans-serif",
    })

    # ---------------------------------------------------------------
    # Callbacks
    # ---------------------------------------------------------------

    # Register the existing Dash app's callbacks onto our app
    # by re-using create_app internals: we embed the dashboard layout
    # and rely on suppress_callback_exceptions

    @app.callback(
        [Output("landing-container", "style"),
         Output("dashboard-container", "style"),
         Output("dashboard-container", "children"),
         Output("current-view", "data")],
        [Input("launch-btn", "n_clicks"),
         Input("nav-home", "n_clicks")],
        [State("analysis-selector", "value"),
         State("current-view", "data")],
        prevent_initial_call=True,
    )
    def toggle_view(
        launch_clicks: int | None,
        home_clicks: int | None,
        selected_path: str,
        current_view: str,
    ) -> tuple:
        from dash import callback_context as ctx

        triggered = ctx.triggered_id if ctx.triggered else None

        if triggered == "nav-home":
            return (
                {"display": "block"},
                {"display": "none"},
                no_update,
                "landing",
            )

        if triggered == "launch-btn" and selected_path:
            # Build a fresh dashboard for the selected analysis
            inner_app = create_app(selected_path)
            return (
                {"display": "none"},
                {"display": "block"},
                inner_app.layout,
                "dashboard",
            )

        return no_update, no_update, no_update, no_update

    # Forward all callbacks from the default dashboard app
    # so the embedded visualization is interactive
    for cb in default_dash_app.callback_map.values():
        inputs = cb.get("inputs", [])
        outputs = cb.get("output", "")
        state = cb.get("state", [])
        # The callbacks are already registered via create_app's internal
        # decorator pattern -- we need to re-register them on our app.
        # Since Dash uses suppress_callback_exceptions, the callbacks from
        # create_app won't auto-transfer. We re-create the app with the
        # same analysis and register callbacks manually.

    # Instead of the complex callback forwarding above, we use a simpler
    # approach: embed the create_app result's callbacks by calling create_app
    # and copying its callback_map.
    _register_dashboard_callbacks(app, default_path)

    return app


def _register_dashboard_callbacks(app: Any, analysis_path: str) -> None:
    """Register the visualization callbacks from create_app onto our app shell."""
    from dash import Input, Output, State, callback_context, dcc, html, no_update

    # Instead of trying to copy callbacks (which is fragile), we re-implement
    # the tab-switching and agent-detail callbacks inline, calling into
    # visualize's helper functions.
    from runner.visualize import (
        _load_analysis,
        _build_network_figure,
        _build_heatmap_figure,
        _build_timeline_figure,
        _build_chat_log,
        AGENT_COLORS,
        SHORT_NAMES,
        BACKGROUND_COLOR,
        CARD_COLOR,
        ACCENT_COLOR,
        TEXT_COLOR,
        MUTED_TEXT,
    )

    analysis = _load_analysis(analysis_path)
    meta = analysis.get("metadata", {})
    labels = analysis["agreement_matrix"]["labels"]
    matrix = analysis["agreement_matrix"]["matrix"]
    transcript_data = analysis.get("_transcript", [])

    network_fig = _build_network_figure(analysis)
    heatmap_fig = _build_heatmap_figure(analysis)
    timeline_fig = _build_timeline_figure(analysis)

    @app.callback(
        Output("tab-content", "children"),
        Input("main-tabs", "value"),
    )
    def render_tab(tab: str) -> Any:
        if tab == "network":
            chat_entries = _build_chat_log(transcript_data)
            return html.Div(style={"display": "flex", "gap": "16px"}, children=[
                html.Div(style={"flex": "3"}, children=[
                    dcc.Graph(
                        id="network-graph", figure=network_fig,
                        style={"height": "600px"},
                        config={"displayModeBar": True, "scrollZoom": True},
                    ),
                ]),
                html.Div(style={
                    "flex": "2", "backgroundColor": CARD_COLOR,
                    "borderRadius": "8px", "padding": "12px",
                    "overflowY": "auto", "maxHeight": "600px",
                    "border": f"1px solid {ACCENT_COLOR}",
                }, children=[
                    html.H4("Deliberation Log", style={
                        "color": TEXT_COLOR, "marginTop": "0", "marginBottom": "12px",
                        "borderBottom": f"1px solid {ACCENT_COLOR}", "paddingBottom": "8px",
                    }),
                    html.Div(chat_entries),
                ]),
            ])
        if tab == "heatmap":
            return dcc.Graph(
                id="heatmap-graph", figure=heatmap_fig,
                style={"height": "600px"}, config={"displayModeBar": True},
            )
        if tab == "timeline":
            return dcc.Graph(
                id="timeline-graph", figure=timeline_fig,
                style={"height": "600px"}, config={"displayModeBar": True},
            )
        if tab == "insights":
            return html.Div(_build_insight_cards(analysis),
                            style={"maxWidth": "800px", "margin": "0 auto"})
        return html.P("Select a tab.", style={"color": MUTED_TEXT})

    @app.callback(
        Output("agent-detail", "children"),
        [Input("network-graph", "clickData"),
         Input("heatmap-graph", "clickData")],
        prevent_initial_call=True,
    )
    def show_agent_detail(net_click: Any, heat_click: Any) -> Any:
        triggered = callback_context.triggered
        if not triggered:
            return []
        click_data = net_click or heat_click
        if not click_data:
            return []
        points = click_data.get("points", [])
        if not points:
            return []
        text = points[0].get("text", "") or points[0].get("x", "") or ""
        # Try to match an agent name
        agent_name = None
        for name in labels:
            if name in str(text) or SHORT_NAMES.get(name, "") in str(text):
                agent_name = name
                break
        if not agent_name:
            return []
        return _build_agent_detail(analysis, agent_name, labels, matrix)


def _build_insight_cards(analysis: dict) -> list:
    """Build insight card elements from analysis data."""
    from dash import html
    from runner.visualize import (
        AGENT_COLORS, SHORT_NAMES, CARD_COLOR, TEXT_COLOR, MUTED_TEXT,
    )
    cards: list = []

    for ins in analysis.get("emergent_insights", []):
        contributors = ", ".join(ins.get("contributing_agents", []))
        cards.append(html.Div([
            html.H4("Emergent Insight", style={"color": "#f39c12", "marginBottom": "4px"}),
            html.P(ins.get("insight", ""), style={"color": TEXT_COLOR}),
            html.P(f"Contributors: {contributors}",
                   style={"color": MUTED_TEXT, "fontSize": "0.85em"}),
            html.P(ins.get("synthesis_description", ""),
                   style={"color": MUTED_TEXT, "fontSize": "0.85em", "fontStyle": "italic"}),
        ], style={
            "backgroundColor": CARD_COLOR, "padding": "16px", "borderRadius": "8px",
            "marginBottom": "12px", "borderLeft": "4px solid #f39c12",
        }))

    for cluster in analysis.get("topic_clusters", []):
        agents_str = ", ".join(cluster.get("agents_engaged", []))
        rr = cluster.get("round_range", [])
        round_str = f"Rounds {rr[0]}\u2013{rr[1]}" if len(rr) == 2 else ""
        cards.append(html.Div([
            html.H4(cluster.get("theme", "Topic"), style={"color": "#3498db", "marginBottom": "4px"}),
            html.P(f"Agents: {agents_str}", style={"color": TEXT_COLOR, "fontSize": "0.9em"}),
            html.P(round_str, style={"color": MUTED_TEXT, "fontSize": "0.85em"}),
        ], style={
            "backgroundColor": CARD_COLOR, "padding": "16px", "borderRadius": "8px",
            "marginBottom": "12px", "borderLeft": "4px solid #3498db",
        }))

    for agent_name, qinfo in analysis.get("key_quotes", {}).items():
        color = AGENT_COLORS.get(agent_name, "#aaaaaa")
        cards.append(html.Div([
            html.H4(SHORT_NAMES.get(agent_name, agent_name),
                     style={"color": color, "marginBottom": "4px"}),
            html.Blockquote(f"\u201c{qinfo.get('quote', '')}\u201d", style={
                "color": TEXT_COLOR, "fontStyle": "italic",
                "borderLeft": f"3px solid {color}", "paddingLeft": "12px", "margin": "8px 0",
            }),
            html.P(f"Round {qinfo.get('round', '?')} \u2014 {qinfo.get('why_impactful', '')}",
                   style={"color": MUTED_TEXT, "fontSize": "0.85em"}),
        ], style={
            "backgroundColor": CARD_COLOR, "padding": "16px", "borderRadius": "8px",
            "marginBottom": "12px",
        }))

    if not cards:
        cards.append(html.P("No insights data available.",
                            style={"color": MUTED_TEXT, "textAlign": "center", "padding": "40px"}))
    return cards


def _build_agent_detail(
    analysis: dict, agent_name: str, labels: list, matrix: list,
) -> list:
    """Build agent detail panel elements."""
    from dash import html
    from runner.visualize import (
        AGENT_COLORS, SHORT_NAMES, TEXT_COLOR, MUTED_TEXT,
    )
    color = AGENT_COLORS.get(agent_name, "#aaaaaa")
    elements: list = [
        html.H3(agent_name, style={"color": color, "marginBottom": "8px"}),
    ]
    tracking = analysis.get("position_tracking", {}).get(agent_name, {})
    if tracking:
        shifted = tracking.get("shifted", False)
        badge_color = "#e74c3c" if shifted else "#2ecc71"
        badge_text = "SHIFTED" if shifted else "STABLE"
        elements.extend([
            html.Div([
                html.Span(badge_text, style={
                    "backgroundColor": badge_color, "color": "#fff",
                    "padding": "2px 8px", "borderRadius": "4px",
                    "fontSize": "0.8em", "marginRight": "8px",
                }),
                html.Span(tracking.get("shift_description", ""),
                           style={"color": MUTED_TEXT, "fontSize": "0.85em"}),
            ], style={"marginBottom": "8px"}),
            html.P([
                html.B("Initial: ", style={"color": MUTED_TEXT}),
                html.Span(tracking.get("initial_position", ""), style={"color": TEXT_COLOR}),
            ], style={"fontSize": "0.9em", "margin": "4px 0"}),
            html.P([
                html.B("Final: ", style={"color": MUTED_TEXT}),
                html.Span(tracking.get("final_position", ""), style={"color": TEXT_COLOR}),
            ], style={"fontSize": "0.9em", "margin": "4px 0"}),
        ])
    qinfo = analysis.get("key_quotes", {}).get(agent_name, {})
    if qinfo.get("quote"):
        elements.append(html.Blockquote(
            f"\u201c{qinfo['quote']}\u201d", style={
                "color": TEXT_COLOR, "fontStyle": "italic",
                "borderLeft": f"3px solid {color}", "paddingLeft": "12px", "margin": "12px 0",
            },
        ))
    if agent_name in labels:
        idx = labels.index(agent_name)
        scores = [(labels[j], matrix[idx][j]) for j in range(len(labels)) if j != idx]
        if scores:
            ally = max(scores, key=lambda x: x[1])
            rival = min(scores, key=lambda x: x[1])
            elements.extend([
                html.P([
                    html.B("Top ally: ", style={"color": "#2ecc71"}),
                    html.Span(f"{SHORT_NAMES.get(ally[0], ally[0])} ({ally[1]:+.2f})",
                              style={"color": TEXT_COLOR}),
                ], style={"fontSize": "0.9em", "margin": "4px 0"}),
                html.P([
                    html.B("Top rival: ", style={"color": "#e74c3c"}),
                    html.Span(f"{SHORT_NAMES.get(rival[0], rival[0])} ({rival[1]:+.2f})",
                              style={"color": TEXT_COLOR}),
                ], style={"fontSize": "0.9em", "margin": "4px 0"}),
            ])
    return elements


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

app = build_app()
server = app.server  # For WSGI deployment (gunicorn, etc.)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    print(f"\n  K-ZERO Dashboard: http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
