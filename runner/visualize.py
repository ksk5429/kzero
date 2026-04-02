"""Council of 8 — Interactive Dash visualization for deliberation analysis results.

Usage:
    python -m runner.visualize analysis_result.json [--port 8050] [--export output.html]

Programmatic:
    from runner.visualize import create_app
    app = create_app("analysis_result.json")
    app.run(port=8050)
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import plotly.graph_objects as go

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BACKGROUND_COLOR = "#1a1a2e"
CARD_COLOR = "#16213e"
ACCENT_COLOR = "#0f3460"
TEXT_COLOR = "#e0e0e0"
MUTED_TEXT = "#8a8a9a"

AGENT_COLORS: dict[str, str] = {
    "Elon Musk": "#e74c3c",
    "Richard Feynman": "#3498db",
    "Kobe Bryant": "#f39c12",
    "Steve Jobs": "#ecf0f1",
    "Jean-Paul Sartre": "#9b59b6",
    "George Carlin": "#2ecc71",
    "Bryan Johnson": "#2980b9",
    "Kevin (\uae40\uacbd\uc120)": "#bdc3c7",
}

AGENT_GROUPS: dict[str, list[str]] = {
    "Innovators": ["Elon Musk", "Kobe Bryant", "Steve Jobs"],
    "Thinkers": ["Richard Feynman", "Jean-Paul Sartre", "Bryan Johnson"],
    "Wildcards": ["George Carlin", "Kevin (\uae40\uacbd\uc120)"],
}

SHORT_NAMES: dict[str, str] = {
    "Elon Musk": "Musk",
    "Richard Feynman": "Feynman",
    "Kobe Bryant": "Kobe",
    "Steve Jobs": "Jobs",
    "Jean-Paul Sartre": "Sartre",
    "George Carlin": "Carlin",
    "Bryan Johnson": "Johnson",
    "Kevin (\uae40\uacbd\uc120)": "Kevin",
}

PLOTLY_TEMPLATE = "plotly_dark"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_json(path: str | Path) -> dict[str, Any]:
    """Load and validate a JSON file, returning its parsed contents."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_analysis(path: str | Path) -> dict[str, Any]:
    """Load the analysis_result.json and its companion transcript."""
    analysis = _load_json(path)

    required_keys = {"metadata", "agreement_matrix"}
    missing = required_keys - set(analysis.keys())
    if missing:
        raise ValueError(f"analysis_result.json missing required keys: {missing}")

    transcript: list[dict[str, Any]] = []
    transcript_path = analysis.get("metadata", {}).get("transcript_path")
    if transcript_path:
        tp = Path(transcript_path)
        if not tp.is_absolute():
            tp = Path(path).parent / tp
        if tp.exists():
            transcript = _load_json(tp)
            if isinstance(transcript, dict):
                transcript = transcript.get("messages", [])
        else:
            logger.warning("Transcript file not found: %s", tp)

    analysis["_transcript"] = transcript
    return analysis


# ---------------------------------------------------------------------------
# Spring layout (Fruchterman-Reingold)
# ---------------------------------------------------------------------------

def _spring_layout(
    n_nodes: int,
    edges: list[tuple[int, int, float]],
    iterations: int = 100,
    seed: int = 42,
) -> list[tuple[float, float]]:
    """Compute 2D positions for *n_nodes* using simple Fruchterman-Reingold forces.

    Parameters
    ----------
    n_nodes : int
        Number of nodes.
    edges : list of (i, j, weight)
        Edge list with absolute weight used as spring strength.
    iterations : int
        Number of simulation steps.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    list of (x, y) tuples — one per node.
    """
    rng = np.random.default_rng(seed)
    area = 10.0
    k = math.sqrt(area / max(n_nodes, 1))
    pos = rng.uniform(-2, 2, size=(n_nodes, 2))

    for step in range(iterations):
        temp = max(0.01, 2.0 * (1.0 - step / iterations))
        disp = np.zeros_like(pos)

        # Repulsive forces between all pairs
        for i in range(n_nodes):
            diff = pos[i] - pos
            dist = np.linalg.norm(diff, axis=1)
            dist = np.where(dist < 0.01, 0.01, dist)
            rep = (k * k / dist)[:, None] * (diff / dist[:, None])
            rep[i] = 0.0
            disp[i] += rep.sum(axis=0)

        # Attractive forces along edges
        for i, j, w in edges:
            diff = pos[j] - pos[i]
            dist = max(np.linalg.norm(diff), 0.01)
            strength = w * dist / k
            force = strength * diff / dist
            disp[i] += force
            disp[j] -= force

        # Apply displacement clamped by temperature
        norms = np.linalg.norm(disp, axis=1, keepdims=True)
        norms = np.where(norms < 0.01, 0.01, norms)
        pos += (disp / norms) * np.minimum(norms, temp)

    # Center around origin
    pos -= pos.mean(axis=0)
    return [(float(pos[i, 0]), float(pos[i, 1])) for i in range(n_nodes)]


