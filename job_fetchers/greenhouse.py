"""Greenhouse-based job fetchers for companies using Greenhouse ATS."""

import requests

from models import Job, JobFilters
from .base import BaseJobFetcher


class GreenhouseJobFetcher(BaseJobFetcher):
    """Base class for companies using Greenhouse ATS."""

    name = "greenhouse"
    company_name = ""
    board_token = ""  # Greenhouse board token

    def fetch_jobs(self, filters: JobFilters) -> list[Job]:
        """Fetch jobs from Greenhouse job board API."""
        if not self.board_token:
            return []

        headers = {
            "User-Agent": "JobSearchAgent/1.0",
            "Accept": "application/json",
        }

        try:
            response = requests.get(
                f"https://boards-api.greenhouse.io/v1/boards/{self.board_token}/jobs",
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

        for item in data.get("jobs", []):
            title = item.get("title", "")
            title_lower = title.lower()

            # Check if any query term matches the title
            if not any(term in title_lower for term in query_terms):
                continue

            location = item.get("location", {}).get("name", "")
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
                description="",  # Would need additional API call for full description
                url=item.get("absolute_url", ""),
                source=self.name,
                remote=is_remote,
                experience_level=self._normalize_experience_level(title),
            )

            jobs.append(job)

            if len(jobs) >= filters.limit:
                break

        return jobs


class OpenAIFetcher(GreenhouseJobFetcher):
    """Fetch jobs from OpenAI careers."""
    name = "openai"
    company_name = "OpenAI"
    board_token = "openai"


class AnthropicFetcher(GreenhouseJobFetcher):
    """Fetch jobs from Anthropic careers."""
    name = "anthropic"
    company_name = "Anthropic"
    board_token = "anthropic"
