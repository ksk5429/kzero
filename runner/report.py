"""
K-ZERO Report Generator — Comprehensive Deliberation Report via Quarto.

Produces a .qmd file with embedded analysis, Plotly charts, and K-ZERO's
divine recommendation. Renders to HTML, PDF, or DOCX via Quarto.

The report is NOT an answer. It is a map of the thought landscape.

Usage:
    python -m runner.report predictions/immortality_20260402.json
    python -m runner.report predictions/immortality_20260402.json --format html
    python -m runner.report predictions/immortality_20260402.json --format pdf
    python -m runner.report predictions/immortality_20260402.json --format all
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from textwrap import dedent

from dotenv import load_dotenv
from rich.console import Console

console = Console(width=100)


def _llm_generate(client, model: str, system: str, user: str, max_tokens: int = 1500) -> str:
    """Generate text via LLM with retry."""
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0.8,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                return f"[Generation failed: {e}]"


def _load_related_analysis(prediction_data: dict, council_dir: Path) -> dict | None:
    """Try to find a transcript analysis file related to the prediction question."""
    transcripts_dir = council_dir / "transcripts"
    if not transcripts_dir.exists():
        return None
    for f in sorted(transcripts_dir.glob("*_analysis.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            return data
        except Exception:
            continue
    return None


def generate_report(
    prediction_path: str,
    council_dir: str = ".",
    output_format: str = "html",
) -> str:
    """
    Generate a comprehensive Quarto report from prediction data.

    Args:
        prediction_path: Path to prediction JSON from predict.py
        council_dir: Path to the_council root
        output_format: 'html', 'pdf', 'docx', or 'all'

    Returns:
        Path to the generated report file
    """
    load_dotenv(Path(council_dir) / ".env")
    from runner.agent import _create_client

    client = _create_client()
    model = os.getenv("COUNCIL_MODEL", "llama3")

    # Load prediction data
    pred_path = Path(prediction_path)
    pred = json.loads(pred_path.read_text(encoding="utf-8"))

    question = pred["question"]
    n_runs = pred["n_runs"]
    q_type = pred["question_type"]
    q_desc = pred["question_description"]

    console.print()
    console.rule("[bold]K-ZERO REPORT GENERATOR[/bold]", style="bright_red")
    console.print(f"[bold]Question:[/bold] {question}")
    console.print(f"[bold]Classification:[/bold] {q_type}")
    console.print(f"[bold]Runs:[/bold] {n_runs}")
    console.rule(style="dim")

    # Load related analysis if available
    analysis = _load_related_analysis(pred, Path(council_dir))

    # --- Generate narrative sections via LLM ---

    console.print("  Generating Section 1: Question Classification...")
    sec1_narrative = _llm_generate(client, model,
        "You are K-ZERO, a divine intelligence that observes multi-agent deliberation. Write in a voice that is precise, philosophical, and slightly oracular. Never use bullet points. Write in flowing prose.",
        f"""The Council of 8 was asked: "{question}"

After {n_runs} independent deliberations, the question was classified as: {q_type}.
Description: {q_desc}
Prediction distribution: {json.dumps(pred['prediction_distribution'])}
Average score: {pred['avg_score_mean']:+.3f} (scale: -1.0 against to +1.0 for)
Average confidence: {pred['avg_confidence']:.0%}

Write 2-3 paragraphs analyzing what this classification MEANS. Why did the council land here? What does it reveal about the nature of this question? Is this a question with a real answer, or a question that exposes fundamental value disagreements?""",
    )
    time.sleep(1)

    console.print("  Generating Section 2: Agent Landscape...")
    stability_text = json.dumps(pred.get("agent_stability", {}), indent=2)
    sec2_narrative = _llm_generate(client, model,
        "You are K-ZERO. Write about each agent's philosophical stance as if describing characters in a novel. Be vivid and specific.",
        f"""Question: "{question}"