# ---------------------------------------------------------------------------
# Figure builders
# ---------------------------------------------------------------------------

def _build_network_figure(
    analysis: dict[str, Any],
) -> go.Figure:
    """Force-directed network graph of agent interactions."""
    am = analysis["agreement_matrix"]
    labels: list[str] = am["labels"]
    matrix: list[list[float]] = am["matrix"]
    n = len(labels)
    key_quotes = analysis.get("key_quotes", {})

    # Build edge list
    edges: list[tuple[int, int, float]] = []
    for i in range(n):
        for j in range(i + 1, n):
            w = matrix[i][j]
            if abs(w) > 0.05:
                edges.append((i, j, abs(w)))

    positions = _spring_layout(n, edges)
    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]

    fig = go.Figure()

    # Draw edges
    for i, j, w in edges:
        score = matrix[i][j]
        if score > 0.2:
            edge_color = "rgba(46, 204, 113, 0.5)"
        elif score < -0.2:
            edge_color = "rgba(231, 76, 60, 0.5)"
        else:
            edge_color = "rgba(150, 150, 150, 0.3)"
        width = max(1.0, abs(score) * 6)
        fig.add_trace(go.Scatter(
            x=[xs[i], xs[j], None],
            y=[ys[i], ys[j], None],
            mode="lines",
            line=dict(width=width, color=edge_color),
            hoverinfo="skip",
            showlegend=False,
        ))

    # Determine group for each agent
    def _group_for(name: str) -> str:
        for group, members in AGENT_GROUPS.items():
            if name in members:
                return group
        return "Other"

    # Draw nodes
    hover_texts: list[str] = []
    colors: list[str] = []
    for idx, name in enumerate(labels):
        color = AGENT_COLORS.get(name, "#ffffff")
        colors.append(color)
        group = _group_for(name)
        quote_info = key_quotes.get(name, {})
        quote_text = quote_info.get("quote", "—")
        if len(quote_text) > 120:
            quote_text = quote_text[:117] + "..."
        hover_texts.append(
            f"<b>{name}</b><br>"
            f"Group: {group}<br>"
            f"<i>\"{quote_text}\"</i>"
        )

    fig.add_trace(go.Scatter(
        x=xs,
        y=ys,
        mode="markers+text",
        marker=dict(size=28, color=colors, line=dict(width=2, color="#ffffff")),
        text=[SHORT_NAMES.get(n, n) for n in labels],
        textposition="top center",
        textfont=dict(color=TEXT_COLOR, size=11),
        hovertext=hover_texts,
        hoverinfo="text",
        showlegend=False,
    ))

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor=BACKGROUND_COLOR,
        plot_bgcolor=BACKGROUND_COLOR,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=20, r=20, t=40, b=20),
        title=dict(text="Agent Interaction Network", font=dict(color=TEXT_COLOR)),
        hoverlabel=dict(bgcolor=CARD_COLOR, font_size=12),
    )
    return fig


def _build_heatmap_figure(analysis: dict[str, Any]) -> go.Figure:
    """8x8 agreement/conflict heatmap."""
    am = analysis["agreement_matrix"]
    labels: list[str] = am["labels"]
    matrix: list[list[float]] = am["matrix"]
    short = [SHORT_NAMES.get(n, n) for n in labels]

    # Build annotation text
    annotations: list[list[str]] = []
    for row in matrix:
        annotations.append([f"{v:+.2f}" if abs(v) > 0.01 else "0" for v in row])

    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=short,
        y=short,
        colorscale="RdYlGn",
        zmin=-1,
        zmax=1,
        text=annotations,
        texttemplate="%{text}",
        textfont=dict(size=11),
        hovertemplate=(
            "<b>%{y}</b> vs <b>%{x}</b><br>"
            "Score: %{z:.2f}<extra></extra>"
        ),
        colorbar=dict(
            title="Agreement",
            tickvals=[-1, -0.5, 0, 0.5, 1],
            ticktext=["Disagree", "", "Neutral", "", "Agree"],
        ),
    ))

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor=BACKGROUND_COLOR,
        plot_bgcolor=BACKGROUND_COLOR,
        title=dict(text="Agreement / Conflict Matrix", font=dict(color=TEXT_COLOR)),
        xaxis=dict(tickfont=dict(color=TEXT_COLOR)),
        yaxis=dict(tickfont=dict(color=TEXT_COLOR), autorange="reversed"),
        margin=dict(l=80, r=40, t=60, b=80),
        hoverlabel=dict(bgcolor=CARD_COLOR, font_size=12),
    )
    return fig


