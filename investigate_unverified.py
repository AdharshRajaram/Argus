#!/usr/bin/env python3
"""
Investigate unverified companies to find their correct ATS configurations.
"""

import re
import httpx
from typing import Optional, Tuple, List

# Companies that couldn't be verified
UNVERIFIED_COMPANIES = [
    {"name": "Adept AI", "career_url": "https://jobs.lever.co/adept", "ats_type": "lever"},
    {"name": "Cohere", "career_url": "https://jobs.ashbyhq.com/cohere", "ats_type": "ashby"},
    {"name": "OpenAI", "career_url": "https://jobs.ashbyhq.com/openai", "ats_type": "ashby"},
    {"name": "Perplexity AI", "career_url": "https://jobs.ashbyhq.com/perplexityai", "ats_type": "ashby"},
    {"name": "DoorDash", "career_url": "https://boards.greenhouse.io/doordash", "ats_type": "greenhouse"},
    {"name": "Confluent", "career_url": "https://www.confluent.io/careers/", "ats_type": "greenhouse"},
    {"name": "Expedia", "career_url": "https://careers.expediagroup.com", "ats_type": "greenhouse"},
    {"name": "Grab", "career_url": "https://grab.careers", "ats_type": "greenhouse"},
    {"name": "Two Sigma", "career_url": "https://careers.twosigma.com", "ats_type": "greenhouse"},
    {"name": "Uber", "career_url": "https://www.uber.com/global/en/careers/list/", "ats_type": "greenhouse"},
    {"name": "Wayfair", "career_url": "https://www.wayfair.com/careers", "ats_type": "greenhouse"},
    {"name": "Yelp", "career_url": "https://www.yelp.careers", "ats_type": "greenhouse"},
    {"name": "Zillow", "career_url": "https://www.zillow.com/careers/", "ats_type": "greenhouse"},
]

client = httpx.Client(
    timeout=20.0,
    headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    },
    follow_redirects=True,
)


def try_greenhouse_slugs(company_name: str) -> List[Tuple[str, int]]:
    """Try various Greenhouse slug patterns."""
    name = company_name.lower()
    slugs = [
        name.replace(" ", ""),
        name.replace(" ", "-"),
        name.replace(" ", "_"),
        name.split()[0],
        # Common variations
        name.replace(" ", "") + "careers",
        name.replace(" ", "") + "jobs",
    ]

    # Add specific known variations
    slug_map = {
        "doordash": ["doordash", "doordashusa", "doordashcareers"],
        "confluent": ["confluent", "confluentinc"],
        "expedia": ["expedia", "expediagroup", "expediagroupcareers"],
        "grab": ["grab", "grabcareers", "grabtaxi"],
        "two sigma": ["twosigma", "two-sigma", "twosigmainvestments"],
        "uber": ["uber", "ubercareers"],
        "wayfair": ["wayfair", "wayfaircareers"],
        "yelp": ["yelp", "yelpcareers"],
        "zillow": ["zillow", "zillowgroup", "zillowcareers"],
    }

    if name in slug_map:
        slugs.extend(slug_map[name])

    results = []
    for slug in set(slugs):
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        try:
            response = client.get(api_url)
            if response.status_code == 200:
                data = response.json()
                jobs = data.get("jobs", [])
                if jobs:
                    results.append((slug, len(jobs)))
        except Exception:
            pass

    return results


def try_lever_slugs(company_name: str) -> List[Tuple[str, int]]:
    """Try various Lever slug patterns."""
    name = company_name.lower()
    slugs = [
        name.replace(" ", ""),
        name.replace(" ", "-"),
        name.split()[0],
        # Remove common suffixes
        name.replace(" ai", "").replace(" ", ""),
    ]

    results = []
    for slug in set(slugs):
        api_url = f"https://api.lever.co/v0/postings/{slug}"
        try:
            response = client.get(api_url)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and data:
                    results.append((slug, len(data)))
        except Exception:
            pass

    return results


