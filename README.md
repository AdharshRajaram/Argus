# Argus

A Python-based job search agent that automatically crawls company career pages to find relevant job listings. It supports multiple Applicant Tracking Systems (ATS), user profiles for different preferences, and provides flexible filtering options.

## Features

- **Multi-ATS Support**: Automatically detects and crawls jobs from:
  - Greenhouse
  - Lever
  - Ashby
  - Workday
  - Amazon (custom API)
  - Google (custom fetcher)
  - TikTok (custom API)
  - Uber (custom API)
  - Custom career pages (via Playwright)

- **User Profiles**: Support for multiple users with different job preferences
  - Each profile has its own titles, locations, and filters
  - Results are stored separately per profile
  - Optionally customize company lists per profile

- **Smart Filtering**:
  - Filter by job titles (with fuzzy matching)
  - Filter by location (states, cities, remote)
  - Exclude specific levels (staff, principal, lead, etc.)

- **Auto-Detection**: Automatically detects ATS type from career URLs and finds direct API endpoints

- **Incremental Results**: Saves results organized by date and company, avoiding duplicates across runs

## Installation

```bash
# Clone the repository
git clone https://github.com/mshen1019/Argus.git
cd Argus

# (Optional) Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for custom ATS sites)
python -m playwright install chromium
```

## Quick Start

```bash
# Run with the default profile
python run_search.py

# Run with a specific profile
python run_search.py alice
```

This will:
1. Load the profile configuration from `config/profiles/<name>/`
2. Load companies from the profile or fall back to `config/companies.yaml`
3. Crawl all companies and save matching jobs to `job_results/<profile>/`

## User Profiles

Profiles allow multiple users to have different job search preferences. Each profile is a directory under `config/profiles/` containing a `titles.yaml` file.

### Profile Structure

```
config/
├── companies.yaml              # Global company list (shared by all profiles)
└── profiles/
    ├── default/
    │   └── titles.yaml         # Default user preferences
    ├── alice/
    │   ├── titles.yaml         # Alice's job preferences
    │   └── companies.yaml      # (Optional) Alice's custom company list
    └── bob/
        └── titles.yaml         # Bob's job preferences
```

### Creating a New Profile

1. Create a new directory under `config/profiles/`:
   ```bash
   mkdir config/profiles/myprofile
   ```

2. Create a `titles.yaml` with your preferences:
   ```yaml
   titles:
     - Data Scientist
     - Machine Learning Engineer
     - Research Scientist

   locations:
     - California
     - New York
     - Remote

   exclude_levels:
     - junior
     - intern
   ```

3. (Optional) Create a custom `companies.yaml` if you want to search different companies

4. Run your search:
   ```bash
   python run_search.py myprofile
   # or
   python search.py --profile myprofile
   ```

### Profile Output

Results are stored separately for each profile:

```
job_results/
├── default/
│   └── 2026-01-25/
│       ├── OpenAI/
│       │   └── jobs.json
│       └── ...
├── alice/
│   └── 2026-01-25/
│       └── ...
└── bob/
    └── 2026-01-25/
        └── ...
```

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

  - name: Amazon
    career_url: https://www.amazon.jobs
    ats_type: amazon

  - name: Google
    career_url: https://careers.google.com/jobs/results/
    ats_type: google
```

**Supported ATS types:**
- `greenhouse` - Greenhouse.io job boards
- `lever` - Lever.co job boards
- `ashby` - Ashby HQ job boards
- `workday` - Workday job sites
- `amazon` - Amazon.jobs (custom API)
- `google` - Google Careers (custom fetcher)
- `tiktok` - TikTok/ByteDance careers (custom API)
- `uber` - Uber careers (custom API)
- `meta` - Meta careers (limited due to bot detection)
- `custom` - Custom career pages (uses Playwright)

### Job Titles & Filters (`config/profiles/<name>/titles.yaml`)

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
- `intern` - Internship positions

## CLI Usage

For more control, use the CLI directly:

```bash
# Using profiles (recommended)
python search.py --profile default
python search.py --profile alice --timeout 60

# Using explicit config files
python search.py \
  --companies config/companies.yaml \
  --titles config/profiles/default/titles.yaml \
  --output job_results/custom
```

**Options:**
- `-p, --profile` - Profile name (loads from `config/profiles/<name>/`)
- `-c, --companies` - Path to companies YAML file (overrides profile)
- `-t, --titles` - Path to job titles YAML file (overrides profile)
- `-o, --output` - Output directory for results
- `--timeout` - Request timeout in seconds (default: 30)

## Output

Results are saved in a profile and date-organized structure:

```
job_results/
└── default/
    └── 2026-01-25/
        ├── OpenAI/
        │   ├── jobs.json
        │   └── jobs.csv
        ├── Anthropic/
        │   ├── jobs.json
        │   └── jobs.csv
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
    "discovered_at": "2026-01-25T10:30:00"
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
Argus/
├── config/
│   ├── companies.yaml          # Global company list
│   └── profiles/               # User profiles
│       ├── default/
│       │   └── titles.yaml
│       ├── Ming/
│       │   └── titles.yaml
│       └── Yaxi/
│           └── titles.yaml
├── Argus/                      # Main package
│   ├── orchestrator.py         # Main orchestration logic
│   ├── filter.py               # Job title/location filtering
│   ├── store.py                # Job persistence
│   ├── registry.py             # Company registry management
│   ├── models.py               # Data models
│   └── ats/                    # ATS-specific adapters
│       ├── greenhouse.py
│       ├── lever.py
│       ├── ashby.py
│       ├── workday.py
│       ├── amazon.py           # Amazon.jobs API
│       ├── google.py           # Google Careers
│       ├── tiktok.py           # TikTok/ByteDance
│       ├── uber.py             # Uber Careers
│       ├── generic.py          # Playwright-based fallback
│       └── detector.py         # ATS auto-detection
├── job_results/                # Output directory
│   ├── default/                # Results for default profile
│   └── <profile>/              # Results for other profiles
├── run_search.py               # Quick runner script
├── search.py                   # CLI entry point
├── fix_ats_config.py           # ATS config fixer tool
└── requirements.txt            # Dependencies
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
- Rideshare: Uber, Lyft
- Social: TikTok, Pinterest, LinkedIn
- And many more...

## Requirements

- Python 3.9+
- httpx
- playwright
- pyyaml

## Usage & Responsibility

This project is intended for **personal job search and small-scale use**.

Users are responsible for ensuring that their use of this tool complies with
the terms of service of the websites they access and with applicable laws
and regulations.

This tool performs **read-only access** to publicly available job postings.
It does **not** automate job applications, form submissions, or authentication
flows.

The author does not operate any centralized crawling service and does not
collect or store user data.

## License

MIT
