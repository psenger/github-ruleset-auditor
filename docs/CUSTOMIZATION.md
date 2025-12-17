# Customizing the Ruleset

[← Back to README](../README.md)

> **Note:** Customization currently requires editing the Python source code. There's no config file yet. If you'd like this feature, [open a feature request](https://github.com/psenger/github-ruleset-auditor/issues/new?template=feature_request.md).

## Default Rules Applied

- Require 1 PR approval
- Block force pushes
- Block branch deletion
- Owner bypasses all rules

To customize, edit the `create_default_ruleset()` method in `github_ruleset_auditor.py`. Find it by searching for `def create_default_ruleset`.

## The Default Configuration

```python
{
    "name": "default-branch-protection",
    "target": "branch",
    "enforcement": "active",
    "conditions": {
        "ref_name": {
            "include": ["~DEFAULT_BRANCH"]
        }
    },
    "rules": [
        {"type": "deletion"},
        {"type": "non_fast_forward"},
        {
            "type": "pull_request",
            "parameters": {
                "required_approving_review_count": 1,
                "dismiss_stale_reviews_on_push": True,
                "require_code_owner_review": False,
                "require_last_push_approval": False
            }
        }
    ],
    "bypass_actors": [
        {
            "actor_id": 5,
            "actor_type": "RepositoryRole",
            "bypass_mode": "always"
        }
    ]
}
```

The `~DEFAULT_BRANCH` reference automatically targets whatever branch is set as default (`main`, `master`, `develop`, etc.).

---

## Pull Request Options

| Parameter                           | Default | Description                             |
|-------------------------------------|---------|-----------------------------------------|
| `required_approving_review_count`   | `1`     | Number of approvals required            |
| `dismiss_stale_reviews_on_push`     | `True`  | Reset approvals when new commits pushed |
| `require_code_owner_review`         | `False` | Require approval from CODEOWNERS        |
| `require_last_push_approval`        | `False` | Last pusher can't be an approver        |
| `required_review_thread_resolution` | `False` | All comments must be resolved           |

### Example: Require 2 Approvals

```python
"required_approving_review_count": 2,
```

### Example: Strict Review Requirements

```python
{
    "type": "pull_request",
    "parameters": {
        "required_approving_review_count": 2,
        "dismiss_stale_reviews_on_push": True,
        "require_code_owner_review": True,
        "require_last_push_approval": True,
        "required_review_thread_resolution": True
    }
}
```

---

## Available Rule Types

| Rule Type                 | Description                    |
|---------------------------|--------------------------------|
| `deletion`                | Prevent branch deletion        |
| `non_fast_forward`        | Prevent force pushes           |
| `pull_request`            | Require PRs with reviews       |
| `required_linear_history` | No merge commits (rebase only) |
| `required_signatures`     | Require signed commits         |
| `required_status_checks`  | Require CI checks to pass      |

### Example: Add Required Status Checks

```python
"rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {
        "type": "pull_request",
        "parameters": {
            "required_approving_review_count": 1,
            "dismiss_stale_reviews_on_push": True
        }
    },
    {
        "type": "required_status_checks",
        "parameters": {
            "strict_required_status_checks_policy": True,
            "required_status_checks": [
                {"context": "ci/build"},
                {"context": "ci/test"}
            ]
        }
    }
]
```

---

## Bypass Actors

Control who can bypass the rules.

### For Personal Repos (by role)

```python
"bypass_actors": [
    {
        "actor_id": 5,              # 5 = Maintain role (see table below)
        "actor_type": "RepositoryRole",
        "bypass_mode": "always"
    }
]
```

### For Organization Repos (specific user)

```python
"bypass_actors": [
    {
        "actor_id": 12345678,       # Your GitHub user ID
        "actor_type": "User",
        "bypass_mode": "always"
    }
]
```

### For Teams

```python
"bypass_actors": [
    {
        "actor_id": 7654321,        # Team ID
        "actor_type": "Team",
        "bypass_mode": "always"
    }
]
```

### Finding Your User ID or Team ID

```bash
# Your user ID
curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user | grep '"id"' | head -1
# Or: gh api user --jq .id

# Another user's ID
gh api users/USERNAME --jq .id

# Team ID (org repos only)
gh api orgs/YOUR_ORG/teams/TEAM_SLUG --jq .id
```

### Bypass Modes

| Mode           | Description                  |
|----------------|------------------------------|
| `always`       | Bypass all rules             |
| `pull_request` | Only bypass when merging PRs |

### Repository Role IDs

| ID | Role     |
|----|----------|
| 1  | Read     |
| 2  | Triage   |
| 4  | Write    |
| 5  | Maintain |

> Note: ID 3 is not used by GitHub's API.

---

## Using CODEOWNERS

CODEOWNERS lets you require reviews from specific people for specific file paths.

### 1. Create `.github/CODEOWNERS`

```
# Default reviewers
*                   @your-username

# Specific paths
/src/api/           @api-team
/docs/              @docs-team
*.js                @frontend-team
/security/          @security-team @your-username
```

### 2. Enable in the ruleset

```python
"require_code_owner_review": True,
```

Now PRs touching those paths require approval from the designated owners.

### CODEOWNERS Rules

- Later rules override earlier rules (last match wins)
- Patterns use `.gitignore` syntax
- Teams use `@org/team-name` format
- Individual users use `@username` format

---

## Complete Example: Production-Grade Setup

```python
ruleset_config = {
    "name": "production-protection",
    "target": "branch",
    "enforcement": "active",
    "conditions": {
        "ref_name": {
            "include": ["~DEFAULT_BRANCH"]
        }
    },
    "rules": [
        {"type": "deletion"},
        {"type": "non_fast_forward"},
        {"type": "required_linear_history"},
        {
            "type": "pull_request",
            "parameters": {
                "required_approving_review_count": 2,
                "dismiss_stale_reviews_on_push": True,
                "require_code_owner_review": True,
                "require_last_push_approval": True,
                "required_review_thread_resolution": True
            }
        },
        {
            "type": "required_status_checks",
            "parameters": {
                "strict_required_status_checks_policy": True,
                "required_status_checks": [
                    {"context": "ci/build"},
                    {"context": "ci/test"},
                    {"context": "security/snyk"}
                ]
            }
        }
    ],
    "bypass_actors": [
        {
            "actor_id": 7654321,    # Your release team ID
            "actor_type": "Team",
            "bypass_mode": "pull_request"
        }
    ]
}
```

This setup:
- Requires 2 approvals
- Requires code owner approval
- Requires all CI checks to pass
- Enforces linear history (rebase workflow)
- Only the release team can bypass (and only for merging PRs)

---

## Troubleshooting

### "Can't bypass rules as owner"

Check `bypass_actors` in your ruleset:
- **Personal repos:** Use `RepositoryRole` with ID `5` (Maintain)
- **Org repos:** Add your user ID explicitly with `actor_type: "User"`

### "Approval dismissed after push"

This is intentional if `dismiss_stale_reviews_on_push` is `True`. New commits require re-approval to prevent sneaking in changes after review.
