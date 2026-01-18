"""Lever-based job fetchers for companies using Lever ATS."""

import requests

from models import Job, JobFilters
from .base import BaseJobFetcher


class LeverJobFetcher(BaseJobFetcher):
    """Base class for companies using Lever ATS."""

    name = "lever"
    company_name = ""
    lever_slug = ""  # Company's Lever URL slug

    def fetch_jobs(self, filters: JobFilters) -> list[Job]:
        """Fetch jobs from Lever job board API."""
        if not self.lever_slug:
            return []

        headers = {
            "User-Agent": "JobSearchAgent/1.0",
            "Accept": "application/json",
        }

        try:
            response = requests.get(
                f"https://api.lever.co/v0/postings/{self.lever_slug}",
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"  [!] {self.company_name} API error: {e}")
            return []

        jobs = []
        query_lower = filters.query.lower()
        query_terms = query_lower.split()

        for item in data:
            title = item.get("text", "")
            title_lower = title.lower()

            # Check if any query term matches the title
            if not any(term in title_lower for term in query_terms):
                continue

            # Get location
            categories = item.get("categories", {})
            location = categories.get("location", "")
            is_remote = "remote" in location.lower()

            if filters.remote_only and not is_remote:
                continue

            if filters.location:
                if filters.location.lower() not in location.lower():
                    continue

            job = Job(
                title=title,
                company=self.company_name,
                location=location,
                description=item.get("descriptionPlain", "")[:2000],
                url=item.get("hostedUrl", ""),
                source=self.name,
                remote=is_remote,
                experience_level=self._normalize_experience_level(title),
            )

            jobs.append(job)

            if len(jobs) >= filters.limit:
                break

        return jobs
