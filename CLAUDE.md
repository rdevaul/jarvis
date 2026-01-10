# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Jarvis is a conversational work tracker that integrates with Confluence. It uses Claude to have natural conversations with users about their work, then generates structured updates for their Confluence journal/project pages.

## Build Commands

```bash
# Install in development mode (use existing .venv)
source .venv/bin/activate
pip install -e ".[dev]"

# Run the CLI
jarvis

# Configure a Confluence page (first-time setup or reconfigure)
jarvis --configure

# Use a specific page URL
jarvis --url "https://confluence.example.com/display/SPACE/Page"

# Lint
ruff check src/

# Type check
mypy src/

# Run tests
pytest
```

## Configuration

**Environment variables** (`.env` file, not tracked in git):
- `CONFLUENCE_URL` - Base URL for Confluence Server/Data Center
- `CONFLUENCE_TOKEN` - Personal Access Token for Confluence API
- `ANTHROPIC_API_KEY` - Claude API key

**Page configuration** (`~/.jarvis/config.json`):
- Created via `jarvis --configure`
- Maps Confluence page URLs to their heading structure
- Stores which headings are used for journal entries vs projects

## Architecture

```
src/jarvis/
├── cli.py          # Entry point, argument parsing, conversation loop
├── config.py       # Page configuration management (~/.jarvis/config.json)
├── conversation.py # Claude-powered dialogue and structured data extraction
├── confluence.py   # Confluence REST API integration (read/write pages)
└── models.py       # Pydantic models: JournalEntry, Project, ConversationState
```

**Data flow:**
1. On first run, `--configure` wizard asks user to map page headings
2. CLI loads config and existing projects from Confluence page
3. User has natural conversation with Claude about their work
4. When user says "done", Claude extracts structured data (journal entries, project updates)
5. User confirms, then updates are pushed to Confluence under configured headings

**Key models:**
- `JournalEntry`: Dated summary of work with `to_confluence_html()` method
- `Project`: Full project structure (classification, status, next steps, executive summary, prototypes, supporting work)
- `PageConfig`: Maps a Confluence page URL to its journal heading and project headings

**Confluence integration:**
- Uses `atlassian-python-api` library
- `extract_headings()` parses page to show available section headings
- `prepend_journal_entry_configured()` inserts entries after user-specified heading
- `update_or_create_project_configured()` creates projects under user-specified headings
