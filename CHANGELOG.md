# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2025-12-17

### Added
- Initial release
- Audit repositories for existing branch protection rulesets
- Support for personal repos (`-u/--username`) and organization repos (`-o/--org`)
- Visibility filtering: `--visibility public|private|all`
- CSV manifest generation for review before applying changes
- Apply rulesets from CSV with `--from-csv`
- Dry-run mode (`--dry-run`) to preview changes
- Single repo testing (`-r/--repo`)
- Default ruleset configuration:
  - Blocks force pushes
  - Blocks branch deletion
  - Requires 1 PR approval
  - Owner bypasses all rules
- Skip archived and forked repositories automatically
- `--version` flag for version checking

### Security
- Read-only audit by default (no changes without explicit `--apply` or `--from-csv`)
- Token never stored to disk
- No external network calls except GitHub API

---

## Version History

| Version | Date       | Highlights |
|---------|------------|------------|
| 1.0.0   | 2025-12-17 | Initial release |

[Unreleased]: https://github.com/psenger/github-ruleset-auditor/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/psenger/github-ruleset-auditor/releases/tag/v1.0.0
