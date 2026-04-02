"""Post-simulation transcript analyzer for the Council of 8 deliberation system.

Reads a transcript JSON produced by the Council Runner and uses the same
OpenAI-compatible LLM API (Groq/Llama) to extract structured insights:
pairwise agreement, position tracking, emergent insights, topic clusters,
and key quotes.

Usage:
    python -m runner.analyze transcripts/meaning_of_life_20260402_160855.json
    python -m runner.analyze transcripts/meaning_of_life_20260402_160855.json --output my_analysis.json
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from runner.agent import _create_client

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

# Load .env from the project root (the_council/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

console = Console()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_json(text: str) -> dict | list:
    """Extract valid JSON from LLM output, stripping markdown fences if present.

    Tries, in order:
      1. Direct ``json.loads`` on the raw text.
      2. Strip ```json ... ``` fences and parse.
      3. Find the first ``{`` or ``[`` and parse from there.

    Raises ``ValueError`` if no valid JSON is found.
    """
    # 1) Try raw
    text_stripped = text.strip()
    try:
        return json.loads(text_stripped)
    except json.JSONDecodeError:
        pass

    # 2) Strip markdown fences
    fence_pattern = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)
    match = fence_pattern.search(text_stripped)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3) Find first { or [
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start_idx = text_stripped.find(start_char)
        if start_idx == -1:
            continue
        end_idx = text_stripped.rfind(end_char)
        if end_idx == -1 or end_idx <= start_idx:
            continue
        candidate = text_stripped[start_idx : end_idx + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    # 4) Try to repair truncated JSON by closing brackets
    for start_char in ["{", "["]:
        start_idx = text_stripped.find(start_char)
        if start_idx == -1:
            continue
        fragment = text_stripped[start_idx:]
        repaired = _repair_json(fragment)
        if repaired is not None:
            return repaired

    raise ValueError(f"Could not extract valid JSON from LLM output:\n{text_stripped[:500]}")


def _repair_json(fragment: str):
    """Attempt to repair truncated JSON by closing open brackets/braces."""
    # Remove any trailing partial key-value
    # Find last complete value (ends with , or } or ] or number or "true"/"false"/"null" or quoted string)
    lines = fragment.rstrip().rstrip(",").split("\n")
    # Try removing lines from the end until we get parseable JSON
    for trim in range(min(20, len(lines))):
        candidate = "\n".join(lines[:len(lines) - trim]).rstrip().rstrip(",")
        # Count open/close brackets
        open_braces = candidate.count("{") - candidate.count("}")
        open_brackets = candidate.count("[") - candidate.count("]")
        # Close them
        closing = "}" * open_braces + "]" * open_brackets
        try:
            return json.loads(candidate + closing)
        except json.JSONDecodeError:
            continue
    return None


def _llm_call(
    client: Any,
    model: str,
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    max_retries: int = 5,
) -> dict | list:
    """Make an LLM call with retries, key rotation, and exponential backoff.

    Returns parsed JSON from the response.
    """
    from runner.agent import _rotate_client
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            if not response.choices:
                raise RuntimeError("LLM returned no choices")
            raw_text = response.choices[0].message.content or ""
            return _extract_json(raw_text)
        except Exception as exc:
            err_msg = str(exc).lower()
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                console.print(
                    f"  [yellow]Attempt {attempt + 1} failed ({exc!s:.80}), "
                    f"retrying in {wait}s...[/yellow]"
                )
                # Rotate API key on rate limit or quota errors
                if "rate" in err_msg or "429" in err_msg or "quota" in err_msg:
                    client = _rotate_client()
                time.sleep(wait)
            else:
                raise


# ---------------------------------------------------------------------------
# Transcript helpers
# ---------------------------------------------------------------------------


def _format_transcript_for_prompt(transcript: list[dict]) -> str:
    """Convert transcript entries into a readable text block for the LLM."""
    lines: list[str] = []
    for entry in transcript:
        speaker = entry["speaker"]
        text = entry["text"]
        r = entry.get("round", "?")
        lines.append(f"[Round {r}] {speaker}: {text}")
    return "\n\n".join(lines)


def _get_agent_names(transcript: list[dict]) -> list[str]:
    """Return sorted list of unique agent speaker names (excluding moderator / god_mode)."""
    names: set[str] = set()
    for entry in transcript:
        if entry.get("type") == "agent":
            names.add(entry["speaker"])
    return sorted(names)


def _get_total_rounds(transcript: list[dict]) -> int:
    """Return the highest round number in the transcript."""
    return max((entry.get("round", 0) for entry in transcript), default=0)


# ---------------------------------------------------------------------------
# Analysis calls
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are an expert discourse analyst specializing in multi-party deliberations. "
    "You produce precise, structured JSON output. "
    "Return ONLY valid JSON. No markdown fences. No explanation text."
)


def _call_pairwise_and_positions(
    client: Any,
    model: str,
    transcript_text: str,
    agent_names: list[str],
) -> dict:
    """Call 1: Pairwise agreement matrix + position tracking."""
    names_str = ", ".join(agent_names)
    user_prompt = f"""Analyze the following multi-agent deliberation transcript.

AGENTS: {names_str}

TRANSCRIPT:
{transcript_text}

Produce a JSON object with exactly two keys:

1. "agreement_matrix": An object where each key is "SpeakerA -> SpeakerB" (for every ordered pair of agents). Each value is an object with:
   - "score": float from -1.0 (strong disagreement) to +1.0 (strong agreement)
   - "evidence": a short quote from the transcript supporting the score

2. "position_tracking": An object keyed by agent name. Each value has:
   - "initial_position": their stance in round 1 (1-2 sentences)
   - "final_position": their stance in the last round (1-2 sentences)
   - "shifted": boolean, true if their position meaningfully changed
   - "shift_description": if shifted, describe how (otherwise null)

Return ONLY valid JSON. No markdown fences. No explanation text."""

    return _llm_call(client, model, _SYSTEM_PROMPT, user_prompt, max_tokens=8192)


def _call_insights_and_clusters(
    client: Any,
    model: str,
    transcript_text: str,
    agent_names: list[str],
) -> dict:
    """Call 2: Emergent insights + topic clusters."""
    names_str = ", ".join(agent_names)
    user_prompt = f"""Analyze the following multi-agent deliberation transcript.

AGENTS: {names_str}

TRANSCRIPT:
{transcript_text}

Produce a JSON object with exactly two keys:

1. "emergent_insights": An array of objects, each representing an idea that NO single agent held initially but emerged from the interaction. Each object has:
   - "insight": the emergent idea (1-2 sentences)
   - "contributing_agents": array of agent names who contributed to its emergence
   - "emerged_in_round": the round where it crystallized
   - "evidence": a short supporting quote

2. "topic_clusters": An array of objects, each representing a thematic cluster. Each has:
   - "theme": name of the theme (3-5 words)
   - "description": what the theme covers (1 sentence)
   - "engaged_agents": array of agent names who engaged with this theme
   - "round_range": [start_round, end_round]

Return ONLY valid JSON. No markdown fences. No explanation text."""

    return _llm_call(client, model, _SYSTEM_PROMPT, user_prompt, max_tokens=8192)


def _call_key_quotes(
    client: Any,
    model: str,
    transcript_text: str,
    agent_names: list[str],
) -> dict:
    """Call 3: Key quotes from each agent."""
    names_str = ", ".join(agent_names)
    user_prompt = f"""Analyze the following multi-agent deliberation transcript.

AGENTS: {names_str}

TRANSCRIPT:
{transcript_text}

Produce a JSON object with exactly one key:

1. "key_quotes": An object keyed by agent name. Each value is an object with:
   - "quote": the most impactful statement from that agent (exact quote, max 3 sentences)
   - "round": the round number where it was said
   - "why_it_matters": 1 sentence explaining why this quote is significant to the deliberation

Return ONLY valid JSON. No markdown fences. No explanation text."""

    return _llm_call(client, model, _SYSTEM_PROMPT, user_prompt, max_tokens=8192)


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------


def _build_symmetric_matrix(
    agreement_data: dict,
    agent_names: list[str],
) -> list[list[float]]:
    """Convert the pairwise agreement dict into a symmetric NxN matrix.

    ``agreement_data`` has keys like ``"SpeakerA -> SpeakerB"`` with a
    ``"score"`` field.  We average ``A->B`` and ``B->A`` to make the matrix
    symmetric, then set the diagonal to 0.
    """
    n = len(agent_names)
    name_to_idx = {name: i for i, name in enumerate(agent_names)}
    matrix = np.zeros((n, n), dtype=float)

    for key, value in agreement_data.items():
        parts = key.split("->")
        if len(parts) != 2:
            continue
        a_name = parts[0].strip()
        b_name = parts[1].strip()
        score = float(value.get("score", 0.0))
        a_idx = name_to_idx.get(a_name)
        b_idx = name_to_idx.get(b_name)
        if a_idx is not None and b_idx is not None:
            matrix[a_idx, b_idx] = score

    # Symmetrize by averaging A->B and B->A
    symmetric = (matrix + matrix.T) / 2.0
    np.fill_diagonal(symmetric, 0.0)
    return symmetric.tolist()


# ---------------------------------------------------------------------------
# Main analysis function
# ---------------------------------------------------------------------------


def analyze_transcript(transcript_path: str, output_path: str | None = None) -> dict:
    """Analyze a Council transcript and return structured results.

    Args:
        transcript_path: Path to the transcript JSON file.
        output_path: Optional path for the output JSON. Defaults to
            ``<transcript_stem>_analysis.json`` in the same directory.

    Returns:
        The merged analysis dict.
    """
    transcript_path_obj = Path(transcript_path).resolve()
    if not transcript_path_obj.exists():
        console.print(f"[red]Transcript not found: {transcript_path_obj}[/red]")
        sys.exit(1)

    transcript: list[dict] = json.loads(transcript_path_obj.read_text(encoding="utf-8"))
    agent_names = _get_agent_names(transcript)
    total_rounds = _get_total_rounds(transcript)
    total_messages = len(transcript)
    transcript_text = _format_transcript_for_prompt(transcript)

    model = os.getenv("COUNCIL_MODEL", "llama-3.3-70b-versatile")

    console.print(
        Panel(
            f"[bold]Transcript:[/bold] {transcript_path_obj.name}\n"
            f"[bold]Agents:[/bold] {len(agent_names)} — {', '.join(agent_names)}\n"
            f"[bold]Rounds:[/bold] {total_rounds}  |  [bold]Messages:[/bold] {total_messages}\n"
            f"[bold]Model:[/bold] {model}",
            title="[bold cyan]Council Transcript Analyzer[/bold cyan]",
            border_style="cyan",
        )
    )

    client = _create_client()

    # ---- Call 1: Pairwise + Positions ---------------------------------
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Call 1/3 — Pairwise agreement & position tracking...", total=None)
        result_1 = _call_pairwise_and_positions(client, model, transcript_text, agent_names)
        progress.update(task, completed=True, description="[green]Call 1/3 — Done[/green]")

    time.sleep(2)  # rate-limit protection

    # ---- Call 2: Insights + Clusters -----------------------------------
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Call 2/3 — Emergent insights & topic clusters...", total=None)
        result_2 = _call_insights_and_clusters(client, model, transcript_text, agent_names)
        progress.update(task, completed=True, description="[green]Call 2/3 — Done[/green]")

    time.sleep(2)  # rate-limit protection

    # ---- Call 3: Key Quotes --------------------------------------------
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Call 3/3 — Key quotes...", total=None)
        result_3 = _call_key_quotes(client, model, transcript_text, agent_names)
        progress.update(task, completed=True, description="[green]Call 3/3 — Done[/green]")

    # ---- Post-process: build symmetric matrix --------------------------
    agreement_raw = result_1.get("agreement_matrix", {})
    symmetric_matrix = _build_symmetric_matrix(agreement_raw, agent_names)

    # Infer scenario title from filename (e.g., "meaning_of_life" -> "Meaning of Life")
    stem = transcript_path_obj.stem
    # Strip trailing timestamp pattern like _20260402_160855
    title_part = re.sub(r"_\d{8}_\d{6}$", "", stem)
    scenario_title = title_part.replace("_", " ").title()

    # ---- Merge all results ---------------------------------------------
    analysis = {
        "metadata": {
            "transcript_path": str(transcript_path_obj),
            "scenario_title": scenario_title,
            "model": model,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "agent_names": agent_names,
            "total_rounds": total_rounds,
            "total_messages": total_messages,
        },
        "agreement_matrix": {
            "labels": agent_names,
            "matrix": symmetric_matrix,
            "raw_pairwise": agreement_raw,
        },
        "position_tracking": result_1.get("position_tracking", {}),
        "emergent_insights": result_2.get("emergent_insights", []),
        "topic_clusters": result_2.get("topic_clusters", []),
        "key_quotes": result_3.get("key_quotes", {}),
    }

    # ---- Write output ---------------------------------------------------
    if output_path is None:
        output_path_obj = transcript_path_obj.parent / f"{stem}_analysis.json"
    else:
        output_path_obj = Path(output_path).resolve()

    output_path_obj.write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    console.print(
        f"\n[bold green]Analysis complete.[/bold green] "
        f"Saved to [cyan]{output_path_obj}[/cyan]"
    )

    # Print quick summary
    n_insights = len(analysis["emergent_insights"])
    n_clusters = len(analysis["topic_clusters"])
    n_shifted = sum(
        1
        for v in analysis["position_tracking"].values()
        if isinstance(v, dict) and v.get("shifted")
    )
    console.print(
        f"  Emergent insights: {n_insights}  |  "
        f"Topic clusters: {n_clusters}  |  "
        f"Agents who shifted: {n_shifted}/{len(agent_names)}"
    )

    return analysis


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print(
            "[red]Usage: python -m runner.analyze <transcript.json> [--output <path>][/red]"
        )
        sys.exit(1)

    _transcript_path = sys.argv[1]
    _output_path = None

    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            _output_path = sys.argv[idx + 1]
        else:
            console.print("[red]--output requires a path argument[/red]")
            sys.exit(1)

    analyze_transcript(_transcript_path, _output_path)
