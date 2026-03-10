.PHONY: setup start update agent test clean

# First-time setup: create venv, install deps, run wizard
setup:
	@echo "🤖 Setting up JobHunter..."
	python -m venv venv
	. venv/bin/activate && pip install -e .
	. venv/bin/activate && jobhunter --setup

# Run full pipeline
start:
	jobhunter

# Incremental daily update (new jobs only) + email
update:
	jobhunter --update

# Quick test (2 sources, ~3 min)
quick:
	jobhunter --mode quick

# Install daily 8am automation
agent:
	jobhunter --install-agent

# Show today's digest
digest:
	jobhunter --show-digest

# Run tests
test:
	pytest tests/ -v

# Clean generated outputs (keep memory/job_pool.json)
clean:
	rm -rf outputs/digests/* outputs/applications/*
	@echo "Cleaned digests and applications. Excel and job pool preserved."
