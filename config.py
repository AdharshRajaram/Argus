import os


class Config:
    """Configuration for the job search agent."""

    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    RAPIDAPI_KEY: str = os.getenv("RAPIDAPI_KEY", "")

    # Claude model for matching
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

    # API endpoints
    JSEARCH_BASE_URL: str = "https://jsearch.p.rapidapi.com"
    GOOGLE_CAREERS_URL: str = "https://careers.google.com/api/v3/search/"
    META_CAREERS_URL: str = "https://www.metacareers.com/graphql"
    APPLE_JOBS_URL: str = "https://jobs.apple.com/api/role/search"

    @classmethod
    def validate(cls, sources: list[str] | None = None) -> list[str]:
        """Check for missing required configuration. Returns list of missing keys."""
        missing = []
        if not cls.ANTHROPIC_API_KEY:
            missing.append("ANTHROPIC_API_KEY")
        # Only require RAPIDAPI_KEY if jsearch is in sources
        if sources is None or "jsearch" in sources:
            if not cls.RAPIDAPI_KEY:
                missing.append("RAPIDAPI_KEY (for JSearch - get free key at rapidapi.com)")
        return missing
