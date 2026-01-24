#!/usr/bin/env python3
"""
Script to automatically detect and fix ATS types and career URLs in companies.yaml.

This script will:
1. Validate each company's career URL
2. Auto-detect the correct ATS type
3. Find direct ATS URLs when companies embed job boards
4. Verify that detected URLs actually return jobs
5. Update the YAML file with corrections
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

import httpx
import yaml


@dataclass
class ATSInfo:
    """Information about a detected ATS."""
    ats_type: str
    direct_url: str
    job_count: int = 0
    verified: bool = False


class ATSFixer:
    """Detects and fixes ATS configurations."""

    # URL patterns for known ATS systems
    ATS_URL_PATTERNS = {
        "greenhouse": [
            r"boards\.greenhouse\.io/(\w+)",
            r"job-boards\.greenhouse\.io/(\w+)",
            r"api\.greenhouse\.io",
        ],
        "lever": [
            r"jobs\.lever\.co/(\w+)",
        ],
        "ashby": [
            r"jobs\.ashbyhq\.com/(\w+)",
        ],
        "workday": [
            r"(\w+)\.wd\d+\.myworkdayjobs\.com",
            r"(\w+)\.myworkdaysite\.com",
        ],
    }

    # HTML indicators for embedded ATS
    HTML_INDICATORS = {
        "greenhouse": [
            (r'<iframe[^>]+src=["\']([^"\']*greenhouse\.io[^"\']*)["\']', "iframe"),
            (r'<script[^>]+src=["\']([^"\']*greenhouse\.io[^"\']*)["\']', "script"),
            (r'data-greenhouse-embed[^>]*["\']([^"\']+)["\']', "embed"),
            (r'boards\.greenhouse\.io/(\w+)', "link"),
            (r'job-boards\.greenhouse\.io/(\w+)', "link"),
            (r'"greenhouse":\s*{\s*"board_token":\s*"(\w+)"', "config"),
        ],
        "lever": [
            (r'<iframe[^>]+src=["\']([^"\']*lever\.co[^"\']*)["\']', "iframe"),
            (r'jobs\.lever\.co/(\w+)', "link"),
            (r'api\.lever\.co/v0/postings/(\w+)', "api"),
        ],
        "ashby": [
            (r'<iframe[^>]+src=["\']([^"\']*ashbyhq\.com[^"\']*)["\']', "iframe"),
            (r'jobs\.ashbyhq\.com/(\w+)', "link"),
        ],
        "workday": [
            (r'<iframe[^>]+src=["\']([^"\']*workday[^"\']*)["\']', "iframe"),
            (r'(\w+)\.wd\d+\.myworkdayjobs\.com', "link"),
        ],
    }

    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout
        self.client = httpx.Client(
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            follow_redirects=True,
        )

    def detect_from_url(self, url: str) -> Optional[Tuple[str, str]]:
        """Detect ATS type and extract slug from URL pattern.

        Returns: (ats_type, company_slug) or None
        """
        for ats_type, patterns in self.ATS_URL_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, url, re.IGNORECASE)
                if match:
                    slug = match.group(1) if match.groups() else None
                    return (ats_type, slug)
        return None

    def detect_from_html(self, html: str) -> Optional[Tuple[str, str]]:
        """Detect ATS type from HTML content.

        Returns: (ats_type, direct_url_or_slug) or None
        """
        for ats_type, patterns in self.HTML_INDICATORS.items():
            for pattern, pattern_type in patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    extracted = match.group(1) if match.groups() else None
                    return (ats_type, extracted)
        return None

    def build_direct_url(self, ats_type: str, slug: str) -> str:
        """Build the direct ATS URL from type and slug."""
        url_templates = {
            "greenhouse": f"https://boards.greenhouse.io/{slug}",
            "lever": f"https://jobs.lever.co/{slug}",
            "ashby": f"https://jobs.ashbyhq.com/{slug}",
        }
        return url_templates.get(ats_type, "")

    def verify_greenhouse(self, slug: str) -> Tuple[bool, int]:
        """Verify Greenhouse board and get job count."""
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        try:
            response = self.client.get(api_url)
            if response.status_code == 200:
                data = response.json()
                jobs = data.get("jobs", [])
                return (True, len(jobs))
        except Exception:
            pass
        return (False, 0)

    def verify_lever(self, slug: str) -> Tuple[bool, int]:
        """Verify Lever board and get job count."""
        api_url = f"https://api.lever.co/v0/postings/{slug}"
        try:
            response = self.client.get(api_url)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    return (True, len(data))
        except Exception:
            pass
        return (False, 0)

    def verify_ashby(self, slug: str) -> Tuple[bool, int]:
        """Verify Ashby board and get job count."""
        api_url = "https://jobs.ashbyhq.com/api/non-user-graphql"
        # Updated query - jobPostings are now at the board level
        query = {
            "operationName": "ApiJobBoardWithTeams",
            "variables": {"organizationHostedJobsPageName": slug},
            "query": """
                query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
                    jobBoard: jobBoardWithTeams(
                        organizationHostedJobsPageName: $organizationHostedJobsPageName
                    ) {
                        jobPostings { id }
                    }
                }
            """
        }
        try:
            response = self.client.post(
                api_url,
                json=query,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                data = response.json()
                job_board = data.get("data", {}).get("jobBoard", {})
                if job_board:
                    job_postings = job_board.get("jobPostings", [])
                    return (True, len(job_postings))
        except Exception:
            pass
        return (False, 0)

    def verify_ats(self, ats_type: str, slug: str) -> Tuple[bool, int]:
        """Verify ATS configuration and get job count."""
        verifiers = {
            "greenhouse": self.verify_greenhouse,
            "lever": self.verify_lever,
            "ashby": self.verify_ashby,
        }
        verifier = verifiers.get(ats_type)
        if verifier:
            return verifier(slug)
        return (False, 0)

    def extract_slug_from_url(self, url: str, ats_type: str) -> Optional[str]:
        """Extract company slug from an ATS URL."""
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")
        if path_parts and path_parts[0]:
            return path_parts[0]
        return None

    def analyze_company(self, name: str, career_url: str, current_ats: str) -> ATSInfo:
        """Analyze a company and detect the correct ATS configuration."""
        print(f"  Analyzing {name}...")

        # Step 1: Check if current URL is already a direct ATS URL
        url_detection = self.detect_from_url(career_url)
        if url_detection:
            ats_type, slug = url_detection
            if slug:
                verified, job_count = self.verify_ats(ats_type, slug)
                if verified:
                    direct_url = self.build_direct_url(ats_type, slug)
                    return ATSInfo(
                        ats_type=ats_type,
                        direct_url=direct_url or career_url,
                        job_count=job_count,
                        verified=True
                    )

        # Step 2: Fetch the career page and analyze HTML
        try:
            response = self.client.get(career_url)
            if response.status_code == 200:
                html = response.text

                # Check HTML for embedded ATS
                html_detection = self.detect_from_html(html)
                if html_detection:
                    ats_type, extracted = html_detection

                    # Determine slug from extracted value
                    if extracted and "." in extracted:
                        # It's a URL, extract slug
                        slug = self.extract_slug_from_url(extracted, ats_type)
                    else:
                        slug = extracted

                    if slug:
                        verified, job_count = self.verify_ats(ats_type, slug)
                        if verified:
                            direct_url = self.build_direct_url(ats_type, slug)
                            return ATSInfo(
                                ats_type=ats_type,
                                direct_url=direct_url,
                                job_count=job_count,
                                verified=True
                            )
        except Exception as e:
            print(f"    Error fetching {career_url}: {e}")

        # Step 3: Try common slug variations based on company name
        slug_variations = self._generate_slug_variations(name)
        for ats_type in ["greenhouse", "lever", "ashby"]:
            for slug in slug_variations:
                verified, job_count = self.verify_ats(ats_type, slug)
                if verified and job_count > 0:
                    direct_url = self.build_direct_url(ats_type, slug)
                    return ATSInfo(
                        ats_type=ats_type,
                        direct_url=direct_url,
                        job_count=job_count,
                        verified=True
                    )

        # Could not detect/verify ATS
        return ATSInfo(
            ats_type=current_ats,
            direct_url=career_url,
            job_count=0,
            verified=False
        )

    def _generate_slug_variations(self, company_name: str) -> list:
        """Generate possible slug variations from company name."""
        name = company_name.lower()
        variations = [
            name.replace(" ", ""),           # "Scale AI" -> "scaleai"
            name.replace(" ", "-"),          # "Scale AI" -> "scale-ai"
            name.replace(" ", "_"),          # "Scale AI" -> "scale_ai"
            name.split()[0] if " " in name else name,  # "Scale AI" -> "scale"
        ]
        # Remove common suffixes
        for suffix in [" ai", " inc", " labs", " technologies"]:
            if name.endswith(suffix):
                base = name[:-len(suffix)]
                variations.extend([
                    base.replace(" ", ""),
                    base.replace(" ", "-"),
                ])
        return list(set(variations))

    def close(self):
        """Close the HTTP client."""
        self.client.close()


def load_companies(yaml_path: str) -> dict:
    """Load companies from YAML file."""
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)


def save_companies(yaml_path: str, data: dict):
    """Save companies to YAML file."""
    # Custom representer to preserve formatting
    def str_representer(dumper, data):
        if '\n' in data:
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)

    yaml.add_representer(str, str_representer)

    with open(yaml_path, 'w') as f:
        # Write header comment
        f.write("# Company configuration for MLE / ML Scientist job search\n")
        f.write("# Alphabetically sorted by company name\n")
        f.write("# Use direct ATS URLs for reliable job fetching\n\n")

        # Write companies
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def main():
    """Main entry point."""
    yaml_path = Path("config/companies.yaml")

    if not yaml_path.exists():
        print(f"Error: {yaml_path} not found")
        sys.exit(1)

    print("Loading companies configuration...")
    data = load_companies(yaml_path)
    companies = data.get("companies", [])

    print(f"Found {len(companies)} companies to analyze\n")

    fixer = ATSFixer()
    changes = []

    try:
        for company in companies:
            name = company.get("name", "Unknown")
            career_url = company.get("career_url", "")
            current_ats = company.get("ats_type", "unknown")

            result = fixer.analyze_company(name, career_url, current_ats)

            # Check if we need to update
            needs_update = False
            updates = {}

            if result.verified:
                if result.ats_type != current_ats:
                    updates["ats_type"] = (current_ats, result.ats_type)
                    needs_update = True

                if result.direct_url != career_url:
                    updates["career_url"] = (career_url, result.direct_url)
                    needs_update = True

                if needs_update:
                    company["ats_type"] = result.ats_type
                    company["career_url"] = result.direct_url
                    changes.append({
                        "name": name,
                        "updates": updates,
                        "job_count": result.job_count
                    })
                    print(f"    ✓ Updated: {updates}")
                else:
                    print(f"    ✓ OK ({result.job_count} jobs)")
            else:
                if current_ats == "custom":
                    print(f"    - Skipped (custom ATS)")
                else:
                    print(f"    ⚠ Could not verify (keeping current config)")

    finally:
        fixer.close()

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    if changes:
        print(f"\n{len(changes)} companies updated:\n")
        for change in changes:
            print(f"  {change['name']}:")
            for field, (old, new) in change['updates'].items():
                print(f"    {field}: {old} -> {new}")
            print(f"    (verified with {change['job_count']} jobs)")

        # Save changes
        print("\nSaving changes to companies.yaml...")
        save_companies(yaml_path, data)
        print("Done!")
    else:
        print("\nNo changes needed. All configurations are correct.")


if __name__ == "__main__":
    main()
