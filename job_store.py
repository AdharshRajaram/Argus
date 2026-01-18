"""Job storage and deduplication using SQLite."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from models import Job, MatchResult


class JobStore:
    """Store and deduplicate jobs using SQLite database."""

    def __init__(self, db_path: str = "jobs.db"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self._init_db()

    def _init_db(self):
        """Initialize database tables."""
        cursor = self.conn.cursor()

        # Table for tracking seen jobs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seen_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                first_seen_date TEXT NOT NULL,
                last_seen_date TEXT NOT NULL,
                UNIQUE(job_id, company)
            )
        """)

        # Table for storing match results
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                location TEXT,
                url TEXT NOT NULL,
                score INTEGER,
                reasoning TEXT,
                search_date TEXT NOT NULL,
                is_new INTEGER DEFAULT 1,
                UNIQUE(job_id, company, search_date)
            )
        """)

        # Index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_seen_jobs_lookup
            ON seen_jobs(job_id, company)
        """)

        self.conn.commit()

    def extract_job_id(self, job: Job) -> str:
        """Extract a unique job ID from the job URL or title.

        Different ATS systems have different URL patterns:
        - Greenhouse: /jobs/123456
        - Lever: /jobs/abc-def-123
        - Custom: use URL hash
        """
        url = job.url.lower()

        # Greenhouse pattern: extract numeric ID
        if "greenhouse.io" in url or "/jobs/" in url:
            parts = url.rstrip("/").split("/")
            for part in reversed(parts):
                # Look for numeric ID or alphanumeric ID
                if part.isdigit() or (len(part) > 5 and "-" not in part):
                    return part

        # Lever pattern: /jobs/job-title-id
        if "lever.co" in url:
            parts = url.rstrip("/").split("/")
            if parts:
                return parts[-1]

        # Scale AI pattern: /careers/123456
        if "scale.com/careers" in url:
            parts = url.rstrip("/").split("/")
            if parts and parts[-1].isdigit():
                return parts[-1]

        # DoorDash pattern: /jobs/title/123456
        if "doordash.com" in url or "careersatdoordash" in url:
            parts = url.rstrip("/").split("/")
            if parts and parts[-1].isdigit():
                return parts[-1]

        # Databricks pattern: extract job ID from URL
        if "databricks.com" in url:
            parts = url.rstrip("/").split("/")
            for part in reversed(parts):
                if part.isdigit() or "-" in part:
                    return part

        # Fallback: use hash of URL
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()[:12]

    def is_new_job(self, job: Job) -> bool:
        """Check if a job has been seen before."""
        job_id = self.extract_job_id(job)
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM seen_jobs WHERE job_id = ? AND company = ?",
            (job_id, job.company)
        )
        return cursor.fetchone() is None

    def mark_job_seen(self, job: Job) -> bool:
        """Mark a job as seen. Returns True if it was new."""
        job_id = self.extract_job_id(job)
        today = datetime.now().strftime("%Y-%m-%d")
        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO seen_jobs (job_id, company, title, url, first_seen_date, last_seen_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (job_id, job.company, job.title, job.url, today, today))
            self.conn.commit()
            return True  # New job
        except sqlite3.IntegrityError:
            # Job already exists, update last_seen_date
            cursor.execute("""
                UPDATE seen_jobs SET last_seen_date = ?, title = ?, url = ?
                WHERE job_id = ? AND company = ?
            """, (today, job.title, job.url, job_id, job.company))
            self.conn.commit()
            return False  # Existing job

    def filter_new_jobs(self, jobs: list[Job]) -> list[Job]:
        """Filter to only new jobs that haven't been seen before."""
        return [job for job in jobs if self.is_new_job(job)]

    def save_match_results(self, results: list[MatchResult], search_date: Optional[str] = None):
        """Save match results to database."""
        if search_date is None:
            search_date = datetime.now().strftime("%Y-%m-%d")

        cursor = self.conn.cursor()
        for result in results:
            job = result.job
            job_id = self.extract_job_id(job)
            is_new = 1 if self.mark_job_seen(job) else 0

            try:
                cursor.execute("""
                    INSERT INTO job_matches
                    (job_id, company, title, location, url, score, reasoning, search_date, is_new)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_id, job.company, job.title, job.location,
                    job.url, result.score, result.reasoning,
                    search_date, is_new
                ))
            except sqlite3.IntegrityError:
                # Already saved for this date
                pass

        self.conn.commit()

    def get_stats(self) -> dict:
        """Get statistics about stored jobs."""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM seen_jobs")
        total_seen = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT company) FROM seen_jobs")
        companies = cursor.fetchone()[0]

        cursor.execute("SELECT company, COUNT(*) as cnt FROM seen_jobs GROUP BY company ORDER BY cnt DESC")
        by_company = cursor.fetchall()

        return {
            "total_jobs_seen": total_seen,
            "companies_tracked": companies,
            "jobs_by_company": dict(by_company),
        }

    def get_new_jobs_since(self, date: str) -> list[dict]:
        """Get all new jobs found since a specific date."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT title, company, location, url, score, reasoning, search_date
            FROM job_matches
            WHERE search_date >= ? AND is_new = 1
            ORDER BY score DESC
        """, (date,))

        columns = ["title", "company", "location", "url", "score", "reasoning", "search_date"]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def close(self):
        """Close database connection."""
        self.conn.close()
