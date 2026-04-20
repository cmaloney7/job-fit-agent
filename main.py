"""
main.py — CLI entry point for the Job Fit Agent.

Run with:
    python main.py --jd data/sample_jds/example.txt
    python main.py --jd data/sample_jds/example.txt --resume data/resume.txt
    python main.py --help

LEARNING NOTE: argparse is Python's built-in CLI argument parser.
It handles --flags, help text, and type validation automatically.
"""

import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# LEARNING NOTE: rich is a third-party library for beautiful terminal output.
# Console is the main class. print() from rich understands markdown-style formatting.
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from src.analyzer import JobFitAnalyzer
from src.models import FitLevel

console = Console()


def display_analysis(analysis) -> None:
    """Pretty-print a FitAnalysis using rich formatting."""

    # Color-code by fit level
    color_map = {
        FitLevel.STRONG:   "green",
        FitLevel.PARTIAL:  "yellow",
        FitLevel.STRETCH:  "orange3",
        FitLevel.NOT_FIT:  "red",
    }
    color = color_map.get(analysis.fit_level, "white")

    # Header panel
    console.print(Panel(
        f"[bold {color}]{analysis.fit_level.value} — {analysis.fit_score}/100[/bold {color}]\n"
        f"[white]{analysis.headline}[/white]",
        title=f"[bold]{analysis.job_title or 'Job'} @ {analysis.company_name or 'Company'}[/bold]",
        border_style=color,
    ))

    if analysis.reasoning:
        console.print(f"\n[dim]{analysis.reasoning}[/dim]\n")

    # Strong matches
    if analysis.strong_matches:
        console.print("[bold green]✓ Strong Matches[/bold green]")
        for match in analysis.strong_matches:
            console.print(f"  [green]•[/green] {match}")

    # Gaps
    if analysis.gaps:
        console.print("\n[bold]Gaps[/bold]")
        severity_colors = {"blocking": "red", "notable": "yellow", "minor": "dim"}
        for gap in analysis.gaps:
            c = severity_colors.get(gap.severity, "white")
            console.print(f"  [{c}][{gap.severity}][/{c}] {gap.skill}")
            console.print(f"    [dim]→ {gap.bridge}[/dim]")

    # Differentiators
    if analysis.differentiators:
        console.print("\n[bold cyan]★ Differentiators[/bold cyan]")
        for d in analysis.differentiators:
            console.print(f"  [cyan]•[/cyan] {d}")

    # Cover letter angles
    if analysis.cover_letter_angles:
        console.print("\n[bold]Cover Letter Angles[/bold]")
        for i, angle in enumerate(analysis.cover_letter_angles, 1):
            console.print(f"  {i}. {angle}")

    # Interview questions
    if analysis.likely_interview_questions:
        console.print("\n[bold yellow]⚠ Likely Interview Questions[/bold yellow]")
        for q in analysis.likely_interview_questions:
            console.print(f"  [yellow]?[/yellow] {q}")

    # Things to address proactively
    if analysis.things_to_address_proactively:
        console.print("\n[bold red]▲ Address Proactively[/bold red]")
        for t in analysis.things_to_address_proactively:
            console.print(f"  [red]![/red] {t}")

    # Verdict
    verdict = "[bold green]Worth applying[/bold green]" if analysis.is_worth_applying() \
              else "[bold red]Consider skipping[/bold red]"
    console.print(f"\n[bold]Verdict:[/bold] {verdict}\n")


def main():
    parser = argparse.ArgumentParser(
        description="AI-powered job fit analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --jd data/sample_jds/gravie.txt
  python main.py --jd data/sample_jds/gravie.txt --resume data/resume.txt
  python main.py --jd-text "Senior QA Engineer, 5+ years Cypress required..."
        """
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--jd", metavar="FILE", help="Path to job description file")
    input_group.add_argument("--jd-text", metavar="TEXT", help="Job description as raw text")

    parser.add_argument(
        "--resume", metavar="FILE",
        default="data/resume.txt",
        help="Path to resume file (default: data/resume.txt)"
    )
    parser.add_argument(
        "--model",
        default="claude-opus-4-6",
        help="Claude model to use (default: claude-opus-4-6)"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output raw JSON instead of formatted display"
    )

    args = parser.parse_args()

    # Load resume
    resume_path = Path(args.resume)
    if not resume_path.exists():
        console.print(f"[red]Resume file not found: {args.resume}[/red]")
        console.print("[dim]Create data/resume.txt and paste your resume text into it.[/dim]")
        sys.exit(1)

    resume_text = resume_path.read_text(encoding="utf-8").strip()

    # Load JD
    if args.jd:
        jd_path = Path(args.jd)
        if not jd_path.exists():
            console.print(f"[red]JD file not found: {args.jd}[/red]")
            sys.exit(1)
        jd_text = jd_path.read_text(encoding="utf-8").strip()
    else:
        jd_text = args.jd_text

    # Run analysis
    console.print("[dim]Analyzing fit...[/dim]")
    analyzer = JobFitAnalyzer(model=args.model)

    try:
        analysis = analyzer.analyze(resume_text, jd_text)
    except Exception as e:
        console.print(f"[red]Analysis failed: {e}[/red]")
        sys.exit(1)

    # Output
    if args.json:
        import json, dataclasses
        # LEARNING NOTE: dataclasses don't JSON-serialize automatically.
        # This converts to dict first. A cleaner solution would use a library
        # like pydantic — that's a good Phase 1.5 upgrade.
        def serialize(obj):
            if hasattr(obj, '__dict__'):
                return {k: serialize(v) for k, v in obj.__dict__.items()}
            if hasattr(obj, 'value'):
                return obj.value
            if isinstance(obj, list):
                return [serialize(i) for i in obj]
            return obj
        print(json.dumps(serialize(analysis), indent=2))
    else:
        display_analysis(analysis)


if __name__ == "__main__":
    main()
