"""Data models for Jarvis."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ProjectClassification(str, Enum):
    """Classification levels for projects."""

    MOONSHOT = "Moonshot"
    CORE = "Core"
    EXPLORATORY = "Exploratory"
    MAINTENANCE = "Maintenance"


class JournalEntry(BaseModel):
    """A dated journal entry summarizing work done."""

    date: datetime = Field(default_factory=datetime.now)
    summary: str = Field(..., description="Summary of tasks undertaken in the period")
    period_description: str = Field(
        default="today", description="Description of time period covered (e.g., 'today', 'this week')"
    )

    def to_confluence_html(self) -> str:
        """Convert to Confluence storage format HTML."""
        date_str = self.date.strftime("%Y-%m-%d %H:%M")
        return f"""<h3>{date_str}</h3>
<p>{self.summary}</p>
"""


class Project(BaseModel):
    """A project with status tracking."""

    title: str
    classification: ProjectClassification
    status: str = Field(..., description="One-line status description")
    next_steps: str = Field(..., description="One-line next steps description")
    executive_summary: str = Field(..., description="Description of what the project explores and why it's significant")
    prototypes: str | None = Field(default=None, description="Description of physical or software prototypes")
    supporting_work: str | None = Field(
        default=None, description="Simulation, white papers, and other supporting work products"
    )
    image_url: str | None = Field(default=None, description="Optional image URL for the project header")

    def to_confluence_html(self) -> str:
        """Convert to Confluence storage format HTML."""
        parts = []

        # Title with optional image
        if self.image_url:
            parts.append(f'<ac:image><ri:url ri:value="{self.image_url}" /></ac:image>')

        # Status block
        parts.append(f"""<p><strong>Classification:</strong> {self.classification.value}<br />
<strong>Status:</strong> {self.status}<br />
<strong>Next Steps:</strong> {self.next_steps}</p>
""")

        # Executive Summary
        parts.append(f"""<h4>Executive Summary</h4>
<p>{self.executive_summary}</p>
""")

        # Prototypes (if any)
        if self.prototypes:
            parts.append(f"""<h4>Prototypes</h4>
<p>{self.prototypes}</p>
""")

        # Supporting work (if any)
        if self.supporting_work:
            parts.append(f"""<h4>Simulation, White Paper, and Supporting Work Products</h4>
<p>{self.supporting_work}</p>
""")

        return "\n".join(parts)


class ConversationState(BaseModel):
    """Tracks the state of a Jarvis conversation."""

    journal_entries: list[JournalEntry] = Field(default_factory=list)
    projects_to_update: list[Project] = Field(default_factory=list)
    projects_to_create: list[Project] = Field(default_factory=list)
    raw_notes: list[str] = Field(default_factory=list, description="Raw notes gathered during conversation")