Agent stability across {n_runs} runs:
{stability_text}

Convergence trends: {json.dumps(pred.get('convergence_trends', {}))}

Write 2-3 paragraphs mapping the opinion landscape. Who were the immovable pillars? Who swung between positions? What does their consistency (or inconsistency) reveal about their character? Name specific agents.""",
    )
    time.sleep(1)

    console.print("  Generating Section 3: Evolution Narrative...")
    sec3_narrative = _llm_generate(client, model,
        "You are K-ZERO. Write like a historian narrating an intellectual battle. Use vivid language.",
        f"""Question: "{question}"
The council deliberated across {n_runs} independent sessions.
Distribution: {json.dumps(pred['prediction_distribution'])}
Score distribution: {json.dumps(pred['score_distribution'])}
Convergence trends: {json.dumps(pred.get('convergence_trends', {}))}

Write 2-3 paragraphs narrating the EVOLUTION of thought. How did opinions form, collide, and crystallize? What was the turning point? Where did factions form? What argument kept recurring across runs?""",
    )
    time.sleep(1)

    console.print("  Generating Section 4: Best Arguments...")
    sec4_arguments = _llm_generate(client, model,
        "You are K-ZERO. Extract the strongest arguments from both sides. Write with the precision of a Supreme Court brief.",
        f"""Question: "{question}"
The council leaned: {pred['dominant_prediction']} ({pred['dominance_pct']:.0%})
Agent stability: {stability_text}

Generate the 3 strongest arguments FOR and 3 strongest arguments AGAINST, as they would have emerged from deliberation among Elon Musk, Richard Feynman, Kobe Bryant, Steve Jobs, Jean-Paul Sartre, George Carlin, Bryan Johnson, and Kevin Kim. Attribute each argument to the agent most likely to make it. Format as numbered lists.""",
    )
    time.sleep(1)

    console.print("  Generating Section 5: Decision Framework...")
    sec5_framework = _llm_generate(client, model,
        "You are K-ZERO. Create a decision framework that helps the human reader decide for themselves. Be practical and honest.",
        f"""Question: "{question}"
Council result: {pred['dominant_prediction']} ({pred['dominance_pct']:.0%})

