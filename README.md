# GitHub Ruleset Auditor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

**Stop worrying about unprotected repos.**

Audit 100+ repositories in seconds. Apply consistent branch protection with one command. Keep your default branch safe from accidental pushes, force-pushes, and leaked CI tokens.

## Why You Need This

By default, GitHub repositories have **no branch protection**:

- Anyone with write access can push directly to your default branch
- Anyone can force-push and rewrite history
- Leaked CI tokens can push malicious code directly to production
- No code review required

If you have dozens of repositories, manually configuring protection through the GitHub UI is tedious, inconsistent, and easy to forget.

**This tool audits all your repos and applies consistent protection in bulk.**

## What This Tool Does

✅ Audits all your repos for existing branch protection
✅ Generates a CSV manifest for you to review before making changes
✅ Applies rulesets to unprotected repos (only the ones you choose)
✅ Skips archived and forked repos automatically
✅ Works with any default branch (`main`, `master`, `develop`, etc.)

## What This Tool Does NOT Do

❌ Does not delete repositories or branches
❌ Does not modify or overwrite existing rulesets
❌ Does not store your token anywhere
❌ Does not send data anywhere except GitHub's API
❌ Does not require any external services or databases

## Security & Trust

- **Read-only by default**: Audit mode makes zero changes to your repos
- **Explicit opt-in**: You must use `--apply` or `--from-csv` to make any changes
- **Dry-run available**: Preview exactly what would happen with `--dry-run`
- **No data collection**: No analytics, no telemetry, no phone-home
- **Minimal permissions**: Only needs `public_repo` scope for public repos
- **Fully open source**: Read the code yourself—it's one Python file

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│  1. AUDIT          2. REVIEW            3. APPLY               │
│                                                                 │
│  Scan all repos    Open CSV in Excel    Apply rulesets to      │
│  for existing   →  or any editor.    →  repos you marked       │
│  protection        Mark YES/NO.         as YES.                │
│                                                                 │
│  (read-only)       (your decision)      (writes to GitHub)     │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.8 or higher with pip
- A GitHub account
- A GitHub Personal Access Token ([create one](https://github.com/settings/tokens)) or GitHub CLI

### Install

```bash
git clone https://github.com/psenger/github-ruleset-auditor.git
cd github-ruleset-auditor
pip install .
```

### Set Your Token

**Option A: Using GitHub CLI (easiest)**
```bash
export GITHUB_TOKEN=$(gh auth token)
```

**Option B: Using a Personal Access Token**
```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
```

| What you want to audit | Token scope needed |
|------------------------|--------------------|
| Public repos only      | `public_repo`      |
| Private or all repos   | `repo`             |

### Run Your First Audit

```bash
github-ruleset-auditor -u YOUR_USERNAME
```

**Sample output:**
```
Fetching public repositories for user: octocat...
  Page 1: 23 repos (skipped 2 archived, 5 forked)
Total eligible repositories: 23

Checking ruleset status for 23 repositories...
----------------------------------------------------------------------
[1/23] octocat/hello-world (branch: main)
    ✗ No ruleset
[2/23] octocat/my-api (branch: main)
    ✓ Has ruleset: default-branch-protection (active)
...

SUMMARY
======================================================================
Total repositories scanned: 23
  ✓ With ruleset:    8
  ✗ Without ruleset: 15

Manifest saved:
  CSV:  ruleset_manifest_20241215_143052.csv
```

### Review and Apply

1. Open the CSV in Excel, VS Code, or any editor
2. Change `apply_protection` column to `YES` or `NO` for each repo
3. Preview your changes:
   ```bash
   github-ruleset-auditor --from-csv ruleset_manifest_*.csv --dry-run
   ```
4. Apply for real:
   ```bash
   github-ruleset-auditor --from-csv ruleset_manifest_*.csv
   ```

## What Gets Applied

The default ruleset protects your default branch:

| Rule                            | You (owner)      | Everyone Else              |
|---------------------------------|------------------|----------------------------|
| Push directly to default branch | Allowed (bypass) | Blocked                    |
| Merge PRs without approval      | Allowed (bypass) | Blocked (needs 1 approval) |
| Force push                      | Allowed (bypass) | Blocked                    |
| Delete default branch           | Allowed (bypass) | Blocked                    |

You keep full bypass permissions. Everyone else must follow the rules.

## Command Reference

```
github-ruleset-auditor [OPTIONS]

Required (pick one):
  -u, --username USER    GitHub username (personal repos)
  -o, --org ORG          GitHub organization
  -f, --from-csv FILE    Apply from CSV manifest

Optional:
  -v, --visibility TYPE  public (default), private, or all
  -r, --repo NAME        Single repo only (for testing)
  -a, --apply            Apply rulesets without CSV review
  -d, --dry-run          Preview without making changes
  -t, --token TOKEN      GitHub token (or use GITHUB_TOKEN env var)
  --output-dir DIR       Where to save manifests (default: .)
  --version              Show version
```

### Examples

```bash
# Audit public repos (default)
github-ruleset-auditor -u octocat

# Audit private repos only
github-ruleset-auditor -u octocat --visibility private

# Audit all repos (public + private)
github-ruleset-auditor -u octocat --visibility all

# Test on a single repo first
github-ruleset-auditor -u octocat -r my-repo --apply --dry-run

# Apply to all unprotected repos (skip CSV review)
github-ruleset-auditor -u octocat --apply
```

## Limitations

- Skips archived and forked repositories
- Will not overwrite existing rulesets
- Requires admin access to create rulesets
- Uses the modern Rulesets API (not legacy branch protection)
- Customization requires editing source code (no config file yet)

## Customization

To change the number of required approvals, add status checks, or configure CODEOWNERS, see **[docs/CUSTOMIZATION.md](docs/CUSTOMIZATION.md)**.

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## Found a Bug? Have an Idea?

- **Bug?** [Open a bug report](https://github.com/psenger/github-ruleset-auditor/issues/new?template=bug_report.md)
- **Feature idea?** [Request a feature](https://github.com/psenger/github-ruleset-auditor/issues/new?template=feature_request.md)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## License

MIT License - see [LICENSE](LICENSE).
