"""Validate all character data loads correctly before running the simulation."""

import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table


def validate(council_dir):
    """Validate all Council data integrity."""
    council_dir = Path(council_dir)
    import io, sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    console = Console(width=100, force_terminal=True)
    errors = []
    warnings = []

    console.rule("[bold]Council of 8 — Data Validation[/bold]")

    # 1. Check profiles
    profiles_path = council_dir / "profiles" / "council_profiles.json"
    if profiles_path.exists():
        profiles = json.loads(profiles_path.read_text(encoding="utf-8"))
        console.print(f"[green]✓[/green] Profiles loaded: {len(profiles)} agents")
    else:
        errors.append("profiles/council_profiles.json not found")

    # 2. Check simulation config
    config_path = council_dir / "config" / "simulation_config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        n_configs = len(config.get("agent_activity_configs", []))
        console.print(f"[green]✓[/green] Simulation config loaded: {n_configs} activity configs")
    else:
        errors.append("config/simulation_config.json not found")

    # 3. Check scenarios
    scenarios_dir = council_dir / "scenarios"
    scenarios = list(scenarios_dir.glob("*.json")) if scenarios_dir.exists() else []
    console.print(f"[green]✓[/green] Scenarios found: {len(scenarios)}")
    for s in scenarios:
        data = json.loads(s.read_text(encoding="utf-8"))
        console.print(f"  [dim]- {data.get('title', s.name)}[/dim]")

    # 4. Check each character folder
    console.print()
    required_files = [
        "personality_matrix.json",
        "voice.md",
        "axioms.md",
        "clash_points.md",
        "memory_seeds.md",
    ]

    char_dirs = {
        "musk": "Elon Musk",
        "feynman": "Richard Feynman",
        "kobe": "Kobe Bryant",
        "jobs": "Steve Jobs",
        "sartre": "Jean-Paul Sartre",
        "carlin": "George Carlin",
        "johnson": "Bryan Johnson",
        "kevin": "Kevin (김경선)",
    }

    table = Table(title="Character Data Integrity")
    table.add_column("Character", style="bold")
    table.add_column("personality", justify="center")
    table.add_column("voice", justify="center")
    table.add_column("axioms", justify="center")
    table.add_column("clash", justify="center")
    table.add_column("memory", justify="center")
    table.add_column("sources", justify="center")

    for dirname, display_name in char_dirs.items():
        char_dir = council_dir / "characters" / dirname
        row = [display_name]

        for f in required_files:
            path = char_dir / f
            if path.exists():
                size = path.stat().st_size
                if f.endswith(".json"):
                    try:
                        json.loads(path.read_text(encoding="utf-8"))
                        row.append(f"[green]✓ {size//1024}k[/green]")
                    except json.JSONDecodeError:
                        row.append("[red]✗ BAD JSON[/red]")
                        errors.append(f"{dirname}/{f}: invalid JSON")
                else:
                    row.append(f"[green]✓ {size//1024}k[/green]")
            else:
                row.append("[red]✗ MISSING[/red]")
                errors.append(f"{dirname}/{f}: missing")

        # Check sources
        sources_dir = char_dir / "sources"
        if sources_dir.exists():
            n_sources = len(list(sources_dir.glob("*")))
            row.append(f"[green]{n_sources} files[/green]" if n_sources > 0 else "[yellow]empty[/yellow]")
        else:
            row.append("[yellow]no dir[/yellow]")
            warnings.append(f"{dirname}/sources/: directory missing")

        table.add_row(*row)

    console.print(table)

    # 5. Test agent loading
    console.print()
    try:
        from runner.agent import load_agents

        class FakeClient:
            """Fake client for validation only."""
            api_key = "test"

        agents = load_agents(council_dir, client=FakeClient())
        console.print(f"[green]✓[/green] Agent loading: {len(agents)} agents initialized successfully")

        # Print system prompt sizes
        prompt_table = Table(title="System Prompt Sizes")
        prompt_table.add_column("Agent", style="bold")
        prompt_table.add_column("Prompt Size", justify="right")
        prompt_table.add_column("~Tokens", justify="right")

        for name, agent in sorted(agents.items(), key=lambda x: x[1].user_id):
            size = len(agent.system_prompt)
            approx_tokens = size // 4  # rough estimate
            prompt_table.add_row(name, f"{size:,} chars", f"~{approx_tokens:,}")

        console.print(prompt_table)
    except Exception as e:
        errors.append(f"Agent loading failed: {e}")
        console.print(f"[red]✗[/red] Agent loading failed: {e}")

    # 6. Check API key
    console.print()
    import os
    from dotenv import load_dotenv
    load_dotenv(council_dir / ".env")
    key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "")
    model = os.getenv("COUNCIL_MODEL", "")
    if key and key != "unused":
        console.print(f"[green]✓[/green] API key found: {key[:12]}...")
        if base_url:
            console.print(f"[green]✓[/green] Base URL: {base_url}")
        if model:
            console.print(f"[green]✓[/green] Model: {model}")
    else:
        warnings.append("No LLM_API_KEY in .env -- needed for simulation")
        console.print("[yellow]![/yellow] No LLM_API_KEY found -- create .env (see .env.example)")

    # Summary
    console.print()
    console.rule("[bold]Validation Summary[/bold]")
    if errors:
        for e in errors:
            console.print(f"[red]ERROR:[/red] {e}")
    if warnings:
        for w in warnings:
            console.print(f"[yellow]WARN:[/yellow] {w}")
    if not errors and not warnings:
        console.print("[bold green]All checks passed. Ready to run.[/bold green]")
    elif not errors:
        console.print("[bold yellow]Passed with warnings. Simulation can run.[/bold yellow]")
    else:
        console.print(f"[bold red]{len(errors)} errors found. Fix before running.[/bold red]")

    return len(errors) == 0


if __name__ == "__main__":
    council_dir = Path(__file__).parent.parent
    success = validate(council_dir)
    sys.exit(0 if success else 1)
