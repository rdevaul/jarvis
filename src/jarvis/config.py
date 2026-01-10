"""Configuration management for Jarvis."""

import json
from pathlib import Path

from pydantic import BaseModel, Field


CONFIG_FILE = Path.home() / ".jarvis" / "config.json"


class PageConfig(BaseModel):
    """Configuration for a specific Confluence page."""

    url: str
    page_id: str
    page_title: str
    journal_heading: str = Field(
        description="The heading under which journal entries should be added"
    )
    project_headings: list[str] = Field(
        default_factory=list,
        description="Headings under which projects are organized (e.g., 'Moonshots', 'Preliminary Investigations')"
    )


class JarvisConfig(BaseModel):
    """Global Jarvis configuration."""

    default_page_url: str | None = None
    pages: dict[str, PageConfig] = Field(
        default_factory=dict,
        description="Page configurations keyed by URL"
    )

    def get_page_config(self, url: str) -> PageConfig | None:
        """Get configuration for a specific page URL."""
        return self.pages.get(url)

    def set_page_config(self, config: PageConfig) -> None:
        """Save configuration for a page."""
        self.pages[config.url] = config
        if self.default_page_url is None:
            self.default_page_url = config.url


def load_config() -> JarvisConfig:
    """Load configuration from disk."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            data = json.load(f)
            return JarvisConfig.model_validate(data)
    return JarvisConfig()


def save_config(config: JarvisConfig) -> None:
    """Save configuration to disk."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config.model_dump(), f, indent=2)


def get_config_path() -> Path:
    """Return the path to the config file."""
    return CONFIG_FILE
