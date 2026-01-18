import requests

from config import Config
from models import Job, JobFilters
from .base import BaseJobFetcher


class AppleJobsFetcher(BaseJobFetcher):
    """Fetch jobs from Apple Jobs."""

    name = "apple"

    def fetch_jobs(self, filters: JobFilters) -> list[Job]:
        """Fetch jobs from Apple Jobs API."""
        params = {
            "searchString": filters.query,
            "page": 1,
            "locale": "en-us",
            "sort": "relevance",
        }

        if filters.location:
            params["location"] = filters.location

        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        }

        try:
            response = requests.get(
                Config.APPLE_JOBS_URL,
                params=params,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"  [!] Apple Jobs API error: {e}")
            return []

        jobs = []
        results = data.get("searchResults", [])

        for item in results[:filters.limit]:
            locations = item.get("locations", [])
            location_str = ""
            if locations:
                loc = locations[0]
                location_str = f"{loc.get('city', '')}, {loc.get('stateProvince', '')}".strip(", ")

            is_remote = item.get("workFromHome", False) or "remote" in location_str.lower()

            if filters.remote_only and not is_remote:
                continue

            job = Job(
                title=item.get("postingTitle", ""),
                company="Apple",
                location=location_str,
                description=item.get("jobSummary", "")[:2000],
                url=f"https://jobs.apple.com/en-us/details/{item.get('positionId', '')}",
                source=self.name,
                remote=is_remote,
                experience_level=self._normalize_experience_level(item.get("postingTitle", "")),
            )

            jobs.append(job)

        return jobs
