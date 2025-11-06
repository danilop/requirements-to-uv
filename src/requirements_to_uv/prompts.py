"""Interactive prompts for user input."""

from pathlib import Path
from typing import Optional

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class InteractivePrompter:
    """Handle interactive prompts for missing metadata."""

    def __init__(self, non_interactive: bool = False):
        """Initialize prompter with interaction mode."""
        self.non_interactive = non_interactive

    def confirm_metadata(self, metadata: dict) -> dict:
        """Display detected metadata and allow user to confirm or modify."""
        if self.non_interactive:
            return metadata

        console.print("\n[bold cyan]Detected Project Metadata[/bold cyan]")

        # Create a table to display metadata
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Field", style="cyan")
        table.add_column("Detected Value", style="green")

        table.add_row("Name", metadata.get("name", "Not detected"))
        table.add_row("Version", metadata.get("version", "Not detected"))
        table.add_row(
            "Description", metadata.get("description", "Not detected") or "Not detected"
        )
        table.add_row(
            "README", metadata.get("readme", "Not detected") or "Not detected"
        )
        table.add_row("Python Version", metadata.get("requires_python", "Not detected"))
        table.add_row(
            "License", metadata.get("license", "Not detected") or "Not detected"
        )

        authors = metadata.get("authors", [])
        if authors and authors[0]:
            author_str = authors[0].get("name", "")
            if "email" in authors[0]:
                author_str += f" <{authors[0]['email']}>"
            table.add_row("Author", author_str)
        else:
            table.add_row("Author", "Not detected")

        console.print(table)

        # Ask if user wants to modify
        if not questionary.confirm("Accept these values?", default=True).ask():
            return self._prompt_for_metadata(metadata)

        return metadata

    def _prompt_for_metadata(self, current: dict) -> dict:
        """Prompt user for each metadata field."""
        metadata = {}

        # Project name
        metadata["name"] = questionary.text(
            "Project name:", default=current.get("name", "my-project")
        ).ask()

        # Version
        metadata["version"] = questionary.text(
            "Version:", default=current.get("version", "0.1.0")
        ).ask()

        # Description
        metadata["description"] = questionary.text(
            "Description:", default=current.get("description", "")
        ).ask()

        # Python version
        python_versions = [
            ">=3.8",
            ">=3.9",
            ">=3.10",
            ">=3.11",
            ">=3.12",
            ">=3.13",
        ]
        default_py = current.get("requires_python", ">=3.8")
        metadata["requires_python"] = questionary.select(
            "Minimum Python version:",
            choices=python_versions,
            default=default_py if default_py in python_versions else ">=3.8",
        ).ask()

        # License
        licenses = [
            "MIT",
            "Apache-2.0",
            "GPL-3.0",
            "BSD-3-Clause",
            "ISC",
            "None",
            "Other",
        ]
        current_license = current.get("license", "None")
        if current_license and current_license not in licenses:
            licenses.insert(-1, current_license)

        license_choice = questionary.select(
            "License:",
            choices=licenses,
            default=current_license if current_license in licenses else "None",
        ).ask()

        if license_choice == "Other":
            license_choice = questionary.text("Enter license identifier:").ask()

        metadata["license"] = license_choice if license_choice != "None" else None

        # Author
        if questionary.confirm(
            "Add author information?", default=bool(current.get("authors"))
        ).ask():
            author_name = questionary.text(
                "Author name:",
                default=current.get("authors", [{}])[0].get("name", "")
                if current.get("authors")
                else "",
            ).ask()

            author_email = questionary.text(
                "Author email (optional):",
                default=current.get("authors", [{}])[0].get("email", "")
                if current.get("authors")
                else "",
            ).ask()

            authors = []
            if author_name or author_email:
                author = {}
                if author_name:
                    author["name"] = author_name
                if author_email:
                    author["email"] = author_email
                authors.append(author)

            metadata["authors"] = authors
        else:
            metadata["authors"] = []

        # Keep detected values for fields we didn't prompt for
        metadata["readme"] = current.get("readme")
        metadata["repository_url"] = current.get("repository_url")
        metadata["is_git_repo"] = current.get("is_git_repo")

        return metadata

    def confirm_requirements_files(self, files: dict[str, Path]) -> dict[str, Path]:
        """Confirm detected requirements files and their categorization."""
        if self.non_interactive or not files:
            return files

        console.print("\n[bold cyan]Detected Requirements Files[/bold cyan]")

        # Display detected files
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Category", style="cyan")
        table.add_column("File", style="green")

        for category, filepath in files.items():
            table.add_row(category, str(filepath.name))

        console.print(table)

        if not questionary.confirm(
            "Are these categorizations correct?", default=True
        ).ask():
            # Allow user to re-categorize
            new_files = {}
            for filepath in files.values():
                category = questionary.select(
                    f"Category for {filepath.name}:",
                    choices=["main", "dev", "test", "docs", "lint", "skip"],
                ).ask()

                if category != "skip":
                    new_files[category] = filepath

            return new_files

        return files

    def confirm_conversion(self, warnings: list[str]) -> bool:
        """Display warnings and ask user to confirm conversion."""
        if self.non_interactive:
            return True

        if warnings:
            console.print("\n[bold yellow]Warnings:[/bold yellow]")
            for warning in warnings:
                console.print(f"  • {warning}")

        return questionary.confirm("\nProceed with conversion?", default=True).ask()

    def prompt_merge_strategy(self) -> str:
        """Ask user how to handle existing pyproject.toml."""
        console.print("\n[bold yellow]Existing pyproject.toml found![/bold yellow]")

        choice = questionary.select(
            "How would you like to proceed?",
            choices=[
                "Merge dependencies (recommended)",
                "Create backup and overwrite",
                "Cancel",
            ],
        ).ask()

        if "Merge" in choice:
            return "merge"
        elif "backup" in choice:
            return "overwrite"
        else:
            return "cancel"

    def show_success(self, output_file: Path, backup_file: Optional[Path] = None):
        """Display success message."""
        message = f"[bold green]✓[/bold green] Successfully created {output_file.name}"

        if backup_file:
            message += f"\n  Backup saved to: {backup_file.name}"

        console.print(Panel(message, style="green"))

    def show_error(self, message: str):
        """Display error message."""
        console.print(Panel(f"[bold red]Error:[/bold red] {message}", style="red"))

    def show_info(self, message: str):
        """Display informational message."""
        console.print(f"[cyan]ℹ[/cyan] {message}")

    def show_warning(self, message: str):
        """Display warning message."""
        console.print(f"[yellow]⚠[/yellow] {message}")
