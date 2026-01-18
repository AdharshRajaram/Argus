"""Job fetchers for big tech companies."""

import requests

from models import Job, JobFilters
from .base import BaseJobFetcher


class AmazonScienceFetcher(BaseJobFetcher):
    """Fetch jobs from Amazon Science / AWS AI."""

    name = "amazon"

    def fetch_jobs(self, filters: JobFilters) -> list[Job]:
        """Fetch jobs from Amazon jobs API."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # Amazon uses a search API
        payload = {
            "size": filters.limit,
            "offset": 0,
            "queryLanguage": "en",
            "searchableContentLanguages": ["en"],
            "filters": {
                "normalized_keywords": [filters.query]
            },
            "sort": "relevance"
        }

        if filters.location:
            payload["filters"]["normalized_city_name"] = [filters.location]

        try:
            response = requests.post(
                "https://www.amazon.jobs/api/jobs",
                json=payload,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"  [!] Amazon jobs API error: {e}")
            return []

        jobs = []
        query_lower = filters.query.lower()

        for item in data.get("jobs", [])[:filters.limit]:
            title = item.get("title", "")

            # Filter to ML/AI/Research roles
            title_lower = title.lower()
            if not any(term in title_lower for term in ["scientist", "machine learning", "ml", "ai", "research"]):
                continue

            location = item.get("normalized_location", "") or item.get("city", "")
            is_remote = "remote" in location.lower() or item.get("remote_type", "") == "remote"

            if filters.remote_only and not is_remote:
                continue

            job = Job(
                title=title,
                company="Amazon",
                location=location,
                description=item.get("description", "")[:2000],
                url=f"https://www.amazon.jobs{item.get('job_path', '')}",
                source=self.name,
                remote=is_remote,
                experience_level=self._normalize_experience_level(title),
            )

            jobs.append(job)

        return jobs


class MicrosoftResearchFetcher(BaseJobFetcher):
    """Fetch jobs from Microsoft Careers."""

    name = "microsoft"

    def fetch_jobs(self, filters: JobFilters) -> list[Job]:
        """Fetch jobs from Microsoft careers API."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Accept": "application/json",
        }

        params = {
            "q": filters.query,
            "pg": 1,
            "pgSz": filters.limit,
            "o": "Relevance",
            "flt": "true",
        }

        if filters.location:
            params["lc"] = filters.location

        try:
            response = requests.get(
                "https://gcsservices.careers.microsoft.com/search/api/v1/search",
                params=params,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"  [!] Microsoft careers API error: {e}")
            return []

        jobs = []

        for item in data.get("operationResult", {}).get("result", {}).get("jobs", [])[:filters.limit]:
            title = item.get("title", "")
            location = item.get("primaryWorkLocation", {}).get("city", "")
            country = item.get("primaryWorkLocation", {}).get("country", "")
            if country:
                location = f"{location}, {country}" if location else country

            is_remote = item.get("remoteWork", "") == "Yes"

            if filters.remote_only and not is_remote:
                continue

            job = Job(
                title=title,
                company="Microsoft",
                location=location,
                description=item.get("description", "")[:2000],
                url=f"https://careers.microsoft.com/v2/global/en/job/{item.get('jobId', '')}",
                source=self.name,
                remote=is_remote,
                experience_level=self._normalize_experience_level(title),
            )

            jobs.append(job)

        return jobs


class GoogleAIFetcher(BaseJobFetcher):
    """Fetch jobs from Google Careers with AI/ML focus."""

    name = "google"

    def fetch_jobs(self, filters: JobFilters) -> list[Job]:
        """Fetch jobs from Google careers."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Accept": "application/json",
        }

        # Google's careers API
        params = {
            "q": f"{filters.query}",
            "location": filters.location or "",
            "page": 1,
        }

        try:
            # Try the public job search endpoint
            response = requests.get(
                "https://careers.google.com/api/v3/search/",
                params=params,
                headers=headers,
                timeout=30,
            )

            if response.status_code != 200:
                # Google's API is not publicly accessible, skip
                return []

            data = response.json()
        except requests.RequestException:
            return []

        jobs = []
        for item in data.get("jobs", [])[:filters.limit]:
            title = item.get("title", "")
            locations = item.get("locations", [])
            location = locations[0].get("display", "") if locations else ""

            is_remote = "remote" in location.lower()

            if filters.remote_only and not is_remote:
                continue

            job = Job(
                title=title,
                company="Google",
                location=location,
                description=item.get("description", "")[:2000],
                url=f"https://careers.google.com/jobs/results/{item.get('id', '')}",
                source=self.name,
                remote=is_remote,
                experience_level=self._normalize_experience_level(title),
            )

            jobs.append(job)

        return jobs


class MetaAIFetcher(BaseJobFetcher):
    """Fetch jobs from Meta Careers."""

    name = "meta"

    def fetch_jobs(self, filters: JobFilters) -> list[Job]:
        """Fetch jobs from Meta careers."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # Meta's careers API endpoint
        params = {
            "q": filters.query,
            "page": 1,
            "results_per_page": filters.limit,
        }

        try:
            response = requests.get(
                "https://www.metacareers.com/jobs",
                params=params,
                headers=headers,
                timeout=30,
            )

            # Meta doesn't have a public JSON API, would need scraping
            # For now, return empty
            return []

        except requests.RequestException:
            return []
