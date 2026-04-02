"""
K-ZERO Artifact Generator — turn deliberation reports into learning materials via NotebookLM.

The report is the seed. NotebookLM is the multiplier. One question becomes:
- A podcast (Audio Overview)
- A study guide
- Flashcards
- A quiz
- A mind map
- A slide deck
- A briefing doc

The book was always the translation layer between superior and inferior intelligence.
Now K-ZERO generates that book, and NotebookLM makes it learnable.

Usage:
    python -m runner.artifacts reports/immortality_20260402.pdf
    python -m runner.artifacts reports/immortality_20260402.pdf --all
    python -m runner.artifacts reports/immortality_20260402.pdf --podcast --quiz --flashcards
"""

import asyncio
import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console(width=100)


async def generate_artifacts(
    report_path: str,
    output_dir: str = None,
    podcast: bool = False,
    study_guide: bool = False,
    quiz: bool = False,
    flashcards: bool = False,
    slides: bool = False,
    mind_map: bool = False,
    briefing: bool = False,
    all_artifacts: bool = False,
):
    """Upload a K-ZERO report to NotebookLM and generate learning artifacts."""
    from notebooklm import NotebookLMClient

    report_path = Path(report_path)
    if not report_path.exists():
        console.print(f"[red]Report not found: {report_path}[/red]")
        return

    # Output directory
    if output_dir:
        out = Path(output_dir)
    else:
        out = report_path.parent / f"{report_path.stem}_artifacts"
    out.mkdir(parents=True, exist_ok=True)

    # If --all, enable everything
    if all_artifacts:
        podcast = study_guide = quiz = flashcards = slides = mind_map = briefing = True

    # If nothing selected, default to podcast + study guide + quiz
    if not any([podcast, study_guide, quiz, flashcards, slides, mind_map, briefing]):
        podcast = study_guide = quiz = True

    console.print()
    console.rule("[bold]K-ZERO ARTIFACT GENERATOR[/bold]", style="bright_red")
    console.print(f"[bold]Source:[/bold] {report_path.name}")
    console.print(f"[bold]Output:[/bold] {out}")

    artifacts_to_generate = []
    if podcast:
        artifacts_to_generate.append("podcast")
    if study_guide:
        artifacts_to_generate.append("study_guide")
    if quiz:
        artifacts_to_generate.append("quiz")
    if flashcards:
        artifacts_to_generate.append("flashcards")
    if slides:
        artifacts_to_generate.append("slides")
    if mind_map:
        artifacts_to_generate.append("mind_map")
    if briefing:
        artifacts_to_generate.append("briefing")

    console.print(f"[bold]Generating:[/bold] {', '.join(artifacts_to_generate)}")
    console.rule(style="dim")

    try:
        async with await NotebookLMClient.from_storage() as client:
            # 1. Create a notebook for this report
            notebook_name = f"K-ZERO: {report_path.stem[:50]}"
            console.print(f"  Creating notebook: {notebook_name}")
            nb = await client.notebooks.create(notebook_name)
            notebook_id = nb.id
            console.print(f"  [green]Notebook created: {notebook_id}[/green]")

            # 2. Upload the report as a source
            console.print(f"  Uploading report: {report_path.name}")
            if report_path.suffix == ".pdf":
                await client.sources.add_file(notebook_id, str(report_path), wait=True)
            elif report_path.suffix in (".html", ".md", ".qmd", ".txt"):
                # Upload as text
                text = report_path.read_text(encoding="utf-8")
                await client.sources.add_text(notebook_id, text, title=report_path.stem)
            else:
                console.print(f"[yellow]Unsupported format: {report_path.suffix}. Trying as file...[/yellow]")
                await client.sources.add_file(notebook_id, str(report_path), wait=True)

            console.print(f"  [green]Source uploaded[/green]")

            # 3. Generate artifacts
            results = {}

            if podcast:
                console.print("  Generating podcast (Audio Overview)...")
                try:
                    status = await client.artifacts.generate_audio(
                        notebook_id,
                        instructions="This is a K-ZERO deliberation report where 8 brilliant minds debated a question. Make the podcast engaging and highlight the key clashes and the divine recommendation at the end.",
                        audio_format="deep-dive",
                    )
                    await client.artifacts.wait_for_completion(notebook_id, status.task_id)
                    audio_path = out / "podcast.mp3"
                    await client.artifacts.download_audio(notebook_id, str(audio_path))
                    results["podcast"] = str(audio_path)
                    console.print(f"  [green]Podcast saved: {audio_path.name}[/green]")
                except Exception as e:
                    console.print(f"  [yellow]Podcast error: {e}[/yellow]")

            if study_guide:
                console.print("  Generating study guide...")
                try:
                    status = await client.artifacts.generate_report(
                        notebook_id,
                        report_format="study-guide",
                    )
                    await client.artifacts.wait_for_completion(notebook_id, status.task_id)
                    guide_path = out / "study_guide.md"
                    await client.artifacts.download_report(notebook_id, str(guide_path))
                    results["study_guide"] = str(guide_path)
                    console.print(f"  [green]Study guide saved: {guide_path.name}[/green]")
                except Exception as e:
                    console.print(f"  [yellow]Study guide error: {e}[/yellow]")

            if quiz:
                console.print("  Generating quiz...")
                try:
                    status = await client.artifacts.generate_quiz(
                        notebook_id,
                        difficulty="hard",
                        quantity="more",
                    )
                    await client.artifacts.wait_for_completion(notebook_id, status.task_id)
                    quiz_path = out / "quiz.json"
                    await client.artifacts.download_quiz(notebook_id, str(quiz_path), output_format="json")
                    results["quiz"] = str(quiz_path)
                    console.print(f"  [green]Quiz saved: {quiz_path.name}[/green]")
                except Exception as e:
                    console.print(f"  [yellow]Quiz error: {e}[/yellow]")

            if flashcards:
                console.print("  Generating flashcards...")
                try:
                    status = await client.artifacts.generate_flashcards(
                        notebook_id,
                        quantity="more",
                    )
                    await client.artifacts.wait_for_completion(notebook_id, status.task_id)
                    cards_path = out / "flashcards.json"
                    await client.artifacts.download_flashcards(notebook_id, str(cards_path), output_format="json")
                    results["flashcards"] = str(cards_path)
                    console.print(f"  [green]Flashcards saved: {cards_path.name}[/green]")
                except Exception as e:
                    console.print(f"  [yellow]Flashcards error: {e}[/yellow]")

            if slides:
                console.print("  Generating slide deck...")
                try:
                    status = await client.artifacts.generate_slide_deck(
                        notebook_id,
                    )
                    await client.artifacts.wait_for_completion(notebook_id, status.task_id)
                    slides_path = out / "slides.pdf"
                    await client.artifacts.download_slide_deck(notebook_id, str(slides_path))
                    results["slides"] = str(slides_path)
                    console.print(f"  [green]Slides saved: {slides_path.name}[/green]")
                except Exception as e:
                    console.print(f"  [yellow]Slides error: {e}[/yellow]")

            if mind_map:
                console.print("  Generating mind map...")
                try:
                    status = await client.artifacts.generate_mind_map(notebook_id)
                    await client.artifacts.wait_for_completion(notebook_id, status.task_id)
                    map_path = out / "mind_map.json"
                    await client.artifacts.download_mind_map(notebook_id, str(map_path))
                    results["mind_map"] = str(map_path)
                    console.print(f"  [green]Mind map saved: {map_path.name}[/green]")
                except Exception as e:
                    console.print(f"  [yellow]Mind map error: {e}[/yellow]")

            if briefing:
                console.print("  Generating briefing doc...")
                try:
                    status = await client.artifacts.generate_report(
                        notebook_id,
                        report_format="briefing-doc",
                    )
                    await client.artifacts.wait_for_completion(notebook_id, status.task_id)
                    brief_path = out / "briefing.md"
                    await client.artifacts.download_report(notebook_id, str(brief_path))
                    results["briefing"] = str(brief_path)
                    console.print(f"  [green]Briefing saved: {brief_path.name}[/green]")
                except Exception as e:
                    console.print(f"  [yellow]Briefing error: {e}[/yellow]")

            # Summary
            console.print()
            console.rule("[bold]ARTIFACTS GENERATED[/bold]", style="bright_red")

            table = Table(title="Learning Materials")
            table.add_column("Artifact", style="bold")
            table.add_column("File")
            table.add_column("Status")

            for name in artifacts_to_generate:
                if name in results:
                    table.add_row(name, Path(results[name]).name, "[green]OK[/green]")
                else:
                    table.add_row(name, "-", "[red]FAILED[/red]")

            console.print(table)
            console.print(f"\n  All artifacts in: {out}")
            console.print(f"  NotebookLM notebook: {notebook_name}")
            console.rule(style="dim")

            return results

    except Exception as e:
        console.print(f"[red]NotebookLM error: {e}[/red]")
        console.print("[yellow]Make sure you've run: notebooklm login[/yellow]")
        return {}


