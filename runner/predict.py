"""
K-ZERO Prediction Engine — run N simulations, aggregate outcomes, plot distribution.

Core insight: If a question CONVERGES across N runs, it has an answer.
If it DIVERGES, it's genuinely open. The distribution reveals truth.

Usage:
    python -m runner.predict "Should humanity pursue immortality?" --runs 10
    python -m runner.predict "What is the meaning of life?" --runs 20 --rounds 3
"""

import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

from runner.agent import load_agents, _create_client
from runner.evolution import EvolutionTracker

console = Console(width=100)


def run_single_simulation(
    agents: dict,
    question: str,
    client,
    model: str,
    rounds: int = 3,
    speakers_per_round: int = 2,
    run_id: int = 0,
) -> dict:
    """Run one simulation and return evolution results."""
    tracker = EvolutionTracker(list(agents.keys()), question, client, model)
    transcript = [{"speaker": "[GOD_MODE]", "text": question, "round": 0, "type": "god_mode"}]

    agent_names = list(agents.keys())

    for round_num in range(1, rounds + 1):
        speakers = random.sample(agent_names, min(speakers_per_round, len(agent_names)))

        for name in speakers:
            agent = agents[name]
            try:
                response = agent.respond(
                    transcript,
                    current_topic=question,
                    max_tokens=int(os.getenv("COUNCIL_MAX_TOKENS", "600")),
                )
                transcript.append({
                    "speaker": name, "text": response,
                    "round": round_num, "type": "agent",
                })
                tracker.extract_position(name, response, round_num)
            except Exception:
                pass  # Skip on error, continue simulation

    prediction = tracker.get_prediction()
    convergence = tracker.get_convergence_report()

    return {
        "run_id": run_id,
        "prediction": prediction,
        "convergence": convergence,
        "n_messages": len(transcript),
    }


def aggregate_predictions(results: list[dict], question: str) -> dict:
    """Aggregate N simulation results into a probability distribution."""
    n_runs = len(results)

    # Collect all predictions
    predictions = [r["prediction"]["prediction"] for r in results]
    avg_scores = [r["prediction"]["average_score"] for r in results]
    confidences = [r["prediction"]["confidence"] for r in results]
    trends = [r["convergence"]["convergence_trend"] for r in results]

    # Prediction distribution
    pred_counts = {}
    for p in predictions:
        pred_counts[p] = pred_counts.get(p, 0) + 1

    # Score distribution (binned)
    score_bins = {"strong_against": 0, "against": 0, "neutral": 0, "for": 0, "strong_for": 0}
    for s in avg_scores:
        if s < -0.5:
            score_bins["strong_against"] += 1
        elif s < -0.1:
            score_bins["against"] += 1
        elif s < 0.1:
            score_bins["neutral"] += 1
        elif s < 0.5:
            score_bins["for"] += 1
        else:
            score_bins["strong_for"] += 1

    # Convergence pattern
    trend_counts = {}
    for t in trends:
        trend_counts[t] = trend_counts.get(t, 0) + 1

    # Per-agent stability (how consistent is each agent across runs?)
    agent_scores: dict[str, list[float]] = {}
    for r in results:
        for agent_name, data in r["convergence"].get("current_positions", {}).items():
            if agent_name not in agent_scores:
                agent_scores[agent_name] = []
            agent_scores[agent_name].append(data["score"])

    agent_stability = {}
    for name, scores in agent_scores.items():
        if len(scores) >= 2:
            mean = sum(scores) / len(scores)
            variance = sum((s - mean) ** 2 for s in scores) / len(scores)
            agent_stability[name] = {
                "mean_score": round(mean, 3),
                "variance": round(variance, 4),
                "stable": variance < 0.1,
                "consistent_side": "FOR" if mean > 0.2 else "AGAINST" if mean < -0.2 else "SWINGS",
            }

    # Overall classification
    dominant_prediction = max(pred_counts, key=pred_counts.get)
    dominance_pct = pred_counts[dominant_prediction] / n_runs

    if dominance_pct > 0.8:
        question_type = "CONVERGENT"
        question_desc = "This question has a clear answer among these minds."
    elif dominance_pct > 0.6:
        question_type = "LEANING"
        question_desc = f"The council leans {dominant_prediction} but with significant dissent."
    elif max(pred_counts.values()) == min(pred_counts.values()):
        question_type = "GENUINELY_OPEN"
        question_desc = "This question has no convergent answer — it's genuinely open."
    else:
        question_type = "CONTESTED"
        question_desc = "The council is split — real fault lines exist."

    return {
        "question": question,
        "n_runs": n_runs,
        "question_type": question_type,
        "question_description": question_desc,
        "prediction_distribution": pred_counts,
        "dominant_prediction": dominant_prediction,
        "dominance_pct": round(dominance_pct, 3),
        "score_distribution": score_bins,
        "avg_score_mean": round(sum(avg_scores) / len(avg_scores), 3),
        "avg_confidence": round(sum(confidences) / len(confidences), 3),
        "convergence_trends": trend_counts,
        "agent_stability": agent_stability,
        "timestamp": datetime.now().isoformat(),
    }


