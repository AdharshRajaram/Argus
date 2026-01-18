"""Web crawler for company career pages using Playwright."""

import re
import time
from typing import Optional
from urllib.parse import urljoin, quote

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout

from models import Job, JobFilters


class CareerPageCrawler:
    """Crawl career pages using Playwright headless browser."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser = None

    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def crawl_company(self, company: dict, filters: JobFilters) -> list[Job]:
        """Crawl a company's career page based on its configuration."""
        company_name = company.get("name", "")
        crawl_method = company.get("crawl_method", "")

        # Map company names to specific crawl methods
        crawl_methods = {
            "Google": self._crawl_google,
            "Google DeepMind": self._crawl_google_deepmind,
            "Meta": self._crawl_meta,
            "Meta AI": self._crawl_meta,
            "Amazon": self._crawl_amazon,
            "Apple": self._crawl_apple,
            "Microsoft": self._crawl_microsoft,
            "OpenAI": self._crawl_openai,
            "Netflix": self._crawl_netflix,
        }

        method = crawl_methods.get(company_name)
        if method:
            return method(company, filters)
        return []

    def _crawl_google(self, company: dict, filters: JobFilters) -> list[Job]:
        """Crawl Google Careers."""
        page = self.browser.new_page()
        jobs = []

        try:
            query = quote(filters.query)
            location = quote(filters.location or "")
            url = f"https://www.google.com/about/careers/applications/jobs/results?q={query}&location={location}"

            page.goto(url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)

            # Wait for job cards to load
            page.wait_for_selector('[data-job-id]', timeout=10000)

            # Extract job listings
            job_cards = page.query_selector_all('[data-job-id]')

            for card in job_cards[:filters.limit]:
                try:
                    title_el = card.query_selector('h3')
                    location_el = card.query_selector('[class*="location"]')
                    link_el = card.query_selector('a')

                    title = title_el.inner_text() if title_el else ""
                    location = location_el.inner_text() if location_el else ""
                    href = link_el.get_attribute('href') if link_el else ""

                    if not self._matches_query(title, filters.query):
                        continue

                    jobs.append(Job(
                        title=title,
                        company="Google",
                        location=location,
                        url=urljoin("https://www.google.com", href) if href else "",
                        source="crawler",
                        remote="remote" in location.lower(),
                        experience_level=self._infer_level(title),
                    ))
                except Exception:
                    continue

        except PlaywrightTimeout:
            pass
        except Exception as e:
            print(f"Error crawling Google: {e}")
        finally:
            page.close()

        return jobs

    def _crawl_google_deepmind(self, company: dict, filters: JobFilters) -> list[Job]:
        """Crawl Google DeepMind Careers."""
        page = self.browser.new_page()
        jobs = []

        try:
            url = "https://deepmind.google/about/careers/"
            page.goto(url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)

            # Click on search/filter if available
            try:
                search_input = page.query_selector('input[type="search"], input[placeholder*="Search"]')
                if search_input:
                    search_input.fill(filters.query)
                    page.keyboard.press("Enter")
                    time.sleep(2)
            except Exception:
                pass

            # Extract job listings
            job_links = page.query_selector_all('a[href*="/careers/"]')

            seen_urls = set()
            for link in job_links:
                try:
                    href = link.get_attribute('href') or ""
                    if "/careers/" not in href or href in seen_urls:
                        continue
                    seen_urls.add(href)

                    title = link.inner_text().strip()
                    if not title or not self._matches_query(title, filters.query):
                        continue

                    jobs.append(Job(
                        title=title,
                        company="Google DeepMind",
                        location="",
                        url=urljoin("https://deepmind.google", href),
                        source="crawler",
                        remote=False,
                        experience_level=self._infer_level(title),
                    ))

                    if len(jobs) >= filters.limit:
                        break
                except Exception:
                    continue

        except PlaywrightTimeout:
            pass
        except Exception as e:
            print(f"Error crawling DeepMind: {e}")
        finally:
            page.close()

        return jobs

    def _crawl_meta(self, company: dict, filters: JobFilters) -> list[Job]:
        """Crawl Meta Careers."""
        page = self.browser.new_page()
        jobs = []

        try:
            query = quote(filters.query)
            url = f"https://www.metacareers.com/jobs?q={query}"

            page.goto(url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)

            # Wait for job listings
            time.sleep(3)  # Give time for JS to render

            # Try to find job cards
            job_cards = page.query_selector_all('[role="listitem"], [data-testid*="job"], a[href*="/jobs/"]')

            seen_urls = set()
            for card in job_cards:
                try:
                    # Try to get link and title
                    link = card.query_selector('a[href*="/jobs/"]') or card
                    href = link.get_attribute('href') if link else ""

                    if not href or "/jobs/" not in href or href in seen_urls:
                        continue
                    seen_urls.add(href)

                    title = link.inner_text().strip().split('\n')[0]
                    if not title or not self._matches_query(title, filters.query):
                        continue

                    jobs.append(Job(
                        title=title,
                        company="Meta",
                        location="",
                        url=urljoin("https://www.metacareers.com", href),
                        source="crawler",
                        remote=False,
                        experience_level=self._infer_level(title),
                    ))

                    if len(jobs) >= filters.limit:
                        break
                except Exception:
                    continue

        except PlaywrightTimeout:
            pass
        except Exception as e:
            print(f"Error crawling Meta: {e}")
        finally:
            page.close()

        return jobs

    def _crawl_amazon(self, company: dict, filters: JobFilters) -> list[Job]:
        """Crawl Amazon Jobs."""
        page = self.browser.new_page()
        jobs = []

        try:
            query = quote(filters.query)
            location = quote(filters.location or "")
            url = f"https://www.amazon.jobs/en/search?base_query={query}&loc_query={location}"

            page.goto(url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)

            # Wait for job cards
            time.sleep(2)

            job_cards = page.query_selector_all('.job-tile, [class*="job-card"], a[href*="/jobs/"]')

            seen_urls = set()
            for card in job_cards:
                try:
                    title_el = card.query_selector('h3, [class*="title"]')
                    location_el = card.query_selector('[class*="location"]')
                    link_el = card.query_selector('a[href*="/jobs/"]') or card

                    href = link_el.get_attribute('href') if link_el else ""
                    if not href or href in seen_urls:
                        continue
                    seen_urls.add(href)

                    title = title_el.inner_text() if title_el else link_el.inner_text().split('\n')[0]
                    location = location_el.inner_text() if location_el else ""

                    if not self._matches_query(title, filters.query):
                        continue

                    jobs.append(Job(
                        title=title.strip(),
                        company="Amazon",
                        location=location.strip(),
                        url=urljoin("https://www.amazon.jobs", href),
                        source="crawler",
                        remote="remote" in location.lower(),
                        experience_level=self._infer_level(title),
                    ))

                    if len(jobs) >= filters.limit:
                        break
                except Exception:
                    continue

        except PlaywrightTimeout:
            pass
        except Exception as e:
            print(f"Error crawling Amazon: {e}")
        finally:
            page.close()

        return jobs

    def _crawl_apple(self, company: dict, filters: JobFilters) -> list[Job]:
        """Crawl Apple Jobs."""
        page = self.browser.new_page()
        jobs = []

        try:
            query = quote(filters.query)
            url = f"https://jobs.apple.com/en-us/search?search={query}&sort=relevance"

            page.goto(url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)

            time.sleep(2)

            job_rows = page.query_selector_all('tr[class*="table-row"], [class*="job-row"], a[href*="/details/"]')

            seen_urls = set()
            for row in job_rows:
                try:
                    link_el = row.query_selector('a[href*="/details/"]') or row
                    href = link_el.get_attribute('href') if link_el else ""

                    if not href or href in seen_urls:
                        continue
                    seen_urls.add(href)

                    title = link_el.inner_text().strip().split('\n')[0]
                    if not self._matches_query(title, filters.query):
                        continue

                    jobs.append(Job(
                        title=title,
                        company="Apple",
                        location="",
                        url=urljoin("https://jobs.apple.com", href),
                        source="crawler",
                        remote=False,
                        experience_level=self._infer_level(title),
                    ))

                    if len(jobs) >= filters.limit:
                        break
                except Exception:
                    continue

        except PlaywrightTimeout:
            pass
        except Exception as e:
            print(f"Error crawling Apple: {e}")
        finally:
            page.close()

        return jobs

    def _crawl_microsoft(self, company: dict, filters: JobFilters) -> list[Job]:
        """Crawl Microsoft Careers."""
        page = self.browser.new_page()
        jobs = []

        try:
            query = quote(filters.query)
            url = f"https://jobs.careers.microsoft.com/global/en/search?q={query}&l=en_us&pg=1&pgSz=20"

            page.goto(url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)

            time.sleep(3)

            job_cards = page.query_selector_all('[class*="ms-DocumentCard"], [class*="job-card"], a[href*="/job/"]')

            seen_urls = set()
            for card in job_cards:
                try:
                    link_el = card.query_selector('a[href*="/job/"]') or card
                    href = link_el.get_attribute('href') if link_el else ""

                    if not href or href in seen_urls:
                        continue
                    seen_urls.add(href)

                    title_el = card.query_selector('h2, [class*="title"]')
                    location_el = card.query_selector('[class*="location"]')

                    title = title_el.inner_text() if title_el else link_el.inner_text().split('\n')[0]
                    location = location_el.inner_text() if location_el else ""

                    if not self._matches_query(title, filters.query):
                        continue

                    jobs.append(Job(
                        title=title.strip(),
                        company="Microsoft",
                        location=location.strip(),
                        url=urljoin("https://jobs.careers.microsoft.com", href),
                        source="crawler",
                        remote="remote" in location.lower(),
                        experience_level=self._infer_level(title),
                    ))

                    if len(jobs) >= filters.limit:
                        break
                except Exception:
                    continue

        except PlaywrightTimeout:
            pass
        except Exception as e:
            print(f"Error crawling Microsoft: {e}")
        finally:
            page.close()

        return jobs

    def _crawl_openai(self, company: dict, filters: JobFilters) -> list[Job]:
        """Crawl OpenAI Careers."""
        page = self.browser.new_page()
        jobs = []

        try:
            url = "https://openai.com/careers/search"
            page.goto(url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)

            time.sleep(2)

            # Find job listings
            job_links = page.query_selector_all('a[href*="/careers/"]')

            seen_urls = set()
            for link in job_links:
                try:
                    href = link.get_attribute('href') or ""
                    if "/careers/search" in href or href in seen_urls:
                        continue
                    if "/careers/" not in href:
                        continue
                    seen_urls.add(href)

                    title = link.inner_text().strip()
                    if not title or len(title) > 100:
                        continue
                    if not self._matches_query(title, filters.query):
                        continue

                    jobs.append(Job(
                        title=title,
                        company="OpenAI",
                        location="San Francisco, CA",
                        url=urljoin("https://openai.com", href),
                        source="crawler",
                        remote=False,
                        experience_level=self._infer_level(title),
                    ))

                    if len(jobs) >= filters.limit:
                        break
                except Exception:
                    continue

        except PlaywrightTimeout:
            pass
        except Exception as e:
            print(f"Error crawling OpenAI: {e}")
        finally:
            page.close()

        return jobs

    def _crawl_netflix(self, company: dict, filters: JobFilters) -> list[Job]:
        """Crawl Netflix Jobs."""
        page = self.browser.new_page()
        jobs = []

        try:
            query = quote(filters.query)
            url = f"https://jobs.netflix.com/search?q={query}"

            page.goto(url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)

            time.sleep(2)

            job_cards = page.query_selector_all('[class*="job-card"], a[href*="/jobs/"]')

            seen_urls = set()
            for card in job_cards:
                try:
                    link_el = card.query_selector('a[href*="/jobs/"]') or card
                    href = link_el.get_attribute('href') if link_el else ""

                    if not href or href in seen_urls:
                        continue
                    seen_urls.add(href)

                    title = link_el.inner_text().strip().split('\n')[0]
                    if not self._matches_query(title, filters.query):
                        continue

                    jobs.append(Job(
                        title=title,
                        company="Netflix",
                        location="",
                        url=urljoin("https://jobs.netflix.com", href),
                        source="crawler",
                        remote=False,
                        experience_level=self._infer_level(title),
                    ))

                    if len(jobs) >= filters.limit:
                        break
                except Exception:
                    continue

        except PlaywrightTimeout:
            pass
        except Exception as e:
            print(f"Error crawling Netflix: {e}")
        finally:
            page.close()

        return jobs

    def _matches_query(self, title: str, query: str) -> bool:
        """Check if title matches any query term."""
        title_lower = title.lower()
        query_terms = query.lower().split()
        return any(term in title_lower for term in query_terms)

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
