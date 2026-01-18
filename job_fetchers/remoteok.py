from datetime import datetime

import requests

from models import Job, JobFilters
from .base import BaseJobFetcher


class RemoteOKFetcher(BaseJobFetcher):
    """Fetch jobs from RemoteOK - free API, no auth required."""

    name = "remoteok"

    def fetch_jobs(self, filters: JobFilters) -> list[Job]:
        """Fetch jobs from RemoteOK API."""
        headers = {
            "User-Agent": "JobSearchAgent/1.0",
            "Accept": "application/json",
        }

        try:
            response = requests.get(
                "https://remoteok.com/api",
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"  [!] RemoteOK API error: {e}")
            return []

        # First item is metadata, skip it
        if data and isinstance(data[0], dict) and "legal" in data[0]:
            data = data[1:]

        jobs = []
        query_lower = filters.query.lower()

        for item in data:
            if not isinstance(item, dict):
                continue

            # Filter by query
            title = item.get("position", "")
            company = item.get("company", "")
            tags = item.get("tags", [])

            # Check if query matches title, company, or tags
            searchable = f"{title} {company} {' '.join(tags)}".lower()
            if query_lower not in searchable:
                continue

            # Filter by location if specified
            location = item.get("location", "Worldwide")
            if filters.location:
                if filters.location.lower() not in location.lower():
                    continue

            posted_date = None
            if item.get("date"):
                try:
                    posted_date = datetime.fromisoformat(item["date"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

            job = Job(
                title=title,
                company=company,
                location=location,
                description=item.get("description", "")[:2000],
                url=item.get("url", ""),
                posted_date=posted_date,
                source=self.name,
                remote=True,  # All RemoteOK jobs are remote
                experience_level=self._normalize_experience_level(title),
            )

            jobs.append(job)

            if len(jobs) >= filters.limit:
                break

        return jobs
