"""ATS detection logic."""

import re
from typing import Optional
from urllib.parse import urlparse
import httpx


class ATSDetector:
    """Detects which ATS system a career page uses."""

    ATS_PATTERNS = {
        "greenhouse": [
            r"boards\.greenhouse\.io",
            r"greenhouse\.io/embed",
            r"api\.greenhouse\.io",
        ],
        "lever": [
            r"jobs\.lever\.co",
            r"lever\.co/embed",
        ],
        "ashby": [
            r"jobs\.ashbyhq\.com",
            r"ashbyhq\.com/api",
        ],
        "workday": [
            r"\.myworkdayjobs\.com",
            r"workday\.com",
            r"wd\d+\.myworkdaysite\.com",
        ],
    }

    HTML_INDICATORS = {
        "greenhouse": [
            "greenhouse",
            "grnhse_app",
            "greenhouse-job-board",
        ],
        "lever": [
            "lever-jobs-container",
            "lever-job-title",
            "jobs.lever.co",
        ],
        "ashby": [
            "ashby-job-posting",
            "ashbyhq",
        ],
        "workday": [
            "workday",
            "WD-",
            "wd-",
        ],
    }

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self.client = httpx.Client(
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
            follow_redirects=True,
        )

    def detect(self, career_url: str) -> str:
        """Detect ATS type from career URL.

        Args:
            career_url: The company's career page URL.

        Returns:
            ATS type: 'greenhouse', 'lever', 'ashby', 'workday', or 'unknown'
        """
        # First check URL patterns
        ats_type = self._check_url_patterns(career_url)
        if ats_type:
            return ats_type

        # Fetch page and check HTML content
        try:
            response = self.client.get(career_url)
            if response.status_code == 200:
                ats_type = self._check_html_content(response.text)
                if ats_type:
                    return ats_type

                # Check for iframe sources
                ats_type = self._check_iframe_sources(response.text)
                if ats_type:
                    return ats_type
        except Exception:
            pass

        return "unknown"

    def _check_url_patterns(self, url: str) -> Optional[str]:
        """Check URL against known ATS patterns."""
        for ats_type, patterns in self.ATS_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return ats_type
        return None

    def _check_html_content(self, html: str) -> Optional[str]:
        """Check HTML content for ATS indicators."""
        html_lower = html.lower()
        for ats_type, indicators in self.HTML_INDICATORS.items():
            for indicator in indicators:
                if indicator.lower() in html_lower:
                    return ats_type
        return None

    def _check_iframe_sources(self, html: str) -> Optional[str]:
        """Check iframe src attributes for ATS URLs."""
        iframe_pattern = r'<iframe[^>]+src=["\']([^"\']+)["\']'
        matches = re.findall(iframe_pattern, html, re.IGNORECASE)
        for src in matches:
            ats_type = self._check_url_patterns(src)
            if ats_type:
                return ats_type
        return None

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self) -> "ATSDetector":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
