"""
Dialectical Evolution Engine — agents don't just respond, they EVOLVE.

Each round follows Hegel's dialectic as an algorithm:
  1. THESIS   — Agent states their position on the question
  2. ANTITHESIS — Agent reviews ALL other responses, identifies challenges
  3. SYNTHESIS — Agent reflects deeply, integrating what challenged them
  4. REVISION  — Agent produces a revised position (may be the same, or shifted)

Over N rounds, positions genuinely evolve. The output is not a transcript
but a THOUGHT EVOLUTION MAP — showing how each mind changed and why.

Usage:
    python -m runner.dialectic "Should humanity pursue immortality?" --rounds 5
    python -m runner.dialectic "Is AI the next stage of evolution?" --rounds 3 --agents 4
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
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from runner.agent import load_agents, _create_client

console = Console(width=110)

AGENT_COLORS = {
    "Elon Musk": "red",
    "Richard Feynman": "cyan",
    "Kobe Bryant": "yellow",
    "Steve Jobs": "white",
    "Jean-Paul Sartre": "magenta",
    "George Carlin": "green",
    "Bryan Johnson": "blue",
    "Kevin (김경선)": "bright_white",
}


def _call_llm(agent, prompt, system_extra="", max_tokens=600):
    """Make an LLM call with the agent's full character context."""
    model = os.getenv("COUNCIL_MODEL", "llama3")
    temp = float(os.getenv("COUNCIL_TEMPERATURE", "0.85"))
    messages = [
        {"role": "system", "content": agent.system_prompt + "\n\n" + system_extra},
        {"role": "user", "content": prompt},
    ]
    for attempt in range(3):
        try:
            response = agent.client.chat.completions.create(
                model=model, max_tokens=max_tokens,
                temperature=temp, messages=messages,
            )
            if response.choices:
                return response.choices[0].message.content or ""
            return ""
        except Exception:
            if attempt < 2:
                from runner.agent import _rotate_client
                agent.client = _rotate_client()
                time.sleep(1)
    return "[No response]"