def try_ashby_slugs(company_name: str) -> List[Tuple[str, int]]:
    """Try various Ashby slug patterns."""
    name = company_name.lower()
    slugs = [
        name.replace(" ", ""),
        name.replace(" ", "-"),
        name.split()[0],
        name.replace(" ai", "").replace(" ", ""),
        name.replace(" ", "") + "ai",
    ]

    # Known variations
    slug_map = {
        "cohere": ["cohere", "cohereai"],
        "openai": ["openai", "open-ai"],
        "perplexity ai": ["perplexity", "perplexityai", "perplexity-ai"],
    }

    if name in slug_map:
        slugs.extend(slug_map[name])

    results = []
    api_url = "https://jobs.ashbyhq.com/api/non-user-graphql"

    for slug in set(slugs):
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
            response = client.post(
                api_url,
                json=query,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                data = response.json()
                job_board = data.get("data", {}).get("jobBoard", {})
                if job_board:
                    job_postings = job_board.get("jobPostings", [])
                    if job_postings:
                        results.append((slug, len(job_postings)))
        except Exception:
            pass

    return results


def check_workday(career_url: str, company_name: str) -> Optional[Tuple[str, int]]:
    """Check if the company uses Workday."""
    name = company_name.lower().replace(" ", "")

    # Common Workday URL patterns
    workday_urls = [
        f"https://{name}.wd5.myworkdayjobs.com/{name}",
        f"https://{name}.wd1.myworkdayjobs.com/{name}",
        f"https://{name}.wd3.myworkdayjobs.com/{name}",
    ]

    for url in workday_urls:
        try:
            response = client.get(url)
            if response.status_code == 200 and "workday" in response.text.lower():
                return (url, -1)  # -1 means we found it but didn't count jobs
        except Exception:
            pass

    return None


def fetch_and_analyze_html(url: str) -> dict:
    """Fetch a URL and analyze for ATS indicators."""
    try:
        response = client.get(url)
        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}"}

        html = response.text
        findings = {
            "final_url": str(response.url),
            "greenhouse_refs": [],
            "lever_refs": [],
            "ashby_refs": [],
            "workday_refs": [],
            "other_ats": [],
        }

        # Check for Greenhouse
        gh_patterns = [
            r'boards\.greenhouse\.io/(\w+)',
            r'job-boards\.greenhouse\.io/(\w+)',
            r'api\.greenhouse\.io/v1/boards/(\w+)',
            r'greenhouse\.io/embed/job_board\?for=(\w+)',
        ]
        for p in gh_patterns:
            matches = re.findall(p, html, re.IGNORECASE)
            findings["greenhouse_refs"].extend(matches)

        # Check for Lever
        lever_patterns = [
            r'jobs\.lever\.co/(\w+)',
            r'api\.lever\.co/v0/postings/(\w+)',
        ]
        for p in lever_patterns:
            matches = re.findall(p, html, re.IGNORECASE)
            findings["lever_refs"].extend(matches)

        # Check for Ashby
        ashby_patterns = [
            r'jobs\.ashbyhq\.com/(\w+)',
        ]
        for p in ashby_patterns:
            matches = re.findall(p, html, re.IGNORECASE)
            findings["ashby_refs"].extend(matches)

        # Check for Workday
        workday_patterns = [
            r'(\w+)\.wd\d+\.myworkdayjobs\.com',
            r'workday\.com',
        ]
        for p in workday_patterns:
            matches = re.findall(p, html, re.IGNORECASE)
            findings["workday_refs"].extend(matches)

        # Check for other ATS systems
        other_ats = [
            ("SmartRecruiters", r'smartrecruiters\.com'),
            ("iCIMS", r'icims\.com'),
            ("Taleo", r'taleo\.net'),
            ("Jobvite", r'jobvite\.com'),
            ("BambooHR", r'bamboohr\.com'),
        ]
        for name, pattern in other_ats:
            if re.search(pattern, html, re.IGNORECASE):
                findings["other_ats"].append(name)

        # Deduplicate
        for key in ["greenhouse_refs", "lever_refs", "ashby_refs", "workday_refs"]:
            findings[key] = list(set(findings[key]))

        return findings

    except Exception as e:
        return {"error": str(e)}


