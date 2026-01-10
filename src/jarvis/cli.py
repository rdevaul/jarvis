"""Command-line interface for Jarvis."""

import argparse
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from jarvis.config import (
    JarvisConfig,
    PageConfig,
    get_config_path,
    load_config,
    save_config,
)
from jarvis.confluence import ConfluenceClient
from jarvis.conversation import JarvisConversation


console = Console()


def print_jarvis(message: str) -> None:
    """Print a message from Jarvis."""
    console.print(Panel(Markdown(message), title="[bold blue]Jarvis[/bold blue]", border_style="blue"))


def print_user_prompt() -> str:
    """Get input from the user."""
    return Prompt.ask("\n[bold green]You[/bold green]")


def configure_page(confluence: ConfluenceClient, page_url: str) -> PageConfig:
    """Interactive configuration for a Confluence page."""
    console.print(f"\n[bold]Configuring page:[/bold] {page_url}\n")

    # Fetch the page
    page = confluence.get_page_by_url(page_url)
    page_id = page["id"]
    page_title = page["title"]

    console.print(f"[green]Found page:[/green] {page_title} (ID: {page_id})\n")

    # Extract headings
    headings = confluence.extract_headings(page_id)

    if not headings:
        console.print("[yellow]No headings found on this page.[/yellow]")
        console.print("You'll need to add section headings to your Confluence page first.")
        sys.exit(1)

    # Display headings
    console.print("[bold]Headings found on this page:[/bold]\n")
    table = Table(show_header=True, header_style="bold")
    table.add_column("#", style="dim", width=4)
    table.add_column("Level", width=6)
    table.add_column("Heading Text")

    for i, h in enumerate(headings, 1):
        table.add_row(str(i), f"H{h['level']}", h["text"])

    console.print(table)
    console.print()

    # Ask for journal heading
    console.print("[bold]Journal Section Configuration[/bold]")
    console.print("Which heading marks the section where journal/log entries should be added?")
    journal_idx = Prompt.ask(
        "Enter the number (or 0 to skip journal entries)",
        default="0"
    )

    journal_heading = ""
    if journal_idx != "0":
        try:
            idx = int(journal_idx) - 1
            if 0 <= idx < len(headings):
                journal_heading = headings[idx]["text"]
                console.print(f"[green]Journal heading set to:[/green] {journal_heading}\n")
            else:
                console.print("[yellow]Invalid selection, journal entries will be prepended to page.[/yellow]\n")
        except ValueError:
            console.print("[yellow]Invalid input, journal entries will be prepended to page.[/yellow]\n")

    # Ask for project headings
    console.print("[bold]Project Sections Configuration[/bold]")
    console.print("Which headings contain project entries? (Enter numbers separated by commas)")
    console.print("New projects will be created under the first matching heading.")
    project_idx_str = Prompt.ask(
        "Enter the numbers (or 0 to skip)",
        default="0"
    )

    project_headings = []
    if project_idx_str != "0":
        try:
            indices = [int(x.strip()) - 1 for x in project_idx_str.split(",")]
            for idx in indices:
                if 0 <= idx < len(headings):
                    project_headings.append(headings[idx]["text"])
            if project_headings:
                console.print(f"[green]Project headings set to:[/green] {', '.join(project_headings)}\n")
        except ValueError:
            console.print("[yellow]Invalid input, projects will be appended to page.[/yellow]\n")

    # Create and return config
    config = PageConfig(
        url=page_url,
        page_id=page_id,
        page_title=page_title,
        journal_heading=journal_heading,
        project_headings=project_headings,
    )

    return config


def run_configure(args: argparse.Namespace) -> None:
    """Run the configuration flow."""
    console.print("\n[bold]Jarvis Configuration[/bold]\n")

    # Get page URL
    page_url = Prompt.ask(
        "Enter your Confluence page URL",
        default="https://confluence.relspace.net/display/DARK/Rich%27s+Moonshot+Journal"
    )

    # Connect to Confluence
    console.print("\n[dim]Connecting to Confluence...[/dim]")
    try:
        confluence = ConfluenceClient()
    except Exception as e:
        console.print(f"[red]Error connecting to Confluence:[/red] {e}")
        sys.exit(1)

    # Configure the page
    page_config = configure_page(confluence, page_url)

    # Load existing config and add/update this page
    config = load_config()
    config.set_page_config(page_config)
    save_config(config)

    console.print(f"\n[green]Configuration saved to:[/green] {get_config_path()}")
    console.print("\nYou can now run [bold]jarvis[/bold] to start tracking your work!")


