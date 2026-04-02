"""
K-ZERO Console — Human-in-the-loop God Mode for the Council of 8.

K-ZERO: Kim Kyeong-Sun as Zero — the god-position that starts from nothing and asks everything.
You pose questions, inject variables, chat with individual agents,
and observe how the council reacts in real-time.

Usage:
    python -m runner.demiurge
    python -m runner.demiurge --scenario scenarios/scenario_02_ai_alignment.json
"""

import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from runner.agent import CouncilAgent, load_agents, _create_client
from runner.modes import DiscussionMode, get_mode, list_modes, get_all_mode_names

# Agent display config
AGENT_COLORS = {
    "Elon Musk": "red",
    "Richard Feynman": "cyan",
    "Kobe Bryant": "yellow",
    "Steve Jobs": "white",
    "Jean-Paul Sartre": "magenta",
    "George Carlin": "green",
    "Bryan Johnson": "blue",
    "Kevin (\uae40\uacbd\uc120)": "bright_white",
}

AGENT_SHORT = {
    "Elon Musk": "musk",
    "Richard Feynman": "feynman",
    "Kobe Bryant": "kobe",
    "Steve Jobs": "jobs",
    "Jean-Paul Sartre": "sartre",
    "George Carlin": "carlin",
    "Bryan Johnson": "johnson",
    "Kevin (\uae40\uacbd\uc120)": "kevin",
}

HELP_TEXT = """
[bold]K-ZERO Console Commands[/bold]

[yellow]/inject[/yellow] <text>     Inject a god-mode variable into the council
[yellow]/ask[/yellow] <name> <text>  Ask a specific agent directly (e.g. /ask feynman Why?)
[yellow]/all[/yellow] <text>         Pose a question — all agents respond
[yellow]/next[/yellow]              Let the next round play out naturally
[yellow]/next[/yellow] <N>           Run N rounds without intervention
[yellow]/who[/yellow]               Show all council members and their current stance
[yellow]/history[/yellow]           Show recent transcript
[yellow]/synthesis[/yellow]         Ask Kevin to synthesize the discussion so far
[yellow]/mode[/yellow]              Show current mode and list available modes
[yellow]/mode[/yellow] <name>       Switch discussion mode (e.g. /mode oxford_debate)
[yellow]/vote[/yellow]              Trigger a YES/NO vote using current mode rules
[yellow]/vote[/yellow] <question>   Trigger a custom vote on a specific question
[yellow]/end[/yellow]               End the session and save transcript
[yellow]/help[/yellow]              Show this help
"""


