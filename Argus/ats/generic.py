"""Generic career page fetcher using Playwright."""

import re
from typing import List
from urllib.parse import urljoin, urlparse

from .base import CareerFetcher
from ..models import Job


class GenericFetcher(CareerFetcher):
    """Generic fetcher using Playwright for JavaScript-rendered pages."""

    # Keywords that indicate job-related links
    JOB_KEYWORDS = [
        "job", "career", "position", "role", "opening",
        "opportunity", "apply", "hiring", "vacancy"
    ]

    # Patterns to exclude
    EXCLUDE_PATTERNS = [
        r"/blog/", r"/news/", r"/about/", r"/contact/",
        r"/privacy", r"/terms", r"/legal/", r"/login",
        r"/signin", r"/signup", r"\.pdf$", r"\.png$",
        r"\.jpg$", r"javascript:", r"mailto:", r"tel:"
    ]

    def __init__(self, company_name: str, career_url: str, timeout: float = 30.0):
        super().__init__(company_name, career_url, timeout)
        self._playwright = None
        self._browser = None

    def fetch_job_list(self) -> List[Job]:
        """Fetch jobs using Playwright for full page rendering."""
        # First try simple HTTP fetch
        jobs = self._fetch_simple()
        if jobs:
            return jobs

        # Fall back to Playwright
        jobs = self._fetch_with_playwright()
        return jobs

    def _fetch_simple(self) -> List[Job]:
        """Try simple HTTP fetch first."""
        jobs = []

        try:
            response = self.client.get(self.career_url)
            if response.status_code == 200:
                jobs = self._extract_jobs_from_html(response.text, self.career_url)
        except Exception:
            pass

        return jobs

    def _fetch_with_playwright(self) -> List[Job]:
        """Fetch using Playwright for JavaScript-rendered content."""
        jobs = []

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                try:
                    page.goto(self.career_url, wait_until="networkidle", timeout=self.timeout * 1000)

                    # Wait for initial dynamic content to load
                    page.wait_for_timeout(3000)

                    # Scroll to load dynamically loaded content (infinite scroll)
                    jobs = self._scroll_and_extract(page)

                except Exception as e:
                    print(f"Playwright error for {self.company_name}: {e}")
                finally:
                    browser.close()

        except ImportError:
            print("Playwright not installed. Run: pip install playwright && playwright install")
        except Exception as e:
            print(f"Error with Playwright for {self.company_name}: {e}")

        return jobs

    def _scroll_and_extract(self, page) -> List[Job]:
        """Scroll page to load all dynamic content and extract jobs."""
        max_scrolls = 10
        scroll_pause = 2000  # ms
        prev_job_count = 0
        no_change_count = 0

        for i in range(max_scrolls):
            # Try clicking "Load More" or "Show More" buttons
            self._click_load_more(page)

            # Scroll to bottom
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(scroll_pause)

            # Extract jobs from current content
            html = page.content()
            jobs = self._extract_jobs_from_html(html, self.career_url)

            # Check if we found new jobs
            if len(jobs) == prev_job_count:
                no_change_count += 1
                if no_change_count >= 2:
                    # No new jobs after 2 scrolls, stop
                    break
            else:
                no_change_count = 0
                prev_job_count = len(jobs)

        return jobs

    def _click_load_more(self, page):
        """Try to click common 'Load More' buttons."""
        load_more_selectors = [
            "button:has-text('Load More')",
            "button:has-text('Show More')",
            "button:has-text('View More')",
            "button:has-text('See More')",
            "a:has-text('Load More')",
            "a:has-text('Show More')",
            "[data-testid='load-more']",
            ".load-more",
            ".show-more",
        ]

        for selector in load_more_selectors:
            try:
                button = page.locator(selector).first
                if button.is_visible(timeout=500):
                    button.click()
                    page.wait_for_timeout(1500)
            except Exception:
                pass

    def _extract_jobs_from_html(self, html: str, base_url: str) -> List[Job]:
        """Extract job listings from HTML content."""
        jobs = []
        seen_urls = set()

        # Find all links
        link_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
        matches = re.findall(link_pattern, html, re.DOTALL | re.IGNORECASE)

        for href, link_text in matches:
            # Clean up link text
            text = re.sub(r'<[^>]+>', '', link_text).strip()

            # Skip if no meaningful text
            if not text or len(text) < 3:
                continue

            # Skip excluded patterns
            if any(re.search(pat, href, re.IGNORECASE) for pat in self.EXCLUDE_PATTERNS):
                continue

            # Check if this looks like a job link
            combined = f"{href} {text}".lower()
            is_job_link = any(kw in combined for kw in self.JOB_KEYWORDS)

            # Also look for links with job IDs or specific patterns
            job_id_pattern = r'/(\d{5,}|[a-f0-9-]{8,})'
            has_job_id = bool(re.search(job_id_pattern, href))

            if is_job_link or has_job_id:
                # Make URL absolute
                url = urljoin(base_url, href)

                # Deduplicate
                canonical = url.split("?")[0].lower()
                if canonical in seen_urls:
                    continue
                seen_urls.add(canonical)

                # Basic title cleaning
                title = self._clean_title(text)

                if len(title) > 5:  # Skip very short titles
                    jobs.append(Job(
                        company=self.company_name,
                        title=title,
                        url=url,
                        source="generic",
                    ))

        return jobs

    def _clean_title(self, text: str) -> str:
        """Clean up extracted job title."""
        # Remove extra whitespace
        text = " ".join(text.split())

        # Remove common suffixes
        for suffix in [" - Apply", " - View", " - Learn More", "Apply Now", "View Job"]:
            text = text.replace(suffix, "")

        return text.strip()
