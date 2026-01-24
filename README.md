# Job Search Agent

A Python-based job search agent that automatically crawls company career pages to find relevant ML/AI job listings. It supports multiple Applicant Tracking Systems (ATS) and provides flexible filtering options.

## Features

- **Multi-ATS Support**: Automatically detects and crawls jobs from:
  - Greenhouse
  - Lever
  - Ashby
  - Workday
  - Custom career pages (via Playwright)

- **Smart Filtering**:
  - Filter by job titles (with fuzzy matching)
  - Filter by location (states, cities, remote)
  - Exclude specific levels (staff, principal, lead, etc.)

- **Auto-Detection**: Automatically detects ATS type from career URLs and finds direct API endpoints

- **Incremental Results**: Saves results organized by date and company, avoiding duplicates

## Installation

```bash
# Clone the repository
git clone https://github.com/mshen1019/job-search-agent.git
cd job-search-agent

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for custom ATS sites)
python -m playwright install chromium
```

## Quick Start

```bash
# Run with default configuration
python run_search.py
```

This will:
1. Load companies from `config/companies.yaml`
2. Load job titles and filters from `config/titles.yaml`
3. Crawl all companies and save matching jobs to `job_results/`

## Configuration

### Companies (`config/companies.yaml`)

Define the companies to crawl:

```yaml
companies:
  - name: OpenAI
    career_url: https://jobs.ashbyhq.com/openai
    ats_type: ashby

  - name: Anthropic
    career_url: https://boards.greenhouse.io/anthropic
    ats_type: greenhouse

  - name: Mistral AI
    career_url: https://jobs.lever.co/mistral
    ats_type: lever
```

**Supported ATS types:**
- `greenhouse` - Greenhouse.io job boards
- `lever` - Lever.co job boards
- `ashby` - Ashby HQ job boards
- `workday` - Workday job sites
- `custom` - Custom career pages (uses Playwright)

### Job Titles & Filters (`config/titles.yaml`)

Configure target job titles, locations, and exclusions:

```yaml
titles:
  - Machine Learning Engineer
  - Senior Machine Learning Engineer
  - Research Scientist
  - Applied Scientist

locations:
  - California
  - Remote

# Exclude specific seniority levels
exclude_levels:
  - staff
  - principal
```

**Available exclusion levels:**
- `staff` - Staff-level positions
- `principal` - Principal-level positions
- `lead` - Lead roles
- `director` - Director-level positions
- `manager` - Manager roles
- `head` - Head of department roles
- `vp` - VP-level positions
- `junior` - Junior/Associate positions

## CLI Usage

For more control, use the CLI directly:

```bash
python search.py \
  --companies config/companies.yaml \
  --titles config/titles.yaml \
  --output job_results \
  --timeout 30
```

**Options:**
- `-c, --companies` - Path to companies YAML file (required)
- `-t, --titles` - Path to job titles YAML file (required)
- `-o, --output` - Output directory for results (default: `job_results`)
- `--timeout` - Request timeout in seconds (default: 30)

## Output

Results are saved in a date-organized structure:

```
job_results/
└── 2024-01-24/
    ├── OpenAI/
    │   └── jobs.json
    ├── Anthropic/
    │   └── jobs.json
    └── ...
```

Each `jobs.json` contains:

```json
[
  {
    "company": "OpenAI",
    "title": "Machine Learning Engineer",
    "url": "https://jobs.ashbyhq.com/openai/abc123",
    "location": "San Francisco, CA",
    "team": "Applied AI",
    "source": "ashby",
    "discovered_at": "2024-01-24T10:30:00"
  }
]
```

## Tools

### Fix ATS Configuration

Automatically detect and fix incorrect ATS types and career URLs:

```bash
python fix_ats_config.py
```

This will:
1. Validate each company's career URL
2. Auto-detect the correct ATS type
3. Find direct ATS URLs when companies use embedded job boards
4. Update `config/companies.yaml` with corrections

### Investigate Unverified Companies

For companies that couldn't be automatically verified:

```bash
python investigate_unverified.py
```

## Project Structure

```
job-search-agent/
├── config/
│   ├── companies.yaml      # Company list & career URLs
│   └── titles.yaml         # Target job titles & filters
├── job_search_agent/       # Main package
│   ├── orchestrator.py     # Main orchestration logic
│   ├── filter.py           # Job title/location filtering
│   ├── store.py            # Job persistence
│   ├── registry.py         # Company registry management
│   ├── models.py           # Data models
│   └── ats/                # ATS-specific adapters
│       ├── greenhouse.py
│       ├── lever.py
│       ├── ashby.py
│       ├── workday.py
│       ├── generic.py      # Playwright-based fallback
│       └── detector.py     # ATS auto-detection
├── run_search.py           # Quick runner script
├── search.py               # CLI entry point
├── fix_ats_config.py       # ATS config fixer tool
└── requirements.txt        # Dependencies
```

## Adding New Companies

1. Find the company's career page URL
2. Add to `config/companies.yaml`:

```yaml
  - name: New Company
    career_url: https://jobs.lever.co/newcompany
    ats_type: lever
```

3. If unsure about ATS type, set to `unknown` and run `fix_ats_config.py`

## Supported Companies

The default configuration includes 50+ tech companies:
- AI Labs: OpenAI, Anthropic, DeepMind, Mistral AI, Cohere, xAI, Perplexity AI
- Big Tech: Google, Meta, Apple, Microsoft, Amazon
- Finance: Stripe, Block, Coinbase, Plaid, Brex
- And many more...

## Requirements

- Python 3.9+
- httpx
- playwright
- pyyaml

## License

MIT
