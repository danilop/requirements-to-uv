"""Merge new dependencies with existing pyproject.toml."""

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


class PyProjectMerger:
    """Handle merging of new dependencies with existing pyproject.toml."""

    def __init__(self):
        """Initialize merger."""
        self.warnings = []

    def merge(self, existing_path: Path, new_pyproject: dict) -> dict:
        """Merge new pyproject data with existing file."""
        # Load existing pyproject.toml
        try:
            with open(existing_path, "rb") as f:
                existing = tomllib.load(f)
        except Exception as e:
            self.warnings.append(f"Error reading existing pyproject.toml: {e}")
            return new_pyproject

        # Merge project section
        if "project" in new_pyproject:
            existing.setdefault("project", {})
            self._merge_project_section(existing["project"], new_pyproject["project"])

        # Merge dependency-groups section
        if "dependency-groups" in new_pyproject:
            existing.setdefault("dependency-groups", {})
            self._merge_dependency_groups(
                existing["dependency-groups"], new_pyproject["dependency-groups"]
            )

        # Merge tool.uv.sources section
        if "tool" in new_pyproject and "uv" in new_pyproject["tool"]:
            existing.setdefault("tool", {}).setdefault("uv", {})
            if "sources" in new_pyproject["tool"]["uv"]:
                existing["tool"]["uv"].setdefault("sources", {})
                self._merge_sources(
                    existing["tool"]["uv"]["sources"],
                    new_pyproject["tool"]["uv"]["sources"],
                )

        return existing

    def _merge_project_section(self, existing: dict, new: dict):
        """Merge project section, preserving existing metadata."""
        # Only update empty fields
        for key in ["name", "version", "description", "readme", "requires-python"]:
            if key not in existing or not existing[key]:
                if key in new:
                    existing[key] = new[key]

        # Merge dependencies
        if "dependencies" in new:
            existing.setdefault("dependencies", [])
            existing["dependencies"] = self._merge_dependency_lists(
                existing["dependencies"], new["dependencies"]
            )

        # Merge authors (append if not present)
        if "authors" in new and new["authors"]:
            existing.setdefault("authors", [])
            for author in new["authors"]:
                if author not in existing["authors"]:
                    existing["authors"].append(author)

        # Add license if not present
        if "license" not in existing and "license" in new:
            existing["license"] = new["license"]

    def _merge_dependency_groups(self, existing: dict, new: dict):
        """Merge dependency groups."""
        for group, deps in new.items():
            if group in existing:
                # Merge with existing group
                existing[group] = self._merge_dependency_lists(existing[group], deps)
            else:
                # Add new group
                existing[group] = deps

    def _merge_dependency_lists(self, existing: list[str], new: list[str]) -> list[str]:
        """Merge two dependency lists, avoiding duplicates."""
        # Parse package names from dependency strings
        existing_packages = set()
        for dep in existing:
            pkg_name = self._extract_package_name(dep)
            if pkg_name:
                existing_packages.add(pkg_name.lower())

        # Add new dependencies that aren't already present
        merged = list(existing)
        for dep in new:
            pkg_name = self._extract_package_name(dep)
            if pkg_name and pkg_name.lower() not in existing_packages:
                merged.append(dep)
                existing_packages.add(pkg_name.lower())
            elif pkg_name:
                self.warnings.append(
                    f"Package '{pkg_name}' already exists in dependencies, skipping"
                )

        return merged

    def _extract_package_name(self, dep_string: str) -> str:
        """Extract package name from dependency string."""
        # Handle strings like "package[extra]>=1.0 ; marker"
        # Split on various delimiters
        for delimiter in ["[", ">", "<", "=", "~", "!", ";", " "]:
            if delimiter in dep_string:
                dep_string = dep_string.split(delimiter)[0]

        return dep_string.strip()

    def _merge_sources(self, existing: dict, new: dict):
        """Merge tool.uv.sources section."""
        for package, source in new.items():
            if package in existing:
                # Check if sources are different
                if existing[package] != source:
                    self.warnings.append(
                        f"Different source for '{package}' already exists, using new source"
                    )
                existing[package] = source
            else:
                existing[package] = source

    def get_warnings(self) -> list[str]:
        """Get list of warnings generated during merge."""
        return self.warnings
