import json

from anthropic import Anthropic

from config import Config
from models import Job, MatchResult, Resume


def match_jobs(resume: Resume, jobs: list[Job], preferences: str = "") -> list[MatchResult]:
    """Use Claude to match and rank jobs against a resume and preferences.

    Args:
        resume: Parsed resume data
        jobs: List of jobs to match against
        preferences: Optional natural language description of job preferences

    Returns:
        List of MatchResult objects sorted by score (highest first)
    """
    if not jobs:
        return []

    client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    # Build resume summary for the prompt
    resume_summary = f"""
Skills: {', '.join(resume.skills[:20])}
Previous Roles: {', '.join(resume.job_titles[:5])}
Years of Experience: {resume.years_experience or 'Not specified'}
Education: {', '.join(resume.education[:3])}
Summary: {resume.summary}
"""

    # Build preferences section
    preferences_section = ""
    if preferences:
        preferences_section = f"""
CANDIDATE'S JOB PREFERENCES:
{preferences}

IMPORTANT: Weight the candidate's stated preferences heavily in scoring. Jobs that match their preferences should score higher.
"""

    # Build jobs list for the prompt
    jobs_text = ""
    for i, job in enumerate(jobs):
        jobs_text += f"""
Job {i+1}:
- Title: {job.title}
- Company: {job.company}
- Location: {job.location}
- Remote: {'Yes' if job.remote else 'No'}
- Description: {job.description[:500]}...
---
"""

    prompt = f"""You are a job matching expert. Analyze how well each job matches the candidate's background and preferences.

CANDIDATE PROFILE:
{resume_summary}
{preferences_section}
JOBS TO EVALUATE:
{jobs_text}

For each job, provide a match score (0-100) and brief reasoning.
Consider:
- Skill alignment (do they have the required skills?)
- Experience level match
- Role fit (does the job title/responsibilities align with their background?)
- Preference match (does the job match their stated preferences for company, location, level, etc.?)

Return a JSON array with objects for each job:
[
  {{"job_index": 1, "score": 85, "reasoning": "Strong match because..."}},
  ...
]

Order by job_index (1, 2, 3...). Return ONLY valid JSON, no other text."""

    response = client.messages.create(
        model=Config.CLAUDE_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.content[0].text.strip()

    # Handle potential markdown code blocks
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])

    scores = json.loads(response_text)

    # Build results
    results = []
    for score_data in scores:
        job_index = score_data.get("job_index", 0) - 1
        if 0 <= job_index < len(jobs):
            results.append(
                MatchResult(
                    job=jobs[job_index],
                    score=score_data.get("score", 0),
                    reasoning=score_data.get("reasoning", ""),
                )
            )

    # Sort by score descending
    results.sort(key=lambda x: x.score, reverse=True)

    return results
