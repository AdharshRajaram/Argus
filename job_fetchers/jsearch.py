from datetime import datetime, timedelta

import requests

from config import Config
from models import Job, JobFilters
from .base import BaseJobFetcher


class JSearchFetcher(BaseJobFetcher):
    """Fetch jobs from JSearch API (aggregates LinkedIn, Indeed, Glassdoor, ZipRecruiter)."""

    name = "jsearch"

    def fetch_jobs(self, filters: JobFilters) -> list[Job]:
        """Fetch jobs from JSearch API."""
        if not Config.RAPIDAPI_KEY:
            print("  [!] Skipping JSearch: RAPIDAPI_KEY not set")
            return []

        headers = {
            "X-RapidAPI-Key": Config.RAPIDAPI_KEY,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }

        # Build query with location if provided
        query = filters.query
        if filters.location:
            query = f"{query} in {filters.location}"

        params = {
            "query": query,
            "page": "1",
            "num_pages": "1",
            "date_posted": self._get_date_posted(filters.days_ago),
        }

        if filters.remote_only:
            params["remote_jobs_only"] = "true"

        try:
            response = requests.get(
                f"{Config.JSEARCH_BASE_URL}/search",
                headers=headers,
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"  [!] JSearch API error: {e}")
            return []

        jobs = []
        for item in data.get("data", [])[:filters.limit]:
            posted_date = None
            if item.get("job_posted_at_datetime_utc"):
                try:
                    posted_date = datetime.fromisoformat(
                        item["job_posted_at_datetime_utc"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            job = Job(
                title=item.get("job_title", ""),
                company=item.get("employer_name", ""),
                location=item.get("job_city", "") or item.get("job_country", ""),
                description=item.get("job_description", "")[:2000],
                url=item.get("job_apply_link", "") or item.get("job_google_link", ""),
                posted_date=posted_date,
                source=self.name,
                remote=item.get("job_is_remote", False),
                experience_level=self._normalize_experience_level(
                    item.get("job_required_experience", {}).get("experience_level", "")
                    if isinstance(item.get("job_required_experience"), dict)
                    else ""
                ),
            )

            # Apply experience filter if specified
            if filters.experience_level and job.experience_level:
                if job.experience_level != filters.experience_level:
                    continue

            jobs.append(job)

        return jobs

    def _get_date_posted(self, days_ago: int) -> str:
        """Convert days_ago to JSearch date_posted parameter."""
        if days_ago <= 1:
            return "today"
        if days_ago <= 3:
            return "3days"
        if days_ago <= 7:
            return "week"
        return "month"
