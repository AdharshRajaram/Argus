import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from models import MatchResult


def print_results_table(results: list[MatchResult]) -> None:
    """Print match results as a formatted CLI table."""
    console = Console()

    if not results:
        console.print("[yellow]No matching jobs found.[/yellow]")
        return

    table = Table(title="Job Matches", show_lines=True)

    table.add_column("Rank", style="cyan", width=5)
    table.add_column("Score", style="green", width=6)
    table.add_column("Title", style="white", width=30)
    table.add_column("Company", style="blue", width=15)
    table.add_column("Location", width=20)
    table.add_column("Remote", width=6)
    table.add_column("Source", width=8)

    for i, result in enumerate(results, 1):
        score_color = "green" if result.score >= 70 else "yellow" if result.score >= 50 else "red"
        remote_icon = "[green]Yes[/green]" if result.job.remote else "[dim]No[/dim]"

        table.add_row(
            str(i),
            f"[{score_color}]{result.score}[/{score_color}]",
            result.job.title[:30],
            result.job.company[:15],
            result.job.location[:20] if result.job.location else "-",
            remote_icon,
            result.job.source,
        )

    console.print(table)
    console.print()

    # Print top 3 with reasoning
    console.print("[bold]Top Match Analysis:[/bold]")
    for i, result in enumerate(results[:3], 1):
        console.print(f"\n[cyan]{i}. {result.job.title}[/cyan] at [blue]{result.job.company}[/blue]")
        console.print(f"   Score: [green]{result.score}/100[/green]")
        console.print(f"   [dim]{result.reasoning}[/dim]")
        if result.job.url:
            console.print(f"   [link={result.job.url}]Apply Here[/link]")


def save_results_json(results: list[MatchResult], output_path: str | None = None) -> str:
    """Save results to a JSON file.

    Args:
        results: Match results to save
        output_path: Optional output path. If None, generates timestamped filename.

    Returns:
        Path to the saved file
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"jobs_{timestamp}.json"

    output_data = {
        "generated_at": datetime.now().isoformat(),
        "total_jobs": len(results),
        "results": [
            {
                "rank": i,
                "score": r.score,
                "reasoning": r.reasoning,
                "job": {
                    "title": r.job.title,
                    "company": r.job.company,
                    "location": r.job.location,
                    "remote": r.job.remote,
                    "url": r.job.url,
                    "source": r.job.source,
                    "description": r.job.description,
                    "posted_date": r.job.posted_date.isoformat() if r.job.posted_date else None,
                },
            }
            for i, r in enumerate(results, 1)
        ],
    }

    Path(output_path).write_text(json.dumps(output_data, indent=2))

    console = Console()
    console.print(f"\n[green]Results saved to:[/green] {output_path}")

    return output_path
