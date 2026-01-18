#!/usr/bin/env python3
"""Job Search Agent - Find jobs that match your background."""

import argparse
import sys

from rich.console import Console

from config import Config
from models import JobFilters
from resume_parser import parse_resume
from matcher import match_jobs
from output import print_results_table, save_results_json
from job_fetchers import (
    JSearchFetcher,
    RemoteOKFetcher,
    ArbeitnowFetcher,
    OpenAIFetcher,
    AnthropicFetcher,
    AmazonScienceFetcher,
    MicrosoftResearchFetcher,
    GoogleAIFetcher,
    MetaAIFetcher,
)


def main():
    parser = argparse.ArgumentParser(
        description="Find jobs that match your background using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --resume resume.pdf --query "ML engineer"
  python main.py --resume resume.pdf --query "research scientist" --remote --location "San Francisco"
  python main.py --resume resume.pdf --query "applied scientist" -p "Senior role at FAANG, working on LLMs, Bay Area preferred"

Required environment variables:
  ANTHROPIC_API_KEY  - For AI-powered matching
  RAPIDAPI_KEY       - For JSearch API (get free key at rapidapi.com)
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
        help="Job search query (e.g., 'software engineer', 'data scientist')",
    )
    parser.add_argument(
        "--location", "-l",
        help="Location filter (e.g., 'San Francisco', 'New York')",
    )
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Only show remote jobs",
    )
    parser.add_argument(
        "--experience", "-e",
        choices=["entry", "mid", "senior"],
        help="Experience level filter",
    )
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=30,
        help="Only show jobs posted within N days (default: 30)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output JSON file path (default: jobs_TIMESTAMP.json)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max jobs to fetch per source (default: 10)",
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=["jsearch", "remoteok", "arbeitnow", "openai", "anthropic", "amazon", "microsoft", "google", "meta"],
        default=["jsearch", "openai", "anthropic", "amazon", "microsoft"],
        help="Job sources to search (default: jsearch + big tech)",
    )
    parser.add_argument(
        "--preferences", "-p",
        help="Describe your ideal job in natural language (e.g., 'Senior role at a big tech company like Google or Meta, Bay Area or remote, working on LLMs and NLP')",
    )

    args = parser.parse_args()

    console = Console()

    # Validate config
    missing = Config.validate(args.sources)
    if missing:
        console.print("[red]Missing required configuration:[/red]")
        for key in missing:
            console.print(f"  - {key}")
        console.print("\nSet environment variables and try again.")
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
        experience_level=args.experience,
        days_ago=args.days,
        limit=args.limit,
    )

    # Fetch jobs from all sources
    console.print(f"\n[bold]Searching for:[/bold] {args.query}")
    if args.location:
        console.print(f"  Location: {args.location}")
    if args.remote:
        console.print("  Remote only: Yes")
    if args.experience:
        console.print(f"  Experience: {args.experience}")

    fetchers = {
        "jsearch": JSearchFetcher(),
        "remoteok": RemoteOKFetcher(),
        "arbeitnow": ArbeitnowFetcher(),
        "openai": OpenAIFetcher(),
        "anthropic": AnthropicFetcher(),
        "amazon": AmazonScienceFetcher(),
        "microsoft": MicrosoftResearchFetcher(),
        "google": GoogleAIFetcher(),
        "meta": MetaAIFetcher(),
    }

    all_jobs = []
    console.print("\n[bold]Fetching jobs...[/bold]")

    for source_name in args.sources:
        fetcher = fetchers.get(source_name)
        if fetcher:
            console.print(f"  [{source_name}] ", end="")
            jobs = fetcher.fetch_jobs(filters)
            console.print(f"[green]Found {len(jobs)} jobs[/green]")
            all_jobs.extend(jobs)

    if not all_jobs:
        console.print("\n[yellow]No jobs found matching your criteria.[/yellow]")
        sys.exit(0)

    console.print(f"\n[bold]Total jobs found:[/bold] {len(all_jobs)}")

    # Match jobs with resume
    console.print("\n[bold]Analyzing job matches with AI...[/bold]")
    if args.preferences:
        console.print(f"  [dim]Preferences: {args.preferences[:80]}...[/dim]" if len(args.preferences) > 80 else f"  [dim]Preferences: {args.preferences}[/dim]")
    try:
        results = match_jobs(resume, all_jobs, preferences=args.preferences or "")
    except Exception as e:
        console.print(f"[red]Error matching jobs: {e}[/red]")
        sys.exit(1)

    # Output results
    console.print()
    print_results_table(results)

    # Save to JSON
    output_path = save_results_json(results, args.output)


if __name__ == "__main__":
    main()
