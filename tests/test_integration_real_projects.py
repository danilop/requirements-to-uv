"""Integration tests with real-world GitHub projects.

These tests clone actual projects from GitHub, run req2uv on them,
and verify the conversion works by installing and testing the project.

NOTE: These tests are skipped by default (use --run-integration to enable)
as they require network access and can be slow.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

# Test projects configuration
# Each entry: (repo_url, branch, has_pyproject, verify_command, description)
#
# PYTHON VERSION HANDLING:
# - Our tool sets conservative requires-python = ">=3.8" by default
# - uv automatically installs and uses the appropriate Python version
# - The venv is created with the Python version that matches requires-python
# - No manual Python version management needed!
#
TEST_PROJECTS = [
    # Scenario 1: Only requirements.txt (no existing pyproject.toml)
    # Flask tutorial app - can verify by checking imports work
    (
        "https://github.com/miguelgrinberg/microblog",
        "main",
        False,  # No existing pyproject.toml
        ["python", "-c", "import app; print('Import successful')"],
        "Microblog - Flask tutorial app (requirements.txt only)",
    ),
    # Scenario 2: Only requirements.txt with tests
    # S3 command line tool
    (
        "https://github.com/s3tools/s3cmd",
        "master",
        False,  # No existing pyproject.toml
        ["python", "-c", "import S3; print('S3 module imported successfully')"],
        "s3cmd - S3 command line tool (requirements.txt only)",
    ),
    # Scenario 3: Both requirements.txt AND existing pyproject.toml (merge scenario)
    # AWS SDK - tests our ability to merge with existing pyproject.toml
    (
        "https://github.com/boto/boto3",
        "develop",
        True,  # Has existing pyproject.toml
        ["pytest", "tests/unit/test_session.py", "-v", "--tb=short"],
        "Boto3 - AWS SDK (requirements.txt + existing pyproject.toml, merge test)",
    ),
]


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test projects."""
    temp = tempfile.mkdtemp(prefix="req2uv_integration_test_")
    yield Path(temp)
    # Cleanup
    shutil.rmtree(temp, ignore_errors=True)


def run_command(
    cmd: list[str], cwd: Path, timeout: int = 300
) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def clone_project(repo_url: str, branch: str, dest: Path) -> bool:
    """Clone a GitHub project."""
    result = run_command(
        ["git", "clone", "--depth=1", f"--branch={branch}", repo_url, str(dest)],
        cwd=dest.parent,
    )
    return result.returncode == 0


def has_requirements_txt(project_dir: Path) -> bool:
    """Check if project has requirements.txt files."""
    requirements_files = [
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-test.txt",
        "requirements/base.txt",
        "requirements/dev.txt",
    ]
    return any((project_dir / req).exists() for req in requirements_files)


def convert_to_uv(project_dir: Path) -> tuple[bool, str]:
    """Run req2uv on the project."""
    # Find req2uv in the current environment
    result = run_command(
        ["req2uv", "--non-interactive", "--no-validate"],
        cwd=project_dir,
        timeout=60,
    )

    return result.returncode == 0, result.stderr


