# Contributing to GitHub Ruleset Auditor

[← Back to README](README.md)

Thank you for your interest in contributing!

## Code of Conduct

Be respectful and constructive. We're all here to make this tool better.

## How to Contribute

### Reporting Bugs

1. Check [existing issues](https://github.com/psenger/github-ruleset-auditor/issues) to avoid duplicates
2. [Open a bug report](https://github.com/psenger/github-ruleset-auditor/issues/new?template=bug_report.md)

### Suggesting Features

1. Check existing issues for similar suggestions
2. [Open a feature request](https://github.com/psenger/github-ruleset-auditor/issues/new?template=feature_request.md)

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Test your changes
5. Commit with clear messages (`git commit -m "Add feature X"`)
6. Push to your fork (`git push origin feature/my-feature`)
7. Open a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/github-ruleset-auditor.git
cd github-ruleset-auditor

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Set up your token for integration tests (optional)
export GITHUB_TOKEN=$(gh auth token)
```

## Code Style

- Follow [PEP 8](https://pep8.org/) conventions
- Use descriptive variable and function names
- Add docstrings to functions
- Keep functions focused and small

## Testing

This project uses [pytest](https://pytest.org/) for testing.

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=github_ruleset_auditor --cov-report=term-missing

# Run a specific test class
pytest tests/test_auditor.py::TestRulesetDetection -v

# Run a specific test
pytest tests/test_auditor.py::TestVersion::test_version_exists -v
```

### Test Structure

```
tests/
├── __init__.py
└── test_auditor.py      # Main test file
    ├── TestVersion               # Version string tests
    ├── TestGitHubRulesetAuditor  # Class initialization
    ├── TestRulesetDetection      # API and detection logic
    ├── TestRulesetCreation       # Ruleset creation
    ├── TestCSVParsing            # CSV manifest parsing
    ├── TestRepoFiltering         # Archive/fork filtering
    └── TestIntegration           # Real API tests (need GITHUB_TOKEN)
```

### Writing Tests

- Use `unittest.mock.patch` to mock API calls
- Don't make real API calls in unit tests (use mocks)
- Integration tests that need real API access should use `@pytest.mark.skipif`
- Aim for descriptive test names: `test_should_skip_archived_repos`

### Before Submitting a PR

1. **Run the test suite** - All tests must pass
2. **Check coverage** - Don't significantly decrease coverage
3. **Manual testing** (optional) - Test with real repos if your change affects API calls

```bash
# Manual testing with real token
export GITHUB_TOKEN=$(gh auth token)
github-ruleset-auditor -u YOUR_USERNAME -r REPO_NAME --apply --dry-run
```

## Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Fix bug" not "Fixes bug")
- Keep the first line under 72 characters
- Reference issues when relevant (`Fix #123`)

## Pull Request Guidelines

- One feature/fix per PR
- Update documentation if needed (see `docs/` folder)
- Be responsive to feedback

## Releasing

For maintainers: See [RELEASING.md](RELEASING.md) for the release process.

## Questions?

Open an issue with the "question" label or start a discussion.

---

Thank you for contributing!
