"""Parse requirements.txt files and extract dependency information."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from packaging.requirements import Requirement, InvalidRequirement


@dataclass
class ParsedRequirement:
    """Structured representation of a parsed requirement."""

    package: str
    version_spec: str
    extras: list[str]
    markers: Optional[str]
    source_type: str  # 'pypi', 'git', 'url', 'path'
    source_info: dict
    editable: bool
    line_number: int
    original_line: str
    warnings: list[str]


class RequirementsParser:
    """Parser for requirements.txt files with comprehensive edge case handling."""

    # Regex patterns for different requirement formats
    GIT_URL_PATTERN = re.compile(
        r"^(?P<editable>-e\s+)?"
        r"git\+(?P<protocol>https?|ssh|git)://(?P<url>[^@#]+)"
        r"(?:@(?P<ref>[^#]+))?"
        r"(?:#(?P<fragment>.+))?$"
    )

    VCS_PATTERN = re.compile(r"^(?P<editable>-e\s+)?(?P<vcs>hg|svn|bzr)\+")

    URL_PATTERN = re.compile(
        r"^(?P<url>https?://[^\s#]+\.(?:whl|tar\.gz|zip|tgz|tar\.bz2))"
        r"(?:#(?P<fragment>.+))?$"
    )

    LOCAL_PATH_PATTERN = re.compile(
        r"^(?P<editable>-e\s+)?"
        r"(?P<path>\.{1,2}/[^\s]+|/[^\s]+|[a-zA-Z]:[/\\][^\s]+)$"
    )

    POETRY_VERSION_PATTERN = re.compile(r"\^(\d+\.\d+(?:\.\d+)?)")

    def __init__(self, warn_callback=None):
        """Initialize parser with optional warning callback."""
        self.warn = warn_callback or print
        self.parsed_files = set()  # Track parsed files to prevent infinite loops

    def parse_file(self, filepath: Path) -> list[ParsedRequirement]:
        """Parse a requirements.txt file and return structured requirements."""
        if filepath in self.parsed_files:
            self.warn(f"Warning: Circular reference detected, skipping {filepath}")
            return []

        self.parsed_files.add(filepath)
        requirements = []

        try:
            # Try UTF-8 first, fallback to latin-1
            try:
                content = filepath.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                self.warn(
                    f"Warning: UTF-8 decode failed for {filepath}, trying latin-1"
                )
                content = filepath.read_text(encoding="latin-1")

            lines = content.splitlines()
            lines = self._handle_continuations(lines)

            for line_num, line in enumerate(lines, 1):
                parsed = self._parse_line(line, line_num, filepath)
                if parsed:
                    requirements.append(parsed)

        except FileNotFoundError:
            self.warn(f"Error: File not found: {filepath}")
        except Exception as e:
            self.warn(f"Error reading {filepath}: {e}")

        return requirements

    def _handle_continuations(self, lines: list[str]) -> list[str]:
        """Join lines that end with backslash continuation."""
        result = []
        current_line = ""

        for line in lines:
            stripped = line.rstrip()
            if stripped.endswith("\\"):
                current_line += stripped[:-1] + " "
            else:
                current_line += stripped
                if current_line:
                    result.append(current_line)
                current_line = ""

        if current_line:
            result.append(current_line)

        return result

    def _parse_line(
        self, line: str, line_num: int, filepath: Path
    ) -> Optional[ParsedRequirement]:
        """Parse a single line from requirements.txt."""
        original_line = line
        warnings = []

        # Strip whitespace
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            return None

        # Strip inline comments (but preserve markers with semicolons)
        if "#" in line:
            # Don't strip if it's part of a URL fragment
            if not re.search(r"git\+.*#|https?://.*#", line):
                line = line.split("#")[0].strip()

        # Handle -r (recursive requirements)
        if line.startswith("-r ") or line.startswith("--requirement "):
            ref_file = line.split(maxsplit=1)[1].strip()
            ref_path = filepath.parent / ref_file
            self.warn(f"Info: Processing referenced file: {ref_path}")
            # This will be handled by the caller
            return None

        # Handle -c (constraints)
        if line.startswith("-c ") or line.startswith("--constraint "):
            warnings.append(
                "Constraints files not directly supported in pyproject.toml. "
                "Consider merging into main requirements or using CLI."
            )
            return None

        # Handle global options
        if line.startswith("--"):
            return self._handle_global_option(line, line_num, original_line, warnings)

        # Handle hashes
        if "--hash=" in line:
            line, hash_warning = self._strip_hashes(line)
            warnings.append(hash_warning)

        # Try to parse as Git URL
        git_match = self.GIT_URL_PATTERN.match(line)
        if git_match:
            return self._parse_git_requirement(
                git_match, line_num, original_line, warnings
            )

        # Check for other VCS (unsupported)
        vcs_match = self.VCS_PATTERN.match(line)
        if vcs_match:
            vcs_type = vcs_match.group("vcs")
            warnings.append(
                f"VCS type '{vcs_type}' not supported by uv. Only git is supported."
            )
            return None

        # Try to parse as direct URL
        url_match = self.URL_PATTERN.match(line)
        if url_match:
            return self._parse_url_requirement(
                url_match, line_num, original_line, warnings
            )

        # Try to parse as local path
        path_match = self.LOCAL_PATH_PATTERN.match(line)
        if path_match:
            return self._parse_path_requirement(
                path_match, line_num, original_line, warnings
            )

        # Parse as standard PEP 508 requirement
        return self._parse_standard_requirement(line, line_num, original_line, warnings)

    def _strip_hashes(self, line: str) -> tuple[str, str]:
        """Remove hashes from requirement line and return warning."""
        # Remove all --hash= options
        cleaned = re.sub(r"\s*--hash=[^\s]+", "", line)
        warning = (
            "Package hashes not supported in pyproject.toml. "
            "Use uv.lock for reproducible installs with hash verification."
        )
        return cleaned.strip(), warning

    def _handle_global_option(
        self, line: str, line_num: int, original_line: str, warnings: list[str]
    ) -> Optional[ParsedRequirement]:
        """Handle global options like --index-url, --find-links, etc."""
        if line.startswith("--index-url") or line.startswith("--extra-index-url"):
            url = line.split(maxsplit=1)[1] if " " in line else ""
            warnings.append(
                f"Index URLs not supported in pyproject.toml. "
                f"Configure via: uv pip install --index-url {url}"
            )
        elif line.startswith("--find-links"):
            warnings.append("--find-links not supported in pyproject.toml")
        elif line.startswith("--trusted-host"):
            warnings.append("--trusted-host is a CLI-only option")
        else:
            warnings.append(f"Unsupported option: {line.split()[0]}")

        # Return a placeholder to preserve warnings
        if warnings:
            return ParsedRequirement(
                package="",
                version_spec="",
                extras=[],
                markers=None,
                source_type="option",
                source_info={"option": line},
                editable=False,
                line_number=line_num,
                original_line=original_line,
                warnings=warnings,
            )
        return None

    def _parse_git_requirement(
        self, match: re.Match, line_num: int, original_line: str, warnings: list[str]
    ) -> ParsedRequirement:
        """Parse a Git URL requirement."""
        editable = bool(match.group("editable"))
        protocol = match.group("protocol")
        url = match.group("url")
        ref = match.group("ref") or "main"
        fragment = match.group("fragment") or ""

        # Parse fragment (egg=name, subdirectory=path)
        package_name = None
        subdirectory = None

        if fragment:
            for part in fragment.split("&"):
                if part.startswith("egg="):
                    package_name = part[4:]
                elif part.startswith("subdirectory="):
                    subdirectory = part[13:]

        # Generate package name if not specified
        if not package_name:
            # Extract from URL (last part before .git)
            url_parts = url.rstrip("/").split("/")
            package_name = url_parts[-1].replace(".git", "")

        # Convert SSH URLs to HTTPS if possible
        if protocol == "ssh":
            if "github.com" in url or "gitlab.com" in url or "bitbucket.org" in url:
                url = url.replace("git@", "").replace(":", "/")
                protocol = "https"
                warnings.append(f"Converted SSH URL to HTTPS for {package_name}")
            else:
                warnings.append(
                    f"SSH URLs may not be supported. Consider using HTTPS for {package_name}"
                )

        source_info = {"url": f"{protocol}://{url}", "ref": ref, "editable": editable}

        if subdirectory:
            source_info["subdirectory"] = subdirectory

        return ParsedRequirement(
            package=package_name,
            version_spec="",
            extras=[],
            markers=None,
            source_type="git",
            source_info=source_info,
            editable=editable,
            line_number=line_num,
            original_line=original_line,
            warnings=warnings,
        )

    def _parse_url_requirement(
        self, match: re.Match, line_num: int, original_line: str, warnings: list[str]
    ) -> ParsedRequirement:
        """Parse a direct URL requirement."""
        url = match.group("url")
        fragment = match.group("fragment") or ""

        # Extract package name from URL or fragment
        package_name = None
        if fragment and "egg=" in fragment:
            package_name = fragment.split("egg=")[1].split("&")[0]
        else:
            # Try to extract from filename
            filename = url.split("/")[-1]
            # Remove version and extension
            package_name = re.sub(r"-\d+.*", "", filename)

        source_info = {"url": url}

        return ParsedRequirement(
            package=package_name,
            version_spec="",
            extras=[],
            markers=None,
            source_type="url",
            source_info=source_info,
            editable=False,
            line_number=line_num,
            original_line=original_line,
            warnings=warnings,
        )

    def _parse_path_requirement(
        self, match: re.Match, line_num: int, original_line: str, warnings: list[str]
    ) -> ParsedRequirement:
        """Parse a local path requirement."""
        editable = bool(match.group("editable"))
        path = match.group("path").strip()

        # Extract package name from path (last component)
        package_name = Path(path).name

        source_info = {"path": path, "editable": editable}

        return ParsedRequirement(
            package=package_name,
            version_spec="",
            extras=[],
            markers=None,
            source_type="path",
            source_info=source_info,
            editable=editable,
            line_number=line_num,
            original_line=original_line,
            warnings=warnings,
        )

    def _parse_standard_requirement(
        self, line: str, line_num: int, original_line: str, warnings: list[str]
    ) -> Optional[ParsedRequirement]:
        """Parse a standard PEP 508 requirement."""
        # Check for Poetry-style ^ version
        if "^" in line:
            line, poetry_warning = self._convert_poetry_version(line)
            warnings.append(poetry_warning)

        try:
            req = Requirement(line)

            # Extract version specifier
            version_spec = str(req.specifier) if req.specifier else ""

            # Extract extras
            extras = list(req.extras) if req.extras else []

            # Extract markers
            markers = str(req.marker) if req.marker else None

            return ParsedRequirement(
                package=req.name,
                version_spec=version_spec,
                extras=extras,
                markers=markers,
                source_type="pypi",
                source_info={},
                editable=False,
                line_number=line_num,
                original_line=original_line,
                warnings=warnings,
            )

        except InvalidRequirement as e:
            self.warn(f"Error parsing line {line_num}: {line}")
            self.warn(f"  Reason: {e}")
            return None

    def _convert_poetry_version(self, line: str) -> tuple[str, str]:
        """Convert Poetry's ^ version syntax to PEP 440 compatible range."""
        match = self.POETRY_VERSION_PATTERN.search(line)
        if not match:
            return line, "Poetry ^ syntax detected but couldn't parse version"

        version = match.group(1)
        parts = version.split(".")

        # ^ means "compatible version": ^1.2.3 -> >=1.2.3,<2.0.0
        if len(parts) >= 1:
            major = int(parts[0])
            upper_bound = f"<{major + 1}.0.0"
            lower_bound = f">={version}"
            converted = line.replace(f"^{version}", f"{lower_bound},{upper_bound}")

            warning = (
                f"Converted Poetry syntax ^{version} to {lower_bound},{upper_bound}. "
                "Poetry's ^ syntax is not part of PEP 440."
            )
            return converted, warning

        return line, "Could not convert Poetry ^ syntax"

    def find_requirements_files(self, directory: Path) -> dict[str, Path]:
        """Find all requirements files in a directory and categorize them."""
        files = {}

        # Common patterns
        patterns = {
            "main": ["requirements.txt", "requirements.in"],
            "dev": [
                "requirements-dev.txt",
                "dev-requirements.txt",
                "requirements_dev.txt",
            ],
            "test": [
                "requirements-test.txt",
                "test-requirements.txt",
                "requirements_test.txt",
            ],
            "docs": [
                "requirements-docs.txt",
                "docs-requirements.txt",
                "requirements_docs.txt",
            ],
            "lint": [
                "requirements-lint.txt",
                "lint-requirements.txt",
                "requirements_lint.txt",
            ],
        }

        for category, pattern_list in patterns.items():
            for pattern in pattern_list:
                filepath = directory / pattern
                if filepath.exists():
                    files[category] = filepath
                    break  # Use first matching file for each category

        return files
