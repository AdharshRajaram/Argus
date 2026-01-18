"""Company-based job fetcher that reads from companies.yaml."""

from pathlib import Path
from typing import Optional

import requests
import yaml

from models import Job, JobFilters
from generic_crawler import GenericCareerCrawler


class CompanyFetcher:
    """Fetch jobs directly from target companies based on their ATS type."""

    def __init__(self, config_path: str = "companies.yaml"):
        self.config_path = Path(config_path)
        self.companies = self._load_companies()

    def _load_companies(self) -> dict:
        """Load company configurations from YAML file."""
        if not self.config_path.exists():
            return {}
        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def get_all_companies(self) -> list[dict]:
        """Get flat list of all companies."""
        all_companies = []
        for category, companies in self.companies.items():
            if isinstance(companies, list):
                for company in companies:
                    company["category"] = category
                    all_companies.append(company)
        return all_companies

    def fetch_all_jobs(self, filters: JobFilters, categories: list[str] | None = None, use_crawler: bool = True) -> list[Job]:
        """Fetch jobs from all configured companies.

        Args:
            filters: Job search filters
            categories: Optional list of categories to search (e.g., ['ai_labs', 'big_tech'])
                       If None, searches all categories.
            use_crawler: Whether to use web crawler for companies without APIs
        """
        all_jobs = []
        companies = self.get_all_companies()

        # Filter companies by category
        target_companies = []
        for company in companies:
            if categories and company.get("category") not in categories:
                continue
            target_companies.append(company)

        if not target_companies:
            print("  No companies to search.")
            return all_jobs

        # Use the generic crawler for all companies
        print(f"\n  Crawling {len(target_companies)} companies...")
        print("  (Using unified generic crawler - this may take a moment)\n")

        try:
            with GenericCareerCrawler(headless=True, slow_mo=100) as crawler:
                for company in target_companies:
                    name = company.get("name", "Unknown")
                    careers_url = company.get("careers_url", "")

                    if not careers_url:
                        print(f"  [{name}] No careers URL configured, skipping")
                        continue

                    print(f"  [{name}] ", end="", flush=True)
                    try:
                        jobs = crawler.crawl(name, careers_url, filters)
                        print(f"Found {len(jobs)} jobs")
                        all_jobs.extend(jobs)
                    except Exception as e:
                        print(f"Error: {e}")

        except Exception as e:
            print(f"  Crawler initialization error: {e}")
            print("  Make sure Playwright is installed: playwright install chromium")

        return all_jobs

    def _fetch_company_jobs(self, company: dict, filters: JobFilters) -> list[Job]:
        """Fetch jobs from a single company based on its ATS type."""
        ats = company.get("ats", "custom")

        if ats == "greenhouse":
            return self._fetch_greenhouse(company, filters)
        elif ats == "lever":
            return self._fetch_lever(company, filters)
        elif ats == "ashby":
            return self._fetch_ashby(company, filters)
        else:
            # Custom ATS - skip for now (would need per-company implementation)
            return []

    def _fetch_greenhouse(self, company: dict, filters: JobFilters) -> list[Job]:
        """Fetch jobs from Greenhouse ATS."""
        board_token = company.get("board_token")
        if not board_token:
            return []

        headers = {
            "User-Agent": "JobSearchAgent/1.0",
            "Accept": "application/json",
        }

        try:
            response = requests.get(
                f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs",
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise Exception(f"API error: {e}")

        return self._parse_greenhouse_jobs(data, company, filters)

    def _parse_greenhouse_jobs(self, data: dict, company: dict, filters: JobFilters) -> list[Job]:
        """Parse Greenhouse API response into Job objects."""
        jobs = []
        query_terms = filters.query.lower().split()

        for item in data.get("jobs", []):
            title = item.get("title", "")
            title_lower = title.lower()

            # Filter by query terms
            if not any(term in title_lower for term in query_terms):
                continue

            location = item.get("location", {}).get("name", "")
            is_remote = "remote" in location.lower()

            # Apply filters
            if filters.remote_only and not is_remote:
                continue

            if filters.location:
                if filters.location.lower() not in location.lower() and not is_remote:
                    continue

            job = Job(
                title=title,
                company=company["name"],
                location=location,
                description="",
                url=item.get("absolute_url", ""),
                source="greenhouse",
                remote=is_remote,
                experience_level=self._infer_level(title),
            )
            jobs.append(job)

            if len(jobs) >= filters.limit:
                break

        return jobs

    def _fetch_lever(self, company: dict, filters: JobFilters) -> list[Job]:
        """Fetch jobs from Lever ATS."""
        company_slug = company.get("company_slug")
        if not company_slug:
            return []

        headers = {
            "User-Agent": "JobSearchAgent/1.0",
            "Accept": "application/json",
        }

        try:
            response = requests.get(
                f"https://api.lever.co/v0/postings/{company_slug}",
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise Exception(f"API error: {e}")

        return self._parse_lever_jobs(data, company, filters)

    def _parse_lever_jobs(self, data: list, company: dict, filters: JobFilters) -> list[Job]:
        """Parse Lever API response into Job objects."""
        jobs = []
        query_terms = filters.query.lower().split()

        for item in data:
            title = item.get("text", "")
            title_lower = title.lower()

            # Filter by query terms
            if not any(term in title_lower for term in query_terms):
                continue

            categories = item.get("categories", {})
            location = categories.get("location", "")
            is_remote = "remote" in location.lower()

            # Apply filters
            if filters.remote_only and not is_remote:
                continue

            if filters.location:
                if filters.location.lower() not in location.lower() and not is_remote:
                    continue

            job = Job(
                title=title,
                company=company["name"],
                location=location,
                description=item.get("descriptionPlain", "")[:2000],
                url=item.get("hostedUrl", ""),
                source="lever",
                remote=is_remote,
                experience_level=self._infer_level(title),
            )
            jobs.append(job)

            if len(jobs) >= filters.limit:
                break

        return jobs

    def _fetch_ashby(self, company: dict, filters: JobFilters) -> list[Job]:
        """Fetch jobs from Ashby ATS."""
        company_slug = company.get("company_slug")
        if not company_slug:
            return []

        headers = {
            "User-Agent": "JobSearchAgent/1.0",
            "Accept": "application/json",
        }

        try:
            response = requests.get(
                f"https://api.ashbyhq.com/posting-api/job-board/{company_slug}",
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise Exception(f"API error: {e}")

        return self._parse_ashby_jobs(data, company, filters)

    def _parse_ashby_jobs(self, data: dict, company: dict, filters: JobFilters) -> list[Job]:
        """Parse Ashby API response into Job objects."""
        jobs = []
        query_terms = filters.query.lower().split()

        for item in data.get("jobs", []):
            title = item.get("title", "")
            title_lower = title.lower()

            # Filter by query terms
            if not any(term in title_lower for term in query_terms):
                continue

            location = item.get("location", "")
            is_remote = item.get("isRemote", False) or "remote" in location.lower()

            # Apply filters
            if filters.remote_only and not is_remote:
                continue

            if filters.location:
                if filters.location.lower() not in location.lower() and not is_remote:
                    continue

            job = Job(
                title=title,
                company=company["name"],
                location=location,
                description=item.get("descriptionPlain", "")[:2000] if item.get("descriptionPlain") else "",
                url=item.get("jobUrl", ""),
                source="ashby",
                remote=is_remote,
                experience_level=self._infer_level(title),
            )
            jobs.append(job)

            if len(jobs) >= filters.limit:
                break

        return jobs

    def _infer_level(self, title: str) -> str:
        """Infer experience level from job title."""
        title_lower = title.lower()
        if any(x in title_lower for x in ["senior", "sr.", "sr ", "staff", "principal", "lead"]):
            return "senior"
        if any(x in title_lower for x in ["junior", "jr.", "jr ", "entry", "associate", "new grad"]):
            return "entry"
        if any(x in title_lower for x in [" ii", " 2", "mid"]):
            return "mid"
        return ""
