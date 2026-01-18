"""Generic web crawler that works with any company career page."""

import re
import time
from urllib.parse import urljoin, urlparse, quote

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout

from models import Job, JobFilters


class GenericCareerCrawler:
    """
    A unified web crawler that can scrape jobs from any company career page.

    It works by:
    1. Navigating to the career page
    2. Looking for search inputs and entering the query
    3. Finding job links using common URL patterns
    4. Extracting job titles and metadata
    """

    # Common patterns for job URLs
    JOB_URL_PATTERNS = [
        r'/jobs?/',
        r'/careers?/',
        r'/positions?/',
        r'/openings?/',
        r'/opportunities?/',
        r'/details/',
        r'/job-details/',
        r'/apply/',
        r'/requisition/',
        r'/posting/',
        # ATS platforms
        r'greenhouse\.io/.*jobs',
        r'lever\.co/',
        r'ashbyhq\.com/',
        r'workable\.com/',
        r'smartrecruiters\.com/',
        r'myworkday',
        r'icims\.com/',
    ]

    # Patterns to exclude (not actual job pages)
    EXCLUDE_PATTERNS = [
        r'/search',
        r'/filter',
        r'/category',
        r'/team',
        r'/location',
        r'/department',
        r'/login',
        r'/signin',
        r'/about',
        r'/blog',
        r'/news',
        r'#',
        r'javascript:',
    ]

    def __init__(self, headless: bool = True, slow_mo: int = 100):
        """
        Initialize the crawler.

        Args:
            headless: Run browser in headless mode
            slow_mo: Slow down operations by this many ms (helps with JS-heavy sites)
        """
        self.headless = headless
        self.slow_mo = slow_mo
        self.playwright = None
        self.browser = None

    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def crawl(self, company_name: str, careers_url: str, filters: JobFilters) -> list[Job]:
        """
        Crawl a company's career page for jobs.

        Args:
            company_name: Name of the company
            careers_url: URL of the company's careers page
            filters: Job search filters

        Returns:
            List of Job objects found
        """
        # Create page with realistic browser context
        context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        page = context.new_page()
        jobs = []

        try:
            # Step 1: Navigate to careers page
            page.goto(careers_url, timeout=90000, wait_until="networkidle")
            time.sleep(3)  # Wait for JS to initialize

            # Step 1.5: Check if we need to follow a "view jobs" link
            jobs_page_url = self._find_jobs_page_link(page, careers_url)
            if jobs_page_url and jobs_page_url != careers_url:
                page.goto(jobs_page_url, timeout=90000, wait_until="networkidle")
                time.sleep(3)

            # Step 2: Try to find and use search functionality
            searched = self._try_search(page, filters.query)
            if searched:
                time.sleep(3)  # Wait for search results

            # Step 3: Scroll to load more jobs (for infinite scroll pages)
            self._scroll_page(page)

            # Step 4: Extract job listings
            jobs = self._extract_jobs(page, company_name, page.url, filters)

        except PlaywrightTimeout:
            print(f"Timeout loading {careers_url}")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            page.close()
            context.close()

        return jobs

    def _find_jobs_page_link(self, page: Page, base_url: str) -> str | None:
        """Look for a link to the actual jobs listing page."""
        jobs_link_patterns = [
            'a[href*="/jobs"]',
            'a[href*="/openings"]',
            'a[href*="/positions"]',
            'a:has-text("View all jobs")',
            'a:has-text("See all jobs")',
            'a:has-text("Open roles")',
            'a:has-text("Explore roles")',
            'a:has-text("View openings")',
            'a:has-text("Browse jobs")',
        ]

        for selector in jobs_link_patterns:
            try:
                link = page.query_selector(selector)
                if link:
                    href = link.get_attribute('href')
                    if href and not any(x in href.lower() for x in ['login', 'signin', '#', 'javascript']):
                        return urljoin(base_url, href)
            except Exception:
                continue

        return None

    def _try_search(self, page: Page, query: str) -> bool:
        """Try to find a search input and enter the query."""
        search_selectors = [
            'input[type="search"]',
            'input[placeholder*="search" i]',
            'input[placeholder*="Search" i]',
            'input[placeholder*="keyword" i]',
            'input[placeholder*="Keyword" i]',
            'input[name*="search" i]',
            'input[name*="query" i]',
            'input[name*="keyword" i]',
            'input[id*="search" i]',
            'input[class*="search" i]',
            'input[aria-label*="search" i]',
            'input[aria-label*="Search" i]',
        ]

        for selector in search_selectors:
            try:
                search_input = page.query_selector(selector)
                if search_input and search_input.is_visible():
                    search_input.fill(query)
                    time.sleep(0.5)

                    # Try to submit the search
                    # First try pressing Enter
                    search_input.press("Enter")
                    time.sleep(1)

                    # Also try clicking a search button if present
                    search_buttons = [
                        'button[type="submit"]',
                        'button[aria-label*="search" i]',
                        'button[class*="search" i]',
                        '[role="button"][class*="search" i]',
                    ]
                    for btn_selector in search_buttons:
                        try:
                            btn = page.query_selector(btn_selector)
                            if btn and btn.is_visible():
                                btn.click()
                                break
                        except:
                            continue

                    return True
            except Exception:
                continue

        return False

    def _scroll_page(self, page: Page, scrolls: int = 3):
        """Scroll page to load more content (for infinite scroll)."""
        for _ in range(scrolls):
            try:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)
            except Exception:
                break

    def _extract_jobs(self, page: Page, company_name: str, base_url: str, filters: JobFilters) -> list[Job]:
        """Extract job listings from the page."""
        jobs = []
        seen_urls = set()
        query_terms = filters.query.lower().split()

        # Get all links on the page
        links = page.query_selector_all('a[href]')

        for link in links:
            try:
                href = link.get_attribute('href') or ""

                # Skip if not a job URL
                if not self._is_job_url(href):
                    continue

                # Build full URL
                full_url = urljoin(base_url, href)

                # Skip duplicates
                url_key = self._normalize_url(full_url)
                if url_key in seen_urls:
                    continue
                seen_urls.add(url_key)

                # Get job title
                title = self._extract_title(link)
                if not title:
                    continue

                # Check if title matches query
                if not self._matches_query(title, query_terms):
                    continue

                # Try to get location from nearby elements
                location = self._extract_location(link)

                # Check location filter
                is_remote = "remote" in location.lower() if location else False
                if filters.remote_only and not is_remote:
                    if filters.location and location:
                        if filters.location.lower() not in location.lower():
                            continue

                jobs.append(Job(
                    title=title,
                    company=company_name,
                    location=location,
                    url=full_url,
                    source="crawler",
                    remote=is_remote,
                    experience_level=self._infer_level(title),
                ))

                if len(jobs) >= filters.limit:
                    break

            except Exception:
                continue

        return jobs

    def _is_job_url(self, url: str) -> bool:
        """Check if URL looks like a job posting."""
        url_lower = url.lower()

        # Check exclusions first
        for pattern in self.EXCLUDE_PATTERNS:
            if re.search(pattern, url_lower):
                return False

        # Check if matches job patterns
        for pattern in self.JOB_URL_PATTERNS:
            if re.search(pattern, url_lower):
                return True

        return False

    def _normalize_url(self, url: str) -> str:
        """Normalize URL to avoid duplicates."""
        # Remove tracking parameters
        parsed = urlparse(url)
        return f"{parsed.netloc}{parsed.path}".rstrip('/')

    def _extract_title(self, link) -> str:
        """Extract job title from a link element."""
        # Try to get text directly from the link
        try:
            text = link.inner_text().strip()

            # Clean up the text
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if lines:
                title = lines[0]

                # Filter out non-title text
                if len(title) > 10 and len(title) < 150:
                    # Skip if it looks like navigation/buttons
                    skip_words = ['apply', 'view all', 'see all', 'load more', 'show more', 'back', 'next', 'previous']
                    if not any(skip in title.lower() for skip in skip_words):
                        return title
        except Exception:
            pass

        # Try to find title in child elements
        title_selectors = ['h1', 'h2', 'h3', 'h4', '[class*="title"]', '[class*="name"]']
        for selector in title_selectors:
            try:
                title_el = link.query_selector(selector)
                if title_el:
                    text = title_el.inner_text().strip()
                    if text and len(text) > 10 and len(text) < 150:
                        return text
            except Exception:
                continue

        return ""

    def _extract_location(self, link) -> str:
        """Try to extract location from near the link."""
        try:
            # Get parent element
            parent = link.evaluate_handle("el => el.parentElement")
            if parent:
                # Look for location-like elements
                location_selectors = [
                    '[class*="location"]',
                    '[class*="Location"]',
                    '[class*="place"]',
                    '[data-*="location"]',
                ]
                for selector in location_selectors:
                    try:
                        loc_el = parent.as_element().query_selector(selector)
                        if loc_el:
                            return loc_el.inner_text().strip()
                    except:
                        continue

                # Try to find location in parent text
                try:
                    parent_text = parent.as_element().inner_text()
                    lines = parent_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        # Check if line looks like a location
                        if any(x in line for x in [',', 'Remote', 'USA', 'US', 'UK', 'CA', 'San', 'New York', 'London']):
                            if len(line) < 100:
                                return line
                except:
                    pass
        except Exception:
            pass

        return ""

    def _matches_query(self, title: str, query_terms: list[str]) -> bool:
        """Check if title matches any query term."""
        title_lower = title.lower()
        return any(term in title_lower for term in query_terms)

    def _infer_level(self, title: str) -> str:
        """Infer experience level from job title."""
        title_lower = title.lower()
        if any(x in title_lower for x in ["senior", "sr.", "sr ", "staff", "principal", "lead", " iv", " v"]):
            return "senior"
        if any(x in title_lower for x in ["junior", "jr.", "jr ", "entry", "associate", "new grad", " i ", " 1 "]):
            return "entry"
        if any(x in title_lower for x in [" ii", " 2", " iii", " 3", "mid"]):
            return "mid"
        return ""
