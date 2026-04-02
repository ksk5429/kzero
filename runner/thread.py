"""Twitter/X thread generator for Council of 8 transcripts.

Reads a transcript JSON and its analysis JSON, then generates a shareable
Twitter/X thread formatted as markdown — each tweet under 280 characters.

Usage:
    python -m runner.thread transcripts/meaning_of_life_*.json
    python -m runner.thread transcripts/meaning_of_life_*.json --output thread.md

Programmatic:
    from runner.thread import generate_thread
    md = generate_thread("transcripts/meaning_of_life_20260402.json")
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Ensure UTF-8 output on Windows terminals (avoids cp949 encoding errors)
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass

console = Console()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MAX_TWEET_LEN = 280


def _truncate(text: str, limit: int) -> str:
    """Truncate *text* to *limit* characters, adding ellipsis if needed."""
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _find_analysis_path(transcript_path: Path) -> Path:
    """Auto-detect the analysis JSON from a transcript path.

    Convention: ``<stem>_analysis.json`` in the same directory.
    """
    analysis = transcript_path.with_name(
        transcript_path.stem + "_analysis.json"
    )
    if analysis.exists():
        return analysis
    raise FileNotFoundError(
        f"Analysis file not found: {analysis}\n"
        "Run  python -m runner.analyze  on the transcript first."
    )


def _load_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _most_extreme_pair(
    raw_pairwise: dict[str, dict],
    *,
    most_negative: bool = True,
) -> tuple[str, str, float, str]:
    """Return (agent_a, agent_b, score, evidence) for the most extreme pair."""
    best_key = None
    best_score = 0.0
    for key, val in raw_pairwise.items():
        score = val["score"]
        if most_negative and score < best_score:
            best_score = score
            best_key = key
        elif not most_negative and score > best_score:
            best_score = score
            best_key = key
    if best_key is None:
        # fallback: first entry
        best_key = next(iter(raw_pairwise))
        best_score = raw_pairwise[best_key]["score"]

    parts = best_key.split(" -> ")
    agent_a = parts[0].strip()
    agent_b = parts[1].strip() if len(parts) > 1 else "Unknown"
    evidence = raw_pairwise[best_key].get("evidence", "")
    return agent_a, agent_b, best_score, evidence


def _extract_god_mode_text(transcript: list[dict]) -> str | None:
    """Return the first god-mode injection text from the transcript."""
    for msg in transcript:
        if msg.get("type") == "god_mode":
            return msg["text"]
    return None


def _build_quote_tweet(name: str, quote: str, context: str) -> str:
    """Build a single-agent quote tweet, truncating to fit 280 chars."""
    prefix = f"{name} dropped this:\n\n'"
    suffix = "'"
    # Reserve space for context line
    context_line = f"\n\n{context}"
    available = MAX_TWEET_LEN - len(prefix) - len(suffix) - len(context_line)
    if available < 40:
        # Drop context if it doesn't fit
        context_line = ""
        available = MAX_TWEET_LEN - len(prefix) - len(suffix)
    truncated_quote = _truncate(quote, available)
    tweet = f"{prefix}{truncated_quote}{suffix}{context_line}"
    return _truncate(tweet, MAX_TWEET_LEN)


# ---------------------------------------------------------------------------
# Thread builder
# ---------------------------------------------------------------------------


def generate_thread(
    transcript_path: str | Path,
    analysis_path: str | Path | None = None,
) -> str:
    """Generate a Twitter/X thread as a markdown string.

    Parameters
    ----------
    transcript_path:
        Path to the transcript JSON file.
    analysis_path:
        Path to the analysis JSON file. If ``None``, auto-detected from
        the transcript filename (``<stem>_analysis.json``).

    Returns
    -------
    str
        Markdown-formatted thread.
    """
    transcript_path = Path(transcript_path)
    if analysis_path is None:
        analysis_path = _find_analysis_path(transcript_path)
    else:
        analysis_path = Path(analysis_path)

    transcript: list[dict] = _load_json(transcript_path)
    analysis: dict = _load_json(analysis_path)

    metadata = analysis.get("metadata", {})
    scenario_title = metadata.get("scenario_title", "a hard question")
    agent_names = metadata.get("agent_names", [])
    key_quotes: dict = analysis.get("key_quotes", {})
    raw_pairwise: dict = analysis.get("agreement_matrix", {}).get(
        "raw_pairwise", {}
    )
    emergent_insights: list[dict] = analysis.get("emergent_insights", [])

    tweets: list[str] = []

    # ---- Tweet 1: Hook ----
    agent_count = len(agent_names)
    names_str = ", ".join(agent_names[:4])
    if agent_count > 4:
        names_str += f", and {agent_count - 4} more"
    hook = (
        f"I dropped {agent_count} geniuses into a room and asked them: "
        f"{scenario_title}?\n\n"
        f"{names_str}.\n\n"
        f"Here's what happened. [thread]"
    )
    tweets.append(_truncate(hook, MAX_TWEET_LEN))

    # ---- Tweet 2: Setup ----
    setup = (
        "The setup: Each agent has ~3,500 tokens of personality — "
        "speech patterns, memories, cognitive biases, clash dynamics.\n\n"
        "Not generic chatbots. Faithful recreations from primary sources."
    )
    tweets.append(_truncate(setup, MAX_TWEET_LEN))

    # ---- Tweets 3..N: Key quotes per agent ----
    for name, entry in key_quotes.items():
        quote = entry.get("quote", "")
        why = entry.get("why_it_matters", "")
        # Shorten context to a punchy line
        context_short = why.split(".")[0] if why else ""
        tweet = _build_quote_tweet(name, quote, context_short)
        tweets.append(tweet)

    # ---- Conflict tweet ----
    if raw_pairwise:
        a, b, score, evidence = _most_extreme_pair(
            raw_pairwise, most_negative=True
        )
        # Split evidence into two quotes if possible
        conflict_body = f"The biggest clash: {a} vs {b} (score: {score})\n\n"
        available = MAX_TWEET_LEN - len(conflict_body) - len("\n\nAbsolutely brutal.")
        conflict_body += _truncate(evidence, available)
        conflict_body += "\n\nAbsolutely brutal."
        tweets.append(_truncate(conflict_body, MAX_TWEET_LEN))

    # ---- Emergent insight tweet ----
    if emergent_insights:
        insight = emergent_insights[0]
        insight_text = insight.get("insight", "")
        prefix = (
            "But here's what NONE of them said individually "
            "-- it emerged from the collision:\n\n'"
        )
        suffix = (
            "'\n\nThis is why multi-agent deliberation > single chatbot."
        )
        available = MAX_TWEET_LEN - len(prefix) - len(suffix)
        tweet = prefix + _truncate(insight_text, available) + suffix
        tweets.append(_truncate(tweet, MAX_TWEET_LEN))

    # ---- Alliance tweet ----
    if raw_pairwise:
        a, b, score, evidence = _most_extreme_pair(
            raw_pairwise, most_negative=False
        )
        alliance_prefix = (
            f"Unexpected alliance: {a} and {b} agreed (score: +{score})\n\n"
        )
        available = MAX_TWEET_LEN - len(alliance_prefix)
        tweet = alliance_prefix + _truncate(evidence, available)
        tweets.append(_truncate(tweet, MAX_TWEET_LEN))

    # ---- K-ZERO moment tweet ----
    god_text = _extract_god_mode_text(transcript)
    if god_text:
        kzero_prefix = "Then I played God:\n\n> '"
        kzero_suffix = "'\n\nAnd everything changed."
        available = MAX_TWEET_LEN - len(kzero_prefix) - len(kzero_suffix)
        tweet = kzero_prefix + _truncate(god_text, available) + kzero_suffix
        tweets.append(_truncate(tweet, MAX_TWEET_LEN))

    # ---- CTA tweet ----
    cta = (
        "Build your own council. It's free:\n\n"
        "1. Clone the repo\n"
        "2. Get free Groq key: console.groq.com\n"
        "3. Run: python -m runner.demiurge\n\n"
        f"{agent_count} minds. 1 question. Infinite consequences."
    )
    tweets.append(_truncate(cta, MAX_TWEET_LEN))

    # ---- Assemble markdown ----
    lines: list[str] = [
        f"# Twitter Thread: {scenario_title}",
        "",
        f"Generated from `{transcript_path.name}`",
        "",
        "---",
        "",
    ]
    for i, tweet in enumerate(tweets, 1):
        lines.append(f"**{i}/{len(tweets)}**")
        lines.append("")
        lines.append(tweet)
        lines.append("")
        char_count = len(tweet)
        marker = "OVER" if char_count > MAX_TWEET_LEN else "OK"
        lines.append(f"*({char_count} chars — {marker})*")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for thread generation."""
    if len(sys.argv) < 2:
        console.print(
            "[red]Usage: python -m runner.thread <transcript.json> "
            "[--analysis <analysis.json>] [--output <output.md>][/red]"
        )
        sys.exit(1)

    transcript_path = Path(sys.argv[1])
    analysis_path: Path | None = None
    output_path: Path | None = None

    # Parse optional flags
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] in ("--analysis", "-a") and i + 1 < len(args):
            analysis_path = Path(args[i + 1])
            i += 2
        elif args[i] in ("--output", "-o") and i + 1 < len(args):
            output_path = Path(args[i + 1])
            i += 2
        else:
            i += 1

    if not transcript_path.exists():
        console.print(f"[red]Transcript not found: {transcript_path}[/red]")
        sys.exit(1)

    # Generate
    console.print(
        Panel(
            f"[bold]Generating thread from[/bold]\n{transcript_path.name}",
            title="Twitter/X Thread Generator",
            border_style="cyan",
        )
    )

    thread_md = generate_thread(transcript_path, analysis_path)

    # Determine output path
    if output_path is None:
        output_path = transcript_path.with_name(
            transcript_path.stem + "_thread.md"
        )

    output_path.write_text(thread_md, encoding="utf-8")

    # Display the thread in console
    console.print()
    tweets = thread_md.split("---")
    for section in tweets:
        stripped = section.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("Generated"):
            try:
                console.print(Panel(stripped, border_style="blue"))
            except UnicodeEncodeError:
                # Fallback for Windows terminals that cannot render Unicode
                safe = stripped.encode("ascii", errors="replace").decode("ascii")
                console.print(Panel(safe, border_style="blue"))

    console.print(
        f"\n[green]Thread saved to:[/green] {output_path}"
    )
    console.print(
        f"[dim]Total tweets in thread: "
        f"{thread_md.count('**') // 2}[/dim]"
    )


if __name__ == "__main__":
    main()