def _build_timeline_figure(analysis: dict[str, Any]) -> go.Figure:
    """Timeline scatter — X=round, Y=agent, size=message length."""
    transcript: list[dict[str, Any]] = analysis.get("_transcript", [])
    labels = analysis["agreement_matrix"]["labels"]

    if not transcript:
        fig = go.Figure()
        fig.add_annotation(
            text="No transcript data available",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=18, color=MUTED_TEXT),
        )
        fig.update_layout(
            template=PLOTLY_TEMPLATE,
            paper_bgcolor=BACKGROUND_COLOR,
            plot_bgcolor=BACKGROUND_COLOR,
        )
        return fig

    fig = go.Figure()

    # Separate agent messages from system messages
    agent_msgs: dict[str, list[dict[str, Any]]] = {}
    system_msgs: list[dict[str, Any]] = []

    for msg in transcript:
        speaker = msg.get("agent") or msg.get("speaker") or msg.get("role", "")
        rnd = msg.get("round", 1)
        content = msg.get("content") or msg.get("message") or ""

        if speaker in ("moderator", "god_mode", "system"):
            system_msgs.append({"round": rnd, "content": content, "role": speaker})
        else:
            agent_msgs.setdefault(speaker, []).append({
                "round": rnd,
                "content": content,
            })

    # Plot agent messages
    for agent_name, msgs in agent_msgs.items():
        rounds = [m["round"] for m in msgs]
        contents = [m["content"] for m in msgs]
        sizes = [max(8, min(40, len(c) / 20)) for c in contents]
        hover = [
            f"<b>{agent_name}</b> (Round {r})<br>"
            f"{c[:300]}{'...' if len(c) > 300 else ''}"
            for r, c in zip(rounds, contents)
        ]
        color = AGENT_COLORS.get(agent_name, "#aaaaaa")
        fig.add_trace(go.Scatter(
            x=rounds,
            y=[agent_name] * len(rounds),
            mode="markers",
            marker=dict(size=sizes, color=color, opacity=0.85,
                        line=dict(width=1, color="#ffffff")),
            hovertext=hover,
            hoverinfo="text",
            name=SHORT_NAMES.get(agent_name, agent_name),
        ))

    # Plot system messages as diamond markers
    if system_msgs:
        fig.add_trace(go.Scatter(
            x=[m["round"] for m in system_msgs],
            y=[m["role"] for m in system_msgs],
            mode="markers",
            marker=dict(
                size=14, color="#ff6b6b", symbol="diamond",
                line=dict(width=1, color="#ffffff"),
            ),
            hovertext=[
                f"<b>{m['role']}</b> (Round {m['round']})<br>"
                f"{m['content'][:300]}{'...' if len(m['content']) > 300 else ''}"
                for m in system_msgs
            ],
            hoverinfo="text",
            name="System",
        ))

    total_rounds = analysis.get("metadata", {}).get("total_rounds", 3)
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor=BACKGROUND_COLOR,
        plot_bgcolor=BACKGROUND_COLOR,
        title=dict(text="Deliberation Timeline", font=dict(color=TEXT_COLOR)),
        xaxis=dict(
            title="Round", dtick=1, range=[0.5, total_rounds + 0.5],
            tickfont=dict(color=TEXT_COLOR),
        ),
        yaxis=dict(tickfont=dict(color=TEXT_COLOR, size=10)),
        margin=dict(l=140, r=40, t=60, b=60),
        hoverlabel=dict(bgcolor=CARD_COLOR, font_size=11),
        legend=dict(font=dict(color=TEXT_COLOR)),
    )
    return fig


