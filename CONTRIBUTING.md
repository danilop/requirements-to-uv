# Contributing to requirements-to-uv

Thank you for considering contributing to requirements-to-uv! This document provides guidelines and instructions for contributing.

## Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/danilop/requirements-to-uv.git
   cd requirements-to-uv
   ```

2. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install dependencies**
   ```bash
   uv sync
   uv sync --group dev
   ```

4. **Install pre-commit hooks** (recommended)
   ```bash
   uv run pre-commit install
   ```

## Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, well-documented code
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed

3. **Run tests**
   ```bash
   # Run all tests
   uv run pytest

   # Run with coverage
   uv run pytest --cov=requirements_to_uv --cov-report=html
   ```

4. **Format and lint your code**
   ```bash
   # Format with black
   uv run black .

   # Lint with ruff
   uv run ruff check .

   # Type check with mypy
   uv run mypy src/requirements_to_uv
   ```

## Code Style

- **Python**: Follow PEP 8 guidelines
- **Line length**: 100 characters maximum
- **Docstrings**: Use Google-style docstrings
- **Type hints**: Use type hints for function signatures
- **Imports**: Organize imports (stdlib, third-party, local)

## Testing Guidelines

- Write tests for all new features and bug fixes
- Use descriptive test names that explain what is being tested
- Keep tests focused and independent
- Aim for high test coverage (>80%)

### Test Structure

```python
def test_specific_feature():
    """Test that specific feature works correctly."""
    # Arrange
    setup_code()

    # Act
    result = function_under_test()

    # Assert
    assert result == expected_value
```

## Documentation

- Update README.md if you add new features or change behavior
- Add docstrings to all public functions and classes
- Include examples in docstrings when helpful
- Update the CHANGELOG.md (if applicable)

## Commit Messages

Write clear, descriptive commit messages:

```
Add feature to parse Poetry-style version constraints

- Implement regex pattern for ^ syntax
- Convert to PEP 440 compatible version ranges
- Add tests for edge cases
- Update documentation
```

Format:
- First line: Brief summary (50 chars or less)
- Blank line
- Detailed description (if needed)

## Pull Request Process

1. **Update your branch** with the latest main
   ```bash
   git fetch origin
   git rebase origin/main
   ```

2. **Push your changes**
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create a Pull Request**
   - Use a clear, descriptive title
   - Describe what changes you made and why
   - Reference any related issues
   - Add screenshots/examples if applicable

4. **Respond to feedback**
   - Be open to suggestions
   - Make requested changes promptly
   - Update your PR as needed

## Issue Guidelines

When creating an issue:

- **Bug reports**: Include steps to reproduce, expected behavior, actual behavior, and environment details
- **Feature requests**: Explain the use case and why it would be valuable
- **Questions**: Check existing issues and documentation first

### Bug Report Template

```
**Description**
A clear description of the bug.

**Steps to Reproduce**
1. Run command...
2. With file containing...
3. See error...

**Expected Behavior**
What you expected to happen.

**Actual Behavior**
What actually happened.

**Environment**
- OS: [e.g., macOS 14.0]
- Python version: [e.g., 3.12]
- requirements-to-uv version: [e.g., 0.1.0]
- uv version: [e.g., 0.5.0]

**Additional Context**
Any other relevant information.
```

## Areas for Contribution

We welcome contributions in these areas:

- **Bug fixes**: Fix reported issues
- **Features**: Implement new features from the roadmap
- **Tests**: Improve test coverage
- **Documentation**: Improve or translate documentation
- **Performance**: Optimize existing code
- **Compatibility**: Support more edge cases in requirements.txt parsing

## Questions?

If you have questions:
- Check the README.md and existing documentation
- Search existing issues
- Create a new issue with the "question" label

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Respect different viewpoints and experiences

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
