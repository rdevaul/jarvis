# Jarvis

Conversational work tracker and status update generator for Confluence.

Jarvis uses Claude to have natural conversations about your work, then generates structured updates for your Confluence pages—including dated journal entries and project status updates.

## Features

- **Conversational interface**: Describe your work naturally; Jarvis asks clarifying questions
- **Journal entries**: Timestamped summaries added under your log/journal section
- **Project updates**: Structured project entries with classification, status, next steps, executive summary, prototypes, and supporting work
- **Configurable page structure**: Map your Confluence page's headings during setup
- **Confluence Server/Data Center support**: Works with self-hosted Confluence instances

## Installation

### Prerequisites

- Python 3.11+
- A Confluence Server/Data Center instance with API access
- An Anthropic API key for Claude

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/jarvis.git
   cd jarvis
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install the package**:
   ```bash
   pip install -e .
   ```

4. **Create a `.env` file** in the project root:
   ```bash
   # Confluence Configuration
   CONFLUENCE_URL=https://confluence.yourcompany.com
   CONFLUENCE_TOKEN=your_confluence_token_here

   # Anthropic Configuration
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

## Getting API Keys

### Confluence Personal Access Token

1. Log in to your Confluence instance
2. Click your profile icon → **Settings** (or **Profile**)
3. Look for **Personal Access Tokens** in the sidebar
4. Click **Create token**
5. Give it a name (e.g., "Jarvis") and create
6. Copy the token immediately—it won't be shown again

### Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign in or create an account
3. Navigate to **Settings** → **API Keys**
4. Click **Create Key**
5. Copy the key (starts with `sk-ant-`)

## Usage

### First-time setup

Configure Jarvis for your Confluence page:

```bash
jarvis --configure
```

This will:
1. Ask for your Confluence page URL
2. Fetch the page and display all headings
3. Let you specify which heading is for journal/log entries
4. Let you specify which heading(s) contain projects

Configuration is saved to `~/.jarvis/config.json`.

### Daily use

Start a conversation about your work:

```bash
jarvis
```

Jarvis will:
1. Connect to your configured Confluence page
2. Ask what you've been working on
3. Have a natural conversation to gather details
4. Prompt you to type `done` when ready
5. Show a preview of what will be generated
6. Push updates to Confluence after your confirmation

### Command-line options

```bash
jarvis                     # Start conversation with default page
jarvis --configure         # Run configuration wizard
jarvis --url URL           # Use a specific Confluence page URL
```

## Project Structure

```
jarvis/
├── src/jarvis/
│   ├── cli.py          # Entry point and conversation loop
│   ├── config.py       # Page configuration management
│   ├── confluence.py   # Confluence API integration
│   ├── conversation.py # Claude-powered dialogue
│   └── models.py       # Data models (JournalEntry, Project, etc.)
├── .env                # API keys (not tracked in git)
├── pyproject.toml      # Project configuration
└── README.md
```

## Generated Content Format

### Journal Entry

Added under your configured journal heading with timestamp:

```
### 2025-01-09 14:35

Summary of work accomplished during this session...
```

### Project Entry

Created or updated under your configured project headings:

```
### Project Title

Classification: Moonshot
Status: Active development
Next Steps: Complete prototype testing

#### Executive Summary
Description of what the project explores and why it's significant...

#### Prototypes
Description of physical or software prototypes...

#### Simulation, White Paper, and Supporting Work Products
Supporting materials and research...
```

## License

MIT License - see LICENSE file for details.
