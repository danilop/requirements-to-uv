## Testing Guide

### Test Suite Overview

The project has two types of tests:

1. **Unit Tests** - Fast, isolated tests of individual components
2. **Integration Tests** - Slow, comprehensive tests with real GitHub projects

### Running Tests

#### Quick Tests (Unit Tests Only)

```bash
# Run all unit tests (fast, ~1 second)
uv run pytest tests -v

# Run specific test file
uv run pytest tests/test_parser.py -v

# Run with coverage
uv run pytest tests --cov=requirements_to_uv --cov-report=html
```

#### Integration Tests with Real Projects

Integration tests clone real GitHub projects and test the full conversion workflow.

**⚠️ Important Notes:**
- Requires network access (clones from GitHub)
- Takes 5-10 minutes to complete
- Requires ~100MB temporary disk space
- Projects are cloned to `/tmp` and cleaned up automatically

**Run integration tests:**

```bash
# Run ALL tests including integration (slow!)
uv run pytest tests --run-integration -v

# Run ONLY integration tests
uv run pytest tests --run-integration -m integration -v

# Run specific integration test
uv run pytest tests/test_integration_real_projects.py::test_real_project_conversion[microblog] --run-integration -v
```

### Test Projects

The integration tests use 3 diverse real-world projects:

#### 1. **Microblog** (Flask Tutorial App)
- **Scenario**: requirements.txt only (create new pyproject.toml)
- **Type**: Web application
- **Repo**: https://github.com/miguelgrinberg/microblog
- **Verification**: Import app module successfully

#### 2. **s3cmd** (S3 Command Line Tool)
- **Scenario**: requirements.txt only (create new pyproject.toml)
- **Type**: CLI tool
- **Repo**: https://github.com/s3tools/s3cmd
- **Verification**: Import S3 module successfully

#### 3. **Boto3** (AWS SDK)
- **Scenario**: requirements.txt + existing pyproject.toml (merge scenario)
- **Type**: Library
- **Repo**: https://github.com/boto/boto3
- **Verification**: Run unit tests

**Python Version Management:**
- `req2uv` sets conservative `requires-python = ">=3.8"` by default
- `uv sync` automatically installs the appropriate Python version
- No manual Python version management needed!
- The venv is created with the Python version that satisfies `requires-python`

### What Integration Tests Verify

For each project, the tests:

1. ✅ Clone the project from GitHub
2. ✅ **Verify requirements.txt exists** (will FAIL if project removes it)
3. ✅ **Check for existing pyproject.toml** (will FAIL if project changes structure)
4. ✅ Run `req2uv --non-interactive`
5. ✅ Verify valid pyproject.toml was generated
6. ✅ Install dependencies with `uv sync`
7. ✅ Verify project works (run tests or imports)
8. ✅ Clean up temporary files

**Important**: Steps 2-3 act as guards to detect when test projects change over time. If a project removes requirements.txt or adds/removes pyproject.toml, the test will fail immediately with a clear message, prompting you to find alternative test projects.

### Test Scenarios Covered

- **Create**: Convert project with only requirements.txt
- **Merge**: Merge requirements.txt into existing pyproject.toml
- **Web Apps**: Flask application with dependencies
- **CLI Tools**: Serverless deployment tool
- **Libraries**: AWS SDK with complex dependencies

### Continuous Integration

For CI/CD pipelines, run both test suites:

```yaml
# GitHub Actions example
- name: Run unit tests
  run: uv run pytest tests -v

- name: Run integration tests
  run: uv run pytest tests --run-integration -v
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

### Skipping Tests

```bash
# Skip integration tests (default behavior)
uv run pytest tests -v

# Skip specific tests
uv run pytest tests -v -k "not test_slow"

# Run only fast tests
uv run pytest tests -m "not integration" -v
```

### Writing New Tests

#### Unit Tests

Create test files in `tests/` with `test_` prefix:

```python
def test_my_feature():
    """Test that my feature works."""
    result = my_function()
    assert result == expected_value