def run_conversation(args: argparse.Namespace) -> None:
    """Run the main conversation flow."""
    console.print("\n[bold]Welcome to Jarvis[/bold] - Your work tracking assistant\n")

    # Load config
    config = load_config()

    # Check if we have a configured page
    if not config.default_page_url:
        console.print("[yellow]No page configured yet.[/yellow]")
        console.print("Run [bold]jarvis --configure[/bold] to set up your Confluence page.\n")

        if not Confirm.ask("Would you like to configure now?"):
            sys.exit(0)

        run_configure(args)
        config = load_config()

    page_url = args.url if args.url else config.default_page_url
    page_config = config.get_page_config(page_url)

    if not page_config:
        console.print(f"[yellow]Page not configured:[/yellow] {page_url}")
        console.print("Run [bold]jarvis --configure[/bold] to set up this page.\n")
        sys.exit(1)

    # Initialize Confluence client
    console.print("[dim]Connecting to Confluence...[/dim]")
    try:
        confluence = ConfluenceClient()
        existing_projects = confluence.list_existing_projects(page_config.page_id)
        console.print(f"[green]Connected![/green] Found {len(existing_projects)} existing projects.\n")
    except Exception as e:
        console.print(f"[red]Error connecting to Confluence:[/red] {e}")
        console.print("[yellow]Continuing without Confluence connection...[/yellow]\n")
        confluence = None
        existing_projects = []

    # Initialize conversation
    try:
        conversation = JarvisConversation(existing_projects=existing_projects)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    # Start the conversation
    print_jarvis("Hello! I'm here to help you track your work and update your Confluence page. "
                 "What have you been working on?")

    # Conversation loop
    while True:
        user_input = print_user_prompt()

        if user_input.lower() in ("quit", "exit", "q"):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if user_input.lower() in ("done", "finish", "generate"):
            # Extract and confirm
            console.print("\n[dim]Analyzing conversation...[/dim]")
            try:
                conversation.extract_structured_data()
                summary = conversation.get_summary()

                console.print("\n[bold]Here's what I'll generate:[/bold]")
                console.print(Panel(summary, border_style="yellow"))

                if not Confirm.ask("\nDoes this look correct?"):
                    print_jarvis("No problem! Let's continue our conversation. "
                                "Tell me more about your work, or correct anything I got wrong.")
                    continue

                # Generate and push to Confluence
                if confluence and page_config:
                    console.print("\n[dim]Updating Confluence...[/dim]")

                    for entry in conversation.state.journal_entries:
                        if page_config.journal_heading:
                            confluence.prepend_journal_entry_configured(
                                page_config.page_id, entry, page_config.journal_heading
                            )
                        else:
                            confluence.prepend_journal_entry(page_config.page_id, entry)
                        console.print("[green]✓[/green] Added journal entry")

                    for project in conversation.state.projects_to_update:
                        if page_config.project_headings:
                            confluence.update_or_create_project_configured(
                                page_config.page_id, project, page_config.project_headings
                            )
                        else:
                            confluence.update_or_create_project(page_config.page_id, project)
                        console.print(f"[green]✓[/green] Updated project: {project.title}")

                    for project in conversation.state.projects_to_create:
                        if page_config.project_headings:
                            confluence.update_or_create_project_configured(
                                page_config.page_id, project, page_config.project_headings
                            )
                        else:
                            confluence.update_or_create_project(page_config.page_id, project)
                        console.print(f"[green]✓[/green] Created project: {project.title}")

                    console.print("\n[bold green]Done![/bold green] Your Confluence page has been updated.")
                else:
                    console.print("\n[yellow]Confluence not connected. Here's the generated content:[/yellow]")
                    for entry in conversation.state.journal_entries:
                        console.print(Panel(entry.to_confluence_html(), title="Journal Entry"))
                    for project in conversation.state.projects_to_update + conversation.state.projects_to_create:
                        console.print(Panel(project.to_confluence_html(), title=project.title))

                break

            except Exception as e:
                console.print(f"[red]Error during extraction:[/red] {e}")
                print_jarvis("I had trouble understanding our conversation. "
                            "Could you summarize the key points again?")
                continue

        # Regular conversation turn
        response = conversation.chat(user_input)
        print_jarvis(response)


def main() -> None:
    """Main entry point for Jarvis CLI."""
    parser = argparse.ArgumentParser(
        description="Jarvis - Agentic work tracker and status update generator"
    )
    parser.add_argument(
        "--configure", "-c",
        action="store_true",
        help="Run the configuration wizard to set up a Confluence page"
    )
    parser.add_argument(
        "--url", "-u",
        type=str,
        help="Confluence page URL to use (overrides default)"
    )

    args = parser.parse_args()

    if args.configure:
        run_configure(args)
    else:
        run_conversation(args)


if __name__ == "__main__":
    main()
