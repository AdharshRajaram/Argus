"""Base interface for career page fetchers."""

from abc import ABC, abstractmethod
from typing import List, Optional
import httpx

from ..models import Job


class CareerFetcher(ABC):
    """Abstract base class for ATS-specific job fetchers."""

    def __init__(self, company_name: str, career_url: str, timeout: float = 30.0):
        self.company_name = company_name
        self.career_url = career_url
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
                follow_redirects=True,
            )
        return self._client

    @abstractmethod
    def fetch_job_list(self) -> List[Job]:
        """Fetch all jobs from the career page.

        Returns:
            List of Job objects found on the career page.
        """
        pass

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "CareerFetcher":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