def main():
    parser = argparse.ArgumentParser(description="K-ZERO Artifact Generator via NotebookLM")
    parser.add_argument("report", help="Path to K-ZERO report (PDF, HTML, or QMD)")
    parser.add_argument("--output", "-o", help="Output directory for artifacts")
    parser.add_argument("--all", action="store_true", help="Generate all artifact types")
    parser.add_argument("--podcast", action="store_true", help="Generate podcast (Audio Overview)")
    parser.add_argument("--study-guide", action="store_true", help="Generate study guide")
    parser.add_argument("--quiz", action="store_true", help="Generate quiz")
    parser.add_argument("--flashcards", action="store_true", help="Generate flashcards")
    parser.add_argument("--slides", action="store_true", help="Generate slide deck")
    parser.add_argument("--mind-map", action="store_true", help="Generate mind map")
    parser.add_argument("--briefing", action="store_true", help="Generate briefing doc")

    args = parser.parse_args()

    asyncio.run(generate_artifacts(
        report_path=args.report,
        output_dir=args.output,
        podcast=args.podcast,
        study_guide=args.study_guide,
        quiz=args.quiz,
        flashcards=args.flashcards,
        slides=args.slides,
        mind_map=args.mind_map,
        briefing=args.briefing,
        all_artifacts=args.all,
    ))


if __name__ == "__main__":
    main()