def plot_distribution(agg: dict, output_path: str = None):
    """Generate a Plotly visualization of the prediction distribution."""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError:
        console.print("[yellow]plotly not available — skipping visualization[/yellow]")
        return

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "Prediction Distribution",
            "Average Score Distribution",
            "Convergence Trends",
            "Agent Stability",
        ],
        specs=[[{"type": "pie"}, {"type": "bar"}],
               [{"type": "bar"}, {"type": "bar"}]],
    )

    # 1. Prediction pie chart
    pred = agg["prediction_distribution"]
    colors = {"FOR": "#2ecc71", "AGAINST": "#e74c3c", "SPLIT": "#f39c12", "NEUTRAL": "#95a5a6"}
    fig.add_trace(go.Pie(
        labels=list(pred.keys()),
        values=list(pred.values()),
        marker_colors=[colors.get(k, "#95a5a6") for k in pred.keys()],
        hole=0.4,
        textinfo="label+percent",
    ), row=1, col=1)

    # 2. Score distribution bar
    score_dist = agg["score_distribution"]
    score_colors = ["#e74c3c", "#e67e22", "#95a5a6", "#27ae60", "#2ecc71"]
    fig.add_trace(go.Bar(
        x=list(score_dist.keys()),
        y=list(score_dist.values()),
        marker_color=score_colors,
    ), row=1, col=2)

    # 3. Convergence trends bar
    trends = agg["convergence_trends"]
    trend_colors = {"CONVERGING": "#2ecc71", "DIVERGING": "#e74c3c",
                    "STABLE": "#f39c12", "INSUFFICIENT_DATA": "#95a5a6"}
    fig.add_trace(go.Bar(
        x=list(trends.keys()),
        y=list(trends.values()),
        marker_color=[trend_colors.get(k, "#95a5a6") for k in trends.keys()],
    ), row=2, col=1)

    # 4. Agent stability
    stability = agg["agent_stability"]
    if stability:
        names = [n.split()[0] for n in stability.keys()]
        means = [v["mean_score"] for v in stability.values()]
        variances = [v["variance"] for v in stability.values()]
        bar_colors = ["#2ecc71" if v["stable"] else "#e74c3c" for v in stability.values()]
        fig.add_trace(go.Bar(
            x=names,
            y=means,
            error_y=dict(type="data", array=[v ** 0.5 for v in variances], visible=True),
            marker_color=bar_colors,
        ), row=2, col=2)

    fig.update_layout(
        title=f"K-ZERO Prediction: \"{agg['question'][:60]}\" ({agg['n_runs']} runs)",
        template="plotly_dark",
        paper_bgcolor="#1a1a2e",
        plot_bgcolor="#1a1a2e",
        font_color="#e0e0e0",
        height=700,
        showlegend=False,
    )

    if output_path:
        fig.write_html(output_path)
        console.print(f"[green]Visualization saved: {output_path}[/green]")
    else:
        fig.show()

    return fig