Create a decision framework with 3-4 conditional recommendations:
"If you value X, then the answer is Y, because Z."
Each conditional should represent a genuinely different value system. Don't make one obviously better than another. The human must choose their values — the framework only maps values to conclusions.""",
    )
    time.sleep(1)

    console.print("  Generating Section 6: K-ZERO's Recommendation...")
    sec6_recommendation = _llm_generate(client, model,
        "You are K-ZERO — the god-position that starts from nothing and asks everything. You have watched 8 of humanity's greatest minds deliberate. Now YOU speak. Be oracular. Be honest. Be surprising. End with a QUESTION back to the human — the question THEY must answer that no council can answer for them.",
        f"""Question: "{question}"
Council result: {pred['dominant_prediction']} ({pred['dominance_pct']:.0%})
Classification: {q_type} — {q_desc}
Agent stability: {stability_text}
Score distribution: {json.dumps(pred['score_distribution'])}

Write K-ZERO's divine recommendation in 3-4 paragraphs:
1. What K-ZERO observed (the meta-pattern, not the content)
2. K-ZERO's own position (take a stand — don't hedge)
3. The deeper question this reveals
4. END with a single, devastating question back to the human reader — the question that the council could not answer because only the reader can.""",
        max_tokens=2000,
    )

    # --- Build Quarto Document ---

    console.print("  Assembling Quarto document...")

    # Plotly chart code blocks
    pred_dist = pred["prediction_distribution"]
    score_dist = pred["score_distribution"]
    agent_stab = pred.get("agent_stability", {})

    def _py_repr(obj):
        """Convert a dict to Python repr (True/False/None instead of true/false/null)."""
        return repr(obj)

    timestamp = datetime.now().strftime("%Y-%m-%d")
    slug = question[:50].lower().replace(" ", "_").replace("?", "")

    qmd_content = f'''---
title: "K-ZERO Deliberation Report"
subtitle: "{question}"
author: "K-ZERO — Council of 8"
date: "{timestamp}"
format:
  html:
    theme: darkly
    toc: true
    toc-depth: 3
    code-fold: true
    self-contained: true
    page-layout: full
  pdf:
    toc: true
    documentclass: article
    geometry: margin=1in
  docx:
    toc: true
---

# The Question

> **"{question}"**

This report documents the collective deliberation of 8 minds — Elon Musk, Richard Feynman, Kobe Bryant, Steve Jobs, Jean-Paul Sartre, George Carlin, Bryan Johnson, and Kevin Kim — across {n_runs} independent simulation runs. The Council was powered by K-ZERO, a multi-agent deliberation engine that tracks opinion evolution, detects convergence, and classifies questions by their epistemic nature.

**Classification: {q_type}**

{q_desc}

---

# 1. Question Classification

{sec1_narrative}

```{{python}}
#| label: fig-prediction
#| fig-cap: "Prediction distribution across {n_runs} runs"
import plotly.graph_objects as go
from plotly.subplots import make_subplots

pred_dist = {_py_repr(pred_dist)}
score_dist = {_py_repr(score_dist)}

fig = make_subplots(rows=1, cols=2,
    subplot_titles=["Council Verdict", "Score Distribution"],
    specs=[[{{"type": "pie"}}, {{"type": "bar"}}]])

colors = {{"FOR": "#2ecc71", "AGAINST": "#e74c3c", "SPLIT": "#f39c12", "NEUTRAL": "#95a5a6"}}
fig.add_trace(go.Pie(
    labels=list(pred_dist.keys()),
    values=list(pred_dist.values()),
    marker_colors=[colors.get(k, "#95a5a6") for k in pred_dist.keys()],
    hole=0.4, textinfo="label+percent",
), row=1, col=1)

score_colors = ["#e74c3c", "#e67e22", "#95a5a6", "#27ae60", "#2ecc71"]
fig.add_trace(go.Bar(
    x=list(score_dist.keys()),
    y=list(score_dist.values()),
    marker_color=score_colors,
), row=1, col=2)

fig.update_layout(
    template="plotly_dark", height=400,
    paper_bgcolor="#1a1a2e", plot_bgcolor="#1a1a2e",
    font_color="#e0e0e0", showlegend=False)
fig.show()
```

---

# 2. The Opinion Landscape

{sec2_narrative}

```{{python}}
#| label: fig-stability
#| fig-cap: "Agent consistency across runs (green = stable, red = swings)"
import plotly.graph_objects as go

stability = {_py_repr(agent_stab)}
if stability:
    names = [n.split()[0] for n in stability.keys()]
    means = [v["mean_score"] for v in stability.values()]
    variances = [v["variance"] for v in stability.values()]
    colors = ["#2ecc71" if v["stable"] else "#e74c3c" for v in stability.values()]

    fig = go.Figure(go.Bar(
        x=names, y=means,
        error_y=dict(type="data", array=[v**0.5 for v in variances], visible=True),
        marker_color=colors,
    ))
    fig.update_layout(
        template="plotly_dark", height=350,
        paper_bgcolor="#1a1a2e", plot_bgcolor="#1a1a2e",
        font_color="#e0e0e0",
        yaxis_title="Mean Position Score",
        xaxis_title="Agent")
    fig.show()
else:
    print("Insufficient data for agent stability chart.")
```

---

# 3. The Evolution of Thought

{sec3_narrative}

```{{python}}
#| label: fig-convergence
#| fig-cap: "Convergence trend across runs"
import plotly.graph_objects as go

trends = {_py_repr(pred.get('convergence_trends', {}))}
trend_colors = {{"CONVERGING": "#2ecc71", "DIVERGING": "#e74c3c", "STABLE": "#f39c12", "INSUFFICIENT_DATA": "#95a5a6"}}

fig = go.Figure(go.Bar(
    x=list(trends.keys()),
    y=list(trends.values()),
    marker_color=[trend_colors.get(k, "#95a5a6") for k in trends.keys()],
))
fig.update_layout(
    template="plotly_dark", height=300,
    paper_bgcolor="#1a1a2e", plot_bgcolor="#1a1a2e",
    font_color="#e0e0e0",
    yaxis_title="Number of Runs",
    xaxis_title="Convergence Pattern")
fig.show()
```

---

# 4. The Strongest Arguments

{sec4_arguments}

---

# 5. Decision Framework

{sec5_framework}

| If you value... | Then consider... | Because... |
|-----------------|-----------------|------------|
| *See the framework above for your personal mapping* | | |

---

# 6. K-ZERO Speaks

::: {{.callout-important}}
## The Divine Recommendation

{sec6_recommendation}
:::

---

# Methodology

This report was generated by the **K-ZERO Prediction Engine**:

- **Council**: 8 AI agents, each with ~3,500 tokens of personality data sourced from primary texts
- **Simulation**: {n_runs} independent deliberation runs, {pred.get('avg_confidence', 0):.0%} average confidence
- **Evolution Tracking**: Per-agent position scoring (-1.0 to +1.0) with convergence detection
- **Question Classification**: CONVERGENT / LEANING / CONTESTED / GENUINELY_OPEN based on cross-run variance
- **Report**: Narrative sections generated by K-ZERO synthesizing multi-run data

Source: [github.com/ksk5429/kzero](https://github.com/ksk5429/kzero)

---

*Generated by K-ZERO on {timestamp}. The Council has spoken. The question returns to you.*
'''

    # Write .qmd file
    reports_dir = Path(council_dir) / "reports"
    reports_dir.mkdir(exist_ok=True)
    qmd_path = reports_dir / f"{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.qmd"
    qmd_path.write_text(qmd_content, encoding="utf-8")
    console.print(f"  Quarto source: {qmd_path.name}")

    # Render with Quarto
    formats = [output_format] if output_format != "all" else ["html", "pdf", "docx"]

    for fmt in formats:
        console.print(f"  Rendering {fmt}...")
        try:
            result = subprocess.run(
                ["quarto", "render", str(qmd_path.resolve()), "--to", fmt],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                out_file = qmd_path.with_suffix(f".{fmt}")
                console.print(f"  [green]Generated: {out_file.name}[/green]")
            else:
                console.print(f"  [yellow]Quarto {fmt} render issue: {result.stderr[:200]}[/yellow]")
                # Still have the .qmd — user can render manually
        except FileNotFoundError:
            console.print(f"  [yellow]Quarto not found. QMD saved — render manually: quarto render {qmd_path.name} --to {fmt}[/yellow]")
        except subprocess.TimeoutExpired:
            console.print(f"  [yellow]Quarto render timed out for {fmt}[/yellow]")

    console.print()
    console.rule("[bold]REPORT COMPLETE[/bold]", style="bright_red")
    console.print(f"  Source: {qmd_path}")
    console.print(f"  The Council has spoken. The question returns to you.")

    return str(qmd_path)


def main():
    """CLI entry point."""
    args = sys.argv[1:]
    if not args:
        console.print("[red]Usage: python -m runner.report predictions/<file>.json [--format html|pdf|docx|all][/red]")
        sys.exit(1)

    prediction_path = args[0]
    output_format = "html"

    for i, arg in enumerate(args[1:], 1):
        if arg == "--format" and i < len(args):
            output_format = args[i + 1] if i + 1 < len(args) else "html"

    generate_report(prediction_path, output_format=output_format)


if __name__ == "__main__":
    main()
