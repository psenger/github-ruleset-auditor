# Releasing a New Version

This document describes the process for releasing a new version of GitHub Ruleset Auditor.

## Version Numbering

This project uses [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.x.x): Breaking changes
- **MINOR** (x.1.x): New features, backward compatible
- **PATCH** (x.x.1): Bug fixes, backward compatible

## Pre-Release Checklist

Before releasing, ensure:

- [ ] All tests pass
- [ ] Code works manually with real repos
- [ ] CHANGELOG.md is updated
- [ ] README.md is accurate
- [ ] No sensitive data in code

## Release Process

### 1. Run Tests

```bash
# Run full test suite
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=github_ruleset_auditor --cov-report=term-missing

# Manual smoke test
export GITHUB_TOKEN=$(gh auth token)
github-ruleset-auditor -u YOUR_USERNAME -r SOME_REPO --dry-run
```

All tests must pass before proceeding.

### 2. Update Version

Edit `pyproject.toml` and update the version number:

```toml
[project]
version = "1.1.0"  # <- Update this
```

### 3. Update CHANGELOG.md

Add a new section for the release:

```markdown
## [1.1.0] - 2024-12-20

### Added
- New feature X

### Fixed
- Bug Y

### Changed
- Behavior Z
```

Update the links at the bottom:

```markdown
[Unreleased]: https://github.com/psenger/github-ruleset-auditor/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/psenger/github-ruleset-auditor/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/psenger/github-ruleset-auditor/releases/tag/v1.0.0
```

### 4. Commit the Release

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "Release v1.1.0"
```

### 5. Create Git Tag

```bash
# Create annotated tag
git tag -a v1.1.0 -m "Release v1.1.0"

# Verify tag
git show v1.1.0
```

### 6. Push to GitHub

```bash
# Push commit and tag together
git push origin main --tags
```

### 7. Create GitHub Release

**Option A: Using GitHub CLI**

```bash
gh release create v1.1.0 \
  --title "v1.1.0" \
  --notes-file - <<EOF
## What's Changed

See [CHANGELOG.md](https://github.com/psenger/github-ruleset-auditor/blob/main/CHANGELOG.md#110---2024-12-20) for details.

**Full Changelog**: https://github.com/psenger/github-ruleset-auditor/compare/v1.0.0...v1.1.0
EOF
```

**Option B: Using GitHub Web UI**

1. Go to https://github.com/psenger/github-ruleset-auditor/releases
2. Click "Draft a new release"
3. Select the tag `v1.1.0`
4. Title: `v1.1.0`
5. Description: Link to CHANGELOG section
6. Click "Publish release"

### 8. Verify Release

```bash
# Verify the release is visible
gh release view v1.1.0

# Test installation from GitHub
pip install git+https://github.com/psenger/github-ruleset-auditor.git@v1.1.0

# Verify version
github-ruleset-auditor --version
```

## Publishing to PyPI (Optional)

If you want to publish to PyPI for `pip install github-ruleset-auditor`:

### First Time Setup

```bash
# Install build tools
pip install build twine

# Create PyPI account at https://pypi.org/
# Create API token at https://pypi.org/manage/account/token/
```

### Build and Upload

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info/

# Build package
python -m build

# Check the build
twine check dist/*

# Upload to Test PyPI first (optional)
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*
```

### Verify PyPI Release

```bash
# Wait a minute for PyPI to update, then:
pip install --upgrade github-ruleset-auditor
github-ruleset-auditor --version
```

## Quick Release Script

For convenience, here's a script that automates most steps:

```bash
#!/bin/bash
# release.sh - Run with: ./release.sh 1.1.0

set -e

VERSION=$1

if [ -z "$VERSION" ]; then
    echo "Usage: ./release.sh <version>"
    echo "Example: ./release.sh 1.1.0"
    exit 1
fi

echo "=== Releasing v$VERSION ==="

# Run tests
echo "Running tests..."
pytest tests/ -v
if [ $? -ne 0 ]; then
    echo "Tests failed! Aborting release."
    exit 1
fi

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "Error: Uncommitted changes. Commit or stash them first."
    exit 1
fi

# Confirm
echo ""
echo "Ready to release v$VERSION"
echo "Make sure you have:"
echo "  - Updated version in pyproject.toml to $VERSION"
echo "  - Updated CHANGELOG.md"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Commit, tag, push
git add pyproject.toml CHANGELOG.md
git commit -m "Release v$VERSION"
git tag -a "v$VERSION" -m "Release v$VERSION"
git push origin main --tags

# Create GitHub release
gh release create "v$VERSION" --title "v$VERSION" --notes "See CHANGELOG.md for details."

echo ""
echo "=== Released v$VERSION ==="
echo "View at: https://github.com/psenger/github-ruleset-auditor/releases/tag/v$VERSION"
```

## Hotfix Release

For urgent fixes to a released version:

```bash
# Create hotfix branch from tag
git checkout -b hotfix/1.0.1 v1.0.0

# Make fixes, commit
git add .
git commit -m "Fix critical bug X"

# Update version and changelog
# ... edit pyproject.toml to 1.0.1 ...
# ... edit CHANGELOG.md ...

git add pyproject.toml CHANGELOG.md
git commit -m "Release v1.0.1"

# Tag and push
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin hotfix/1.0.1 --tags

# Create PR to merge hotfix back to main
gh pr create --title "Merge hotfix v1.0.1" --base main

# Create release
gh release create v1.0.1 --title "v1.0.1" --notes "Hotfix: ..."
```

## Rollback

If a release has issues:

```bash
# Delete the GitHub release (keeps the tag)
gh release delete v1.1.0

# Or delete both release and tag
gh release delete v1.1.0 --yes
git push --delete origin v1.1.0
git tag -d v1.1.0
```
