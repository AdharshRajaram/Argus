#!/usr/bin/env python3
"""Quick runner script to test the job search."""

import os
import shutil

# Change to project directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Remove old results
if os.path.exists("job_results"):
    shutil.rmtree("job_results")

# Run the search
from job_search_agent.orchestrator import Orchestrator

orchestrator = Orchestrator(
    companies_file="config/companies.yaml",
    titles_file="config/titles.yaml",
    output_dir="job_results",
    timeout=30.0,
)

summary = orchestrator.run()
print("\nDone!")