def run_prediction(
    question: str,
    n_runs: int = 10,
    rounds_per_run: int = 3,
    speakers_per_round: int = 2,
    council_dir: str = ".",
):
    """Run N simulations and produce an aggregated prediction."""
    load_dotenv(Path(council_dir) / ".env")

    client = _create_client()
    model = os.getenv("COUNCIL_MODEL", "llama3")
    agents = load_agents(Path(council_dir), client)

    console.print()
    console.rule("[bold]K-ZERO PREDICTION ENGINE[/bold]", style="bright_red")
    console.print(f"[bold]Question:[/bold] {question}")
    console.print(f"[bold]Runs:[/bold] {n_runs} | [bold]Rounds/run:[/bold] {rounds_per_run} | [bold]Model:[/bold] {model}")
    console.print(f"[bold]Agents:[/bold] {len(agents)} | [bold]Provider:[/bold] {os.getenv('LLM_BASE_URL', 'unknown')}")
    console.rule(style="dim")

    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        console=console,
    ) as progress:
        task = progress.add_task("Running simulations", total=n_runs)

        for i in range(n_runs):
            progress.update(task, description=f"Run {i + 1}/{n_runs}")

            result = run_single_simulation(
                agents, question, client, model,
                rounds=rounds_per_run,
                speakers_per_round=speakers_per_round,
                run_id=i,
            )
            results.append(result)
            progress.advance(task)

    # Aggregate
    console.print()
    console.print("[bold]Aggregating predictions...[/bold]")
    agg = aggregate_predictions(results, question)

    # Display results
    console.print()
    console.rule("[bold]PREDICTION RESULTS[/bold]", style="bright_red")

    # Question classification
    type_colors = {
        "CONVERGENT": "green", "LEANING": "yellow",
        "CONTESTED": "red", "GENUINELY_OPEN": "magenta",
    }
    color = type_colors.get(agg["question_type"], "white")
    console.print(f"  [{color} bold]{agg['question_type']}[/{color} bold]: {agg['question_description']}")
    console.print()

    # Prediction distribution
    table = Table(title="Prediction Distribution")
    table.add_column("Outcome", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("Percentage", justify="right")
    table.add_column("Bar")

    for outcome, count in sorted(agg["prediction_distribution"].items(), key=lambda x: -x[1]):
        pct = count / n_runs
        bar = "#" * int(pct * 30)
        bar_color = "green" if outcome == "FOR" else "red" if outcome == "AGAINST" else "yellow"
        table.add_row(outcome, str(count), f"{pct:.0%}", f"[{bar_color}]{bar}[/{bar_color}]")
    console.print(table)

    # Agent stability
    if agg["agent_stability"]:
        console.print()
        stable_table = Table(title="Agent Consistency Across Runs")
        stable_table.add_column("Agent", style="bold")
        stable_table.add_column("Mean Score", justify="right")
        stable_table.add_column("Variance", justify="right")
        stable_table.add_column("Side")
        stable_table.add_column("Stable?")

        for name, data in sorted(agg["agent_stability"].items(),
                                  key=lambda x: abs(x[1]["mean_score"]), reverse=True):
            short = name.split()[0]
            side_color = "green" if data["consistent_side"] == "FOR" else "red" if data["consistent_side"] == "AGAINST" else "yellow"
            stable_marker = "[green]YES[/green]" if data["stable"] else "[red]NO[/red]"
            stable_table.add_row(
                short,
                f"{data['mean_score']:+.3f}",
                f"{data['variance']:.4f}",
                f"[{side_color}]{data['consistent_side']}[/{side_color}]",
                stable_marker,
            )
        console.print(stable_table)

    console.print()
    console.print(f"  Average confidence: {agg['avg_confidence']:.0%}")
    console.print(f"  Average score: {agg['avg_score_mean']:+.3f}")
    console.rule(style="dim")

    # Save results
    out_dir = Path(council_dir) / "predictions"
    out_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = question[:40].lower().replace(" ", "_").replace("?", "")

    json_path = out_dir / f"{slug}_{timestamp}.json"
    json_path.write_text(json.dumps(agg, indent=2, ensure_ascii=False), encoding="utf-8")
    console.print(f"  Results saved: {json_path.name}")

    # Plot
    html_path = out_dir / f"{slug}_{timestamp}.html"
    plot_distribution(agg, str(html_path))

    return agg


def main():
    """CLI entry point."""
    args = sys.argv[1:]
    if not args:
        console.print("[red]Usage: python -m runner.predict \"Your question here\" --runs 10[/red]")
        sys.exit(1)

    question = args[0]
    n_runs = 10
    rounds = 3

    for i, arg in enumerate(args[1:], 1):
        if arg == "--runs" and i < len(args):
            n_runs = int(args[i + 1]) if i + 1 < len(args) else 10
        elif arg == "--rounds" and i < len(args):
            rounds = int(args[i + 1]) if i + 1 < len(args) else 3

    run_prediction(question, n_runs=n_runs, rounds_per_run=rounds)


if __name__ == "__main__":
    main()
