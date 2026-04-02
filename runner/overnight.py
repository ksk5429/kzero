"""
K-ZERO Overnight Runner — multi-run, multi-step evolving deliberation on Ollama.

Runs N simulations, each with M Hegelian evolution steps.
Positions carry forward between steps within each run.
Aggregates results across all runs into probability distributions.
Saves everything: transcripts, evolution data, and aggregated prediction.

Usage:
    python -m runner.overnight "Should humanity pursue immortality?" --runs 50 --steps 3
    python -m runner.overnight "Is AI the next stage of evolution?" --runs 100 --steps 5
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
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table

console = Console(width=100)


def _run_one_evolution(agents, question, client, model, n_steps, run_id, history_out=None):
    """Run one multi-step Hegelian evolution. Returns per-agent position history."""
    from runner.evolution import EvolutionTracker

    agent_names = [n for n in agents.keys() if "Kevin" not in n]
    tracker = EvolutionTracker(agent_names, question, client, model)
    history = []
    positions = {}  # Carry forward between steps
    round_counter = 0

    for step in range(1, n_steps + 1):
        random.shuffle(agent_names)

        # --- THESIS ---
        round_counter += 1
        for name in agent_names:
            agent = agents[name]
            prev = positions.get(name, "")
            ctx = f" Previous position: \"{prev[:150]}\"." if prev else ""
            try:
                text = agent.respond(history,
                    current_topic=f"Question: \"{question}\".{ctx} State your position.",
                    max_tokens=250)
                if text and not text.startswith("["):
                    entry = {"speaker": name, "text": text, "round": round_counter, "type": "agent"}
                    history.append(entry)
                    tracker.extract_position(name, text, round_counter)
            except Exception:
                pass

        # --- ANTITHESIS ---
        round_counter += 1
        random.shuffle(agent_names)
        for name in agent_names:
            agent = agents[name]
            try:
                text = agent.respond(history,
                    current_topic=f"Question: \"{question}\". Which argument is weakest? Name them. Challenge it.",
                    max_tokens=250)
                if text and not text.startswith("["):
                    entry = {"speaker": name, "text": text, "round": round_counter, "type": "agent"}
                    history.append(entry)
                    tracker.extract_position(name, text, round_counter)
            except Exception:
                pass

        # --- SYNTHESIS ---
        round_counter += 1
        random.shuffle(agent_names)
        for name in agent_names:
            agent = agents[name]
            try:
                text = agent.respond(history,
                    current_topic=f"Question: \"{question}\". Reflect on the tension. What might you be wrong about?",
                    max_tokens=200)
                if text and not text.startswith("["):
                    entry = {"speaker": name, "text": text, "round": round_counter, "type": "agent"}
                    history.append(entry)
            except Exception:
                pass

        # --- REVISION ---
        round_counter += 1
        random.shuffle(agent_names)
        for name in agent_names:
            agent = agents[name]
            prev = positions.get(name, "")
            ctx = f" Previous: \"{prev[:120]}\"." if prev else ""
            try:
                text = agent.respond(history,
                    current_topic=f"Question: \"{question}\".{ctx} State your REVISED position.",
                    max_tokens=250)
                if text and not text.startswith("["):
                    entry = {"speaker": name, "text": text, "round": round_counter, "type": "agent"}
                    history.append(entry)
                    tracker.extract_position(name, text, round_counter)
                    positions[name] = text[:200]
            except Exception:
                pass

    # Save history if requested
    if history_out is not None:
        history_out.extend(history)

    return {
        "run_id": run_id,
        "n_steps": n_steps,
        "n_messages": len(history),
        "prediction": tracker.get_prediction(),
        "convergence": tracker.get_convergence_report(),
        "final_positions": dict(positions),
    }


def run_overnight(
    question: str,
    n_runs: int = 50,
    n_steps: int = 3,
    council_dir: str = ".",
    save_transcripts: bool = True,
):
    """Run N multi-step evolutions overnight and aggregate results."""
    load_dotenv(Path(council_dir) / ".env")
    from runner.agent import load_agents, _create_client

    client = _create_client()
    model = os.getenv("COUNCIL_MODEL", "qwen2.5:7b")
    agents = load_agents(Path(council_dir), client)

    console.print()
    console.rule("[bold bright_red]K-ZERO OVERNIGHT RUNNER[/bold bright_red]")
    console.print(f"[bold]Question:[/bold] {question}")
    console.print(f"[bold]Runs:[/bold] {n_runs} | [bold]Steps/run:[/bold] {n_steps} | [bold]Model:[/bold] {model}")
    console.print(f"[bold]Agents:[/bold] {len(agents)} | [bold]Messages/run:[/bold] ~{n_steps * 4 * 7}")
    total_calls = n_runs * n_steps * 4 * 7
    console.print(f"[bold]Total API calls:[/bold] ~{total_calls}")
    console.rule(style="dim")

    # Output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = question[:40].lower().replace(" ", "_").replace("?", "")
    out_dir = Path(council_dir) / "overnight" / f"{slug}_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    start_time = time.time()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Running evolutions", total=n_runs)

        for i in range(n_runs):
            progress.update(task, description=f"Run {i+1}/{n_runs} ({n_steps} steps)")

            history = []
            result = _run_one_evolution(
                agents, question, client, model,
                n_steps=n_steps, run_id=i, history_out=history,
            )
            results.append(result)

            # Save individual transcript
            if save_transcripts and i < 10:  # Save first 10 full transcripts
                tx_path = out_dir / f"run_{i:04d}.json"
                tx_path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")

            # Save incremental results every 10 runs
            if (i + 1) % 10 == 0:
                _save_aggregation(results, question, n_runs, n_steps, model, out_dir)
                elapsed = time.time() - start_time
                per_run = elapsed / (i + 1)
                remaining = per_run * (n_runs - i - 1)
                console.print(f"  [dim]Checkpoint: {i+1} runs, {elapsed/60:.0f}m elapsed, ~{remaining/60:.0f}m remaining[/dim]")

            progress.advance(task)

    # Final aggregation
    elapsed = time.time() - start_time
    agg = _save_aggregation(results, question, n_runs, n_steps, model, out_dir)

    # Display results
    console.print()
    console.rule("[bold bright_red]OVERNIGHT RESULTS[/bold bright_red]")

    type_colors = {"CONVERGENT": "green", "LEANING": "yellow", "CONTESTED": "red", "GENUINELY_OPEN": "magenta"}
    color = type_colors.get(agg["question_type"], "white")
    console.print(f"  [{color} bold]{agg['question_type']}[/{color} bold]: {agg['question_description']}")
    console.print(f"  Runs: {n_runs} | Steps/run: {n_steps} | Time: {elapsed/60:.0f} minutes")
    console.print()

    # Prediction distribution
    table = Table(title="Prediction Distribution")
    table.add_column("Outcome", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("Pct", justify="right")
    table.add_column("Bar")

    for outcome, count in sorted(agg["prediction_distribution"].items(), key=lambda x: -x[1]):
        pct = count / n_runs
        bar = "#" * int(pct * 30)
        bar_color = "green" if outcome == "FOR" else "red" if outcome == "AGAINST" else "yellow"
        table.add_row(outcome, str(count), f"{pct:.0%}", f"[{bar_color}]{bar}[/{bar_color}]")
    console.print(table)

    # Agent stability
    if agg.get("agent_stability"):
        console.print()
        stable_table = Table(title="Agent Consistency")
        stable_table.add_column("Agent", style="bold")
        stable_table.add_column("Mean", justify="right")
        stable_table.add_column("Var", justify="right")
        stable_table.add_column("Side")

        for name, data in sorted(agg["agent_stability"].items(), key=lambda x: abs(x[1]["mean_score"]), reverse=True):
            side_color = "green" if data["consistent_side"] == "FOR" else "red" if data["consistent_side"] == "AGAINST" else "yellow"
            stable_table.add_row(
                name.split()[0], f"{data['mean_score']:+.2f}", f"{data['variance']:.3f}",
                f"[{side_color}]{data['consistent_side']}[/{side_color}]")
        console.print(stable_table)

    console.print(f"\n  Results: {out_dir}")
    console.rule(style="dim")

    return agg


def _save_aggregation(results, question, n_runs, n_steps, model, out_dir):
    """Aggregate and save results."""
    predictions = [r["prediction"]["prediction"] for r in results]
    avg_scores = [r["prediction"]["average_score"] for r in results]
    confidences = [r["prediction"]["confidence"] for r in results]

    pred_counts = {}
    for p in predictions:
        pred_counts[p] = pred_counts.get(p, 0) + 1

    dominant = max(pred_counts, key=pred_counts.get) if pred_counts else "NONE"
    dominance_pct = pred_counts.get(dominant, 0) / len(results) if results else 0

    if dominance_pct > 0.8:
        q_type, q_desc = "CONVERGENT", "This question has a clear answer among these minds."
    elif dominance_pct > 0.6:
        q_type, q_desc = "LEANING", f"The council leans {dominant} but with significant dissent."
    elif len(pred_counts) > 1 and max(pred_counts.values()) == min(pred_counts.values()):
        q_type, q_desc = "GENUINELY_OPEN", "No convergent answer — genuinely open question."
    else:
        q_type, q_desc = "CONTESTED", "The council is split — real fault lines exist."

    # Per-agent stability
    agent_scores = {}
    for r in results:
        for name, data in r["convergence"].get("current_positions", {}).items():
            if name not in agent_scores:
                agent_scores[name] = []
            agent_scores[name].append(data["score"])

    agent_stability = {}
    for name, scores in agent_scores.items():
        if len(scores) >= 2:
            mean = sum(scores) / len(scores)
            var = sum((s - mean) ** 2 for s in scores) / len(scores)
            agent_stability[name] = {
                "mean_score": round(mean, 3),
                "variance": round(var, 4),
                "stable": var < 0.1,
                "consistent_side": "FOR" if mean > 0.2 else "AGAINST" if mean < -0.2 else "SWINGS",
                "all_scores": [round(s, 2) for s in scores],
            }

    agg = {
        "question": question,
        "n_runs": len(results),
        "n_steps": n_steps,
        "model": model,
        "question_type": q_type,
        "question_description": q_desc,
        "prediction_distribution": pred_counts,
        "dominant_prediction": dominant,
        "dominance_pct": round(dominance_pct, 3),
        "avg_score_mean": round(sum(avg_scores) / len(avg_scores), 3) if avg_scores else 0,
        "avg_confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0,
        "agent_stability": agent_stability,
        "timestamp": datetime.now().isoformat(),
    }

    agg_path = out_dir / "aggregation.json"
    agg_path.write_text(json.dumps(agg, indent=2, ensure_ascii=False), encoding="utf-8")
    return agg


def main():
    args = sys.argv[1:]
    if not args:
        console.print("[red]Usage: python -m runner.overnight \"question\" --runs 50 --steps 3[/red]")
        sys.exit(1)

    question = args[0]
    n_runs = 50
    n_steps = 3

    i = 1
    while i < len(args):
        if args[i] == "--runs" and i + 1 < len(args):
            n_runs = int(args[i + 1]); i += 2
        elif args[i] == "--steps" and i + 1 < len(args):
            n_steps = int(args[i + 1]); i += 2
        else:
            i += 1

    run_overnight(question, n_runs=n_runs, n_steps=n_steps)


if __name__ == "__main__":
    main()
