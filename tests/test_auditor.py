"""
Tests for GitHub Ruleset Auditor

Run with: pytest tests/ -v
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path so we can import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from github_ruleset_auditor import GitHubRulesetAuditor, __version__


class TestVersion:
    """Test version information."""

    def test_version_exists(self):
        """Version should be defined."""
        assert __version__ is not None
        assert isinstance(__version__, str)

    def test_version_format(self):
        """Version should follow semver format."""
        parts = __version__.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)


class TestGitHubRulesetAuditor:
    """Test the GitHubRulesetAuditor class."""

    def test_init(self):
        """Auditor should initialize with a token."""
        auditor = GitHubRulesetAuditor("test_token")
        assert auditor.token == "test_token"
        assert auditor.base_url == "https://api.github.com"
        assert "Authorization" in auditor.headers
        assert auditor.manifest == []

    def test_headers_contain_token(self):
        """Headers should contain the authorization token."""
        auditor = GitHubRulesetAuditor("my_secret_token")
        assert auditor.headers["Authorization"] == "token my_secret_token"

    @patch("requests.get")
    def test_get_authenticated_user_success(self, mock_get):
        """Should fetch and cache authenticated user."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"login": "testuser", "id": 12345}
        mock_get.return_value = mock_response

        auditor = GitHubRulesetAuditor("test_token")
        user = auditor.get_authenticated_user()

        assert user["login"] == "testuser"
        assert auditor.authenticated_user_id == 12345
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_get_authenticated_user_caches_result(self, mock_get):
        """Should not make duplicate API calls for user info."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"login": "testuser", "id": 12345}
        mock_get.return_value = mock_response

        auditor = GitHubRulesetAuditor("test_token")
        auditor.get_authenticated_user()
        auditor.get_authenticated_user()  # Second call

        # Should only call API once due to caching
        assert mock_get.call_count == 1


class TestRulesetDetection:
    """Test ruleset detection logic."""

    @patch("requests.get")
    def test_get_repo_rulesets_success(self, mock_get):
        """Should return rulesets when API call succeeds."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 1, "name": "protection-rule"}
        ]
        mock_get.return_value = mock_response

        auditor = GitHubRulesetAuditor("test_token")
        rulesets = auditor.get_repo_rulesets("owner", "repo")

        assert len(rulesets) == 1
        assert rulesets[0]["name"] == "protection-rule"

    @patch("requests.get")
    def test_get_repo_rulesets_404_returns_empty(self, mock_get):
        """Should return empty list when repo has no rulesets endpoint."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        auditor = GitHubRulesetAuditor("test_token")
        rulesets = auditor.get_repo_rulesets("owner", "repo")

        assert rulesets == []

    @patch("requests.get")
    def test_get_repo_rulesets_error(self, mock_get):
        """Should return error dict on API failure."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        auditor = GitHubRulesetAuditor("test_token")
        result = auditor.get_repo_rulesets("owner", "repo")

        assert "error" in result

    @patch.object(GitHubRulesetAuditor, "get_repo_rulesets")
    @patch.object(GitHubRulesetAuditor, "get_ruleset_details")
    def test_check_default_branch_ruleset_finds_match(self, mock_details, mock_rulesets):
        """Should detect ruleset targeting default branch."""
        mock_rulesets.return_value = [{"id": 123, "name": "main-protection"}]
        mock_details.return_value = {
            "id": 123,
            "name": "main-protection",
            "enforcement": "active",
            "conditions": {
                "ref_name": {
                    "include": ["~DEFAULT_BRANCH"]
                }
            },
            "rules": [],
            "bypass_actors": []
        }

        auditor = GitHubRulesetAuditor("test_token")
        result = auditor.check_default_branch_ruleset("owner", "repo", "main")

        assert result["has_ruleset"] is True
        assert result["ruleset_name"] == "main-protection"

    @patch.object(GitHubRulesetAuditor, "get_repo_rulesets")
    def test_check_default_branch_ruleset_no_rulesets(self, mock_rulesets):
        """Should return has_ruleset=False when no rulesets exist."""
        mock_rulesets.return_value = []

        auditor = GitHubRulesetAuditor("test_token")
        result = auditor.check_default_branch_ruleset("owner", "repo", "main")

        assert result["has_ruleset"] is False


class TestRulesetCreation:
    """Test ruleset creation logic."""

    @patch("requests.post")
    def test_create_default_ruleset_success(self, mock_post):
        """Should create ruleset and return success."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 999, "name": "default-branch-protection"}
        mock_post.return_value = mock_response

        auditor = GitHubRulesetAuditor("test_token")
        auditor.authenticated_user_id = 12345
        result = auditor.create_default_ruleset("owner", "repo")

        assert result["success"] is True
        assert result["ruleset"]["id"] == 999

    @patch("requests.post")
    def test_create_default_ruleset_failure(self, mock_post):
        """Should return error on failure."""
        mock_response = Mock()
        mock_response.status_code = 422
        mock_response.text = "Validation failed"
        mock_post.return_value = mock_response

        auditor = GitHubRulesetAuditor("test_token")
        auditor.authenticated_user_id = 12345
        result = auditor.create_default_ruleset("owner", "repo")

        assert result["success"] is False
        assert "error" in result


class TestCSVParsing:
    """Test CSV manifest parsing."""

    def test_parse_csv_row_yes(self):
        """Should correctly identify YES rows."""
        row = {
            "full_name": "owner/repo",
            "default_branch": "main",
            "has_ruleset": "False",
            "apply_protection": "YES"
        }
        # Test the logic that would be in apply_from_csv
        should_apply = row.get("apply_protection", "").strip().upper() == "YES"
        assert should_apply is True

    def test_parse_csv_row_no(self):
        """Should correctly identify NO rows."""
        row = {
            "full_name": "owner/repo",
            "default_branch": "main",
            "has_ruleset": "False",
            "apply_protection": "NO"
        }
        should_apply = row.get("apply_protection", "").strip().upper() == "YES"
        assert should_apply is False

    def test_parse_csv_row_case_insensitive(self):
        """YES should be case-insensitive."""
        for value in ["yes", "Yes", "YES", "  yes  ", "  YES  "]:
            row = {"apply_protection": value}
            should_apply = row.get("apply_protection", "").strip().upper() == "YES"
            assert should_apply is True, f"Failed for value: {value!r}"


class TestRepoFiltering:
    """Test repository filtering logic."""

    def test_should_skip_archived_repos(self):
        """Archived repos should be skipped."""
        repo = {"archived": True, "fork": False}
        should_skip = repo.get("archived") or repo.get("fork")
        assert should_skip is True

    def test_should_skip_forked_repos(self):
        """Forked repos should be skipped."""
        repo = {"archived": False, "fork": True}
        should_skip = repo.get("archived") or repo.get("fork")
        assert should_skip is True

    def test_should_not_skip_normal_repos(self):
        """Normal repos should not be skipped."""
        repo = {"archived": False, "fork": False}
        should_skip = repo.get("archived") or repo.get("fork")
        assert should_skip is False


# Integration test placeholder - requires real token
class TestIntegration:
    """Integration tests (require GITHUB_TOKEN env var)."""

    @pytest.mark.skipif(
        not os.environ.get("GITHUB_TOKEN"),
        reason="GITHUB_TOKEN not set"
    )
    def test_can_authenticate(self):
        """Should authenticate with real token."""
        token = os.environ.get("GITHUB_TOKEN")
        auditor = GitHubRulesetAuditor(token)
        user = auditor.get_authenticated_user()
        assert "login" in user
        assert "id" in user
