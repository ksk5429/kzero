"""Discussion Mode Engine for the Council of 8.

Loads mode configurations from discussion_modes.json and provides
mode-aware speaker selection, termination checks, voting, and phasing.
"""

import json
import os
import random
import re
from pathlib import Path
from typing import Any


CONFIG_PATH = Path(__file__).parent.parent / "config" / "discussion_modes.json"


def _load_modes_config() -> dict:
    """Load the discussion_modes.json configuration file."""
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


class DiscussionMode:
    """Wraps a single discussion mode configuration and exposes mode-aware methods."""

    def __init__(self, mode_name: str, mode_config: dict, scenario: dict | None = None):
        self.mode_name = mode_name
        self.config = mode_config
        self.scenario = scenario or {}

        self.name = mode_config.get("name", mode_name)
        self.emoji = mode_config.get("emoji", "")
        self.description = mode_config.get("description", "")
        self.objective = mode_config.get("objective", "exploratory")
        self.termination = mode_config.get("termination", {})
        self.interaction = mode_config.get("interaction", {})
        self.scoring = mode_config.get("scoring", {})

    # ------------------------------------------------------------------
    # System instructions
    # ------------------------------------------------------------------

    def get_system_instruction(
        self,
        agent_name: str,
        side: str | None = None,
        phase: str | None = None,
    ) -> str:
        """Return the mode-specific system instruction with template variables filled in.

        Args:
            agent_name: Full agent name (e.g. "Elon Musk").
            side: "for" or "against" (adversarial modes).
            phase: "diverge" or "converge" (brainstorm mode).

        Returns:
            The formatted instruction string.
        """
        # Brainstorm has phase-specific instructions
        if self.mode_name == "brainstorm" and phase:
            key = f"system_instruction_{phase}"
            instruction = self.config.get(key, "")
            if instruction:
                return instruction

        # Socratic has role-specific instructions
        if self.mode_name == "socratic_dialogue":
            questioner = self.interaction.get("questioner", "moderator")
            current_subject = self.interaction.get("current_subject")
            if agent_name == current_subject or (
                questioner != "moderator" and agent_name == questioner
            ):
                if agent_name == questioner or (
                    questioner == "moderator" and "kevin" in agent_name.lower()
                ):
                    return self.config.get("system_instruction_questioner", "")
                return self.config.get("system_instruction_subject", "")
            # For the questioner (Kevin/moderator)
            if "kevin" in agent_name.lower() or agent_name.lower() == questioner.lower():
                return self.config.get("system_instruction_questioner", "")
            return self.config.get("system_instruction_subject", "")

        # Delphi has round-specific instructions
        if self.mode_name == "delphi_method":
            key_round1 = "system_instruction_round1"
            key_revision = "system_instruction_revision"
            # Default to round1; revision is set dynamically by the runner
            return self.config.get(key_round1, "")

        # Standard single instruction
        instruction = self.config.get("system_instruction", "")

        # Fill template variables
        if side:
            side_label = "FOR the proposition" if side == "for" else "AGAINST the proposition"
            instruction = instruction.replace("{side}", side_label)

        # Multiple choice options
        options = self.termination.get("options", [])
        if options and "{options}" in instruction:
            formatted = "\n".join(
                f"  {chr(65 + i)}. {opt}" for i, opt in enumerate(options)
            )
            instruction = instruction.replace("{options}", formatted)

        return instruction

    # ------------------------------------------------------------------
    # Speaker selection
    # ------------------------------------------------------------------

    def select_speakers(
        self,
        agents: dict,
        round_num: int,
        last_speaker: str | None,
        activity_configs: dict,
    ) -> list[str]:
        """Select speakers for this round based on the interaction type.

        Args:
            agents: Dict of agent_name -> CouncilAgent.
            round_num: Current round number (1-based).
            last_speaker: Name of the last agent who spoke, or None.
            activity_configs: Dict of agent_name -> activity config dict.

        Returns:
            List of agent names to speak this round.
        """
        interaction_type = self.interaction.get("type", "free_for_all")
        speakers_per_round = self.interaction.get("speakers_per_round", 2)

        if interaction_type == "free_for_all":
            return self._select_weighted_random(
                agents, last_speaker, activity_configs, speakers_per_round
            )

        if interaction_type == "structured_turns":
            return self._select_round_robin(agents, round_num, speakers_per_round)

        if interaction_type == "adversarial_pairs":
            return self._select_adversarial(agents, round_num, speakers_per_round)

        if interaction_type == "devils_advocate":
            return self._select_devils_advocate(
                agents, activity_configs, speakers_per_round
            )

        if interaction_type == "socratic":
            return self._select_socratic(agents)

        if interaction_type == "delphi":
            # All agents speak each round
            return list(agents.keys())

        # Fallback
        return self._select_weighted_random(
            agents, last_speaker, activity_configs, speakers_per_round
        )

    def _select_weighted_random(
        self,
        agents: dict,
        last_speaker: str | None,
        activity_configs: dict,
        count: int,
    ) -> list[str]:
        """Weighted random selection (existing behavior)."""
        candidates = []
        for name in agents:
            if name == last_speaker:
                continue
            ac = activity_configs.get(name, {})
            weight = ac.get("activity_level", 0.5)
            if ac.get("aggression", 0.5) > 0.6:
                weight *= 1.3
            candidates.append((name, weight))

        if not candidates:
            return list(agents.keys())[:count]

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

    def _select_round_robin(
        self, agents: dict, round_num: int, count: int
    ) -> list[str]:
        """Round-robin speaker selection."""
        agent_list = list(agents.keys())
        total = len(agent_list)
        if total == 0:
            return []
        start = ((round_num - 1) * count) % total
        selected = []
        for i in range(count):
            idx = (start + i) % total
            selected.append(agent_list[idx])
        return selected

    def _select_adversarial(
        self, agents: dict, round_num: int, count: int
    ) -> list[str]:
        """Alternate between team_for and team_against."""
        team_for = self._resolve_team("team_for", agents)
        team_against = self._resolve_team("team_against", agents)

        if not team_for and not team_against:
            # Fallback: split agents in half
            all_names = list(agents.keys())
            mid = len(all_names) // 2
            team_for = all_names[:mid]
            team_against = all_names[mid:]

        half = max(1, count // 2)
        selected = []

        # Alternate starting team each round
        if round_num % 2 == 1:
            first_team, second_team = team_for, team_against
        else:
            first_team, second_team = team_against, team_for

        if first_team:
            idx = ((round_num - 1) // 2) % len(first_team)
            selected.append(first_team[idx % len(first_team)])
        if second_team:
            idx = ((round_num - 1) // 2) % len(second_team)
            selected.append(second_team[idx % len(second_team)])

        return selected[:count]

    def _select_devils_advocate(
        self, agents: dict, activity_configs: dict, count: int
    ) -> list[str]:
        """Always include the devil's advocate plus 1-2 others."""
        da_name = self.interaction.get("devils_advocate_agent")

        # Resolve devil's advocate by name fragment
        if da_name:
            da_name = self._resolve_agent_name(da_name, agents)

        # If no devil's advocate set, pick the agent with highest aggression
        if not da_name:
            best = None
            best_aggression = -1
            for name in agents:
                ac = activity_configs.get(name, {})
                agg = ac.get("aggression", 0.5)
                if agg > best_aggression:
                    best_aggression = agg
                    best = name
            da_name = best

        selected = [da_name] if da_name else []
        others = [n for n in agents if n != da_name]
        remaining = count - len(selected)
        if remaining > 0 and others:
            selected.extend(random.sample(others, min(remaining, len(others))))

        return selected

    def _select_socratic(self, agents: dict) -> list[str]:
        """Questioner + current subject only."""
        questioner = self.interaction.get("questioner", "moderator")
        subject = self.interaction.get("current_subject")

        selected = []

        # Resolve questioner
        if questioner == "moderator":
            for name in agents:
                if "kevin" in name.lower():
                    selected.append(name)
                    break
        else:
            resolved = self._resolve_agent_name(questioner, agents)
            if resolved:
                selected.append(resolved)

        # Resolve subject
        if subject:
            resolved = self._resolve_agent_name(subject, agents)
            if resolved and resolved not in selected:
                selected.append(resolved)
        else:
            # Pick a random non-questioner agent
            others = [n for n in agents if n not in selected]
            if others:
                selected.append(random.choice(others))

        return selected

    def _resolve_agent_name(self, fragment: str, agents: dict) -> str | None:
        """Resolve a partial name to a full agent name."""
        fragment_lower = fragment.lower()
        for name in agents:
            if fragment_lower in name.lower():
                return name
        return None

    def _resolve_team(self, team_key: str, agents: dict) -> list[str]:
        """Resolve a team list from scenario or mode config."""
        # Check scenario first (scenario overrides mode defaults)
        team = self.scenario.get(team_key, [])
        if not team:
            team = self.interaction.get(team_key, [])

        resolved = []
        for fragment in team:
            name = self._resolve_agent_name(fragment, agents)
            if name:
                resolved.append(name)
        return resolved

    # ------------------------------------------------------------------
    # Termination
    # ------------------------------------------------------------------

    def should_terminate(
        self,
        round_num: int,
        transcript: list[dict],
        agents: dict,
    ) -> bool:
        """Check if the deliberation should end based on termination rules.

        Args:
            round_num: Current round number.
            transcript: Full transcript list.
            agents: Dict of agents.

        Returns:
            True if the deliberation should end.
        """
        term_type = self.termination.get("type", "open_synthesis")
        max_rounds = self.termination.get("max_rounds")

        if term_type == "open_synthesis":
            if max_rounds and round_num >= max_rounds:
                return True
            return False

        if term_type in ("binary", "multiple_choice"):
            # These terminate after deliberation rounds, triggering a vote
            if self.termination.get("vote_after_rounds", False):
                # Let the main loop's max_rounds handle termination;
                # voting happens at the end
                return False
            if max_rounds and round_num >= max_rounds:
                return True
            return False

        if term_type == "threshold":
            if max_rounds and round_num >= max_rounds:
                return True
            # Check agreement percentage from recent transcript
            agreement_pct = self.termination.get("agreement_pct", 0.75)
            return self._check_agreement(transcript, agents, agreement_pct)

        return False

    def _check_agreement(
        self, transcript: list[dict], agents: dict, threshold: float
    ) -> bool:
        """Heuristic check for agreement in recent messages."""
        if len(transcript) < 4:
            return False

        recent = transcript[-len(agents):]
        agree_signals = ["agree", "exactly", "right", "yes", "concur", "same"]
        agree_count = 0
        for entry in recent:
            text_lower = entry.get("text", "").lower()
            if any(signal in text_lower for signal in agree_signals):
                agree_count += 1

        total = len(recent) if recent else 1
        return (agree_count / total) >= threshold

    # ------------------------------------------------------------------
    # Voting
    # ------------------------------------------------------------------

    def requires_voting(self) -> bool:
        """Check if this mode ends with a vote."""
        term_type = self.termination.get("type", "open_synthesis")
        return term_type in ("binary", "multiple_choice", "threshold")

    def run_vote(
        self,
        agents: dict,
        transcript: list[dict],
        question: str,
        client: Any,
        model: str,
    ) -> dict:
        """Ask each voting agent to cast a vote and tally results.

        Args:
            agents: Dict of agent_name -> CouncilAgent.
            transcript: Full transcript.
            question: The question to vote on.
            client: OpenAI-compatible client.
            model: Model name to use.

        Returns:
            Dict with keys: votes (list), tally (dict), winner (str), raw (list).
        """
        term_type = self.termination.get("type", "open_synthesis")
        voters = self.scoring.get("voters", "all")

        # Determine who votes
        if voters == "audience":
            audience = self._resolve_team("audience", agents)
            voter_names = audience if audience else list(agents.keys())
        else:
            voter_names = list(agents.keys())

        # Build voting prompt
        if term_type == "multiple_choice":
            options = self.termination.get("options", [])
            options_text = "\n".join(
                f"  {chr(65 + i)}. {opt}" for i, opt in enumerate(options)
            )
            vote_prompt = (
                f"VOTING TIME. Based on the deliberation on: \"{question}\"\n\n"
                f"Pick ONE of the following options:\n{options_text}\n\n"
                "Respond with ONLY the letter of your choice (A, B, C, etc.) "
                "and a one-sentence justification."
            )
        else:
            # Binary (yes/no)
            vote_prompt = (
                f"VOTING TIME. Based on the deliberation on: \"{question}\"\n\n"
                "Cast your vote: YES or NO.\n"
                "Respond with ONLY your vote (YES or NO) "
                "and a one-sentence justification."
            )

        # Collect votes
        votes = []
        raw_responses = []

        for name in voter_names:
            agent = agents.get(name)
            if not agent:
                continue

            # Build transcript context (last 10 messages)
            recent = transcript[-10:]
            transcript_text = "\n".join(
                f"{e['speaker']}: {e['text'][:200]}" for e in recent
            )

            messages = [
                {"role": "system", "content": f"You are {name}. Vote in character."},
                {"role": "user", "content": f"{transcript_text}\n\n{vote_prompt}"},
            ]

            for attempt in range(3):
                try:
                    response = client.chat.completions.create(
                        model=model,
                        max_tokens=100,
                        temperature=0.3,
                        messages=messages,
                    )
                    text = response.choices[0].message.content or ""
                    raw_responses.append({"agent": name, "response": text})
                    vote = self._parse_vote(text, term_type)
                    votes.append({"agent": name, "vote": vote, "justification": text})
                    break
                except Exception as e:
                    if attempt < 2 and ("rate" in str(e).lower() or "429" in str(e)):
                        from runner.agent import _rotate_client
                        client = _rotate_client()
                        import time; time.sleep(1)
                    else:
                        votes.append({"agent": name, "vote": "ERROR", "justification": str(e)})
                        raw_responses.append({"agent": name, "response": f"ERROR: {e}"})
                        break
            import time; time.sleep(0.5)  # Rate limit protection between votes

        # Tally
        tally = {}
        for v in votes:
            choice = v["vote"]
            tally[choice] = tally.get(choice, 0) + 1

        # Determine winner
        winner = max(tally, key=tally.get) if tally else "NO VOTES"

        return {
            "votes": votes,
            "tally": tally,
            "winner": winner,
            "raw": raw_responses,
        }

    def _parse_vote(self, text: str, term_type: str) -> str:
        """Parse a vote from agent response text."""
        text_upper = text.strip().upper()

        if term_type == "multiple_choice":
            # Look for a letter A-Z at the start or standalone
            match = re.search(r'\b([A-Z])\b', text_upper)
            if match:
                return match.group(1)
            return "ABSTAIN"

        # Binary: YES or NO
        if text_upper.startswith("YES") or "\nYES" in text_upper or "YES." in text_upper:
            return "YES"
        if text_upper.startswith("NO") or "\nNO" in text_upper or "NO." in text_upper:
            return "NO"

        # Looser match
        if "YES" in text_upper:
            return "YES"
        if "NO" in text_upper:
            return "NO"

        return "ABSTAIN"

    # ------------------------------------------------------------------
    # Phase (brainstorm mode)
    # ------------------------------------------------------------------

    def get_phase(self, round_num: int, max_rounds: int) -> str:
        """For brainstorm mode, returns 'diverge' or 'converge' based on progress.

        Args:
            round_num: Current round (1-based).
            max_rounds: Total rounds.

        Returns:
            'diverge' or 'converge'.
        """
        diverge_pct = self.termination.get("diverge_rounds_pct", 0.6)
        cutoff = int(max_rounds * diverge_pct)
        if round_num <= cutoff:
            return "diverge"
        return "converge"

    # ------------------------------------------------------------------
    # Team helpers
    # ------------------------------------------------------------------

    def get_agent_side(self, agent_name: str, agents: dict) -> str | None:
        """Determine which side an agent is on in adversarial mode.

        Returns 'for', 'against', 'audience', or None.
        """
        if self.interaction.get("type") != "adversarial_pairs":
            return None

        team_for = self._resolve_team("team_for", agents)
        team_against = self._resolve_team("team_against", agents)
        audience = self._resolve_team("audience", agents)

        if agent_name in team_for:
            return "for"
        if agent_name in team_against:
            return "against"
        if agent_name in audience:
            return "audience"
        return None

    def get_delphi_instruction(self, round_num: int, distribution: str = "", previous_answer: str = "") -> str:
        """Get the Delphi method instruction for a specific round.

        Args:
            round_num: Current round (1-based).
            distribution: Anonymized distribution text for revision rounds.
            previous_answer: This agent's previous answer.

        Returns:
            Formatted instruction string.
        """
        if round_num == 1:
            return self.config.get("system_instruction_round1", "")

        instruction = self.config.get("system_instruction_revision", "")
        instruction = instruction.replace("{distribution}", distribution)
        instruction = instruction.replace("{your_answer}", previous_answer)
        return instruction


def list_modes() -> str:
    """Return a formatted table of all available discussion modes."""
    data = _load_modes_config()
    modes = data.get("modes", {})

    lines = [
        "Available Discussion Modes:",
        "",
        f"  {'Name':<25} {'Emoji':<5} {'Objective':<15} {'Interaction':<20} {'Termination':<15}",
        f"  {'-'*25} {'-'*5} {'-'*15} {'-'*20} {'-'*15}",
    ]

    for key, cfg in modes.items():
        name = cfg.get("name", key)
        emoji = cfg.get("emoji", "")
        obj = cfg.get("objective", "")
        interaction = cfg.get("interaction", {}).get("type", "")
        termination = cfg.get("termination", {}).get("type", "")
        lines.append(f"  {name:<25} {emoji:<5} {obj:<15} {interaction:<20} {termination:<15}")

    lines.append("")
    for key, cfg in modes.items():
        lines.append(f"  {cfg.get('emoji', '')} {key}: {cfg.get('description', '')[:80]}")

    return "\n".join(lines)


def get_mode(mode_name: str, scenario: dict | None = None) -> DiscussionMode:
    """Load a specific discussion mode by name.

    Args:
        mode_name: Key from discussion_modes.json (e.g. 'oxford_debate').
        scenario: Optional scenario dict for team resolution.

    Returns:
        A DiscussionMode instance.

    Raises:
        ValueError: If the mode name is not found.
    """
    data = _load_modes_config()
    modes = data.get("modes", {})

    if mode_name not in modes:
        available = ", ".join(modes.keys())
        raise ValueError(f"Unknown mode '{mode_name}'. Available: {available}")

    return DiscussionMode(mode_name, modes[mode_name], scenario)


def get_all_mode_names() -> list[str]:
    """Return a list of all available mode names."""
    data = _load_modes_config()
    return list(data.get("modes", {}).keys())
