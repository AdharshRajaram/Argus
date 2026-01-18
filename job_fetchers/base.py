from abc import ABC, abstractmethod

from models import Job, JobFilters


class BaseJobFetcher(ABC):
    """Abstract base class for job fetchers."""

    name: str = "base"

    @abstractmethod
    def fetch_jobs(self, filters: JobFilters) -> list[Job]:
        """Fetch jobs matching the given filters.

        Args:
            filters: Job search filters including query, location, etc.

        Returns:
            List of Job objects matching the criteria.
        """
        pass

    def _normalize_experience_level(self, level: str) -> str:
        """Normalize experience level to standard format."""
        level_lower = level.lower()
        if any(x in level_lower for x in ["entry", "junior", "associate", "i ", " 1", "new grad"]):
            return "entry"
        if any(x in level_lower for x in ["senior", "sr", "lead", "principal", "staff"]):
            return "senior"
        if any(x in level_lower for x in ["mid", "intermediate", "ii ", " 2"]):
            return "mid"
        return ""