class DialecticRound:
    """One round of dialectical evolution for all agents."""

    def __init__(self, round_num, question, agents, previous_positions=None):
        self.round_num = round_num
        self.question = question
        self.agents = agents
        self.previous_positions = previous_positions or {}

        # Results for this round
        self.theses = {}       # Initial positions
        self.reviews = {}      # What challenged them
        self.reflections = {}  # Deep thinking
        self.revisions = {}    # Revised positions

    def run(self, verbose=True):
        """Execute the full dialectical cycle."""
        agent_names = list(self.agents.keys())

        if verbose:
            console.print()
            console.rule(f"[bold]Round {self.round_num} — Dialectical Cycle[/bold]", style="bright_white")

        # === PHASE 1: THESIS — Each agent states their position ===
        if verbose:
            console.print("\n[bold dim]Phase 1: THESIS — State your position[/bold dim]")

        for name in agent_names:
            agent = self.agents[name]
            prev = self.previous_positions.get(name, {}).get("revision", "No prior position")

            prompt = (
                f"The question is: \"{self.question}\"\n\n"
                f"Your previous position was: \"{prev}\"\n\n"
                "State your CURRENT position on this question in 2-3 sentences. "
                "Be direct. Take a clear stance. If your position hasn't changed from last round, say so and explain why it holds."
            )

            thesis = _call_llm(agent, prompt, max_tokens=300)
            self.theses[name] = thesis

            if verbose:
                short = name.split()[0]
                color = AGENT_COLORS.get(name, "white")
                console.print(Panel(
                    Text(thesis, style=color),
                    title=f"[{color}]{short} — THESIS[/{color}]",
                    border_style="dim",
                    padding=(0, 1),
                ))
            time.sleep(0.3)

        # === PHASE 2: ANTITHESIS — Review others, find challenges ===
        if verbose:
            console.print("\n[bold dim]Phase 2: ANTITHESIS — Review and challenge[/bold dim]")

        # Compile all theses for review
        all_theses = "\n\n".join(
            f"**{name}**: {thesis}" for name, thesis in self.theses.items()
        )

        for name in agent_names:
            agent = self.agents[name]
            others_theses = "\n\n".join(
                f"**{n}**: {t}" for n, t in self.theses.items() if n != name
            )

            prompt = (
                f"The question is: \"{self.question}\"\n\n"
                f"Your thesis: \"{self.theses[name]}\"\n\n"
                f"Here are the other council members' positions:\n{others_theses}\n\n"
                "Which argument challenges your position the MOST? Why? "
                "Which argument STRENGTHENS your position? "
                "Be specific — name the person and quote their key point. 2-3 sentences."
            )

            review = _call_llm(agent, prompt,
                system_extra="You are reviewing others' arguments. Be honest about what challenges you.",
                max_tokens=400)
            self.reviews[name] = review

            if verbose:
                short = name.split()[0]
                color = AGENT_COLORS.get(name, "white")
                console.print(Panel(
                    Text(review, style="dim"),
                    title=f"[{color}]{short} — ANTITHESIS (reviewing others)[/{color}]",
                    border_style="dim",
                    padding=(0, 1),
                ))
            time.sleep(0.3)

        # === PHASE 3: SYNTHESIS — Deep reflection ===
        if verbose:
            console.print("\n[bold dim]Phase 3: SYNTHESIS — Deep reflection[/bold dim]")

        for name in agent_names:
            agent = self.agents[name]

            prompt = (
                f"The question is: \"{self.question}\"\n\n"
                f"Your thesis: \"{self.theses[name]}\"\n\n"
                f"Your review of others: \"{self.reviews[name]}\"\n\n"
                "Now think DEEPLY. What is the tension between your position and the strongest "
                "counter-argument? Is there a way to hold BOTH truths simultaneously? "
                "What are you NOT seeing? What assumption might be wrong? "
                "Think out loud. 3-4 sentences of genuine reflection."
            )

            reflection = _call_llm(agent, prompt,
                system_extra="Think deeply and honestly. This is private reflection — no audience. Be vulnerable about your uncertainties.",
                max_tokens=500)
            self.reflections[name] = reflection

            if verbose:
                short = name.split()[0]
                color = AGENT_COLORS.get(name, "white")
                console.print(Panel(
                    Text(reflection, style="italic"),
                    title=f"[{color}]{short} — SYNTHESIS (reflecting)[/{color}]",
                    border_style=color,
                    padding=(0, 1),
                ))
            time.sleep(0.3)

        # === PHASE 4: REVISION — Updated position ===
        if verbose:
            console.print("\n[bold dim]Phase 4: REVISION — Updated position[/bold dim]")

        for name in agent_names:
            agent = self.agents[name]
            prev = self.previous_positions.get(name, {}).get("revision", "No prior position")

            prompt = (
                f"The question is: \"{self.question}\"\n\n"
                f"Your original thesis this round: \"{self.theses[name]}\"\n"
                f"The strongest challenge you identified: \"{self.reviews[name]}\"\n"
                f"Your deep reflection: \"{self.reflections[name]}\"\n"
                f"Your position LAST round: \"{prev}\"\n\n"
                "Now state your REVISED position. Has it changed? If so, how and why? "
                "If not, explain why the challenges didn't convince you. "
                "Be honest. Changing your mind is strength, not weakness. 2-3 sentences."
            )

            revision = _call_llm(agent, prompt,
                system_extra="State your revised position clearly. If you changed your mind, own it.",
                max_tokens=300)
            self.revisions[name] = revision

            if verbose:
                short = name.split()[0]
                color = AGENT_COLORS.get(name, "white")
                # Check if position shifted
                shifted = self._detect_shift(name)
                shift_marker = " [bold red]** SHIFTED **[/bold red]" if shifted else ""
                console.print(Panel(
                    Text(revision, style=f"bold {color}"),
                    title=f"[{color}]{short} — REVISION{shift_marker}[/{color}]",
                    border_style=color,
                    padding=(0, 1),
                ))
            time.sleep(0.3)

        return self.get_round_data()

    def _detect_shift(self, name):
        """Detect if an agent's position meaningfully shifted this round."""
        thesis = self.theses.get(name, "").lower()
        revision = self.revisions.get(name, "").lower()

        # Simple heuristic: check for shift language
        shift_words = ["changed", "revised", "shifted", "reconsider", "now I think",
                       "convinced me", "I was wrong", "updated", "evolved", "moved",
                       "no longer", "I now believe", "changed my mind"]
        return any(w in revision for w in shift_words)

    def get_round_data(self):
        """Return structured data for this round."""
        data = {}
        for name in self.agents:
            data[name] = {
                "thesis": self.theses.get(name, ""),
                "review": self.reviews.get(name, ""),
                "reflection": self.reflections.get(name, ""),
                "revision": self.revisions.get(name, ""),
                "shifted": self._detect_shift(name),
            }
        return data