```

#### Integration Tests

Add new projects to `TEST_PROJECTS` in `test_integration_real_projects.py`:

```python
(
    "https://github.com/user/repo",
    "main",
    False,  # has_pyproject: False = create, True = merge
    ["pytest", "tests/", "-v"],  # verification command
    "Description of project",
),
```

### Debugging Failed Tests

#### Unit Test Failures

```bash
# Run with verbose output
uv run pytest tests/test_parser.py -vv

# Run with print statements visible
uv run pytest tests/test_parser.py -v -s

# Drop into debugger on failure
uv run pytest tests/test_parser.py --pdb
```

#### Integration Test Failures

Integration tests print detailed output. Look for:

```
1. Cloning https://github.com/...
   ✓ Cloned to /tmp/...

2. Checking for requirements.txt...
   ✓ Found 3 requirements file(s):
     - requirements.txt
     - requirements-dev.txt

3. Converting with req2uv...
   ✓ Merged with existing pyproject.toml

4. Installing dependencies with uv sync...
   ✗ Installation failed:
   [error details here]
```

To debug locally:

```bash
# Run single integration test with full output
uv run pytest tests/test_integration_real_projects.py::test_real_project_conversion[microblog] \
  --run-integration -vv -s

# Keep temp directory for inspection
# Add this to the test temporarily:
import time; time.sleep(300)  # Gives you 5 minutes to inspect
```

### Test Performance

| Test Type | Count | Time | Network |
|-----------|-------|------|---------|
| Unit Tests | 15 | ~0.2s | No |
| Integration Tests | 3 | ~5-10min | Yes |

### Requirements

All tests require:
- ✅ uv installed
- ✅ git installed
- ✅ req2uv installed (`uv pip install -e .`)

Integration tests additionally require:
- ✅ Network access to GitHub
- ✅ ~100MB disk space in /tmp
- ✅ Patience (5-10 minutes)
- ✅ uv will automatically install required Python versions

### Tips

1. **Run unit tests frequently** during development
2. **Run integration tests before commits** to main
3. **Use `-v` flag** to see detailed output
4. **Use `--run-integration`** explicitly to avoid accidents
5. **Projects are cached** in /tmp during test run but cleaned up after

### Troubleshooting

**"Test skipped"**: You forgot `--run-integration` flag

**"Failed to clone"**: Network issue or GitHub rate limit

**"Installation failed"**:
- Dependency conflict - check stderr output
- Check if test project has updated its dependencies with breaking changes
- uv automatically manages Python versions based on `requires-python`

**"Verification failed"**: Project might have changed, not critical for conversion test

**"No requirements.txt found"** or **"Unexpected pyproject.toml found"**:
- Test project has changed structure
- Find alternative projects using the search scripts in `/tmp`

### Example Session

```bash
# Start fresh
cd requirements-to-uv

# Run quick unit tests
$ uv run pytest tests -v
==================== 15 passed in 0.18s ====================

# All good! Now run full integration suite
$ uv run pytest tests --run-integration -v

======================================================================
Testing: Microblog - Flask tutorial app (requirements.txt only)
Repo: https://github.com/miguelgrinberg/microblog
Scenario: CREATE (requirements.txt only)
======================================================================

1. Cloning https://github.com/miguelgrinberg/microblog...
   ✓ Cloned to /tmp/req2uv_integration_test_xyz/microblog

2. Checking for requirements.txt...
   ✓ Found 1 requirements file(s):
     - requirements.txt
   ✓ No existing pyproject.toml (create scenario)

3. Converting with req2uv...
   ✓ Created new pyproject.toml
   ✓ Valid pyproject.toml with 23 dependencies

4. Installing dependencies with uv sync...
   ✓ Dependencies installed

5. Verifying project with: python -c import app; print('Import successful')...
   ✓ Project verification passed

======================================================================
✓ Successfully converted microblog to uv!
======================================================================

[... continues with other projects ...]

==================== 18 passed in 7m 32s ====================
```

## Summary

- **Unit tests**: Run always, fast, no network
- **Integration tests**: Run before commits, slow, requires network
- **Use `--run-integration`** to enable integration tests
- **Three diverse projects** test real-world scenarios
- **Full workflow tested**: clone → convert → install → verify
