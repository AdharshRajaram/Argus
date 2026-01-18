import requests

from config import Config
from models import Job, JobFilters
from .base import BaseJobFetcher


class GoogleCareersFetcher(BaseJobFetcher):
    """Fetch jobs from Google Careers."""

    name = "google"

    def fetch_jobs(self, filters: JobFilters) -> list[Job]:
        """Fetch jobs from Google Careers."""
        # Google Careers uses a different API structure
        # This endpoint returns job listings in JSON format
        params = {
            "q": filters.query,
            "location": filters.location or "",
            "page": 1,
            "jlo": "en_US",
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
        }

        try:
            # Try the careers.google.com jobs endpoint
            response = requests.get(
                "https://careers.google.com/api/v3/search/",
                params=params,
                headers=headers,
                timeout=30,
            )

            if response.status_code != 200:
                # Fall back to scraping approach - but for now just skip
                print(f"  [!] Google Careers API returned {response.status_code}")
                return []

            data = response.json()
        except requests.RequestException as e:
            print(f"  [!] Google Careers error: {e}")
            return []

        jobs = []
        for item in data.get("jobs", [])[:filters.limit]:
            locations = item.get("locations", [])
            location_str = locations[0].get("display", "") if locations else ""

            is_remote = "remote" in location_str.lower()

            if filters.remote_only and not is_remote:
                continue

            job = Job(
                title=item.get("title", ""),
                company="Google",
                location=location_str,
                description=item.get("description", "")[:2000],
                url=f"https://careers.google.com/jobs/results/{item.get('id', '')}",
                source=self.name,
                remote=is_remote,
                experience_level=self._normalize_experience_level(item.get("title", "")),
            )

            jobs.append(job)

        return jobs