# ---------------------------------------------------------------------------
# Chat log builder (for network tab side panel)
# ---------------------------------------------------------------------------

def _build_chat_log(transcript: list[dict]) -> list:
    """Build a styled chat log from transcript entries for the network side panel."""
    # Lazy import — only needed inside Dash
    try:
        from dash import html
    except ImportError:
        return []

    entries = []
    for entry in transcript:
        speaker = entry.get("speaker", "")
        text = entry.get("text", "")
        rnd = entry.get("round", 0)
        msg_type = entry.get("type", "agent")

        # Truncate long messages
        display_text = text[:300] + "..." if len(text) > 300 else text

        if msg_type == "god_mode" or "GOD" in speaker or "K-ZERO" in speaker:
            # God-mode / K-ZERO injection
            entries.append(html.Div(style={
                "marginBottom": "10px",
                "padding": "8px 10px",
                "backgroundColor": "rgba(231, 76, 60, 0.15)",
                "borderLeft": "3px solid #e74c3c",
                "borderRadius": "4px",
            }, children=[
                html.Span(f"R{rnd} ", style={"color": MUTED_TEXT, "fontSize": "11px"}),
                html.Span("K-ZERO ", style={"color": "#e74c3c", "fontWeight": "bold", "fontSize": "12px"}),
                html.Br(),
                html.Span(display_text, style={"color": "#e0e0e0", "fontSize": "12px", "fontStyle": "italic"}),
            ]))
        elif msg_type == "moderator":
            # Moderator
            entries.append(html.Div(style={
                "marginBottom": "10px",
                "padding": "8px 10px",
                "backgroundColor": "rgba(189, 195, 199, 0.1)",
                "borderLeft": "3px solid #bdc3c7",
                "borderRadius": "4px",
            }, children=[
                html.Span(f"R{rnd} ", style={"color": MUTED_TEXT, "fontSize": "11px"}),
                html.Span("MODERATOR ", style={"color": "#bdc3c7", "fontWeight": "bold", "fontSize": "12px"}),
                html.Br(),
                html.Span(display_text, style={"color": "#e0e0e0", "fontSize": "12px"}),
            ]))
        else:
            # Agent message
            color = AGENT_COLORS.get(speaker, "#e0e0e0")
            short = speaker.split()[0] if speaker else "?"
            entries.append(html.Div(style={
                "marginBottom": "10px",
                "padding": "8px 10px",
                "borderLeft": f"3px solid {color}",
                "borderRadius": "4px",
            }, children=[
                html.Span(f"R{rnd} ", style={"color": MUTED_TEXT, "fontSize": "11px"}),
                html.Span(f"{short} ", style={"color": color, "fontWeight": "bold", "fontSize": "12px"}),
                html.Br(),
                html.Span(display_text, style={"color": "#e0e0e0", "fontSize": "12px"}),
            ]))

    return entries


# ---------------------------------------------------------------------------
# Dash app factory
# ---------------------------------------------------------------------------

