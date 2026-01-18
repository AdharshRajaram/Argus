#!/usr/bin/env python3
"""Scheduled job search script for automated daily/weekly searches."""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from config import Config
from models import JobFilters
from resume_parser import parse_resume
from company_fetcher import CompanyFetcher
from matcher import match_jobs
from job_store import JobStore
from output import print_results_table


def ensure_results_dir(base_dir: str = "search_results") -> Path:
    """Create results directory if it doesn't exist."""
    results_dir = Path(base_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


def run_scheduled_search(
    resume_path: str,
    query: str,
    preferences: str = "",
    categories: list[str] | None = None,
    limit: int = 20,
    results_dir: str = "search_results",
    db_path: str = "jobs.db",
    only_new: bool = True,
    verbose: bool = True,
):
    """
    Run a scheduled job search.

    Args:
        resume_path: Path to resume PDF
        query: Search query (e.g., "machine learning")
        preferences: Natural language job preferences
        categories: Company categories to search
        limit: Max jobs per company
        results_dir: Directory to store results
        db_path: Path to SQLite database for deduplication
        only_new: If True, only match and save new jobs
        verbose: Print progress to stdout
    """
    # Validate API key
    if not Config.ANTHROPIC_API_KEY:
        print("Error: Missing ANTHROPIC_API_KEY", file=sys.stderr)
        sys.exit(1)

    # Setup
    today = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    results_path = ensure_results_dir(results_dir)
    store = JobStore(db_path)

    if verbose:
        print(f"=" * 60)
        print(f"Scheduled Job Search - {today}")
        print(f"=" * 60)
        print(f"Query: {query}")
        print(f"Categories: {categories or 'all'}")
        print(f"Results dir: {results_path}")
        print()

    # Parse resume
    if verbose:
        print("Parsing resume...")
    resume = parse_resume(resume_path)

    # Fetch jobs from all companies
    if verbose:
        print("\nFetching jobs from target companies...")
    fetcher = CompanyFetcher()
    filters = JobFilters(query=query, limit=limit)
    all_jobs = fetcher.fetch_all_jobs(filters, categories=categories)

    if verbose:
        print(f"\nTotal jobs found: {len(all_jobs)}")

    # Filter to new jobs only (if requested)
    if only_new:
        new_jobs = store.filter_new_jobs(all_jobs)
        if verbose:
            print(f"New jobs (not seen before): {len(new_jobs)}")

        if not new_jobs:
            if verbose:
                print("\nNo new jobs found. Exiting.")

            # Still save a summary file
            summary = {
                "search_date": today,
                "timestamp": timestamp,
                "query": query,
                "categories": categories,
                "total_jobs_found": len(all_jobs),
                "new_jobs": 0,
                "results": [],
            }
            summary_file = results_path / f"search_{timestamp}.json"
            with open(summary_file, "w") as f:
                json.dump(summary, f, indent=2)

            store.close()
            return []

        jobs_to_match = new_jobs
    else:
        jobs_to_match = all_jobs

    # Match jobs with AI
    if verbose:
        print(f"\nAnalyzing {len(jobs_to_match)} jobs with AI...")
        if preferences:
            print(f"Preferences: {preferences[:60]}...")

    results = match_jobs(resume, jobs_to_match, preferences)

    # Save results to database
    store.save_match_results(results, today)

    # Display results
    if verbose and results:
        print("\n")
        print_results_table(results)

    # Save results to JSON file
    output_data = {
        "search_date": today,
        "timestamp": timestamp,
        "query": query,
        "preferences": preferences,
        "categories": categories,
        "total_jobs_found": len(all_jobs),
        "new_jobs": len(jobs_to_match),
        "results": [
            {
                "rank": i + 1,
                "score": r.score,
                "reasoning": r.reasoning,
                "job": {
                    "title": r.job.title,
                    "company": r.job.company,
                    "location": r.job.location,
                    "url": r.job.url,
                    "remote": r.job.remote,
                },
            }
            for i, r in enumerate(results)
        ],
    }

    output_file = results_path / f"search_{timestamp}.json"
    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    if verbose:
        print(f"\nResults saved to: {output_file}")

        # Print stats
        stats = store.get_stats()
        print(f"\nDatabase stats:")
        print(f"  Total jobs tracked: {stats['total_jobs_seen']}")
        print(f"  Companies tracked: {stats['companies_tracked']}")

    store.close()
    return results


def show_stats(db_path: str = "jobs.db"):
    """Show statistics from the job database."""
    store = JobStore(db_path)
    stats = store.get_stats()

    print("Job Search Statistics")
    print("=" * 40)
    print(f"Total jobs tracked: {stats['total_jobs_seen']}")
    print(f"Companies tracked: {stats['companies_tracked']}")
    print("\nJobs by company:")
    for company, count in stats["jobs_by_company"].items():
        print(f"  {company}: {count}")

    store.close()


def show_recent(db_path: str = "jobs.db", days: int = 7):
    """Show new jobs from recent searches."""
    from datetime import timedelta

    store = JobStore(db_path)
    since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    jobs = store.get_new_jobs_since(since_date)

    print(f"New jobs found in last {days} days")
    print("=" * 40)

    if not jobs:
        print("No new jobs found.")
    else:
        for job in jobs:
            print(f"\n[{job['score']}/100] {job['title']}")
            print(f"  Company: {job['company']}")
            print(f"  Location: {job['location']}")
            print(f"  Found: {job['search_date']}")
            print(f"  URL: {job['url']}")

    store.close()


def main():
    parser = argparse.ArgumentParser(
        description="Scheduled job search with deduplication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a scheduled search
  python scheduled_search.py --resume resume.pdf --query "machine learning" \\
    --categories ai_labs big_tech --preferences "Senior MLE, Bay Area or Remote"

  # Show statistics
  python scheduled_search.py --stats

  # Show recent new jobs
  python scheduled_search.py --recent --days 7
        """,
    )

    # Search options
    parser.add_argument("--resume", help="Path to resume PDF")
    parser.add_argument("--query", help="Job search query")
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=["ai_labs", "big_tech", "ai_startups", "additional"],
        help="Company categories to search",
    )
    parser.add_argument("--preferences", "-p", default="", help="Job preferences")
    parser.add_argument("--limit", type=int, default=20, help="Max jobs per company")
    parser.add_argument(
        "--results-dir", default="search_results", help="Results directory"
    )
    parser.add_argument("--db", default="jobs.db", help="Database path")
    parser.add_argument(
        "--include-seen",
        action="store_true",
        help="Include previously seen jobs (not just new)",
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")

    # Info options
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument("--recent", action="store_true", help="Show recent new jobs")
    parser.add_argument("--days", type=int, default=7, help="Days for --recent")

    args = parser.parse_args()

    # Handle info commands
    if args.stats:
        show_stats(args.db)
        return

    if args.recent:
        show_recent(args.db, args.days)
        return

    # Validate search arguments
    if not args.resume or not args.query:
        parser.error("--resume and --query are required for searching")

    if not os.path.exists(args.resume):
        parser.error(f"Resume file not found: {args.resume}")

    # Run search
    run_scheduled_search(
        resume_path=args.resume,
        query=args.query,
        preferences=args.preferences,
        categories=args.categories,
        limit=args.limit,
        results_dir=args.results_dir,
        db_path=args.db,
        only_new=not args.include_seen,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
