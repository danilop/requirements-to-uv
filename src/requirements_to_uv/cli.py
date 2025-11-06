"""Command-line interface for requirements-to-uv."""

import shutil
import sys
from pathlib import Path

import click
import tomli_w

from .converter import PyProjectConverter
from .detector import MetadataDetector
from .merger import PyProjectMerger
from .parser import RequirementsParser
from .prompts import InteractivePrompter
from .validator import PyProjectValidator


@click.command()
@click.argument(
    "project_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
)
@click.option(
    "--requirements",
    "-r",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to requirements.txt file (default: auto-detect)",
)
@click.option(
    "--dev",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to dev requirements file",
)
@click.option(
    "--test",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to test requirements file",
)
@click.option(
    "--non-interactive",
    is_flag=True,
    help="Run in non-interactive mode (use all defaults)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview changes without writing files",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite existing pyproject.toml instead of merging",
)
@click.option(
    "--name",
    help="Project name (overrides auto-detection)",
)
@click.option(
    "--version",
    "project_version",
    help="Project version (overrides auto-detection)",
)
@click.option(
    "--python",
    help='Python version constraint (e.g., ">=3.8")',
)
@click.option(
    "--no-validate",
    is_flag=True,
    help="Skip validation of generated pyproject.toml",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Verbose output",
)
def main(
    project_dir: Path,
    requirements: Path | None,
    dev: Path | None,
    test: Path | None,
    non_interactive: bool,
    dry_run: bool,
    overwrite: bool,
    name: str | None,
    project_version: str | None,
    python: str | None,
    no_validate: bool,
    verbose: bool,
):
    """Convert Python project from requirements.txt to uv-managed pyproject.toml.

    PROJECT_DIR is the directory containing the Python project (default: current directory).
    """
    prompter = InteractivePrompter(non_interactive=non_interactive or dry_run)

    try:
        # Step 1: Detect metadata
        if verbose:
            prompter.show_info("Detecting project metadata...")

        detector = MetadataDetector(project_dir)
        metadata = detector.detect_all_metadata()

        # Override with command-line arguments
        if name:
            metadata["name"] = name
        if project_version:
            metadata["version"] = project_version
        if python:
            metadata["requires_python"] = python

        # Confirm metadata in interactive mode
        if not non_interactive:
            metadata = prompter.confirm_metadata(metadata)

        # Step 2: Find and parse requirements files
        if verbose:
            prompter.show_info("Finding requirements files...")

        parser = RequirementsParser(warn_callback=prompter.show_warning)

        # Determine which requirements files to parse
        if requirements:
            # User specified main requirements file
            requirements_files = {"main": requirements}
        else:
            # Auto-detect
            requirements_files = parser.find_requirements_files(project_dir)
            if not requirements_files:
                prompter.show_error(
                    "No requirements.txt found. Specify path with --requirements or "
                    "create a requirements.txt file."
                )
                sys.exit(1)

        # Add explicitly specified dev/test files
        if dev:
            requirements_files["dev"] = dev
        if test:
            requirements_files["test"] = test

        # Confirm file categorization
        if not non_interactive:
            requirements_files = prompter.confirm_requirements_files(requirements_files)

        # Parse all requirements files
        if verbose:
            prompter.show_info("Parsing requirements files...")

        requirements_by_group = {}
        all_warnings = []

        for group, filepath in requirements_files.items():
            if verbose:
                prompter.show_info(f"Parsing {filepath.name}...")

            parsed = parser.parse_file(filepath)
            requirements_by_group[group] = parsed

            # Collect warnings
            for req in parsed:
                all_warnings.extend(req.warnings)

        # Remove duplicates from warnings
        all_warnings = list(dict.fromkeys(all_warnings))

        # Step 3: Convert to pyproject.toml structure
        if verbose:
            prompter.show_info("Converting to pyproject.toml format...")

        converter = PyProjectConverter()
        pyproject = converter.convert_to_pyproject(metadata, requirements_by_group)

        # Add converter warnings
        all_warnings.extend(converter.get_warnings())
        all_warnings = list(dict.fromkeys(all_warnings))

        # Step 4: Handle existing pyproject.toml
        output_path = project_dir / "pyproject.toml"
        backup_path = None

        if output_path.exists():
            if overwrite:
                if not dry_run:
                    # Create backup
                    backup_path = project_dir / "pyproject.toml.backup"
                    shutil.copy(output_path, backup_path)
                    prompter.show_info(f"Backup created: {backup_path.name}")
            else:
                # Merge mode
                if not non_interactive:
                    strategy = prompter.prompt_merge_strategy()
                    if strategy == "cancel":
                        prompter.show_info("Conversion cancelled.")
                        sys.exit(0)
                    elif strategy == "overwrite":
                        if not dry_run:
                            backup_path = project_dir / "pyproject.toml.backup"
                            shutil.copy(output_path, backup_path)
                            prompter.show_info(f"Backup created: {backup_path.name}")
                    else:
                        # Merge
                        if verbose:
                            prompter.show_info(
                                "Merging with existing pyproject.toml..."
                            )

                        merger = PyProjectMerger()
                        pyproject = merger.merge(output_path, pyproject)
                        all_warnings.extend(merger.get_warnings())
                else:
                    # Non-interactive: default to merge
                    if verbose:
                        prompter.show_info("Merging with existing pyproject.toml...")

                    merger = PyProjectMerger()
                    pyproject = merger.merge(output_path, pyproject)
                    all_warnings.extend(merger.get_warnings())

        # Show warnings and confirm
        if not prompter.confirm_conversion(all_warnings):
            prompter.show_info("Conversion cancelled.")
            sys.exit(0)

        # Step 5: Write pyproject.toml
        if dry_run:
            prompter.show_info("DRY RUN - would write the following to pyproject.toml:")
            toml_content = tomli_w.dumps(pyproject)
            toml_content = converter.format_toml_with_comments(toml_content)
            print("\n" + "=" * 60)
            print(toml_content)
            print("=" * 60)
        else:
            if verbose:
                prompter.show_info(f"Writing {output_path.name}...")

            toml_content = tomli_w.dumps(pyproject)
            toml_content = converter.format_toml_with_comments(toml_content)

            output_path.write_text(toml_content, encoding="utf-8")

            # Step 6: Validate
            if not no_validate:
                if verbose:
                    prompter.show_info("Validating pyproject.toml...")

                validator = PyProjectValidator()
                validator.validate(output_path)

                # Show validation warnings
                for warning in validator.get_warnings():
                    prompter.show_warning(warning)

                # Show validation errors
                if validator.has_errors():
                    for error in validator.get_errors():
                        prompter.show_error(error)
                    sys.exit(1)

            # Step 7: Success!
            prompter.show_success(output_path, backup_path)

            # Show next steps
            print("\nNext steps:")
            print("  1. Review the generated pyproject.toml")
            print("  2. Install dependencies: uv sync")
            print("  3. Run your project: uv run <script>")

            if all_warnings:
                print(
                    f"\nNote: {len(all_warnings)} warning(s) were generated during conversion."
                )
                print(
                    "      Review the warnings above and update pyproject.toml as needed."
                )

    except KeyboardInterrupt:
        prompter.show_info("\nConversion cancelled.")
        sys.exit(130)
    except Exception as e:
        prompter.show_error(f"Unexpected error: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