def run_dialectic(
    question: str,
    n_rounds: int = 5,
    n_agents: int = 8,
    council_dir: str = ".",
    verbose: bool = True,
):
    """Run a full dialectical evolution session."""
    load_dotenv(Path(council_dir) / ".env")
    client = _create_client()
    all_agents = load_agents(Path(council_dir), client)

    # Select agents (random subset if n_agents < 8)
    agent_names = list(all_agents.keys())
    if n_agents < len(agent_names):
        agent_names = random.sample(agent_names, n_agents)
    agents = {name: all_agents[name] for name in agent_names}

    if verbose:
        console.print()
        console.print(Panel(
            f"[bold bright_red]D I A L E C T I C   E V O L U T I O N[/bold bright_red]\n\n"
            f"[dim]Question: {question}\n"
            f"Agents: {len(agents)} | Rounds: {n_rounds}\n"
            f"Each round: Thesis → Antithesis → Synthesis → Revision\n"
            f"Model: {os.getenv('COUNCIL_MODEL', 'llama3')}[/dim]",
            border_style="bright_red",
            padding=(1, 2),
        ))

    # Run rounds
    all_rounds = []
    positions = {}  # Current positions carried forward

    for round_num in range(1, n_rounds + 1):
        dr = DialecticRound(round_num, question, agents, positions)
        round_data = dr.run(verbose=verbose)
        all_rounds.append(round_data)

        # Carry forward positions
        for name, data in round_data.items():
            positions[name] = data

    # === EVOLUTION SUMMARY ===
    if verbose:
        console.print()
        console.rule("[bold]EVOLUTION SUMMARY[/bold]", style="bright_red")

        table = Table(title="Position Evolution Across Rounds")
        table.add_column("Agent", style="bold")
        table.add_column("Round 1 Position")
        table.add_column(f"Round {n_rounds} Position")
        table.add_column("Shifts", justify="center")

        for name in agents:
            short = name.split()[0]
            color = AGENT_COLORS.get(name, "white")
            r1 = all_rounds[0].get(name, {}).get("thesis", "?")[:80]
            rn = all_rounds[-1].get(name, {}).get("revision", "?")[:80]
            n_shifts = sum(1 for r in all_rounds if r.get(name, {}).get("shifted", False))
            shift_display = f"[red]{n_shifts}[/red]" if n_shifts > 0 else "0"
            table.add_row(f"[{color}]{short}[/{color}]", r1, rn, shift_display)

        console.print(table)

    # Save results
    out_dir = Path(council_dir) / "dialectics"
    out_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = question[:40].lower().replace(" ", "_").replace("?", "")

    result = {
        "question": question,
        "n_rounds": n_rounds,
        "n_agents": len(agents),
        "agent_names": list(agents.keys()),
        "model": os.getenv("COUNCIL_MODEL", "llama3"),
        "timestamp": datetime.now().isoformat(),
        "rounds": all_rounds,
        "evolution_summary": {
            name: {
                "first_position": all_rounds[0].get(name, {}).get("thesis", ""),
                "final_position": all_rounds[-1].get(name, {}).get("revision", ""),
                "total_shifts": sum(1 for r in all_rounds if r.get(name, {}).get("shifted", False)),
                "all_theses": [r.get(name, {}).get("thesis", "") for r in all_rounds],
                "all_revisions": [r.get(name, {}).get("revision", "") for r in all_rounds],
            }
            for name in agents
        },
    }

    json_path = out_dir / f"{slug}_{timestamp}.json"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    if verbose:
        console.print(f"\n  [dim]Evolution saved: {json_path.name}[/dim]")
        console.rule(style="dim")

    return result


def main():
    args = sys.argv[1:]
    if not args:
        console.print("[red]Usage: python -m runner.dialectic \"Your question\" --rounds 5[/red]")
        sys.exit(1)

    question = args[0]
    n_rounds = 5
    n_agents = 8

    for i, arg in enumerate(args[1:], 1):
        if arg == "--rounds" and i < len(args):
            n_rounds = int(args[i + 1]) if i + 1 < len(args) else 5
        elif arg == "--agents" and i < len(args):
            n_agents = int(args[i + 1]) if i + 1 < len(args) else 8

    run_dialectic(question, n_rounds=n_rounds, n_agents=n_agents)


if __name__ == "__main__":
    main()
