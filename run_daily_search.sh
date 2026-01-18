#!/bin/bash
# Daily job search script
# Add this to your crontab for automated searches

# Configuration - UPDATE THESE PATHS
PROJECT_DIR="/Users/mingshen/workspace/job-search-agent"
RESUME_PATH="/Users/mingshen/Desktop/Seraph Shen/Career/Ming Shen Resume 2025.pdf"
ANTHROPIC_API_KEY="your-api-key-here"  # Or source from a secure location

# Job search settings
QUERY="machine learning"
PREFERENCES="Senior MLE level (NOT Principal or Staff). Location must be Remote, San Diego, or Bay Area. Focus on LLMs and NLP."
CATEGORIES="ai_labs big_tech ai_startups additional"

# Logging
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/search_$(date +%Y%m%d_%H%M%S).log"

# Run the search
cd "$PROJECT_DIR"
source .venv/bin/activate

export ANTHROPIC_API_KEY

echo "Starting scheduled search at $(date)" | tee "$LOG_FILE"

python scheduled_search.py \
    --resume "$RESUME_PATH" \
    --query "$QUERY" \
    --categories $CATEGORIES \
    --preferences "$PREFERENCES" \
    --limit 20 \
    2>&1 | tee -a "$LOG_FILE"

echo "Search completed at $(date)" | tee -a "$LOG_FILE"

# Optional: Send notification (uncomment and configure as needed)
# Example for macOS notification:
# osascript -e 'display notification "Job search completed" with title "Job Search Agent"'

# Example for email (requires mail command configured):
# cat "$LOG_FILE" | mail -s "Daily Job Search Results" your@email.com
