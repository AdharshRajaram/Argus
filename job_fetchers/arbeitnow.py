from datetime import datetime

import requests

from models import Job, JobFilters
from .base import BaseJobFetcher


class ArbeitnowFetcher(BaseJobFetcher):
    """Fetch jobs from Arbeitnow - free API, no auth required."""

    name = "arbeitnow"

    def fetch_jobs(self, filters: JobFilters) -> list[Job]:
        """Fetch jobs from Arbeitnow API."""
        params = {
            "page": 1,
        }

        headers = {
            "User-Agent": "JobSearchAgent/1.0",
            "Accept": "application/json",
        }

        try:
            response = requests.get(
                "https://www.arbeitnow.com/api/job-board-api",
                params=params,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"  [!] Arbeitnow API error: {e}")
            return []

        jobs = []
        query_lower = filters.query.lower()

        for item in data.get("data", []):
            # Filter by query
            title = item.get("title", "")
            company = item.get("company_name", "")
            description = item.get("description", "")
            tags = item.get("tags", [])

            searchable = f"{title} {company} {description} {' '.join(tags)}".lower()
            if query_lower not in searchable:
                continue

            location = item.get("location", "")
            is_remote = item.get("remote", False)

            # Filter by location
            if filters.location:
                if filters.location.lower() not in location.lower():
                    continue

            # Filter by remote
            if filters.remote_only and not is_remote:
                continue

            posted_date = None
            if item.get("created_at"):
                try:
                    # Unix timestamp
                    posted_date = datetime.fromtimestamp(item["created_at"])
                except (ValueError, TypeError):
                    pass

            job = Job(
                title=title,
                company=company,
                location=location,
                description=description[:2000],
                url=item.get("url", ""),
                posted_date=posted_date,
                source=self.name,
                remote=is_remote,
                experience_level=self._normalize_experience_level(title),
            )

            jobs.append(job)

            if len(jobs) >= filters.limit:
                break

        return jobs
