"""Council Runner — main simulation loop for the Council of 8."""

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
from rich.text import Text

from runner.agent import CouncilAgent, load_agents, _create_client
from runner.modes import DiscussionMode, get_mode

# Agent colors for console output
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

AGENT_LABELS = {
    "Elon Musk": "🔴 MUSK",
    "Richard Feynman": "🔵 FEYNMAN",
    "Kobe Bryant": "🟡 KOBE",
    "Steve Jobs": "⚪ JOBS",
    "Jean-Paul Sartre": "🟣 SARTRE",
    "George Carlin": "🟢 CARLIN",
    "Bryan Johnson": "🔷 JOHNSON",
    "Kevin (김경선)": "⬜ KEVIN [MOD]",
}


class CouncilRunner:
    """Orchestrates the Council of 8 deliberation."""

    def __init__(self, council_dir, scenario_path=None):
        self.council_dir = Path(council_dir)
        self.console = Console(width=100)

        # Load environment
        load_dotenv(self.council_dir / ".env")

        # Load simulation config
        config_path = self.council_dir / "config" / "simulation_config.json"
        self.config = json.loads(config_path.read_text(encoding="utf-8"))

        # Load scenario
        if scenario_path:
            self.scenario = json.loads(Path(scenario_path).read_text(encoding="utf-8"))
        else:
            # Default to scenario 01
            self.scenario = json.loads(
                (self.council_dir / "scenarios" / "scenario_01_meaning_of_life.json").read_text(encoding="utf-8")
            )

        # Load agents
        self.client = _create_client()
        self.agents = load_agents(self.council_dir, self.client)

        # Load activity configs for speaker selection
        self.activity_configs = {}
        for ac in self.config.get("agent_activity_configs", []):
            self.activity_configs[ac["entity_name"]] = ac

        # Load discussion mode
        mode_name = self.scenario.get("mode", "philosophical_seminar")
        self.mode = get_mode(mode_name, scenario=self.scenario)

        # State
        self.transcript = []
        self.round_num = 0

    def _select_next_speakers(self, last_speaker=None, count=2):
        """
        Select next speakers based on activity_level and cooldown.
        Returns list of agent names.
        """
        candidates = []
        for name, agent in self.agents.items():
            if name == last_speaker:
                continue  # Cooldown: don't speak twice in a row
            ac = self.activity_configs.get(name, {})
            weight = ac.get("activity_level", 0.5)

            # Boost agents with high aggression if last message was provocative
            if self.transcript and ac.get("aggression", 0.5) > 0.6:
                weight *= 1.3

            candidates.append((name, weight))

        # Weighted random selection using random.choices
        if not candidates:
            return list(self.agents.keys())[:count]

        names = [n for n, _ in candidates]
        weights = [w for _, w in candidates]
        # Use sample-without-replacement via iterative choices
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

    def _print_message(self, speaker, text, msg_type="agent"):
        """Print a formatted message to console."""
        if msg_type == "moderator":
            label = "⬜ KEVIN [MODERATOR]"
            color = "bright_white"
            border = "bright_white"
        elif msg_type == "god_mode":
            label = "⚡ GOD-MODE INJECTION"
            color = "bright_red"
            border = "bright_red"
        elif msg_type == "system":
            label = "📋 SYSTEM"
            color = "dim"
            border = "dim"
        else:
            label = AGENT_LABELS.get(speaker, speaker)
            color = AGENT_COLORS.get(speaker, "white")
            border = color

        self.console.print()
        self.console.print(
            Panel(
                Text(text, style=color),
                title=f"[bold]{label}[/bold]",
                title_align="left",
                border_style=border,
                padding=(0, 1),
            )
        )

    def _add_to_transcript(self, speaker, text, msg_type="agent"):
        """Add a message to the transcript."""
        entry = {
            "speaker": speaker if msg_type == "agent" else f"[{msg_type.upper()}]",
            "text": text,
            "round": self.round_num,
            "timestamp": datetime.now().isoformat(),
            "type": msg_type,
        }
        self.transcript.append(entry)
        return entry

    def _should_inject_moderator(self):
        """Check if moderator should inject a prompt."""
        prompts = self.scenario.get("moderator_prompts", [])
        if not prompts:
            return None

        # Inject moderator prompts at regular intervals
        total_rounds = self.config["simulation"]["max_rounds"]
        interval = max(1, total_rounds // (len(prompts) + 1))

        prompt_index = (self.round_num // interval) - 1
        if self.round_num % interval == 0 and 0 <= prompt_index < len(prompts):
            return prompts[prompt_index]
        return None

    def _should_inject_god_mode(self, total_rounds):
        """Check if god-mode stressor should fire."""
        god_mode = self.scenario.get("god_mode_injection", {})
        mid_point = total_rounds // 2
        late_point = int(total_rounds * 0.8)

        if self.round_num == mid_point and "mid_discussion" in god_mode:
            return god_mode["mid_discussion"]
        if self.round_num == late_point and "late_discussion" in god_mode:
            return god_mode["late_discussion"]
        return None

    def run(self, max_rounds=None, speakers_per_round=2):
        """
        Run the full deliberation.

        Args:
            max_rounds: Override max rounds (default from config)
            speakers_per_round: How many agents speak per round
        """
        max_rounds = max_rounds or self.config["simulation"]["max_rounds"]
        mode = self.mode

        # Header
        self.console.print()
        self.console.rule(f"[bold]THE COUNCIL OF 8[/bold]", style="bright_white")
        self.console.print(f"[dim]Scenario: {self.scenario.get('title', 'Unknown')}[/dim]")
        self.console.print(f"[dim]Mode: {mode.emoji} {mode.name} ({mode.mode_name})[/dim]")
        self.console.print(f"[dim]Rounds: {max_rounds} | Speakers/round: {speakers_per_round}[/dim]")
        self.console.print(f"[dim]Model: {os.getenv('COUNCIL_MODEL', 'llama-3.3-70b-versatile')}[/dim]")
        self.console.rule(style="dim")

        # Opening prompt from moderator (Kevin)
        opening = self.scenario.get("opening_prompt", "The floor is open.")
        self._print_message("Kevin (김경선)", opening, "moderator")
        self._add_to_transcript("Kevin (김경선)", opening, "moderator")

        last_speaker = None

        for self.round_num in range(1, max_rounds + 1):
            # Check mode-level termination
            if mode.should_terminate(self.round_num, self.transcript, self.agents):
                self._print_message("", "Mode termination condition reached.", "system")
                break

            # Determine brainstorm phase if applicable
            phase = None
            if mode.mode_name == "brainstorm":
                phase = mode.get_phase(self.round_num, max_rounds)

            self.console.print()
            phase_label = f" [{phase.upper()}]" if phase else ""
            self.console.rule(
                f"[dim]Round {self.round_num}/{max_rounds}{phase_label}[/dim]",
                style="dim",
            )

            # Check for moderator injection
            mod_prompt = self._should_inject_moderator()
            if mod_prompt:
                self._print_message("Kevin (김경선)", mod_prompt, "moderator")
                self._add_to_transcript("Kevin (김경선)", mod_prompt, "moderator")

            # Check for god-mode injection
            god_prompt = self._should_inject_god_mode(max_rounds)
            if god_prompt:
                self._print_message("", god_prompt, "god_mode")
                self._add_to_transcript("GOD-MODE", god_prompt, "god_mode")

            # Select speakers using mode engine
            speakers = mode.select_speakers(
                self.agents, self.round_num, last_speaker, self.activity_configs
            )

            for speaker_name in speakers:
                agent = self.agents.get(speaker_name)
                if not agent:
                    continue

                # Build mode-specific system instruction for this agent
                side = mode.get_agent_side(speaker_name, self.agents)
                mode_instruction = mode.get_system_instruction(
                    speaker_name, side=side, phase=phase
                )

                # Get current topic context
                current_topic = ""
                if mod_prompt:
                    current_topic = mod_prompt
                elif god_prompt:
                    current_topic = god_prompt

                # Append mode instruction to the topic context
                if mode_instruction:
                    current_topic = f"{current_topic}\n\n[MODE: {mode.name}] {mode_instruction}" if current_topic else f"[MODE: {mode.name}] {mode_instruction}"

                # For delphi mode, build anonymous transcript
                transcript_for_agent = self.transcript
                if mode.mode_name == "delphi_method":
                    transcript_for_agent = self._anonymize_transcript(self.transcript)

                try:
                    response = agent.respond(
                        transcript_for_agent,
                        current_topic=current_topic,
                    )
                    self._print_message(speaker_name, response)
                    self._add_to_transcript(speaker_name, response)
                    last_speaker = speaker_name
                except Exception as e:
                    self._print_message(speaker_name, f"[Error: {e}]", "system")

        # Voting phase (if mode requires it)
        if mode.requires_voting():
            self.console.print()
            self.console.rule("[bold]VOTING[/bold]", style="bright_yellow")
            question = self.scenario.get("title", "The question at hand")
            model = os.getenv("COUNCIL_MODEL", "llama-3.3-70b-versatile")
            results = mode.run_vote(
                self.agents, self.transcript, question, self.client, model
            )
            self._display_vote_results(results)

        # Closing synthesis by Kevin
        self.console.print()
        self.console.rule("[bold]SYNTHESIS[/bold]", style="bright_white")

        kevin = self.agents.get("Kevin (김경선)")
        if kevin:
            synthesis_prompt = (
                "The deliberation is ending. As the moderator, deliver a final synthesis: "
                "What did the council agree on? Where did they disagree? "
                "What emerged that no single member would have said alone? "
                "Keep it concise — 3-4 paragraphs maximum."
            )
            try:
                synthesis = kevin.respond(
                    self.transcript,
                    current_topic=synthesis_prompt,
                    max_tokens=800,
                )
                self._print_message("Kevin (김경선)", synthesis, "moderator")
                self._add_to_transcript("Kevin (김경선)", synthesis, "moderator")
            except Exception as e:
                self._print_message("Kevin (김경선)", f"[Synthesis error: {e}]", "system")

        # Save transcript
        self._save_transcript()

        self.console.print()
        self.console.rule("[bold]SESSION COMPLETE[/bold]", style="bright_white")

    def _anonymize_transcript(self, transcript):
        """Create an anonymized version of the transcript for Delphi mode."""
        anonymized = []
        for entry in transcript:
            anon_entry = dict(entry)
            if entry.get("type") == "agent":
                anon_entry["speaker"] = f"Anonymous-{hash(entry['speaker']) % 1000:03d}"
            anonymized.append(anon_entry)
        return anonymized

    def _display_vote_results(self, results):
        """Display voting results in a formatted panel."""
        lines = []
        lines.append("VOTE TALLY:")
        for choice, count in sorted(results["tally"].items(), key=lambda x: -x[1]):
            bar = "#" * count
            lines.append(f"  {choice:>10}: {bar} ({count})")
        lines.append(f"\nWINNER: {results['winner']}")
        lines.append("\nIndividual votes:")
        for v in results["votes"]:
            lines.append(f"  {v['agent']}: {v['vote']}")

        self._print_message("", "\n".join(lines), "system")

    def _save_transcript(self):
        """Save transcript as markdown and JSON."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        scenario_id = self.scenario.get("id", "unknown")
        transcripts_dir = self.council_dir / "transcripts"
        transcripts_dir.mkdir(exist_ok=True)

        # Markdown transcript
        md_path = transcripts_dir / f"{scenario_id}_{timestamp}.md"
        lines = [
            f"# Council of 8 — {self.scenario.get('title', 'Deliberation')}",
            f"\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Rounds: {self.round_num}",
            f"Model: {os.getenv('COUNCIL_MODEL', 'llama-3.3-70b-versatile')}",
            "\n---\n",
        ]

        for entry in self.transcript:
            speaker = entry["speaker"]
            text = entry["text"]
            msg_type = entry.get("type", "agent")
            round_num = entry.get("round", 0)

            if msg_type == "moderator":
                lines.append(f"\n### [MODERATOR — Kevin Kim] (Round {round_num})\n\n{text}\n")
            elif msg_type == "god_mode":
                lines.append(f"\n### ⚡ GOD-MODE INJECTION (Round {round_num})\n\n> {text}\n")
            else:
                lines.append(f"\n### {speaker} (Round {round_num})\n\n{text}\n")

        md_path.write_text("\n".join(lines), encoding="utf-8")

        # JSON transcript
        json_path = transcripts_dir / f"{scenario_id}_{timestamp}.json"
        json_path.write_text(
            json.dumps(self.transcript, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        self.console.print(f"\n[dim]Transcript saved: {md_path.name}[/dim]")


def main():
    """CLI entry point."""
    council_dir = Path(__file__).parent.parent
    scenario_path = None
    max_rounds = 5  # Default to 5 for testing

    # Parse CLI args
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--scenario" and i + 1 < len(args):
            scenario_path = args[i + 1]
        elif arg == "--rounds" and i + 1 < len(args):
            max_rounds = int(args[i + 1])

    runner = CouncilRunner(council_dir, scenario_path)
    runner.run(max_rounds=max_rounds)


if __name__ == "__main__":
    main()