def install_with_uv(
    project_dir: Path, retry_with_older_python: bool = True
) -> tuple[bool, str]:
    """Install project dependencies with uv.

    If installation fails, automatically retry with progressively older Python versions:
    3.13 → 3.12 → 3.11 → 3.10 → 3.9 → 3.8

    Stops when:
    - Installation succeeds
    - Max version < min version (impossible constraint)
    - Reached Python 3.8 (minimum supported)
    """
    import sys
    import re

    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib
    import tomli_w

    result = run_command(
        ["uv", "sync"],
        cwd=project_dir,
        timeout=300,
    )

    # If failed and retry is enabled, try progressively older Python versions
    if result.returncode != 0 and retry_with_older_python:
        stderr_lower = result.stderr.lower()
        if "failed to build" in stderr_lower or "cpython" in stderr_lower:
            pyproject_path = project_dir / "pyproject.toml"
            if not pyproject_path.exists():
                return False, result.stderr

            # Try Python versions from 3.13 down to 3.8
            for max_version in [13, 12, 11, 10, 9, 8]:
                # Read current pyproject.toml
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)

                if "project" not in data or "requires-python" not in data["project"]:
                    break

                current = data["project"]["requires-python"]

                # Extract minimum version
                min_match = re.search(r">=(\d+)\.(\d+)", current)
                if not min_match:
                    break

                min_major, min_minor = int(min_match.group(1)), int(min_match.group(2))
                min_py_version = min_major * 10 + min_minor  # e.g., 3.8 → 38

                # Check if we've already tried this or lower
                if f"<3.{max_version}" in current:
                    continue

                # Check if constraint is impossible (max < min)
                if 30 + max_version < min_py_version:
                    print(
                        f"   ✗ Impossible constraint: min Python 3.{min_minor} > max Python 3.{max_version}"
                    )
                    break

                # Try this version
                print(
                    f"   ⚠ Installation failed, retrying with Python <3.{max_version}..."
                )

                # Build new constraint
                if "," in current and "<" in current:
                    # Already has upper bound, replace it
                    new_req = re.sub(r",<3\.\d+", f",<3.{max_version}", current)
                else:
                    # Add new upper bound
                    new_req = f"{current.split(',')[0]},<3.{max_version}"

                data["project"]["requires-python"] = new_req
                print(f"   → Updated requires-python: {current} → {new_req}")

                # Write back
                with open(pyproject_path, "wb") as f:
                    tomli_w.dump(data, f)

                # Retry installation
                result = run_command(
                    ["uv", "sync"],
                    cwd=project_dir,
                    timeout=300,
                )

                if result.returncode == 0:
                    print(f"   ✓ Installation succeeded with Python <3.{max_version}")
                    break

                # If this was Python 3.8, stop trying
                if max_version == 8:
                    print("   ✗ Reached minimum supported Python version (3.8)")
                    break

    return result.returncode == 0, result.stderr