def main():
    print("Investigating unverified companies...\n")
    print("="*70)

    recommendations = []

    for company in UNVERIFIED_COMPANIES:
        name = company["name"]
        url = company["career_url"]
        ats = company["ats_type"]

        print(f"\n{name}")
        print("-" * len(name))
        print(f"Current: {url} ({ats})")

        # First, analyze the career page HTML
        print("Analyzing career page...")
        html_findings = fetch_and_analyze_html(url)

        if "error" not in html_findings:
            if html_findings["greenhouse_refs"]:
                print(f"  Found Greenhouse refs: {html_findings['greenhouse_refs']}")
            if html_findings["lever_refs"]:
                print(f"  Found Lever refs: {html_findings['lever_refs']}")
            if html_findings["ashby_refs"]:
                print(f"  Found Ashby refs: {html_findings['ashby_refs']}")
            if html_findings["workday_refs"]:
                print(f"  Found Workday refs: {html_findings['workday_refs']}")
            if html_findings["other_ats"]:
                print(f"  Found other ATS: {html_findings['other_ats']}")
        else:
            print(f"  Error: {html_findings['error']}")

        # Try slug variations for the expected ATS
        print(f"Trying {ats} slug variations...")

        found = False
        if ats == "greenhouse":
            results = try_greenhouse_slugs(name)
            if results:
                for slug, count in results:
                    print(f"  ✓ Found: boards.greenhouse.io/{slug} ({count} jobs)")
                    recommendations.append({
                        "name": name,
                        "ats_type": "greenhouse",
                        "career_url": f"https://boards.greenhouse.io/{slug}",
                        "jobs": count
                    })
                    found = True
                    break

        elif ats == "lever":
            results = try_lever_slugs(name)
            if results:
                for slug, count in results:
                    print(f"  ✓ Found: jobs.lever.co/{slug} ({count} jobs)")
                    recommendations.append({
                        "name": name,
                        "ats_type": "lever",
                        "career_url": f"https://jobs.lever.co/{slug}",
                        "jobs": count
                    })
                    found = True
                    break

        elif ats == "ashby":
            results = try_ashby_slugs(name)
            if results:
                for slug, count in results:
                    print(f"  ✓ Found: jobs.ashbyhq.com/{slug} ({count} jobs)")
                    recommendations.append({
                        "name": name,
                        "ats_type": "ashby",
                        "career_url": f"https://jobs.ashbyhq.com/{slug}",
                        "jobs": count
                    })
                    found = True
                    break

        # If not found in expected ATS, try all ATS types
        if not found:
            print("  Not found in expected ATS. Trying other ATS types...")

            # Try all
            for try_ats, try_func, url_template in [
                ("greenhouse", try_greenhouse_slugs, "https://boards.greenhouse.io/{}"),
                ("lever", try_lever_slugs, "https://jobs.lever.co/{}"),
                ("ashby", try_ashby_slugs, "https://jobs.ashbyhq.com/{}"),
            ]:
                if try_ats != ats:
                    results = try_func(name)
                    if results:
                        for slug, count in results:
                            print(f"  ✓ Found in {try_ats}: {url_template.format(slug)} ({count} jobs)")
                            recommendations.append({
                                "name": name,
                                "ats_type": try_ats,
                                "career_url": url_template.format(slug),
                                "jobs": count
                            })
                            found = True
                            break
                    if found:
                        break

        if not found:
            # Check for Workday
            workday_result = check_workday(url, name)
            if workday_result:
                print(f"  ✓ Might use Workday: {workday_result[0]}")
                recommendations.append({
                    "name": name,
                    "ats_type": "workday",
                    "career_url": workday_result[0],
                    "jobs": -1
                })
            else:
                print("  ✗ Could not find valid ATS configuration")
                recommendations.append({
                    "name": name,
                    "ats_type": "custom",
                    "career_url": url,
                    "jobs": 0,
                    "note": "Requires manual investigation or custom scraper"
                })

    # Summary
    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)

    for rec in recommendations:
        name = rec["name"]
        ats = rec["ats_type"]
        url = rec["career_url"]
        jobs = rec.get("jobs", 0)
        note = rec.get("note", "")

        print(f"\n{name}:")
        print(f"  ats_type: {ats}")
        print(f"  career_url: {url}")
        if jobs > 0:
            print(f"  (verified: {jobs} jobs)")
        elif note:
            print(f"  ({note})")

    client.close()


if __name__ == "__main__":
    main()
