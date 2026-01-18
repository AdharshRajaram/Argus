import requests

from config import Config
from models import Job, JobFilters
from .base import BaseJobFetcher


class MetaCareersFetcher(BaseJobFetcher):
    """Fetch jobs from Meta Careers."""

    name = "meta"

    def fetch_jobs(self, filters: JobFilters) -> list[Job]:
        """Fetch jobs from Meta Careers GraphQL API."""
        # Meta uses a GraphQL endpoint for job searches
        query = """
        query JobSearchQuery($search: String, $locations: [String], $limit: Int) {
            job_search(
                q: $search
                locations: $locations
                page_size: $limit
            ) {
                results {
                    id
                    title
                    locations
                    description
                    teams
                }
            }
        }
        """

        variables = {
            "search": filters.query,
            "limit": filters.limit,
        }

        if filters.location:
            variables["locations"] = [filters.location]

        try:
            response = requests.post(
                Config.META_CAREERS_URL,
                json={"query": query, "variables": variables},
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"  [!] Meta Careers API error: {e}")
            return []

        jobs = []
        results = data.get("data", {}).get("job_search", {}).get("results", [])

        for item in results[:filters.limit]:
            locations = item.get("locations", [])
            location_str = ", ".join(locations) if locations else ""

            is_remote = "remote" in location_str.lower()

            if filters.remote_only and not is_remote:
                continue

            job = Job(
                title=item.get("title", ""),
                company="Meta",
                location=location_str,
                description=item.get("description", "")[:2000],
                url=f"https://www.metacareers.com/jobs/{item.get('id', '')}",
                source=self.name,
                remote=is_remote,
                experience_level=self._normalize_experience_level(item.get("title", "")),
            )

            jobs.append(job)

        return jobs