class KZeroConsole:
    """Interactive god-mode console for the Council of 8."""

    def __init__(self, council_dir, scenario_path=None):
        self.council_dir = Path(council_dir)
        self.console = Console(width=110)

        load_dotenv(self.council_dir / ".env")

        # Load config
        config_path = self.council_dir / "config" / "simulation_config.json"
        self.config = json.loads(config_path.read_text(encoding="utf-8"))

        # Load scenario (optional — K-ZERO can run without one)
        if scenario_path:
            self.scenario = json.loads(Path(scenario_path).read_text(encoding="utf-8"))
        else:
            self.scenario = {
                "id": "demiurge_session",
                "title": "K-ZERO Free Session",
                "opening_prompt": "The K-ZERO has summoned the Council. Await the first question.",
            }

        # Load agents
        self.client = _create_client()
        self.agents = load_agents(self.council_dir, self.client)

        # Activity configs for speaker selection
        self.activity_configs = {}
        for ac in self.config.get("agent_activity_configs", []):
            self.activity_configs[ac["entity_name"]] = ac

        # Load discussion mode
        mode_name = self.scenario.get("mode", "philosophical_seminar")
        self.mode = get_mode(mode_name, scenario=self.scenario)

        # State
        self.transcript = []
        self.round_num = 0
        self.running = True

    def _resolve_agent_name(self, short):
        """Resolve a short name like 'feynman' to full agent name."""
        short = short.lower().strip()
        for full_name, sname in AGENT_SHORT.items():
            if sname == short or short in full_name.lower():
                return full_name
        return None

    def _select_speakers(self, count=2, exclude=None):
        """Select speakers based on activity weights."""
        candidates = []
        for name in self.agents:
            if exclude and name == exclude:
                continue
            ac = self.activity_configs.get(name, {})
            weight = ac.get("activity_level", 0.5)
            candidates.append((name, weight))

        if not candidates:
            return list(self.agents.keys())[:count]

        names = [n for n, _ in candidates]
        weights = [w for _, w in candidates]
        selected = []
        for _ in range(min(count, len(names))):
            picks = random.choices(names, weights=weights, k=1)
            pick = picks[0]
            selected.append(pick)
            idx = names.index(pick)
            names.pop(idx)
            weights.pop(idx)
            if not names:
                break
        return selected

    def _print_agent(self, name, text):
        """Print an agent's message."""
        color = AGENT_COLORS.get(name, "white")
        short = AGENT_SHORT.get(name, name).upper()
        self.console.print()
        self.console.print(Panel(
            Text(text, style=color),
            title=f"[bold {color}]{short}[/bold {color}]",
            title_align="left",
            border_style=color,
            padding=(0, 1),
        ))

    def _print_demiurge(self, text):
        """Print a K-ZERO injection."""
        self.console.print()
        self.console.print(Panel(
            Text(text, style="bright_red bold"),
            title="[bold bright_red]K-ZERO[/bold bright_red]",
            title_align="left",
            border_style="bright_red",
            padding=(0, 1),
        ))

    def _print_system(self, text):
        """Print a system message."""
        self.console.print(f"[dim]{text}[/dim]")

    def _add_transcript(self, speaker, text, msg_type="agent"):
        """Add entry to transcript."""
        self.transcript.append({
            "speaker": speaker if msg_type == "agent" else f"[{msg_type.upper()}]",
            "text": text,
            "round": self.round_num,
            "timestamp": datetime.now().isoformat(),
            "type": msg_type,
        })

    def _agent_respond(self, name, topic=""):
        """Have a specific agent respond."""
        agent = self.agents.get(name)
        if not agent:
            self._print_system(f"Agent '{name}' not found.")
            return

        try:
            response = agent.respond(self.transcript, current_topic=topic)
            self._print_agent(name, response)
            self._add_transcript(name, response)
        except Exception as e:
            self._print_system(f"[Error from {name}: {e}]")

    def _run_round(self, topic="", speakers_per_round=2):
        """Run one round of natural discussion."""
        self.round_num += 1
        self.console.print()
        self.console.rule(f"[dim]Round {self.round_num}[/dim]", style="dim")

        speakers = self._select_speakers(count=speakers_per_round)
        for name in speakers:
            self._agent_respond(name, topic=topic)
            time.sleep(0.5)  # Brief pause between speakers

    def _cmd_inject(self, text):
        """Inject a god-mode variable."""
        self._print_demiurge(text)
        self._add_transcript("K-ZERO", text, "god_mode")

        # All agents react (pick 3-4 respondents)
        respondents = self._select_speakers(count=3)
        self.round_num += 1
        self.console.rule(f"[dim]Round {self.round_num} (reactions to K-ZERO)[/dim]", style="dim")
        for name in respondents:
            self._agent_respond(name, topic=text)
            time.sleep(0.5)

    def _cmd_ask(self, agent_short, question):
        """Ask a specific agent a question."""
        name = self._resolve_agent_name(agent_short)
        if not name:
            self._print_system(f"Unknown agent: '{agent_short}'. Use /who to see the roster.")
            return

        self._print_demiurge(f"(to {name}) {question}")
        self._add_transcript("K-ZERO", f"(to {name}) {question}", "god_mode")
        self.round_num += 1
        self._agent_respond(name, topic=question)

    def _cmd_all(self, question):
        """Pose a question to all agents."""
        self._print_demiurge(question)
        self._add_transcript("K-ZERO", question, "god_mode")

        self.round_num += 1
        self.console.rule(f"[dim]Round {self.round_num} (all respond)[/dim]", style="dim")

        # All 8 agents respond in random order
        order = list(self.agents.keys())
        random.shuffle(order)
        for name in order:
            self._agent_respond(name, topic=question)
            time.sleep(0.5)

    def _cmd_who(self):
        """Show all council members."""
        self.console.print()
        for name, agent in self.agents.items():
            color = AGENT_COLORS.get(name, "white")
            short = AGENT_SHORT.get(name, "?")
            role = agent.personality.get("role", "")
            self.console.print(f"  [{color}]{short:10}[/{color}] {name} -- {role}")

    def _cmd_history(self, count=10):
        """Show recent transcript."""
        recent = self.transcript[-count:]
        self.console.print()
        for entry in recent:
            speaker = entry["speaker"]
            text = entry["text"][:150] + ("..." if len(entry["text"]) > 150 else "")
            rnd = entry.get("round", "?")
            self.console.print(f"  [dim]R{rnd}[/dim] [bold]{speaker}:[/bold] {text}")

    def _cmd_synthesis(self):
        """Ask Kevin to synthesize."""
        kevin = self.agents.get("Kevin (\uae40\uacbd\uc120)")
        if not kevin:
            self._print_system("Kevin not found in agents.")
            return

        self._print_system("Kevin is synthesizing...")
        prompt = (
            "The K-ZERO asks you to synthesize the discussion so far. "
            "What patterns do you see? Where is agreement? Where is tension? "
            "What has emerged that wasn't there at the start? Be concise."
        )
        try:
            response = kevin.respond(self.transcript, current_topic=prompt, max_tokens=800)
            self._print_agent("Kevin (\uae40\uacbd\uc120)", response)
            self._add_transcript("Kevin (\uae40\uacbd\uc120)", response)
        except Exception as e:
            self._print_system(f"[Synthesis error: {e}]")

    def _cmd_mode(self, mode_name=None):
        """Show current mode or switch to a new one."""
        if not mode_name:
            # Show current mode and list all
            self.console.print()
            self.console.print(
                f"[bold]Current mode:[/bold] {self.mode.emoji} {self.mode.name} "
                f"([yellow]{self.mode.mode_name}[/yellow])"
            )
            self.console.print(f"[dim]{self.mode.description}[/dim]")
            self.console.print()
            self.console.print(list_modes())
        else:
            # Switch mode
            try:
                new_mode = get_mode(mode_name, scenario=self.scenario)
                self.mode = new_mode
                self.console.print()
                self.console.print(
                    f"[bold green]Mode switched to:[/bold green] {new_mode.emoji} "
                    f"{new_mode.name} ([yellow]{new_mode.mode_name}[/yellow])"
                )
                self.console.print(f"[dim]{new_mode.description}[/dim]")
                self.console.print()
                instruction = new_mode.get_system_instruction("", phase=None)
                if instruction:
                    self.console.print(f"[dim italic]System instruction: {instruction}[/dim italic]")
                self._add_transcript(
                    "K-ZERO",
                    f"Mode switched to {new_mode.emoji} {new_mode.name}",
                    "god_mode",
                )
            except ValueError as e:
                self._print_system(str(e))

    def _cmd_vote(self, question=None):
        """Trigger a vote. Uses current mode rules or defaults to YES/NO."""
        if not question:
            question = self.scenario.get("title", "The question at hand")

        self._print_demiurge(f"VOTE CALLED: {question}")
        self._add_transcript("K-ZERO", f"VOTE CALLED: {question}", "god_mode")

        model = os.getenv("COUNCIL_MODEL", "llama-3.3-70b-versatile")
        results = self.mode.run_vote(
            self.agents, self.transcript, question, self.client, model
        )

        # Display results
        self.console.print()
        lines = ["[bold]VOTE RESULTS[/bold]", ""]
        for choice, count in sorted(results["tally"].items(), key=lambda x: -x[1]):
            bar = "#" * count
            lines.append(f"  {choice:>10}: {bar} ({count})")
        lines.append(f"\n  [bold]WINNER: {results['winner']}[/bold]")
        lines.append("")
        for v in results["votes"]:
            color = AGENT_COLORS.get(v["agent"], "white")
            lines.append(f"  [{color}]{v['agent']}[/{color}]: {v['vote']}")

        self.console.print(Panel(
            "\n".join(lines),
            title="[bold bright_yellow]VOTE TALLY[/bold bright_yellow]",
            border_style="bright_yellow",
            padding=(0, 1),
        ))

        # Add to transcript
        tally_text = ", ".join(f"{k}: {v}" for k, v in results["tally"].items())
        self._add_transcript(
            "SYSTEM",
            f"Vote on '{question}' -- {tally_text} -- Winner: {results['winner']}",
            "system",
        )

    def _save_transcript(self):
        """Save transcript to files."""
        if not self.transcript:
            self._print_system("No transcript to save.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        scenario_id = self.scenario.get("id", "demiurge")
        out_dir = self.council_dir / "transcripts"
        out_dir.mkdir(exist_ok=True)

        # JSON
        json_path = out_dir / f"{scenario_id}_{timestamp}.json"
        json_path.write_text(
            json.dumps(self.transcript, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Markdown
        md_path = out_dir / f"{scenario_id}_{timestamp}.md"
        lines = [
            f"# Council of 8 -- K-ZERO Session",
            f"\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Rounds: {self.round_num}",
            f"Mode: Interactive (K-ZERO Console)",
            "\n---\n",
        ]
        for entry in self.transcript:
            speaker = entry["speaker"]
            text = entry["text"]
            rnd = entry.get("round", 0)
            mtype = entry.get("type", "agent")

            if mtype == "god_mode":
                lines.append(f"\n### K-ZERO (Round {rnd})\n\n> {text}\n")
            elif mtype == "moderator":
                lines.append(f"\n### [MODERATOR] (Round {rnd})\n\n{text}\n")
            else:
                lines.append(f"\n### {speaker} (Round {rnd})\n\n{text}\n")

        md_path.write_text("\n".join(lines), encoding="utf-8")
        self._print_system(f"Transcript saved: {json_path.name}")

    def run(self):
        """Main interactive loop."""
        # Banner
        self.console.print()
        self.console.print(Panel(
            "[bold bright_red]K - Z E R O   C O N S O L E[/bold bright_red]\n\n"
            "[dim]You are K-ZERO -- the god-position that starts from nothing and asks everything.\n"
            "8 minds. 1 question. Infinite consequences.\n\n"
            "Pose questions, inject chaos, interrogate minds, watch them collide.\n\n"
            "Type [yellow]/help[/yellow] for commands. Or just type -- your words reshape the world.[/dim]",
            border_style="bright_red",
            padding=(1, 2),
        ))
        self.console.print()

        # Show scenario and mode
        title = self.scenario.get("title", "Free Session")
        self.console.print(f"[bold]Scenario:[/bold] {title}")
        self.console.print(
            f"[bold]Mode:[/bold] {self.mode.emoji} {self.mode.name} "
            f"([yellow]{self.mode.mode_name}[/yellow])"
        )

        # Opening prompt
        opening = self.scenario.get("opening_prompt", "The Council awaits your first question.")
        self._print_system(f"Opening: {opening}")
        self._add_transcript("K-ZERO", opening, "god_mode")

        # Show roster
        self._cmd_who()
        self.console.print()
        self.console.print("[dim]The Council awaits. Type your first question or /help.[/dim]")

        # REPL
        while self.running:
            try:
                self.console.print()
                user_input = Prompt.ask("[bold bright_red]K-ZERO[/bold bright_red]")

                if not user_input.strip():
                    continue

                cmd = user_input.strip()

                # Parse commands
                if cmd.lower() == "/help":
                    self.console.print(HELP_TEXT)

                elif cmd.lower() == "/end":
                    self._cmd_synthesis()
                    self._save_transcript()
                    self.running = False
                    self.console.print()
                    self.console.rule("[bold]SESSION ENDED[/bold]", style="bright_red")

                elif cmd.lower() == "/who":
                    self._cmd_who()

                elif cmd.lower().startswith("/history"):
                    count = 10
                    parts = cmd.split()
                    if len(parts) > 1:
                        try:
                            count = int(parts[1])
                        except ValueError:
                            pass
                    self._cmd_history(count)

                elif cmd.lower() == "/synthesis":
                    self._cmd_synthesis()

                elif cmd.lower().startswith("/next"):
                    parts = cmd.split()
                    rounds = 1
                    if len(parts) > 1:
                        try:
                            rounds = int(parts[1])
                        except ValueError:
                            pass
                    for _ in range(rounds):
                        self._run_round()

                elif cmd.lower().startswith("/ask "):
                    parts = cmd[5:].strip().split(maxsplit=1)
                    if len(parts) < 2:
                        self._print_system("Usage: /ask <agent> <question>")
                    else:
                        self._cmd_ask(parts[0], parts[1])

                elif cmd.lower().startswith("/all "):
                    question = cmd[5:].strip()
                    if question:
                        self._cmd_all(question)
                    else:
                        self._print_system("Usage: /all <question>")

                elif cmd.lower().startswith("/mode"):
                    parts = cmd.split(maxsplit=1)
                    if len(parts) > 1:
                        self._cmd_mode(parts[1].strip())
                    else:
                        self._cmd_mode()

                elif cmd.lower().startswith("/vote"):
                    parts = cmd.split(maxsplit=1)
                    if len(parts) > 1:
                        self._cmd_vote(parts[1].strip())
                    else:
                        self._cmd_vote()

                elif cmd.lower().startswith("/inject "):
                    text = cmd[8:].strip()
                    if text:
                        self._cmd_inject(text)
                    else:
                        self._print_system("Usage: /inject <text>")

                else:
                    # Natural language — treat as a god-mode injection
                    self._cmd_inject(cmd)

            except KeyboardInterrupt:
                self.console.print("\n[dim]Use /end to save and exit.[/dim]")
            except EOFError:
                self._save_transcript()
                self.running = False


def main():
    """CLI entry point."""
    council_dir = Path(__file__).parent.parent
    scenario_path = None

    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--scenario" and i + 1 < len(args):
            scenario_path = args[i + 1]

    console = KZeroConsole(council_dir, scenario_path)
    console.run()


if __name__ == "__main__":
    main()