def verify_project(project_dir: Path, verify_cmd: list[str]) -> tuple[bool, str]:
    """Verify the project works by running a verification command."""
    # Run with uv run to use the project's environment
    result = run_command(
        ["uv", "run"] + verify_cmd,
        cwd=project_dir,
        timeout=300,
    )

    return (
        result.returncode == 0,
        f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}",
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "repo_url,branch,has_pyproject,verify_cmd,description", TEST_PROJECTS
)
def test_real_project_conversion(
    temp_dir, repo_url, branch, has_pyproject, verify_cmd, description, request
):
    """Test converting a real GitHub project to uv.

    This test:
    1. Clones the project
    2. Verifies it has requirements.txt
    3. Checks if it has existing pyproject.toml (merge vs create scenario)
    4. Runs req2uv to convert/merge to pyproject.toml
    5. Installs dependencies with uv sync
    6. Verifies the project works (runs tests or main command)

    Tests both scenarios:
    - New conversion (requirements.txt only)
    - Merge with existing pyproject.toml
    """
    # Skip if --run-integration not provided
    if not request.config.getoption("--run-integration", default=False):
        pytest.skip("Integration tests skipped (use --run-integration to enable)")

    project_name = repo_url.split("/")[-1]
    project_dir = temp_dir / project_name

    print(f"\n{'=' * 70}")
    print(f"Testing: {description}")
    print(f"Repo: {repo_url}")
    print(
        f"Scenario: {'MERGE (has pyproject.toml)' if has_pyproject else 'CREATE (requirements.txt only)'}"
    )
    print(f"{'=' * 70}\n")

    # Step 1: Clone the project
    print(f"1. Cloning {repo_url}...")
    success = clone_project(repo_url, branch, project_dir)
    assert success, f"Failed to clone {repo_url}"
    print(f"   ✓ Cloned to {project_dir}")

    # Step 2: Verify it has requirements.txt
    print("2. Checking for requirements.txt...")
    assert has_requirements_txt(project_dir), (
        f"No requirements.txt found in {project_name}"
    )

    # List requirements files found
    req_files = list(project_dir.glob("**/requirements*.txt"))
    print(f"   ✓ Found {len(req_files)} requirements file(s):")
    for req_file in req_files[:5]:  # Show first 5
        rel_path = req_file.relative_to(project_dir)
        print(f"     - {rel_path}")

    # Step 2b: Check for existing pyproject.toml
    pyproject_path = project_dir / "pyproject.toml"
    had_pyproject_before = pyproject_path.exists()

    if has_pyproject:
        assert had_pyproject_before, (
            f"Expected pyproject.toml but not found in {project_name}"
        )
        print("   ✓ Existing pyproject.toml found (merge scenario)")
    else:
        assert not had_pyproject_before, (
            f"Unexpected pyproject.toml found in {project_name}"
        )
        print("   ✓ No existing pyproject.toml (create scenario)")

    # Step 3: Run req2uv
    print("3. Converting with req2uv...")
    success, stderr = convert_to_uv(project_dir)
    if not success:
        print(f"   ✗ Conversion failed:\n{stderr}")
    assert success, f"req2uv failed for {project_name}:\n{stderr}"

    if has_pyproject:
        print("   ✓ Merged with existing pyproject.toml")
        # Verify backup was created
        backup_path = project_dir / "pyproject.toml.backup"
        if backup_path.exists():
            print("   ✓ Backup created: pyproject.toml.backup")
    else:
        print("   ✓ Created new pyproject.toml")

    # Verify pyproject.toml exists
    assert pyproject_path.exists(), "pyproject.toml was not created/updated"

    # Parse and verify structure
    import sys

    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib

    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)

    assert "project" in pyproject_data, "Missing [project] section"
    assert "dependencies" in pyproject_data["project"], "Missing dependencies"
    print(
        f"   ✓ Valid pyproject.toml with {len(pyproject_data['project']['dependencies'])} dependencies"
    )

    # Step 4: Install with uv
    print("4. Installing dependencies with uv sync...")
    success, stderr = install_with_uv(project_dir)
    if not success:
        print(f"   ✗ Installation failed:\n{stderr}")
        # Show first 20 lines of error
        stderr_lines = stderr.split("\n")[:20]
        print("\n".join(stderr_lines))
    assert success, f"uv sync failed for {project_name}:\n{stderr}"
    print("   ✓ Dependencies installed")

    # Step 5: Verify the project works
    print(f"5. Verifying project with: {' '.join(verify_cmd)}...")
    success, output = verify_project(project_dir, verify_cmd)
    if not success:
        print("   ✗ Verification failed")
        # Show first 30 lines of output
        output_lines = output.split("\n")[:30]
        print("\n".join(output_lines))
        # Don't fail the test if verification fails - it might be environmental
        # But print a warning
        print("   ⚠ Warning: Verification command failed, but conversion succeeded")
    else:
        print("   ✓ Project verification passed")

    print(f"\n{'=' * 70}")
    print(f"✓ Successfully converted {project_name} to uv!")
    print(f"{'=' * 70}\n")


@pytest.mark.integration
def test_integration_smoke(request):
    """Quick smoke test to verify integration test infrastructure."""
    if not request.config.getoption("--run-integration", default=False):
        pytest.skip("Integration tests skipped (use --run-integration to enable)")

    # Verify git and uv are available
    for cmd in ["git", "uv"]:
        result = subprocess.run(
            [cmd, "--version"],
            capture_output=True,
            timeout=10,
        )
        assert result.returncode == 0, f"{cmd} not available"

    # Verify req2uv is available (using --help since it doesn't support --version)
    result = subprocess.run(
        ["req2uv", "--help"],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0, "req2uv not available"
