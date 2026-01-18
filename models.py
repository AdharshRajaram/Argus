from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Resume(BaseModel):
    """Parsed resume data."""
    skills: list[str] = Field(default_factory=list, description="Technical and soft skills")
    job_titles: list[str] = Field(default_factory=list, description="Previous job titles")
    years_experience: Optional[int] = Field(None, description="Total years of experience")
    education: list[str] = Field(default_factory=list, description="Education background")
    summary: str = Field("", description="Brief professional summary")
    raw_text: str = Field("", description="Original resume text")


class Job(BaseModel):
    """Job listing from any source."""
    title: str
    company: str
    location: str = ""
    description: str = ""
    url: str = ""
    posted_date: Optional[datetime] = None
    source: str = ""  # e.g., "jsearch", "google", "meta", "apple"
    remote: bool = False
    experience_level: str = ""  # entry, mid, senior


class JobFilters(BaseModel):
    """Filters for job search."""
    query: str
    location: Optional[str] = None
    remote_only: bool = False
    experience_level: Optional[str] = None  # entry, mid, senior
    days_ago: int = 30
    limit: int = 10


class MatchResult(BaseModel):
    """Result of matching a job against a resume."""
    job: Job
    score: int = Field(ge=0, le=100, description="Match score 0-100")
    reasoning: str = Field("", description="Explanation for the score")
