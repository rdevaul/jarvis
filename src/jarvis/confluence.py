"""Confluence API integration for Jarvis."""

import os
import re

from atlassian import Confluence
from dotenv import load_dotenv

from jarvis.models import JournalEntry, Project


class ConfluenceClient:
    """Client for reading and writing to Confluence pages."""

    def __init__(self) -> None:
        load_dotenv()

        url = os.getenv("CONFLUENCE_URL")
        token = os.getenv("CONFLUENCE_TOKEN")

        if not url or not token:
            raise ValueError("CONFLUENCE_URL and CONFLUENCE_TOKEN must be set in .env")

        self.client = Confluence(url=url, token=token)

    def get_page_by_url(self, page_url: str) -> dict:
        """Get a page by its full URL.

        Args:
            page_url: Full Confluence URL like
                      https://confluence.relspace.net/display/DARK/Rich%27s+Moonshot+Journal

        Returns:
            Page data dict with 'id', 'title', 'body', etc.
        """
        # Parse the URL to extract space key and title
        # Format: /display/SPACE/Page+Title
        match = re.search(r"/display/([^/]+)/(.+)$", page_url)
        if not match:
            raise ValueError(f"Could not parse Confluence URL: {page_url}")

        space_key = match.group(1)
        page_title = match.group(2).replace("+", " ").replace("%27", "'").replace("%20", " ")

        # URL decode common patterns
        from urllib.parse import unquote
        page_title = unquote(page_title)

        page = self.client.get_page_by_title(space_key, page_title, expand="body.storage,version")
        if not page:
            raise ValueError(f"Page not found: {page_title} in space {space_key}")

        return page

    def get_page_content(self, page_id: str) -> str:
        """Get the storage format content of a page."""
        page = self.client.get_page_by_id(page_id, expand="body.storage")
        return page["body"]["storage"]["value"]

    def update_page(self, page_id: str, title: str, new_content: str) -> dict:
        """Update a page's content.

        Args:
            page_id: The page ID
            title: Page title
            new_content: New content in Confluence storage format

        Returns:
            Updated page data
        """
        return self.client.update_page(
            page_id=page_id,
            title=title,
            body=new_content,
        )

    def prepend_journal_entry(self, page_id: str, entry: JournalEntry) -> dict:
        """Add a journal entry to the top of the journal section.

        This looks for a 'Journal' heading and prepends the entry after it.
        """
        page = self.client.get_page_by_id(page_id, expand="body.storage")
        content = page["body"]["storage"]["value"]
        title = page["title"]

        entry_html = entry.to_confluence_html()

        # Look for journal section header and insert after it
        # Common patterns: <h1>Journal</h1>, <h2>Journal</h2>, etc.
        journal_pattern = r"(<h[1-3][^>]*>.*?Journal.*?</h[1-3]>)"
        match = re.search(journal_pattern, content, re.IGNORECASE)

        if match:
            insert_pos = match.end()
            new_content = content[:insert_pos] + "\n" + entry_html + content[insert_pos:]
        else:
            # No journal section found, prepend to beginning
            new_content = entry_html + content

        return self.update_page(page_id, title, new_content)

    def update_or_create_project(self, page_id: str, project: Project) -> dict:
        """Update an existing project section or create a new one.

        Projects are identified by their title within the page.
        """
        page = self.client.get_page_by_id(page_id, expand="body.storage")
        content = page["body"]["storage"]["value"]
        title = page["title"]

        project_html = project.to_confluence_html()

        # Look for existing project section by title
        # Format: <h2>Project Title</h2> or <h3>Project Title</h3>
        escaped_title = re.escape(project.title)
        project_pattern = rf"(<h[2-3][^>]*>.*?{escaped_title}.*?</h[2-3]>)(.*?)(?=<h[1-3]|$)"
        match = re.search(project_pattern, content, re.IGNORECASE | re.DOTALL)

        if match:
            # Replace existing project section
            heading = match.group(1)
            new_content = content[:match.start()] + heading + "\n" + project_html + content[match.end():]
        else:
            # Create new project section - look for Projects heading or append
            projects_pattern = r"(<h[1-2][^>]*>.*?Projects.*?</h[1-2]>)"
            projects_match = re.search(projects_pattern, content, re.IGNORECASE)

            if projects_match:
                insert_pos = projects_match.end()
                new_section = f"\n<h3>{project.title}</h3>\n{project_html}"
                new_content = content[:insert_pos] + new_section + content[insert_pos:]
            else:
                # Append to end
                new_content = content + f"\n<h2>{project.title}</h2>\n{project_html}"

        return self.update_page(page_id, title, new_content)

    def list_existing_projects(self, page_id: str) -> list[str]:
        """Extract project titles from a page.

        Returns a list of project titles found in the page.
        """
        content = self.get_page_content(page_id)

        # Find all h2 and h3 headings that might be projects
        # This is heuristic - we look for headings that aren't "Journal", "Projects", etc.
        heading_pattern = r"<h[2-3][^>]*>(.*?)</h[2-3]>"
        matches = re.findall(heading_pattern, content, re.IGNORECASE)

        # Filter out common non-project headings
        excluded = {"journal", "projects", "executive summary", "prototypes",
                   "simulation, white paper, and supporting work products"}

        projects = []
        for match in matches:
            # Strip HTML tags from the match
            clean = re.sub(r"<[^>]+>", "", match).strip()
            if clean.lower() not in excluded:
                projects.append(clean)

        return projects

    def extract_headings(self, page_id: str) -> list[dict[str, str]]:
        """Extract all headings from a page with their levels.

        Returns a list of dicts with 'level' (1-6) and 'text' keys.
        """
        content = self.get_page_content(page_id)

        # Find all headings h1-h6
        heading_pattern = r"<h([1-6])[^>]*>(.*?)</h\1>"
        matches = re.findall(heading_pattern, content, re.IGNORECASE | re.DOTALL)

        headings = []
        for level, text in matches:
            # Strip HTML tags from the text
            clean_text = re.sub(r"<[^>]+>", "", text).strip()
            if clean_text:
                headings.append({"level": int(level), "text": clean_text})

        return headings

    def prepend_journal_entry_configured(
        self, page_id: str, entry: JournalEntry, journal_heading: str
    ) -> dict:
        """Add a journal entry after the specified journal heading.

        Args:
            page_id: The page ID
            entry: The journal entry to add
            journal_heading: The exact heading text to find (e.g., "Log Entries")
        """
        page = self.client.get_page_by_id(page_id, expand="body.storage")
        content = page["body"]["storage"]["value"]
        title = page["title"]

        entry_html = entry.to_confluence_html()

        # Look for the specified heading
        escaped_heading = re.escape(journal_heading)
        journal_pattern = rf"(<h[1-6][^>]*>[^<]*{escaped_heading}[^<]*</h[1-6]>)"
        match = re.search(journal_pattern, content, re.IGNORECASE)

        if match:
            insert_pos = match.end()
            new_content = content[:insert_pos] + "\n" + entry_html + content[insert_pos:]
        else:
            # Heading not found, prepend to beginning
            new_content = entry_html + content

        return self.update_page(page_id, title, new_content)

    def update_or_create_project_configured(
        self, page_id: str, project: Project, project_headings: list[str]
    ) -> dict:
        """Update an existing project or create under the first project heading.

        Args:
            page_id: The page ID
            project: The project to update/create
            project_headings: List of heading texts where projects live
                             (e.g., ["Moonshots", "Preliminary Investigations"])
        """
        page = self.client.get_page_by_id(page_id, expand="body.storage")
        content = page["body"]["storage"]["value"]
        title = page["title"]

        project_html = project.to_confluence_html()

        # First, look for existing project by title anywhere in the page
        escaped_title = re.escape(project.title)
        project_pattern = rf"(<h[2-4][^>]*>[^<]*{escaped_title}[^<]*</h[2-4]>)(.*?)(?=<h[1-4]|$)"
        match = re.search(project_pattern, content, re.IGNORECASE | re.DOTALL)

        if match:
            # Replace existing project section
            heading = match.group(1)
            new_content = content[:match.start()] + heading + "\n" + project_html + content[match.end():]
        else:
            # Create new project - find first project heading and insert after it
            insert_pos = None
            for proj_heading in project_headings:
                escaped = re.escape(proj_heading)
                pattern = rf"(<h[1-3][^>]*>[^<]*{escaped}[^<]*</h[1-3]>)"
                heading_match = re.search(pattern, content, re.IGNORECASE)
                if heading_match:
                    insert_pos = heading_match.end()
                    break

            if insert_pos:
                new_section = f"\n<h3>{project.title}</h3>\n{project_html}"
                new_content = content[:insert_pos] + new_section + content[insert_pos:]
            else:
                # No project headings found, append to end
                new_content = content + f"\n<h2>{project.title}</h2>\n{project_html}"

        return self.update_page(page_id, title, new_content)
