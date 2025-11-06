"""Convert parsed requirements to pyproject.toml format."""

from .parser import ParsedRequirement


class PyProjectConverter:
    """Convert parsed requirements to pyproject.toml structure."""

    def __init__(self):
        """Initialize converter."""
        self.warnings = []
        self.comments = []

    def convert_to_pyproject(
        self, metadata: dict, requirements_by_group: dict[str, list[ParsedRequirement]]
    ) -> dict:
        """Convert metadata and requirements to pyproject.toml structure."""
        pyproject = {}

        # Build [project] section
        pyproject["project"] = self._build_project_section(
            metadata, requirements_by_group.get("main", [])
        )

        # Build [dependency-groups] section if there are non-main requirements
        dependency_groups = {}
        for group, reqs in requirements_by_group.items():
            if group != "main" and reqs:
                dependency_groups[group] = self._build_dependency_list(reqs)

        if dependency_groups:
            pyproject["dependency-groups"] = dependency_groups

        # Build [tool.uv.sources] section for non-PyPI sources
        sources = self._build_sources_section(requirements_by_group)
        if sources:
            pyproject.setdefault("tool", {})["uv"] = {"sources": sources}

        return pyproject

    def _build_project_section(
        self, metadata: dict, main_requirements: list[ParsedRequirement]
    ) -> dict:
        """Build the [project] section of pyproject.toml."""
        project = {
            "name": metadata["name"],
            "version": metadata["version"],
        }

        # Add optional metadata fields
        if metadata.get("description"):
            project["description"] = metadata["description"]

        if metadata.get("readme"):
            project["readme"] = metadata["readme"]

        if metadata.get("requires_python"):
            project["requires-python"] = metadata["requires_python"]

        if metadata.get("authors"):
            project["authors"] = metadata["authors"]

        if metadata.get("license"):
            project["license"] = {"text": metadata["license"]}

        # Add dependencies
        project["dependencies"] = self._build_dependency_list(main_requirements)

        return project

    def _build_dependency_list(
        self, requirements: list[ParsedRequirement]
    ) -> list[str]:
        """Build a list of dependency strings from parsed requirements."""
        dependencies = []

        for req in requirements:
            # Skip non-package entries (options, etc.)
            if req.source_type == "option":
                # Collect warnings and comments
                self.warnings.extend(req.warnings)
                if req.source_info.get("option"):
                    self.comments.append(
                        f"# Original option: {req.source_info['option']}"
                    )
                continue

            # Collect any warnings
            self.warnings.extend(req.warnings)

            # Build dependency string based on source type
            if req.source_type == "pypi":
                dep_str = self._format_pypi_dependency(req)
            else:
                # Non-PyPI sources: just use package name, source defined in tool.uv.sources
                dep_str = self._format_package_name_only(req)

            if dep_str:
                dependencies.append(dep_str)

        return dependencies

    def _format_pypi_dependency(self, req: ParsedRequirement) -> str:
        """Format a PyPI dependency string."""
        parts = [req.package]

        # Add extras
        if req.extras:
            parts[0] += f"[{','.join(req.extras)}]"

        # Add version specifier
        if req.version_spec:
            parts[0] += req.version_spec

        # Add markers
        if req.markers:
            # Ensure proper formatting with spaces around semicolon
            parts.append(f"; {req.markers}")

        return "".join(parts)

    def _format_package_name_only(self, req: ParsedRequirement) -> str:
        """Format package name with extras but no version (for non-PyPI sources)."""
        package = req.package

        # Add extras if present
        if req.extras:
            package += f"[{','.join(req.extras)}]"

        return package

    def _build_sources_section(
        self, requirements_by_group: dict[str, list[ParsedRequirement]]
    ) -> dict:
        """Build the [tool.uv.sources] section for non-PyPI dependencies."""
        sources = {}

        # Collect all requirements from all groups
        all_requirements = []
        for reqs in requirements_by_group.values():
            all_requirements.extend(reqs)

        for req in all_requirements:
            if req.source_type == "git":
                sources[req.package] = self._format_git_source(req)
            elif req.source_type == "url":
                sources[req.package] = self._format_url_source(req)
            elif req.source_type == "path":
                sources[req.package] = self._format_path_source(req)

        return sources

    def _format_git_source(self, req: ParsedRequirement) -> dict:
        """Format a Git source for tool.uv.sources."""
        source = {"git": req.source_info["url"]}

        # Add ref/tag/branch
        ref = req.source_info.get("ref", "main")

        # Try to determine if it's a tag, branch, or commit
        # For simplicity, use 'rev' for everything except obvious tags
        if ref.startswith("v") and any(c.isdigit() for c in ref):
            source["tag"] = ref
        elif ref in ["main", "master", "develop"]:
            source["branch"] = ref
        else:
            # Could be commit hash or branch
            source["rev"] = ref

        # Add subdirectory if present
        if "subdirectory" in req.source_info:
            source["subdirectory"] = req.source_info["subdirectory"]

        return source

    def _format_url_source(self, req: ParsedRequirement) -> dict:
        """Format a URL source for tool.uv.sources."""
        return {"url": req.source_info["url"]}

    def _format_path_source(self, req: ParsedRequirement) -> dict:
        """Format a path source for tool.uv.sources."""
        source = {"path": req.source_info["path"]}

        if req.editable:
            source["editable"] = True

        return source

    def get_warnings(self) -> list[str]:
        """Get list of warnings generated during conversion."""
        return self.warnings

    def get_comments(self) -> list[str]:
        """Get list of comments to add to the output file."""
        return self.comments

    def format_toml_with_comments(self, toml_content: str) -> str:
        """Add comments to TOML content."""
        if not self.comments:
            return toml_content

        # Add comments at the beginning
        comment_block = "\n".join(self.comments) + "\n\n"
        return comment_block + toml_content
