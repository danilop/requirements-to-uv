# requirements-to-uv

Convert Python projects from `requirements.txt` to [uv](https://github.com/astral-sh/uv)-managed `pyproject.toml` with a single command.

## Features

- **Automatic Detection**: Intelligently detects project metadata from your codebase
- **Comprehensive Parsing**: Handles complex `requirements.txt` formats including:
  - Standard PyPI packages with version specifiers
  - Git dependencies (HTTP, SSH)
  - Local path dependencies (editable and non-editable)
  - Environment markers
  - Package extras
  - Poetry-style version constraints (converts `^` syntax)
- **Smart Merging**: Merges with existing `pyproject.toml` files without losing data
- **Multiple Requirements Files**: Auto-detects and categorizes dev, test, and docs dependencies
- **Interactive & Non-Interactive Modes**: Works in CI/CD pipelines or with user prompts
- **Validation**: Validates generated `pyproject.toml` with optional `uv` integration

## Quick Start

**Get started in 30 seconds:**

```bash
# 1. Install directly from GitHub (one command!)
uv tool install git+https://github.com/danilop/requirements-to-uv.git

# 2. Navigate to your Python project
cd /path/to/your/project

# 3. Run the conversion
req2uv

# 4. Install dependencies with uv
uv sync

# 5. Done! Your project now uses uv
```

The tool automatically:
- ✅ Detects your project metadata (name, version, Python version)
- ✅ Finds all requirements.txt files (main, dev, test, etc.)
- ✅ Converts them to modern pyproject.toml format
- ✅ Validates the output

**Common usage patterns:**

```bash
# Interactive mode (default) - prompts for confirmation
req2uv

# Non-interactive mode - great for CI/CD
req2uv --non-interactive

# Preview changes without writing
req2uv --dry-run

# Specify custom requirements files
req2uv --requirements custom-reqs.txt --dev dev-reqs.txt
```

## Installation

### Install from GitHub (recommended)

```bash
# Install as a uv tool (available globally)
uv tool install git+https://github.com/danilop/requirements-to-uv.git

# Or install in current environment
uv pip install git+https://github.com/danilop/requirements-to-uv.git
```

### Install from source

```bash
# Clone the repository
git clone https://github.com/danilop/requirements-to-uv.git
cd requirements-to-uv

# Install with uv
uv pip install -e .

# Or install as a uv tool
uv tool install .
```

## Usage

### Basic Usage

```bash
# Interactive mode with auto-detection
req2uv

# Specify requirements file explicitly
req2uv --requirements requirements.txt

# Specify multiple requirements files
req2uv --requirements requirements.txt --dev requirements-dev.txt --test requirements-test.txt
```

### Advanced Options

```bash
# Override detected metadata
req2uv --name myproject --version 1.0.0 --python ">=3.11"

# Overwrite existing pyproject.toml (creates backup)
req2uv --overwrite

# Skip validation
req2uv --no-validate

# Verbose output
req2uv --verbose
```

## How It Works

### 1. Metadata Detection

The tool automatically detects project metadata from:

- **Project name**: Directory name (normalized)
- **Version**: `__init__.py`, `setup.py`, or git tags (defaults to `0.1.0`)
- **Python version**: `.python-version` file, classifiers, or current Python version
- **Description**: First line of README
- **Authors**: Git configuration
- **License**: LICENSE file analysis
- **README**: Detects README.md, README.rst, or README.txt

### 2. Requirements File Discovery

Automatically finds and categorizes requirements files:

- `requirements.txt` → main dependencies
- `requirements-dev.txt` → dev dependency group
- `requirements-test.txt` → test dependency group
- `requirements-docs.txt` → docs dependency group
- `requirements-lint.txt` → lint dependency group

### 3. Comprehensive Parsing

Handles all common `requirements.txt` patterns:

#### Standard PyPI Packages
```txt
requests>=2.28.0
flask[async]>=3.0.0
celery[redis,msgpack]>=5.3.0
pytest>=8.0.0 ; python_version >= "3.8"
```

#### Git Dependencies
```txt
git+https://github.com/user/repo.git@main#egg=mypackage
git+https://github.com/user/repo.git@v1.0.0
-e git+https://github.com/user/repo.git@develop
```

Converts to:
```toml
[project]
dependencies = ["mypackage"]

[tool.uv.sources]
mypackage = { git = "https://github.com/user/repo.git", branch = "main" }
```

#### Local Paths
```txt
-e ./local-package
../another-package
```

Converts to:
```toml
[tool.uv.sources]
local-package = { path = "./local-package", editable = true }
another-package = { path = "../another-package" }
```

#### Poetry Version Syntax
```txt
django^4.2.0
```

Converts to:
```toml
dependencies = ["django>=4.2.0,<5.0.0"]
```
With a warning comment about the conversion.

### 4. Smart Merging

When `pyproject.toml` exists:

- **Preserves** existing metadata and sections
- **Appends** new dependencies to existing lists
- **Detects** duplicate packages
- **Creates** backup file (`pyproject.toml.backup`)

## Generated `pyproject.toml` Structure

### Minimal Example

```toml
[project]
name = "my-project"
version = "0.1.0"
description = "My awesome project"
readme = "README.md"
requires-python = ">=3.8"
dependencies = [
    "requests>=2.28.0",
    "flask>=3.0.0",
]
```

### Complete Example

```toml
[project]
name = "my-project"
version = "1.0.0"
description = "A production-ready Python project"
readme = "README.md"
requires-python = ">=3.11"
authors = [
    { name = "John Doe", email = "john@example.com" }
]
license = { text = "MIT" }
dependencies = [
    "requests>=2.28.0",
    "flask[async]>=3.0.0",
    "sqlalchemy>=2.0.0",
    "celery[redis,msgpack]>=5.3.0",
    "mypackage",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "black>=24.0.0",
    "ruff>=0.3.0",
]
test = [
    "coverage>=7.0.0",
    "pytest-cov>=4.0.0",
]

[tool.uv.sources]
mypackage = { git = "https://github.com/user/repo.git", branch = "main" }
local-package = { path = "../local", editable = true }

# Note: Original requirements.txt contained --index-url https://custom-index.com
# Configure this via: uv pip install --index-url https://custom-index.com
```

## Edge Cases & Warnings

### Supported Features

- ✅ Standard PyPI packages
- ✅ Version specifiers (`==`, `>=`, `>`, `<`, `<=`, `!=`, `~=`)
- ✅ Git URLs (HTTPS)
- ✅ Local paths (editable and non-editable)
- ✅ Environment markers
- ✅ Package extras
- ✅ Poetry `^` syntax (with conversion)
- ✅ Comments (stripped)
- ✅ Line continuations (`\`)

### Unsupported Features (with warnings)

⚠️ **Hashes** (`--hash=sha256:...`)
- Not supported in `pyproject.toml`
- Use `uv.lock` for reproducible installs
- Warning generated, hashes stripped

⚠️ **Index URLs** (`--index-url`, `--extra-index-url`)
- Not stored in `pyproject.toml`
- Comment added with original URL
- Configure via `uv` CLI or config

⚠️ **VCS other than Git** (`hg+`, `svn+`, `bzr+`)
- Not supported by `uv`
- Warning generated, dependency skipped

⚠️ **SSH Git URLs**
- Converted to HTTPS if possible (GitHub, GitLab, Bitbucket)
- Warning generated for unknown hosts

## Examples

### Example 1: Simple Project

**Input** (`requirements.txt`):
```txt
requests>=2.28.0
flask>=3.0.0
pytest>=8.0.0
```

**Command**:
```bash
req2uv
```

**Output** (`pyproject.toml`):
```toml
[project]
name = "my-project"
version = "0.1.0"
requires-python = ">=3.8"
dependencies = [
    "requests>=2.28.0",
    "flask>=3.0.0",
    "pytest>=8.0.0",
]
```

### Example 2: With Dev Dependencies

**Input**:
- `requirements.txt`: `requests>=2.28.0`
- `requirements-dev.txt`: `pytest>=8.0.0`

**Command**:
```bash
req2uv
```

**Output**:
```toml
[project]
name = "my-project"
version = "0.1.0"
dependencies = ["requests>=2.28.0"]

[dependency-groups]
dev = ["pytest>=8.0.0"]
```

### Example 3: Git Dependencies

**Input** (`requirements.txt`):
```txt
requests>=2.28.0
git+https://github.com/psf/requests.git@main
```

**Output**:
```toml
[project]
dependencies = [
    "requests>=2.28.0",
    "requests",
]

[tool.uv.sources]
requests = { git = "https://github.com/psf/requests.git", branch = "main" }
```

### Example 4: Non-Interactive CI/CD

```bash
# In CI/CD pipeline
req2uv --non-interactive --no-validate

# Or with all metadata specified
req2uv \
  --non-interactive \
  --name myproject \
  --version 1.0.0 \
  --python ">=3.11"
```

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/danilop/requirements-to-uv.git
cd requirements-to-uv

# Install dependencies
uv sync

# Install development dependencies
uv sync --group dev
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=requirements_to_uv --cov-report=html

# Run specific test
uv run pytest tests/test_parser.py -v
```

### Code Quality

```bash
# Format code
uv run black .

# Lint
uv run ruff check .

# Type checking
uv run mypy src/requirements_to_uv
```

## Troubleshooting

### Common Issues

**Q: Tool says "No requirements.txt found"**
A: Specify the path explicitly: `req2uv --requirements /path/to/requirements.txt`

**Q: Some dependencies are missing in the output**
A: Check warnings in verbose mode: `req2uv --verbose`

**Q: Package names are different from requirements.txt**
A: PyPI normalizes package names (e.g., `python-dateutil` -> `python_dateutil`). This is expected.

**Q: Git SSH URLs fail to convert**
A: The tool converts GitHub/GitLab/Bitbucket SSH URLs to HTTPS automatically. For other hosts, manually edit the generated `pyproject.toml`.

**Q: Validation fails with "uv lock" errors**
A: Some dependencies might not be compatible. Review the generated `pyproject.toml` and adjust version constraints.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Credits

Built with:
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer
- [packaging](https://github.com/pypa/packaging) - Core packaging utilities
- [click](https://click.palletsprojects.com/) - CLI framework
- [rich](https://github.com/Textualize/rich) - Terminal formatting
- [questionary](https://github.com/tmbo/questionary) - Interactive prompts

## Links

- [uv Documentation](https://docs.astral.sh/uv/)
- [PEP 621 - pyproject.toml](https://peps.python.org/pep-0621/)
- [PEP 508 - Dependency Specification](https://peps.python.org/pep-0508/)
