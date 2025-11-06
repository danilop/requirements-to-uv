"""Tests for pyproject.toml converter."""

from requirements_to_uv.converter import PyProjectConverter
from requirements_to_uv.parser import ParsedRequirement


def test_convert_simple_pypi_packages():
    """Test converting simple PyPI packages."""
    converter = PyProjectConverter()

    metadata = {
        "name": "test-project",
        "version": "0.1.0",
        "description": "A test project",
        "requires_python": ">=3.8",
    }

    requirements = [
        ParsedRequirement(
            package="requests",
            version_spec=">=2.28.0",
            extras=[],
            markers=None,
            source_type="pypi",
            source_info={},
            editable=False,
            line_number=1,
            original_line="requests>=2.28.0",
            warnings=[],
        ),
        ParsedRequirement(
            package="flask",
            version_spec=">=3.0.0",
            extras=[],
            markers=None,
            source_type="pypi",
            source_info={},
            editable=False,
            line_number=2,
            original_line="flask>=3.0.0",
            warnings=[],
        ),
    ]

    pyproject = converter.convert_to_pyproject(metadata, {"main": requirements})

    assert "project" in pyproject
    assert pyproject["project"]["name"] == "test-project"
    assert pyproject["project"]["version"] == "0.1.0"
    assert len(pyproject["project"]["dependencies"]) == 2
    assert "requests>=2.28.0" in pyproject["project"]["dependencies"]
    assert "flask>=3.0.0" in pyproject["project"]["dependencies"]


def test_convert_with_extras():
    """Test converting packages with extras."""
    converter = PyProjectConverter()

    metadata = {
        "name": "test-project",
        "version": "0.1.0",
    }

    requirements = [
        ParsedRequirement(
            package="celery",
            version_spec=">=5.0.0",
            extras=["redis", "msgpack"],
            markers=None,
            source_type="pypi",
            source_info={},
            editable=False,
            line_number=1,
            original_line="celery[redis,msgpack]>=5.0.0",
            warnings=[],
        ),
    ]

    pyproject = converter.convert_to_pyproject(metadata, {"main": requirements})

    deps = pyproject["project"]["dependencies"]
    assert len(deps) == 1
    assert "celery[redis,msgpack]>=5.0.0" in deps


def test_convert_with_markers():
    """Test converting packages with environment markers."""
    converter = PyProjectConverter()

    metadata = {
        "name": "test-project",
        "version": "0.1.0",
    }

    requirements = [
        ParsedRequirement(
            package="pytest",
            version_spec=">=8.0.0",
            extras=[],
            markers='python_version >= "3.8"',
            source_type="pypi",
            source_info={},
            editable=False,
            line_number=1,
            original_line='pytest>=8.0.0 ; python_version >= "3.8"',
            warnings=[],
        ),
    ]

    pyproject = converter.convert_to_pyproject(metadata, {"main": requirements})

    deps = pyproject["project"]["dependencies"]
    assert len(deps) == 1
    assert "pytest>=8.0.0" in deps[0]
    assert "python_version" in deps[0]


def test_convert_git_source():
    """Test converting Git source to tool.uv.sources."""
    converter = PyProjectConverter()

    metadata = {
        "name": "test-project",
        "version": "0.1.0",
    }

    requirements = [
        ParsedRequirement(
            package="mypackage",
            version_spec="",
            extras=[],
            markers=None,
            source_type="git",
            source_info={"url": "https://github.com/user/repo.git", "ref": "main"},
            editable=False,
            line_number=1,
            original_line="git+https://github.com/user/repo.git@main",
            warnings=[],
        ),
    ]

    pyproject = converter.convert_to_pyproject(metadata, {"main": requirements})

    # Check dependency is listed
    assert "mypackage" in pyproject["project"]["dependencies"]

    # Check source is defined
    assert "tool" in pyproject
    assert "uv" in pyproject["tool"]
    assert "sources" in pyproject["tool"]["uv"]
    assert "mypackage" in pyproject["tool"]["uv"]["sources"]

    source = pyproject["tool"]["uv"]["sources"]["mypackage"]
    assert source["git"] == "https://github.com/user/repo.git"
    assert "branch" in source or "rev" in source


def test_convert_dependency_groups():
    """Test converting to dependency groups."""
    converter = PyProjectConverter()

    metadata = {
        "name": "test-project",
        "version": "0.1.0",
    }

    main_reqs = [
        ParsedRequirement(
            package="requests",
            version_spec=">=2.28.0",
            extras=[],
            markers=None,
            source_type="pypi",
            source_info={},
            editable=False,
            line_number=1,
            original_line="requests>=2.28.0",
            warnings=[],
        ),
    ]

    dev_reqs = [
        ParsedRequirement(
            package="pytest",
            version_spec=">=8.0.0",
            extras=[],
            markers=None,
            source_type="pypi",
            source_info={},
            editable=False,
            line_number=1,
            original_line="pytest>=8.0.0",
            warnings=[],
        ),
    ]

    pyproject = converter.convert_to_pyproject(
        metadata, {"main": main_reqs, "dev": dev_reqs}
    )

    # Check main dependencies
    assert "requests>=2.28.0" in pyproject["project"]["dependencies"]

    # Check dev dependencies in dependency-groups
    assert "dependency-groups" in pyproject
    assert "dev" in pyproject["dependency-groups"]
    assert "pytest>=8.0.0" in pyproject["dependency-groups"]["dev"]


def test_warnings_collection():
    """Test that warnings are collected during conversion."""
    converter = PyProjectConverter()

    metadata = {
        "name": "test-project",
        "version": "0.1.0",
    }

    requirements = [
        ParsedRequirement(
            package="requests",
            version_spec=">=2.28.0",
            extras=[],
            markers=None,
            source_type="pypi",
            source_info={},
            editable=False,
            line_number=1,
            original_line="requests>=2.28.0",
            warnings=["Test warning"],
        ),
    ]

    converter.convert_to_pyproject(metadata, {"main": requirements})

    warnings = converter.get_warnings()
    assert len(warnings) == 1
    assert "Test warning" in warnings
