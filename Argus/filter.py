"""Job title filtering with token-based matching."""

import re
from typing import List, Set, Tuple


class JobFilter:
    """Filter jobs based on title matching."""

    # Core role words that must match
    ROLE_WORDS = {"engineer", "scientist", "researcher"}

    # Synonyms for role words
    ROLE_SYNONYMS = {
        "engineer": {"eng"},
        "scientist": {"sci"},
        "researcher": {"research"},
    }

    # Domain/specialty synonyms (more conservative)
    DOMAIN_SYNONYMS = {
        "machine": {"ml"},
        "learning": {"ml"},
        "ml": {"machine", "learning"},
        "ai": {"artificial", "intelligence"},
        "artificial": {"ai"},
        "intelligence": {"ai"},
        "applied": {"applications"},
    }

    # Level synonyms
    LEVEL_SYNONYMS = {
        "senior": {"sr", "sr."},
        "staff": {"staff"},
        "principal": {"principal"},
        "junior": {"jr", "jr.", "associate", "entry"},
        "lead": {"lead"},
        "director": {"director"},
        "manager": {"manager", "mgr"},
        "head": {"head"},
        "vp": {"vp", "vice president"},
    }

    def __init__(self, target_titles: List[str], min_score: float = 0.7,
                 exclude_levels: List[str] = None):
        """Initialize filter with target job titles.

        Args:
            target_titles: List of job titles to match against.
            min_score: Minimum similarity score (0-1) to consider a match.
            exclude_levels: List of levels to exclude (e.g., ['staff', 'principal']).
        """
        self.target_titles = target_titles
        self.min_score = min_score
        self.exclude_levels = [lvl.lower() for lvl in (exclude_levels or [])]
        self._excluded_tokens = self._build_excluded_tokens()
        self._parsed_targets = [
            self._parse_title(title) for title in target_titles
        ]

    def _build_excluded_tokens(self) -> Set[str]:
        """Build set of tokens to exclude based on exclude_levels."""
        excluded = set()
        for level in self.exclude_levels:
            excluded.add(level)
            # Also add synonyms for the level
            if level in self.LEVEL_SYNONYMS:
                excluded.update(self.LEVEL_SYNONYMS[level])
        return excluded

    def _has_excluded_level(self, job_title: str) -> bool:
        """Check if job title contains an excluded level."""
        if not self._excluded_tokens:
            return False
        tokens = self._normalize(job_title)
        return bool(tokens & self._excluded_tokens)

    def _normalize(self, text: str) -> Set[str]:
        """Convert text to lowercase token set."""
        text = text.lower()
        text = re.sub(r'[^\w\s-]', ' ', text)
        return set(text.split())

    def _parse_title(self, title: str) -> dict:
        """Parse a job title into components."""
        tokens = self._normalize(title)

        # Find role word
        role = None
        for token in tokens:
            if token in self.ROLE_WORDS:
                role = token
                break
            # Check role synonyms
            for role_word, syns in self.ROLE_SYNONYMS.items():
                if token in syns:
                    role = role_word
                    break

        # Get domain tokens (non-role, non-level words)
        level_words = set()
        for syns in self.LEVEL_SYNONYMS.values():
            level_words.update(syns)
        level_words.update(self.LEVEL_SYNONYMS.keys())

        domain = tokens - self.ROLE_WORDS - level_words
        for role_word, syns in self.ROLE_SYNONYMS.items():
            domain -= syns

        return {"role": role, "domain": domain, "tokens": tokens}

    def _expand_domain(self, domain: Set[str]) -> Set[str]:
        """Expand domain tokens with synonyms."""
        expanded = set(domain)
        for token in domain:
            if token in self.DOMAIN_SYNONYMS:
                expanded.update(self.DOMAIN_SYNONYMS[token])
        return expanded

    def _matches_target(self, job_parsed: dict, target_parsed: dict) -> Tuple[bool, float]:
        """Check if job matches a specific target."""
        # Role must match
        if target_parsed["role"] and job_parsed["role"] != target_parsed["role"]:
            return False, 0.0

        # Expand domains for comparison
        job_domain = self._expand_domain(job_parsed["domain"])
        target_domain = self._expand_domain(target_parsed["domain"])

        # Calculate domain overlap
        if not target_domain:
            # No specific domain required
            return True, 1.0

        intersection = job_domain & target_domain
        score = len(intersection) / len(target_domain) if target_domain else 1.0

        return score >= self.min_score, score

    def matches(self, job_title: str) -> Tuple[bool, float]:
        """Check if a job title matches any target title.

        Args:
            job_title: The job title to check.

        Returns:
            Tuple of (is_match, best_score)
        """
        # Check for excluded levels first
        if self._has_excluded_level(job_title):
            return False, 0.0

        job_parsed = self._parse_title(job_title)
        best_score = 0.0
        best_match = False

        for target_parsed in self._parsed_targets:
            is_match, score = self._matches_target(job_parsed, target_parsed)
            if score > best_score:
                best_score = score
                best_match = is_match

        return best_match, best_score

    def filter_jobs(self, jobs: List) -> List:
        """Filter a list of jobs by title matching.

        Args:
            jobs: List of Job objects.

        Returns:
            List of matching Job objects.
        """
        matching = []
        for job in jobs:
            is_match, score = self.matches(job.title)
            if is_match:
                matching.append(job)
        return matching


