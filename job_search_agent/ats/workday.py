"""Workday ATS adapter."""

import re
import json
from typing import List, Optional
from urllib.parse import urlparse, parse_qs

from .base import CareerFetcher
from ..models import Job


class WorkdayFetcher(CareerFetcher):
    """Fetcher for Workday ATS job boards.

    Workday is more complex and may require Playwright for full rendering.
    This implementation attempts API-based extraction first.
    """

    def __init__(self, company_name: str, career_url: str, timeout: float = 30.0):
        super().__init__(company_name, career_url, timeout)
        self.workday_host = self._extract_workday_host()
        self.company_path = self._extract_company_path()

    def _extract_workday_host(self) -> str:
        """Extract Workday host from URL."""
        parsed = urlparse(self.career_url)
        return parsed.netloc

    def _extract_company_path(self) -> str:
        """Extract company path from Workday URL."""
        parsed = urlparse(self.career_url)
        path = parsed.path.strip("/")
        # Workday URLs typically: company.wd1.myworkdayjobs.com/en-US/External
        parts = path.split("/")
        if len(parts) >= 1:
            return parts[-1] if parts[-1] else (parts[-2] if len(parts) >= 2 else "")
        return ""

    def fetch_job_list(self) -> List[Job]:
        """Fetch jobs from Workday.

        Workday has various implementations. This tries multiple approaches.
        """
        jobs = []

        # Try the search API first
        jobs = self._fetch_from_search_api()
        if jobs:
            return jobs

        # Try parsing the initial page data
        jobs = self._fetch_from_page_data()
        if jobs:
            return jobs

        # Fall back to HTML parsing
        jobs = self._fetch_from_html()

        return jobs

    def _fetch_from_search_api(self) -> List[Job]:
        """Try fetching from Workday search API."""
        jobs = []

        # Common Workday API endpoint pattern
        api_url = f"https://{self.workday_host}/wday/cxs/{self._get_tenant()}/{self.company_path}/jobs"

        try:
            payload = {
                "appliedFacets": {},
                "limit": 100,
                "offset": 0,
                "searchText": ""
            }
            response = self.client.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                data = response.json()
                jobs = self._parse_api_response(data)
        except Exception:
            pass

        return jobs

    def _get_tenant(self) -> str:
        """Extract tenant name from Workday host."""
        # Pattern: company.wd1.myworkdayjobs.com -> company
        host = self.workday_host
        if ".myworkdayjobs.com" in host:
            return host.split(".")[0]
        return host.split(".")[0]

    def _parse_api_response(self, data: dict) -> List[Job]:
        """Parse jobs from Workday API response."""
        jobs = []

        job_postings = data.get("jobPostings", [])
        for job_data in job_postings:
            title = job_data.get("title", "")
            external_path = job_data.get("externalPath", "")

            if title and external_path:
                jobs.append(Job(
                    company=self.company_name,
                    title=title,
                    url=f"https://{self.workday_host}{external_path}",
                    location=self._extract_location(job_data),
                    source="workday",
                ))

        return jobs

    def _extract_location(self, job_data: dict) -> str:
        """Extract location from job data."""
        # Workday stores location in various ways
        locations = job_data.get("locationsText", "")
        if locations:
            return locations

        bullet_fields = job_data.get("bulletFields", [])
        for field in bullet_fields:
            if "location" in str(field).lower():
                return str(field)

        return ""

    def _fetch_from_page_data(self) -> List[Job]:
        """Try extracting job data embedded in the page."""
        jobs = []

        try:
            response = self.client.get(self.career_url)
            if response.status_code == 200:
                # Look for embedded JSON data
                pattern = r'window\.__INITIAL_STATE__\s*=\s*({.*?});'
                match = re.search(pattern, response.text, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                    # Parse the initial state data
                    jobs = self._parse_initial_state(data)
        except Exception:
            pass

        return jobs

    def _parse_initial_state(self, data: dict) -> List[Job]:
        """Parse jobs from Workday initial state."""
        jobs = []

        # Navigate the nested structure
        try:
            # Different Workday versions have different structures
            job_postings = data.get("jobPostings", {}).get("entities", {})
            for job_id, job_data in job_postings.items():
                title = job_data.get("title", "")
                if title:
                    jobs.append(Job(
                        company=self.company_name,
                        title=title,
                        url=f"{self.career_url}/{job_id}",
                        location=job_data.get("location", ""),
                        source="workday",
                    ))
        except Exception:
            pass

        return jobs

    def _fetch_from_html(self) -> List[Job]:
        """Fallback: parse job links from HTML."""
        jobs = []

        try:
            response = self.client.get(self.career_url)
            if response.status_code == 200:
                # Look for job links
                pattern = r'<a[^>]+href="([^"]*job[^"]*)"[^>]*>([^<]+)</a>'
                matches = re.findall(pattern, response.text, re.IGNORECASE)

                seen = set()
                for url, title in matches:
                    if url not in seen and len(title.strip()) > 3:
                        seen.add(url)
                        # Make URL absolute if needed
                        if not url.startswith("http"):
                            url = f"https://{self.workday_host}{url}"
                        jobs.append(Job(
                            company=self.company_name,
                            title=title.strip(),
                            url=url,
                            source="workday",
                        ))
        except Exception:
            pass

        return jobs
