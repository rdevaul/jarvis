"""Claude-powered conversation management for Jarvis."""

import os
from typing import Any

import anthropic
from dotenv import load_dotenv

from jarvis.models import ConversationState, JournalEntry, Project, ProjectClassification


SYSTEM_PROMPT = """You are Jarvis, an intelligent assistant that helps users track their work and generate status updates for Confluence.

Your role is to have a natural conversation to understand:
1. What work the user has been doing (could be today, this week, or any time period)
2. Which projects this work relates to
3. Any new projects that should be created
4. Key accomplishments, progress, and next steps

Be conversational and friendly. Ask clarifying questions when needed. Help the user articulate their work clearly and concisely.

When you have gathered enough information, you will help generate:
- A journal entry summarizing the work period
- Updates to existing projects (classification, status, next steps, executive summary, prototypes, supporting work)
- New project entries if needed

Keep responses concise. Focus on extracting actionable information.

IMPORTANT: When you believe you have gathered sufficient information to generate a meaningful journal entry and any relevant project updates, prompt the user by saying something like: "I think I have enough to work with. Type **done** when you're ready for me to generate your updates, or feel free to add more details."

Do not prompt for "done" too early - make sure you have at least a clear summary of work accomplished and any project context needed."""


EXTRACTION_PROMPT = """Based on our conversation, extract the following structured information. Return valid JSON only.

{
  "journal_entry": {
    "period_description": "today|this week|etc",
    "summary": "Summary of work done"
  },
  "projects_to_update": [
    {
      "title": "Project Name",
      "classification": "Moonshot|Core|Exploratory|Maintenance",
      "status": "One-line status",
      "next_steps": "One-line next steps",
      "executive_summary": "What and why",
      "prototypes": "Description or null",
      "supporting_work": "Description or null"
    }
  ],
  "projects_to_create": [
    // Same structure as projects_to_update
  ]
}

Only include projects that were explicitly discussed. If no projects need updating or creating, use empty arrays."""


class JarvisConversation:
    """Manages the conversation flow with the user."""

    def __init__(self, existing_projects: list[str] | None = None) -> None:
        load_dotenv()

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set in .env")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.messages: list[dict[str, str]] = []
        self.existing_projects = existing_projects or []
        self.state = ConversationState()

    def _get_system_prompt(self) -> str:
        """Get system prompt with context about existing projects."""
        prompt = SYSTEM_PROMPT
        if self.existing_projects:
            project_list = "\n".join(f"- {p}" for p in self.existing_projects)
            prompt += f"\n\nExisting projects on the user's Confluence page:\n{project_list}"
        return prompt

    def chat(self, user_message: str) -> str:
        """Send a message and get a response.

        Args:
            user_message: The user's message

        Returns:
            Jarvis's response
        """
        self.messages.append({"role": "user", "content": user_message})

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=self._get_system_prompt(),
            messages=self.messages,
        )

        assistant_message = response.content[0].text
        self.messages.append({"role": "assistant", "content": assistant_message})

        return assistant_message

    def extract_structured_data(self) -> ConversationState:
        """Extract structured data from the conversation.

        This sends the conversation history plus an extraction prompt
        to get structured JSON output.

        Returns:
            ConversationState with extracted data
        """
        # Add extraction request
        extraction_messages = self.messages + [
            {"role": "user", "content": EXTRACTION_PROMPT}
        ]

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=self._get_system_prompt(),
            messages=extraction_messages,
        )

        import json
        raw_json = response.content[0].text

        # Try to extract JSON from the response (handle markdown code blocks)
        if "```json" in raw_json:
            raw_json = raw_json.split("```json")[1].split("```")[0]
        elif "```" in raw_json:
            raw_json = raw_json.split("```")[1].split("```")[0]

        data = json.loads(raw_json.strip())

        # Build state from extracted data
        state = ConversationState()

        if data.get("journal_entry"):
            je = data["journal_entry"]
            state.journal_entries.append(JournalEntry(
                period_description=je.get("period_description", "today"),
                summary=je["summary"],
            ))

        for proj in data.get("projects_to_update", []):
            state.projects_to_update.append(self._parse_project(proj))

        for proj in data.get("projects_to_create", []):
            state.projects_to_create.append(self._parse_project(proj))

        self.state = state
        return state

    def _parse_project(self, data: dict[str, Any]) -> Project:
        """Parse project data from JSON into a Project model."""
        # Map classification string to enum
        classification_str = data.get("classification", "Exploratory")
        try:
            classification = ProjectClassification(classification_str)
        except ValueError:
            classification = ProjectClassification.EXPLORATORY

        return Project(
            title=data["title"],
            classification=classification,
            status=data["status"],
            next_steps=data["next_steps"],
            executive_summary=data["executive_summary"],
            prototypes=data.get("prototypes"),
            supporting_work=data.get("supporting_work"),
        )

    def get_summary(self) -> str:
        """Get a human-readable summary of what will be generated."""
        if not self.state.journal_entries and not self.state.projects_to_update and not self.state.projects_to_create:
            return "No entries to generate."

        parts = []

        if self.state.journal_entries:
            parts.append(f"Journal Entries: {len(self.state.journal_entries)}")
            for entry in self.state.journal_entries:
                parts.append(f"  - {entry.period_description}: {entry.summary[:50]}...")

        if self.state.projects_to_update:
            parts.append(f"\nProjects to Update: {len(self.state.projects_to_update)}")
            for proj in self.state.projects_to_update:
                parts.append(f"  - {proj.title}")

        if self.state.projects_to_create:
            parts.append(f"\nNew Projects: {len(self.state.projects_to_create)}")
            for proj in self.state.projects_to_create:
                parts.append(f"  - {proj.title}")

        return "\n".join(parts)
