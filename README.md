# Job Search Agent

An AI-powered job search agent that crawls career pages, matches jobs against your resume, and ranks them based on your preferences.

## Features

- **Resume Parsing**: Extracts skills, experience, and job titles from your PDF resume using Claude AI
- **Universal Web Crawler**: Crawls any company career page without custom code per company
- **Smart Matching**: Uses Claude AI to score and rank jobs based on your background and preferences
- **Natural Language Preferences**: Describe your ideal job in plain English (e.g., "Senior MLE, Remote or Bay Area, focus on LLMs")
- **Scheduled Searches**: Automated daily/weekly job searches with cron
- **Deduplication**: SQLite-based tracking to only show new jobs
- **Multiple Output Formats**: CLI table display and JSON export

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/job-search-agent.git
cd job-search-agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## Configuration

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

## Usage

### Search Target Companies

```bash
python search.py \
  --resume path/to/your/resume.pdf \
  --query "machine learning" \
  --categories ai_labs big_tech ai_startups \
  --preferences "Senior MLE level, Remote or Bay Area, focus on LLMs"
```

### Options

| Option | Description |
|--------|-------------|
| `--resume` | Path to your PDF resume (required) |
| `--query` | Job search keywords (required) |
| `--categories` | Company categories: `ai_labs`, `big_tech`, `ai_startups` |
| `--location` | Filter by location |
| `--remote` | Only show remote jobs |
| `--preferences` | Natural language job preferences |
| `--limit` | Max jobs per company (default: 10) |
| `--output` | Output JSON file path |

### Add New Companies

Edit `companies.yaml` to add new target companies:

```yaml
ai_startups:
  - name: New Company
    careers_url: https://newcompany.com/careers
```

The universal crawler will automatically handle any career page.

## Scheduled Searches

Run automated job searches daily or weekly with deduplication (only shows new jobs).

### Manual Scheduled Search

```bash
python scheduled_search.py \
  --resume path/to/resume.pdf \
  --query "machine learning" \
  --categories ai_labs big_tech ai_startups \
  --preferences "Senior MLE, Bay Area or Remote"
```

### View Statistics

```bash
# Show database statistics
python scheduled_search.py --stats

# Show new jobs from last 7 days
python scheduled_search.py --recent --days 7
```

### Setup Automated Daily Search (Cron)

1. Edit the `run_daily_search.sh` script with your paths and API key

2. Make it executable:
```bash
chmod +x run_daily_search.sh
```

3. Add to crontab for daily searches at 9 AM:
```bash
crontab -e
# Add this line:
0 9 * * * /path/to/job-search-agent/run_daily_search.sh
```

For weekly searches (every Monday at 9 AM):
```bash
0 9 * * 1 /path/to/job-search-agent/run_daily_search.sh
```

### Results Storage

- Results are saved to `search_results/search_YYYY-MM-DD_HHMMSS.json`
- Seen jobs are tracked in `jobs.db` (SQLite)
- Logs are saved to `logs/` directory

## Project Structure

```
job-search-agent/
├── search.py            # Main CLI entry point
├── scheduled_search.py  # Scheduled search with deduplication
├── run_daily_search.sh  # Cron job script
├── companies.yaml       # Target companies configuration
├── generic_crawler.py   # Universal web crawler (Playwright)
├── company_fetcher.py   # Orchestrates job fetching
├── job_store.py         # SQLite job storage & deduplication
├── matcher.py           # Claude AI job matching
├── resume_parser.py     # PDF resume parsing
├── models.py            # Data models (Job, Resume, etc.)
├── output.py            # CLI table and JSON output
├── requirements.txt     # Python dependencies
├── search_results/      # Date-stamped search results (auto-created)
├── logs/                # Search logs (auto-created)
└── jobs.db              # SQLite database for deduplication (auto-created)
```

## Requirements

- Python 3.11+
- Anthropic API key (for Claude)
- Playwright (for web crawling)

## License

MIT
