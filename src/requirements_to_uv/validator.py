"""Validate generated pyproject.toml."""

import subprocess
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


class PyProjectValidator:
    """Validate pyproject.toml structure and content."""

    def __init__(self):
        """Initialize validator."""
        self.errors = []
        self.warnings = []

    def validate(self, pyproject_path: Path, skip_uv_check: bool = False) -> bool:
        """Validate a pyproject.toml file."""
        # Check file exists
        if not pyproject_path.exists():
            self.errors.append(f"File not found: {pyproject_path}")
            return False

        # Validate TOML syntax
        if not self._validate_toml_syntax(pyproject_path):
            return False

        # Validate required fields
        if not self._validate_required_fields(pyproject_path):
            return False

        # Validate dependency format
        self._validate_dependencies(pyproject_path)

        # Optionally validate with uv
        if not skip_uv_check:
            self._validate_with_uv(pyproject_path)

        # Return True if no errors (warnings are ok)
        return len(self.errors) == 0

    def _validate_toml_syntax(self, pyproject_path: Path) -> bool:
        """Validate TOML file can be parsed."""
        try:
            with open(pyproject_path, "rb") as f:
                tomllib.load(f)
            return True
        except Exception as e:
            self.errors.append(f"Invalid TOML syntax: {e}")
            return False

    def _validate_required_fields(self, pyproject_path: Path) -> bool:
        """Validate required fields are present."""
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)

            if "project" not in data:
                self.errors.append("Missing [project] section")
                return False

            project = data["project"]

            # Check required fields
            if "name" not in project:
                self.errors.append("Missing required field: project.name")
                return False

            if "version" not in project:
                self.errors.append("Missing required field: project.version")
                return False

            # Validate name format
            name = project["name"]
            if not isinstance(name, str) or not name:
                self.errors.append("project.name must be a non-empty string")
                return False

            # Check for invalid characters in name
            import re

            if not re.match(r"^[a-z0-9]([a-z0-9\-._]*[a-z0-9])?$", name, re.IGNORECASE):
                self.warnings.append(
                    f"Package name '{name}' may not be valid. "
                    "Use lowercase letters, numbers, hyphens, underscores, and dots."
                )

            return True

        except Exception as e:
            self.errors.append(f"Error validating fields: {e}")
            return False

    def _validate_dependencies(self, pyproject_path: Path):
        """Validate dependency format."""
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)

            project = data.get("project", {})

            # Validate main dependencies
            if "dependencies" in project:
                if not isinstance(project["dependencies"], list):
                    self.errors.append("project.dependencies must be a list")
                else:
                    for dep in project["dependencies"]:
                        if not isinstance(dep, str):
                            self.errors.append(
                                f"Invalid dependency (must be string): {dep}"
                            )

            # Validate dependency groups
            if "dependency-groups" in data:
                dep_groups = data["dependency-groups"]
                if not isinstance(dep_groups, dict):
                    self.errors.append("dependency-groups must be a table")
                else:
                    for group, deps in dep_groups.items():
                        if not isinstance(deps, list):
                            self.errors.append(
                                f"dependency-groups.{group} must be a list"
                            )
                        else:
                            for dep in deps:
                                if not isinstance(dep, str):
                                    self.errors.append(
                                        f"Invalid dependency in {group}: {dep}"
                                    )

            # Validate sources
            if (
                "tool" in data
                and "uv" in data["tool"]
                and "sources" in data["tool"]["uv"]
            ):
                sources = data["tool"]["uv"]["sources"]
                if not isinstance(sources, dict):
                    self.errors.append("tool.uv.sources must be a table")
                else:
                    for pkg, source in sources.items():
                        if not isinstance(source, dict):
                            self.errors.append(f"Source for '{pkg}' must be a table")

        except Exception as e:
            self.warnings.append(f"Could not validate dependencies: {e}")

    def _validate_with_uv(self, pyproject_path: Path):
        """Validate using uv if available."""
        try:
            # Check if uv is installed
            result = subprocess.run(
                ["uv", "--version"], capture_output=True, text=True, timeout=5
            )

            if result.returncode != 0:
                self.warnings.append("uv not found, skipping uv validation")
                return

            # Try to run uv lock --dry-run
            result = subprocess.run(
                ["uv", "lock", "--dry-run"],
                cwd=pyproject_path.parent,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                self.warnings.append(f"uv lock validation failed:\n{result.stderr}")
            else:
                # Success - dependencies can be resolved
                pass

        except FileNotFoundError:
            self.warnings.append("uv not installed, skipping uv validation")
        except subprocess.TimeoutExpired:
            self.warnings.append("uv lock validation timed out")
        except Exception as e:
            self.warnings.append(f"Could not validate with uv: {e}")

    def get_errors(self) -> list[str]:
        """Get list of errors."""
        return self.errors

    def get_warnings(self) -> list[str]:
        """Get list of warnings."""
        return self.warnings

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
