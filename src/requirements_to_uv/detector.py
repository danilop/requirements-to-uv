"""Auto-detect project metadata from filesystem and environment."""

import re
import subprocess
from pathlib import Path
from typing import Optional


class MetadataDetector:
    """Detect project metadata from various sources."""

    LICENSE_PATTERNS = {
        "MIT": [
            r"MIT License",
            r"Permission is hereby granted, free of charge",
        ],
        "Apache-2.0": [
            r"Apache License.*Version 2\.0",
            r"Licensed under the Apache License",
        ],
        "GPL-3.0": [
            r"GNU GENERAL PUBLIC LICENSE.*Version 3",
            r"This program is free software: you can redistribute it",
        ],
        "BSD-3-Clause": [
            r"BSD 3-Clause",
            r"Redistribution and use in source and binary forms",
        ],
        "ISC": [
            r"ISC License",
            r"Permission to use, copy, modify",
        ],
    }

    def __init__(self, project_dir: Path):
        """Initialize detector with project directory."""
        self.project_dir = project_dir

    def detect_project_name(self) -> str:
        """Detect project name from directory name."""
        name = self.project_dir.name

        # Normalize: lowercase, replace underscores/spaces with hyphens
        name = name.lower()
        name = re.sub(r"[_\s]+", "-", name)

        # Remove invalid characters
        name = re.sub(r"[^a-z0-9\-.]", "", name)

        # Ensure doesn't start with number or hyphen
        if name and name[0] in "-0123456789":
            name = "project-" + name

        return name or "my-project"

    def detect_version(self) -> str:
        """Detect version from common sources or return default."""
        # Try to find version in __init__.py
        for init_file in self.project_dir.rglob("__init__.py"):
            try:
                content = init_file.read_text(encoding="utf-8")
                match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1)
            except Exception:
                pass

        # Try to find version in setup.py
        setup_py = self.project_dir / "setup.py"
        if setup_py.exists():
            try:
                content = setup_py.read_text(encoding="utf-8")
                match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1)
            except Exception:
                pass

        # Try git tags
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                tag = result.stdout.strip()
                # Remove 'v' prefix if present
                if tag.startswith("v"):
                    tag = tag[1:]
                return tag
        except Exception:
            pass

        # Default version
        return "0.1.0"

    def detect_python_version(self) -> str:
        """Detect minimum Python version from various sources."""
        # Check .python-version file
        python_version_file = self.project_dir / ".python-version"
        if python_version_file.exists():
            try:
                content = python_version_file.read_text(encoding="utf-8").strip()
                # Extract major.minor version
                match = re.match(r"(\d+\.\d+)", content)
                if match:
                    return f">={match.group(1)}"
            except Exception:
                pass

        # Check for version classifiers in setup.py
        setup_py = self.project_dir / "setup.py"
        if setup_py.exists():
            try:
                content = setup_py.read_text(encoding="utf-8")
                # Find highest Python version in classifiers
                versions = re.findall(
                    r"Programming Language :: Python :: (\d+\.\d+)", content
                )
                if versions:
                    min_version = min(
                        versions, key=lambda v: tuple(map(int, v.split(".")))
                    )
                    return f">={min_version}"
            except Exception:
                pass

        # Use permissive fallback - no upper bound initially
        # If installation fails, the auto-retry logic will add constraints
        return ">=3.8"

    def detect_description(self) -> Optional[str]:
        """Detect project description from README."""
        readme = self.find_readme()
        if not readme:
            return None

        try:
            content = readme.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.splitlines() if line.strip()]

            # Skip title/header lines (markdown # or rst ===)
            for line in lines:
                if line.startswith("#") or line.startswith("=") or line.startswith("-"):
                    continue
                # First non-header line is likely the description
                if len(line) > 10 and not line.startswith("!"):  # Skip badges
                    return line[:200]  # Limit to 200 chars

        except Exception:
            pass

        return None

    def find_readme(self) -> Optional[Path]:
        """Find README file in project directory."""
        for filename in ["README.md", "README.rst", "README.txt", "README"]:
            readme = self.project_dir / filename
            if readme.exists():
                return readme
        return None

    def detect_license(self) -> Optional[str]:
        """Detect license type from LICENSE file."""
        for filename in ["LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING"]:
            license_file = self.project_dir / filename
            if license_file.exists():
                try:
                    content = license_file.read_text(encoding="utf-8")

                    # Check against known patterns
                    for license_type, patterns in self.LICENSE_PATTERNS.items():
                        for pattern in patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                return license_type

                    # If we found a LICENSE file but couldn't identify it
                    return "UNKNOWN"

                except Exception:
                    pass

        return None

    def detect_authors(self) -> list[dict[str, str]]:
        """Detect authors from git config."""
        authors = []

        try:
            # Get git user name
            result = subprocess.run(
                ["git", "config", "user.name"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            name = result.stdout.strip() if result.returncode == 0 else None

            # Get git user email
            result = subprocess.run(
                ["git", "config", "user.email"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            email = result.stdout.strip() if result.returncode == 0 else None

            if name or email:
                author = {}
                if name:
                    author["name"] = name
                if email:
                    author["email"] = email
                authors.append(author)

        except Exception:
            pass

        return authors

    def is_git_repo(self) -> bool:
        """Check if project directory is a git repository."""
        git_dir = self.project_dir / ".git"
        return git_dir.exists()

    def get_git_remote_url(self) -> Optional[str]:
        """Get the git remote URL if available."""
        try:
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                # Convert SSH URLs to HTTPS for display
                if url.startswith("git@"):
                    url = url.replace("git@", "https://").replace(".com:", ".com/")
                    url = url.replace(".git", "")
                return url
        except Exception:
            pass

        return None

    def detect_all_metadata(self) -> dict:
        """Detect all metadata and return as dictionary."""
        readme = self.find_readme()

        metadata = {
            "name": self.detect_project_name(),
            "version": self.detect_version(),
            "description": self.detect_description(),
            "readme": readme.name if readme else None,
            "requires_python": self.detect_python_version(),
            "license": self.detect_license(),
            "authors": self.detect_authors(),
            "repository_url": self.get_git_remote_url(),
            "is_git_repo": self.is_git_repo(),
        }

        return metadata
