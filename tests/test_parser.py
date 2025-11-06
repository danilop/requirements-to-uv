"""Tests for requirements.txt parser."""

import tempfile
from pathlib import Path


from requirements_to_uv.parser import RequirementsParser


def test_parse_simple_requirement():
    """Test parsing a simple package requirement."""
    parser = RequirementsParser()
    content = "requests>=2.28.0"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        f.flush()
        filepath = Path(f.name)

    try:
        results = parser.parse_file(filepath)
        assert len(results) == 1

        req = results[0]
        assert req.package == "requests"
        assert req.version_spec == ">=2.28.0"
        assert req.source_type == "pypi"
        assert not req.editable
    finally:
        filepath.unlink()


def test_parse_with_extras():
    """Test parsing package with extras."""
    parser = RequirementsParser()
    content = "celery[redis,msgpack]>=5.0.0"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        f.flush()
        filepath = Path(f.name)

    try:
        results = parser.parse_file(filepath)
        assert len(results) == 1

        req = results[0]
        assert req.package == "celery"
        assert set(req.extras) == {"redis", "msgpack"}
        assert req.version_spec == ">=5.0.0"
    finally:
        filepath.unlink()


def test_parse_with_markers():
    """Test parsing package with environment markers."""
    parser = RequirementsParser()
    content = 'pytest>=8.0.0 ; python_version >= "3.8"'

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        f.flush()
        filepath = Path(f.name)

    try:
        results = parser.parse_file(filepath)
        assert len(results) == 1

        req = results[0]
        assert req.package == "pytest"
        assert req.markers is not None
        assert "python_version" in req.markers
    finally:
        filepath.unlink()


def test_parse_git_url():
    """Test parsing Git URL requirement."""
    parser = RequirementsParser()
    content = "git+https://github.com/user/repo.git@main#egg=mypackage"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        f.flush()
        filepath = Path(f.name)

    try:
        results = parser.parse_file(filepath)
        assert len(results) == 1

        req = results[0]
        assert req.package == "mypackage"
        assert req.source_type == "git"
        assert "github.com/user/repo" in req.source_info["url"]
        assert req.source_info["ref"] == "main"
    finally:
        filepath.unlink()


def test_parse_editable_path():
    """Test parsing editable local path."""
    parser = RequirementsParser()
    content = "-e ./local-package"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        f.flush()
        filepath = Path(f.name)

    try:
        results = parser.parse_file(filepath)
        assert len(results) == 1

        req = results[0]
        assert req.source_type == "path"
        assert req.editable
        assert req.source_info["path"] == "./local-package"
    finally:
        filepath.unlink()


def test_parse_comments():
    """Test that comments are properly ignored."""
    parser = RequirementsParser()
    content = """# This is a comment
requests>=2.28.0  # inline comment
# Another comment
flask>=3.0.0
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        f.flush()
        filepath = Path(f.name)

    try:
        results = parser.parse_file(filepath)
        assert len(results) == 2

        packages = [r.package for r in results]
        assert "requests" in packages
        assert "flask" in packages
    finally:
        filepath.unlink()


def test_parse_with_hashes():
    """Test that hashes are stripped with warning."""
    parser = RequirementsParser()
    warnings = []
    parser.warn = lambda msg: warnings.append(msg)

    content = "requests==2.28.0 --hash=sha256:abc123"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        f.flush()
        filepath = Path(f.name)

    try:
        results = parser.parse_file(filepath)
        assert len(results) == 1

        req = results[0]
        assert req.package == "requests"
        assert "hash" in str(req.warnings).lower()
    finally:
        filepath.unlink()


def test_parse_poetry_version():
    """Test conversion of Poetry's ^ syntax."""
    parser = RequirementsParser()
    content = "django^4.2.0"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        f.flush()
        filepath = Path(f.name)

    try:
        results = parser.parse_file(filepath)
        assert len(results) == 1

        req = results[0]
        assert req.package == "django"
        # Should convert to >=4.2.0,<5.0.0
        assert ">=" in req.version_spec
        assert "<" in req.version_spec
        assert any("Poetry" in w for w in req.warnings)
    finally:
        filepath.unlink()


def test_find_requirements_files(tmp_path):
    """Test finding multiple requirements files."""
    # Create test files
    (tmp_path / "requirements.txt").write_text("requests>=2.0")
    (tmp_path / "requirements-dev.txt").write_text("pytest>=8.0")
    (tmp_path / "requirements-test.txt").write_text("coverage>=7.0")

    parser = RequirementsParser()
    files = parser.find_requirements_files(tmp_path)

    assert "main" in files
    assert "dev" in files
    assert "test" in files
    assert files["main"].name == "requirements.txt"
    assert files["dev"].name == "requirements-dev.txt"