def create_app(analysis_path: str | Path) -> Any:
    """Create and return a Dash app for the given analysis result.

    Parameters
    ----------
    analysis_path : str or Path
        Path to analysis_result.json.

    Returns
    -------
    dash.Dash
        The configured Dash application (call ``app.run()`` to serve).
    """
    try:
        from dash import Dash, Input, Output, callback_context, dcc, html
    except ImportError as exc:
        raise ImportError(
            "Dash is required: pip install dash plotly"
        ) from exc

    analysis = _load_analysis(analysis_path)
    meta = analysis.get("metadata", {})
    labels = analysis["agreement_matrix"]["labels"]
    matrix = analysis["agreement_matrix"]["matrix"]

    # Transcript data for chat log panel
    transcript_data = analysis.get("_transcript", [])

    # Pre-build figures
    network_fig = _build_network_figure(analysis)
    heatmap_fig = _build_heatmap_figure(analysis)
    timeline_fig = _build_timeline_figure(analysis)

    # ----- Helper: build insight cards -----
    def _insight_cards() -> list:
        cards: list = []

        # Emergent insights
        for ins in analysis.get("emergent_insights", []):
            contributors = ", ".join(ins.get("contributing_agents", []))
            cards.append(html.Div([
                html.H4(
                    "Emergent Insight",
                    style={"color": "#f39c12", "marginBottom": "4px"},
                ),
                html.P(ins.get("insight", ""), style={"color": TEXT_COLOR}),
                html.P(
                    f"Contributors: {contributors}",
                    style={"color": MUTED_TEXT, "fontSize": "0.85em"},
                ),
                html.P(
                    ins.get("synthesis_description", ""),
                    style={"color": MUTED_TEXT, "fontSize": "0.85em", "fontStyle": "italic"},
                ),
            ], style={
                "backgroundColor": CARD_COLOR,
                "padding": "16px",
                "borderRadius": "8px",
                "marginBottom": "12px",
                "borderLeft": "4px solid #f39c12",
            }))

        # Topic clusters
        for cluster in analysis.get("topic_clusters", []):
            agents_str = ", ".join(cluster.get("agents_engaged", []))
            rr = cluster.get("round_range", [])
            round_str = f"Rounds {rr[0]}\u2013{rr[1]}" if len(rr) == 2 else ""
            cards.append(html.Div([
                html.H4(
                    cluster.get("theme", "Topic"),
                    style={"color": "#3498db", "marginBottom": "4px"},
                ),
                html.P(
                    f"Agents: {agents_str}",
                    style={"color": TEXT_COLOR, "fontSize": "0.9em"},
                ),
                html.P(
                    round_str,
                    style={"color": MUTED_TEXT, "fontSize": "0.85em"},
                ),
            ], style={
                "backgroundColor": CARD_COLOR,
                "padding": "16px",
                "borderRadius": "8px",
                "marginBottom": "12px",
                "borderLeft": "4px solid #3498db",
            }))

        # Key quotes
        for agent_name, qinfo in analysis.get("key_quotes", {}).items():
            color = AGENT_COLORS.get(agent_name, "#aaaaaa")
            cards.append(html.Div([
                html.H4(
                    SHORT_NAMES.get(agent_name, agent_name),
                    style={"color": color, "marginBottom": "4px"},
                ),
                html.Blockquote(
                    f"\u201c{qinfo.get('quote', '')}\u201d",
                    style={
                        "color": TEXT_COLOR, "fontStyle": "italic",
                        "borderLeft": f"3px solid {color}",
                        "paddingLeft": "12px", "margin": "8px 0",
                    },
                ),
                html.P(
                    f"Round {qinfo.get('round', '?')} \u2014 {qinfo.get('why_impactful', '')}",
                    style={"color": MUTED_TEXT, "fontSize": "0.85em"},
                ),
            ], style={
                "backgroundColor": CARD_COLOR,
                "padding": "16px",
                "borderRadius": "8px",
                "marginBottom": "12px",
            }))

        if not cards:
            cards.append(html.P(
                "No insights data available.",
                style={"color": MUTED_TEXT, "textAlign": "center", "padding": "40px"},
            ))

        return cards

    # ----- Helper: agent detail panel content -----
    def _agent_detail(agent_name: str) -> list:
        color = AGENT_COLORS.get(agent_name, "#aaaaaa")
        elements: list = [
            html.H3(agent_name, style={"color": color, "marginBottom": "8px"}),
        ]

        # Position tracking
        tracking = analysis.get("position_tracking", {}).get(agent_name, {})
        if tracking:
            shifted = tracking.get("shifted", False)
            badge_color = "#e74c3c" if shifted else "#2ecc71"
            badge_text = "SHIFTED" if shifted else "STABLE"
            elements.extend([
                html.Div([
                    html.Span(
                        badge_text,
                        style={
                            "backgroundColor": badge_color, "color": "#fff",
                            "padding": "2px 8px", "borderRadius": "4px",
                            "fontSize": "0.8em", "marginRight": "8px",
                        },
                    ),
                    html.Span(
                        tracking.get("shift_description", ""),
                        style={"color": MUTED_TEXT, "fontSize": "0.85em"},
                    ),
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

        # Key quote
        qinfo = analysis.get("key_quotes", {}).get(agent_name, {})
        if qinfo.get("quote"):
            elements.append(html.Blockquote(
                f"\u201c{qinfo['quote']}\u201d",
                style={
                    "color": TEXT_COLOR, "fontStyle": "italic",
                    "borderLeft": f"3px solid {color}",
                    "paddingLeft": "12px", "margin": "12px 0",
                },
            ))

        # Top ally / rival from agreement matrix
        if agent_name in labels:
            idx = labels.index(agent_name)
            scores = [(labels[j], matrix[idx][j]) for j in range(len(labels)) if j != idx]
            if scores:
                ally = max(scores, key=lambda x: x[1])
                rival = min(scores, key=lambda x: x[1])
                elements.extend([
                    html.P([
                        html.B("Top ally: ", style={"color": "#2ecc71"}),
                        html.Span(
                            f"{SHORT_NAMES.get(ally[0], ally[0])} ({ally[1]:+.2f})",
                            style={"color": TEXT_COLOR},
                        ),
                    ], style={"fontSize": "0.9em", "margin": "4px 0"}),
                    html.P([
                        html.B("Top rival: ", style={"color": "#e74c3c"}),
                        html.Span(
                            f"{SHORT_NAMES.get(rival[0], rival[0])} ({rival[1]:+.2f})",
                            style={"color": TEXT_COLOR},
                        ),
                    ], style={"fontSize": "0.9em", "margin": "4px 0"}),
                ])

        return elements

    # ===================================================================
    # Dash layout
    # ===================================================================

    app = Dash(
        __name__,
        title="Council of 8 — Deliberation Analysis",
        suppress_callback_exceptions=True,
    )

    tab_style = {
        "backgroundColor": BACKGROUND_COLOR,
        "color": MUTED_TEXT,
        "border": "none",
        "padding": "12px 24px",
        "fontWeight": "bold",
    }
    tab_selected_style = {
        **tab_style,
        "color": TEXT_COLOR,
        "borderBottom": "2px solid #f39c12",
    }

    app.layout = html.Div([
        # ---- Header ----
        html.Div([
            html.H1(
                "Council of 8 \u2014 Deliberation Analysis",
                style={"margin": "0", "color": TEXT_COLOR, "fontSize": "1.8em"},
            ),
            html.P(
                meta.get("scenario_title", ""),
                style={"color": "#f39c12", "fontSize": "1.1em", "margin": "4px 0"},
            ),
            html.Div([
                html.Span(
                    f"Rounds: {meta.get('total_rounds', '?')}",
                    style={"marginRight": "24px"},
                ),
                html.Span(
                    f"Messages: {meta.get('total_messages', '?')}",
                    style={"marginRight": "24px"},
                ),
                html.Span(f"Model: {meta.get('model', '?')}"),
            ], style={"color": MUTED_TEXT, "fontSize": "0.9em"}),
        ], style={
            "padding": "24px 32px 16px",
            "backgroundColor": CARD_COLOR,
            "borderBottom": f"1px solid {ACCENT_COLOR}",
        }),

        # ---- Tabs ----
        dcc.Tabs(id="main-tabs", value="network", children=[
            dcc.Tab(label="Network", value="network",
                    style=tab_style, selected_style=tab_selected_style),
            dcc.Tab(label="Conflict Heatmap", value="heatmap",
                    style=tab_style, selected_style=tab_selected_style),
            dcc.Tab(label="Timeline", value="timeline",
                    style=tab_style, selected_style=tab_selected_style),
            dcc.Tab(label="Insights", value="insights",
                    style=tab_style, selected_style=tab_selected_style),
        ], style={"backgroundColor": BACKGROUND_COLOR}),

        # ---- Tab content ----
        html.Div(id="tab-content", style={"padding": "16px 24px"}),

        # ---- Agent detail panel ----
        html.Div(id="agent-detail", style={
            "padding": "16px 24px",
            "backgroundColor": CARD_COLOR,
            "borderTop": f"1px solid {ACCENT_COLOR}",
            "minHeight": "60px",
        }),

        # Hidden store for selected agent
        dcc.Store(id="selected-agent", data=None),
    ], style={
        "backgroundColor": BACKGROUND_COLOR,
        "minHeight": "100vh",
        "fontFamily": "'Segoe UI', 'Noto Sans KR', sans-serif",
    })

    # ===================================================================
    # Callbacks
    # ===================================================================

    @app.callback(
        Output("tab-content", "children"),
        Input("main-tabs", "value"),
    )
    def render_tab(tab: str) -> Any:
        if tab == "network":
            # Two-column layout: graph left, chat log right
            chat_entries = _build_chat_log(transcript_data)
            return html.Div(style={"display": "flex", "gap": "16px"}, children=[
                # Left: Network graph
                html.Div(style={"flex": "3"}, children=[
                    dcc.Graph(
                        id="network-graph",
                        figure=network_fig,
                        style={"height": "600px"},
                        config={"displayModeBar": True, "scrollZoom": True},
                    ),
                ]),
                # Right: Chat history panel
                html.Div(style={
                    "flex": "2",
                    "backgroundColor": CARD_COLOR,
                    "borderRadius": "8px",
                    "padding": "12px",
                    "overflowY": "auto",
                    "maxHeight": "600px",
                    "border": f"1px solid {ACCENT_COLOR}",
                }, children=[
                    html.H4("Deliberation Log",
                             style={"color": TEXT_COLOR, "marginTop": "0",
                                    "marginBottom": "12px",
                                    "borderBottom": f"1px solid {ACCENT_COLOR}",
                                    "paddingBottom": "8px"}),
                    html.Div(chat_entries),
                ]),
            ])
        if tab == "heatmap":
            return dcc.Graph(
                id="heatmap-graph",
                figure=heatmap_fig,
                style={"height": "600px"},
                config={"displayModeBar": True},
            )
        if tab == "timeline":
            return dcc.Graph(
                id="timeline-graph",
                figure=timeline_fig,
                style={"height": "600px"},
                config={"displayModeBar": True},
            )
        if tab == "insights":
            return html.Div(
                _insight_cards(),
                style={
                    "maxWidth": "800px",
                    "margin": "0 auto",
                    "padding": "16px 0",
                },
            )
        return html.P("Unknown tab", style={"color": MUTED_TEXT})

    @app.callback(
        Output("agent-detail", "children"),
        Input("selected-agent", "data"),
    )
    def render_detail(agent_name: str | None) -> Any:
        if not agent_name or agent_name not in labels:
            return html.P(
                "Click an agent node or heatmap cell to view details.",
                style={"color": MUTED_TEXT, "fontStyle": "italic"},
            )
        return _agent_detail(agent_name)

    @app.callback(
        Output("selected-agent", "data"),
        Input("main-tabs", "value"),
        prevent_initial_call=True,
    )
    def _reset_on_tab_change(_tab: str) -> None:
        """Allow click-based selection; reset is intentionally mild."""
        return None

    # Client-side callback for network click -> store
    app.clientside_callback(
        """
        function(clickData) {
            if (!clickData || !clickData.points || clickData.points.length === 0) {
                return window.dash_clientside.no_update;
            }
            var pt = clickData.points[0];
            if (pt.text) { return pt.text; }
            return window.dash_clientside.no_update;
        }
        """,
        Output("selected-agent", "data", allow_duplicate=True),
        Input("network-graph", "clickData"),
        prevent_initial_call=True,
    )

    # Client-side callback for heatmap click -> store
    app.clientside_callback(
        """
        function(clickData) {
            if (!clickData || !clickData.points || clickData.points.length === 0) {
                return window.dash_clientside.no_update;
            }
            var pt = clickData.points[0];
            if (pt.y) { return pt.y; }
            return window.dash_clientside.no_update;
        }
        """,
        Output("selected-agent", "data", allow_duplicate=True),
        Input("heatmap-graph", "clickData"),
        prevent_initial_call=True,
    )

    return app


# ---------------------------------------------------------------------------
# Static HTML export
# ---------------------------------------------------------------------------

def export_static_html(analysis_path: str | Path, output_path: str | Path) -> Path:
    """Generate a self-contained static HTML report (no running server needed).

    Parameters
    ----------
    analysis_path : str or Path
        Path to analysis_result.json.
    output_path : str or Path
        Destination .html file path.

    Returns
    -------
    Path
        The written output file.
    """
    analysis = _load_analysis(analysis_path)
    meta = analysis.get("metadata", {})

    network_fig = _build_network_figure(analysis)
    heatmap_fig = _build_heatmap_figure(analysis)
    timeline_fig = _build_timeline_figure(analysis)

    # Build insights as plain HTML
    insight_html_parts: list[str] = []
    for ins in analysis.get("emergent_insights", []):
        contributors = ", ".join(ins.get("contributing_agents", []))
        insight_html_parts.append(
            f'<div style="background:{CARD_COLOR};padding:16px;border-radius:8px;'
            f'margin-bottom:12px;border-left:4px solid #f39c12">'
            f'<h4 style="color:#f39c12;margin:0 0 4px">Emergent Insight</h4>'
            f'<p style="color:{TEXT_COLOR}">{ins.get("insight", "")}</p>'
            f'<p style="color:{MUTED_TEXT};font-size:0.85em">Contributors: {contributors}</p>'
            f'</div>'
        )
    for agent_name, qinfo in analysis.get("key_quotes", {}).items():
        color = AGENT_COLORS.get(agent_name, "#aaa")
        insight_html_parts.append(
            f'<div style="background:{CARD_COLOR};padding:16px;border-radius:8px;'
            f'margin-bottom:12px">'
            f'<h4 style="color:{color};margin:0 0 4px">'
            f'{SHORT_NAMES.get(agent_name, agent_name)}</h4>'
            f'<blockquote style="color:{TEXT_COLOR};font-style:italic;'
            f'border-left:3px solid {color};padding-left:12px;margin:8px 0">'
            f'&ldquo;{qinfo.get("quote", "")}&rdquo;</blockquote>'
            f'<p style="color:{MUTED_TEXT};font-size:0.85em">'
            f'Round {qinfo.get("round", "?")} &mdash; {qinfo.get("why_impactful", "")}</p>'
            f'</div>'
        )
    insights_block = "\n".join(insight_html_parts) if insight_html_parts else (
        f'<p style="color:{MUTED_TEXT};text-align:center;padding:40px">No insights data.</p>'
    )

    network_div = network_fig.to_html(full_html=False, include_plotlyjs=False)
    heatmap_div = heatmap_fig.to_html(full_html=False, include_plotlyjs=False)
    timeline_div = timeline_fig.to_html(full_html=False, include_plotlyjs=False)

    out = Path(output_path)
    out.write_text(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Council of 8 &mdash; {meta.get('scenario_title', 'Analysis')}</title>
<script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
<style>
  body {{
    background: {BACKGROUND_COLOR};
    color: {TEXT_COLOR};
    font-family: 'Segoe UI', 'Noto Sans KR', sans-serif;
    margin: 0; padding: 0;
  }}
  .header {{
    background: {CARD_COLOR};
    padding: 24px 32px 16px;
    border-bottom: 1px solid {ACCENT_COLOR};
  }}
  .header h1 {{ margin: 0; font-size: 1.8em; }}
  .header .subtitle {{ color: #f39c12; font-size: 1.1em; margin: 4px 0; }}
  .header .stats {{ color: {MUTED_TEXT}; font-size: 0.9em; }}
  .section {{ padding: 24px 32px; }}
  .section h2 {{ color: {TEXT_COLOR}; border-bottom: 1px solid {ACCENT_COLOR}; padding-bottom: 8px; }}
  .insights {{ max-width: 800px; }}
</style>
</head>
<body>
<div class="header">
  <h1>Council of 8 &mdash; Deliberation Analysis</h1>
  <p class="subtitle">{meta.get('scenario_title', '')}</p>
  <p class="stats">
    Rounds: {meta.get('total_rounds', '?')} &nbsp;&bull;&nbsp;
    Messages: {meta.get('total_messages', '?')} &nbsp;&bull;&nbsp;
    Model: {meta.get('model', '?')}
  </p>
</div>
<div class="section">
  <h2>Agent Interaction Network</h2>
  {network_div}
</div>
<div class="section">
  <h2>Agreement / Conflict Matrix</h2>
  {heatmap_div}
</div>
<div class="section">
  <h2>Deliberation Timeline</h2>
  {timeline_div}
</div>
<div class="section">
  <h2>Insights &amp; Key Quotes</h2>
  <div class="insights">{insights_block}</div>
</div>
</body>
</html>""", encoding="utf-8")

    logger.info("Static HTML exported to %s", out)
    return out


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point: ``python -m runner.visualize``."""
    parser = argparse.ArgumentParser(
        description="Council of 8 — Deliberation Visualization",
    )
    parser.add_argument(
        "analysis_path",
        help="Path to analysis_result.json",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8050,
        help="Port for the Dash dev server (default: 8050)",
    )
    parser.add_argument(
        "--export",
        metavar="OUTPUT.html",
        help="Export a static HTML report instead of running the server",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run Dash in debug mode",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(message)s",
    )

    analysis_file = Path(args.analysis_path)
    if not analysis_file.exists():
        logger.error("File not found: %s", analysis_file)
        sys.exit(1)

    if args.export:
        out = export_static_html(analysis_file, args.export)
        print(f"Exported static report to {out}")
        return

    app = create_app(analysis_file)
    print(f"Starting Council of 8 visualization on http://localhost:{args.port}")
    app.run(port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
