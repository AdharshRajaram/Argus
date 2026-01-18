#!/usr/bin/env python3
"""Job Search Agent - Search target companies directly."""

import argparse
import sys

from rich.console import Console

from config import Config
from models import JobFilters
from resume_parser import parse_resume
from matcher import match_jobs
from output import print_results_table, save_results_json
from company_fetcher import CompanyFetcher


def main():
    parser = argparse.ArgumentParser(
        description="Search jobs from your target companies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search all target companies for ML roles
  python search.py --resume resume.pdf --query "machine learning"

  # Search only AI labs
  python search.py --resume resume.pdf --query "research scientist" --categories ai_labs

  # Search AI labs and startups, Bay Area or remote only
  python search.py --resume resume.pdf --query "applied scientist" --categories ai_labs ai_startups --location "San Francisco"

  # With preferences
  python search.py --resume resume.pdf --query "ML engineer" -p "Senior level, remote or Bay Area"

Categories available:
  - ai_labs: Anthropic, OpenAI, DeepMind, Meta AI, Cohere, Mistral
  - big_tech: Google, Meta, Amazon, Apple, Microsoft, Netflix
  - ai_startups: Scale AI, Databricks, Anyscale, W&B, Hugging Face, Ramp, Perplexity
        """,
    )

    parser.add_argument(
        "--resume", "-r",
        required=True,
        help="Path to your resume PDF file",
    )
    parser.add_argument(
        "--query", "-q",
        required=True,
        help="Job search query (e.g., 'machine learning', 'research scientist')",
    )
    parser.add_argument(
        "--categories", "-c",
        nargs="+",
        choices=["ai_labs", "big_tech", "ai_startups"],
        default=["ai_labs", "big_tech", "ai_startups"],
        help="Company categories to search (default: all)",
    )
    parser.add_argument(
        "--location", "-l",
        help="Location filter (e.g., 'San Francisco', 'Remote')",
    )
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Only show remote jobs",
    )
    parser.add_argument(
        "--preferences", "-p",
        help="Describe your ideal job in natural language",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output JSON file path",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Max jobs per company (default: 20)",
    )
    parser.add_argument(
        "--config",
        default="companies.yaml",
        help="Path to companies config file (default: companies.yaml)",
    )

    args = parser.parse_args()
    console = Console()

    # Validate config
    if not Config.ANTHROPIC_API_KEY:
        console.print("[red]Missing ANTHROPIC_API_KEY[/red]")
        sys.exit(1)

    # Parse resume
    console.print(f"\n[bold]Parsing resume:[/bold] {args.resume}")
    try:
        resume = parse_resume(args.resume)
        console.print(f"  [green]Found {len(resume.skills)} skills, {len(resume.job_titles)} job titles[/green]")
    except Exception as e:
        console.print(f"[red]Error parsing resume: {e}[/red]")
        sys.exit(1)

    # Build filters
    filters = JobFilters(
        query=args.query,
        location=args.location,
        remote_only=args.remote,
        days_ago=30,
        limit=args.limit,
    )

    # Display search info
    console.print(f"\n[bold]Searching for:[/bold] {args.query}")
    console.print(f"  Categories: {', '.join(args.categories)}")
    if args.location:
        console.print(f"  Location: {args.location}")
    if args.remote:
        console.print("  Remote only: Yes")

    # Fetch jobs from target companies
    console.print("\n[bold]Fetching jobs from target companies...[/bold]")
    fetcher = CompanyFetcher(config_path=args.config)
    all_jobs = fetcher.fetch_all_jobs(filters, categories=args.categories)

    if not all_jobs:
        console.print("\n[yellow]No jobs found matching your criteria.[/yellow]")
        console.print("[dim]Try broadening your search query or adding more categories.[/dim]")
        sys.exit(0)

    console.print(f"\n[bold]Total jobs found:[/bold] {len(all_jobs)}")

    # Match jobs with resume
    console.print("\n[bold]Analyzing job matches with AI...[/bold]")
    if args.preferences:
        console.print(f"  [dim]Preferences: {args.preferences[:60]}...[/dim]" if len(args.preferences or "") > 60 else f"  [dim]Preferences: {args.preferences}[/dim]")

    try:
        results = match_jobs(resume, all_jobs, preferences=args.preferences or "")
    except Exception as e:
        console.print(f"[red]Error matching jobs: {e}[/red]")
        sys.exit(1)

    # Output results
    console.print()
    print_results_table(results)

    # Save to JSON
    output_file = args.output or f"target_companies_{args.query.replace(' ', '_')}.json"
    save_results_json(results, output_file)


if __name__ == "__main__":
    main()