class LocationFilter:
    """Filter jobs based on location requirements."""

    # Keywords indicating remote work
    REMOTE_KEYWORDS = [
        "remote",
        "work from home",
        "wfh",
        "distributed",
        "anywhere",
    ]

    # State abbreviations and aliases (including major cities)
    STATE_ALIASES = {
        "california": [
            "ca", "calif", "california",
            "san francisco", "sf", "bay area",
            "los angeles", "la", "santa monica",
            "san diego", "san jose", "palo alto",
            "mountain view", "sunnyvale", "menlo park",
            "cupertino", "oakland", "berkeley",
            "south san francisco", "redwood city",
            "santa clara", "irvine", "pasadena",
        ],
        "new york": ["ny", "new york", "nyc", "manhattan", "brooklyn"],
        "texas": ["tx", "texas", "austin", "dallas", "houston"],
        "washington": ["wa", "washington", "seattle", "bellevue", "redmond"],
        "massachusetts": ["ma", "mass", "massachusetts", "boston", "cambridge"],
        "colorado": ["co", "colorado", "denver", "boulder"],
        "illinois": ["il", "illinois", "chicago"],
        "georgia": ["ga", "georgia", "atlanta"],
        "pennsylvania": ["pa", "penn", "pennsylvania", "pittsburgh", "philadelphia"],
        "florida": ["fl", "florida", "miami"],
    }

    def __init__(self, locations: List[str], allow_remote: bool = True):
        """Initialize location filter.

        Args:
            locations: List of target locations (states, cities, or 'remote').
            allow_remote: Whether to include remote positions.
        """
        self.locations = [loc.lower() for loc in locations]
        self.allow_remote = allow_remote
        self._location_patterns = self._build_patterns()

    def _build_patterns(self) -> List[str]:
        """Build list of location patterns to match."""
        patterns = []

        for loc in self.locations:
            # Check if it's a known state
            if loc in self.STATE_ALIASES:
                patterns.extend(self.STATE_ALIASES[loc])
            else:
                # Add as-is (city name, etc.)
                patterns.append(loc)

            # Check if location is an alias for a state
            for state, aliases in self.STATE_ALIASES.items():
                if loc in aliases:
                    patterns.extend(aliases)
                    break

        return list(set(patterns))

    def _is_remote(self, location: str) -> bool:
        """Check if location indicates remote work."""
        location_lower = location.lower()
        return any(kw in location_lower for kw in self.REMOTE_KEYWORDS)

    def _matches_location(self, location: str) -> bool:
        """Check if job location matches any target location."""
        if not location:
            return False

        location_lower = location.lower()

        # Check for remote
        if self.allow_remote and self._is_remote(location_lower):
            return True

        # Check for location patterns
        for pattern in self._location_patterns:
            if pattern in location_lower:
                return True

        return False

    def matches(self, job_location: str) -> bool:
        """Check if a job location matches the filter.

        Args:
            job_location: The job's location string.

        Returns:
            True if location matches, False otherwise.
        """
        if not job_location:
            # No location info - could be remote or unspecified
            return False

        return self._matches_location(job_location)

    def filter_jobs(self, jobs: List) -> List:
        """Filter a list of jobs by location.

        Args:
            jobs: List of Job objects.

        Returns:
            List of matching Job objects.
        """
        return [job for job in jobs if self.matches(job.location or "")]


class TitleNormalizer:
    """Normalize job titles for comparison."""

    # Common prefixes/suffixes to strip
    STRIP_PATTERNS = [
        r'^\s*\[.*?\]\s*',  # [Remote], [Contract], etc.
        r'\s*\(.*?\)\s*$',  # (Remote), (Contract), etc.
        r'\s*-\s*(remote|hybrid|onsite|contract|temporary|intern).*$',
        r'\s*,\s*(remote|hybrid|onsite).*$',
    ]

    @classmethod
    def normalize(cls, title: str) -> str:
        """Normalize a job title."""
        normalized = title.strip()

        for pattern in cls.STRIP_PATTERNS:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)

        # Collapse whitespace
        normalized = ' '.join(normalized.split())

        return normalized
