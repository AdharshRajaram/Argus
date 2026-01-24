"""ATS adapters for job fetching."""

from .base import CareerFetcher
from .detector import ATSDetector
from .greenhouse import GreenhouseFetcher
from .lever import LeverFetcher
from .ashby import AshbyFetcher
from .workday import WorkdayFetcher
from .generic import GenericFetcher

__all__ = [
    "CareerFetcher",
    "ATSDetector",
    "GreenhouseFetcher",
    "LeverFetcher",
    "AshbyFetcher",
    "WorkdayFetcher",
    "GenericFetcher",
]
