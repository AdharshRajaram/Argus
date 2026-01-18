import json
from pathlib import Path

import pdfplumber
from anthropic import Anthropic

from config import Config
from models import Resume


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from a PDF file."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
    return "\n".join(text_parts)


def parse_resume(pdf_path: str) -> Resume:
    """Parse a PDF resume and extract structured information using Claude."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"Resume not found: {pdf_path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Resume must be a PDF file")

    raw_text = extract_text_from_pdf(pdf_path)

    if not raw_text.strip():
        raise ValueError("Could not extract text from PDF")

    client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    prompt = f"""Analyze this resume and extract structured information.
Return a JSON object with these fields:
- skills: list of technical and soft skills mentioned
- job_titles: list of job titles/positions held
- years_experience: estimated total years of professional experience (integer or null)
- education: list of degrees/certifications
- summary: a brief 2-3 sentence professional summary

Resume text:
{raw_text}

Return ONLY valid JSON, no other text."""

    response = client.messages.create(
        model=Config.CLAUDE_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.content[0].text.strip()

    # Handle potential markdown code blocks
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])

    parsed = json.loads(response_text)

    return Resume(
        skills=parsed.get("skills", []),
        job_titles=parsed.get("job_titles", []),
        years_experience=parsed.get("years_experience"),
        education=parsed.get("education", []),
        summary=parsed.get("summary", ""),
        raw_text=raw_text,
    )
