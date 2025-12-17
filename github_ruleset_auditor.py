#!/usr/bin/env python3
"""
GitHub Ruleset Auditor

Audit and enforce branch protection rules across all your GitHub repositories
using the modern Rulesets API (not legacy branch protection).

Features:
1. Fetch repositories for a GitHub user/org (public, private, or all)
2. Check if a default branch ruleset exists
3. Create a manifest of all repos and their ruleset status
4. Optionally apply rulesets to repos that don't have them

The ruleset:
- Adds YOU as a bypass actor (full freedom for you)
- Blocks force pushes and branch deletion
- Requires PRs from other contributors (with your approval)
- Protects against leaked CI tokens

Requirements:
    pip install requests

Usage:
    export GITHUB_TOKEN="your_personal_access_token"

    # Audit public repos only (default)
    github-ruleset-auditor -u YOUR_USERNAME

    # Audit private repos only
    github-ruleset-auditor -u YOUR_USERNAME --visibility private

    # Audit all repos (public + private)
    github-ruleset-auditor -u YOUR_USERNAME --visibility all

    # Apply rulesets (with dry-run)
    github-ruleset-auditor -u YOUR_USERNAME --apply --dry-run
"""

import os
import sys
import json
import csv
import argparse
from datetime import datetime, timezone
from typing import Optional
from importlib.metadata import version, PackageNotFoundError

import requests

# Version is read from pyproject.toml (single source of truth)
try:
    __version__ = version("github-ruleset-auditor")
except PackageNotFoundError:
    # Package not installed (running directly from source)
    __version__ = "dev"


class GitHubRulesetAuditor:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.manifest = []
        self.authenticated_user = None
        self.authenticated_user_id = None

    def get_authenticated_user(self) -> dict:
        """Get the authenticated user's info (for bypass actor)."""
        if self.authenticated_user:
            return self.authenticated_user

        url = f"{self.base_url}/user"
        response = requests.get(url, headers=self.headers)

        if response.status_code != 200:
            print(f"Error getting authenticated user: {response.status_code} - {response.text}")
            sys.exit(1)

        self.authenticated_user = response.json()
        self.authenticated_user_id = self.authenticated_user["id"]
        print(f"Authenticated as: {self.authenticated_user['login']} (ID: {self.authenticated_user_id})")
        return self.authenticated_user

    def get_repos(self, username: Optional[str] = None, org: Optional[str] = None,
                  visibility: str = "public") -> list:
        """Fetch repositories for a user or organization.

        Args:
            username: GitHub username (for personal repos)
            org: GitHub organization name
            visibility: Filter by visibility - 'public', 'private', or 'all'
        """
        repos = []
        page = 1
        per_page = 100

        # Map visibility to API type parameter
        # For orgs: public, private, all
        # For users: public, private, all (but API uses 'owner' for authenticated user's repos)
        if org:
            url = f"{self.base_url}/orgs/{org}/repos"
            api_type = visibility if visibility != "all" else "all"
        else:
            url = f"{self.base_url}/users/{username}/repos"
            api_type = visibility if visibility != "all" else "all"

        params = {"type": api_type, "per_page": per_page}

        visibility_label = visibility if visibility != "all" else "all (public + private)"
        print(f"\nFetching {visibility_label} repositories for {'org: ' + org if org else 'user: ' + username}...")

        while True:
            params["page"] = page
            response = requests.get(url, headers=self.headers, params=params)

            if response.status_code != 200:
                print(f"Error fetching repos: {response.status_code} - {response.text}")
                sys.exit(1)

            page_repos = response.json()
            if not page_repos:
                break

            # Filter based on visibility and exclude archived/forked repos
            filtered_repos = []
            for r in page_repos:
                is_private = r.get("private", False)
                is_archived = r.get("archived", False)
                is_fork = r.get("fork", False)

                # Skip archived and forked repos always
                if is_archived or is_fork:
                    continue

                # Apply visibility filter
                if visibility == "public" and is_private:
                    continue
                if visibility == "private" and not is_private:
                    continue
                # visibility == "all" includes both

                filtered_repos.append(r)

            repos.extend(filtered_repos)

            skipped = len(page_repos) - len(filtered_repos)
            forked = sum(1 for r in page_repos if r.get("fork", False))
            archived = sum(1 for r in page_repos if r.get("archived", False))
            print(f"  Page {page}: {len(filtered_repos)} repos (skipped {archived} archived, {forked} forked)")
            page += 1

        print(f"Total eligible repositories: {len(repos)}")
        return repos

    def get_repo_rulesets(self, owner: str, repo: str) -> list:
        """Get all rulesets for a repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}/rulesets"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return []
        else:
            return {"error": f"{response.status_code}: {response.text}"}

    def get_ruleset_details(self, owner: str, repo: str, ruleset_id: int) -> dict:
        """Get full details of a specific ruleset (including conditions)."""
        url = f"{self.base_url}/repos/{owner}/{repo}/rulesets/{ruleset_id}"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"{response.status_code}: {response.text}"}

    def check_default_branch_ruleset(self, owner: str, repo: str, default_branch: str) -> dict:
        """Check if a ruleset protecting the default branch exists."""
        rulesets = self.get_repo_rulesets(owner, repo)

        if isinstance(rulesets, dict) and "error" in rulesets:
            return {"has_ruleset": None, "error": rulesets["error"]}

        # Look for a ruleset targeting the default branch
        # Note: The list endpoint doesn't include conditions, so we need to fetch details
        for ruleset in rulesets:
            ruleset_id = ruleset.get("id")
            if not ruleset_id:
                continue

            # Fetch full details to get conditions
            details = self.get_ruleset_details(owner, repo, ruleset_id)
            if isinstance(details, dict) and "error" in details:
                continue

            conditions = details.get("conditions", {})
            ref_name = conditions.get("ref_name", {})
            includes = ref_name.get("include", [])

            # Check if it targets default branch or the specific branch name
            if "~DEFAULT_BRANCH" in includes or f"refs/heads/{default_branch}" in includes or default_branch in includes:
                return {
                    "has_ruleset": True,
                    "ruleset_id": details.get("id"),
                    "ruleset_name": details.get("name"),
                    "enforcement": details.get("enforcement"),
                    "rules": details.get("rules", []),
                    "bypass_actors": details.get("bypass_actors", []),
                }

        return {"has_ruleset": False}

    def create_default_ruleset(self, owner: str, repo: str, is_org: bool = False) -> dict:
        """Create a ruleset for the default branch.

        For org repos, adds the authenticated user as a bypass actor.
        For personal repos, bypass_actors is omitted (owner has full access by default).
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/rulesets"

        ruleset_config = {
            "name": "default-branch-protection",
            "target": "branch",
            "enforcement": "active",
            "conditions": {
                "ref_name": {
                    "exclude": [],
                    "include": ["~DEFAULT_BRANCH"]
                }
            },
            "rules": [
                {
                    "type": "deletion"
                },
                {
                    "type": "non_fast_forward"
                },
                {
                    "type": "pull_request",
                    "parameters": {
                        "required_approving_review_count": 1,
                        "dismiss_stale_reviews_on_push": True,
                        "require_code_owner_review": False,
                        "require_last_push_approval": False,
                        "required_review_thread_resolution": False
                    }
                }
            ],
        }

        # Add bypass actors
        # For org repos: use User type with authenticated user ID
        # For personal repos: use RepositoryRole type (5 = Maintain role, includes owner)
        if is_org:
            ruleset_config["bypass_actors"] = [
                {
                    "actor_id": self.authenticated_user_id,
                    "actor_type": "User",
                    "bypass_mode": "always"
                }
            ]
        else:
            # RepositoryRole IDs: 1=Read, 2=Triage, 4=Write, 5=Maintain
            # Owner has maintain+ permissions, so this gives them bypass
            ruleset_config["bypass_actors"] = [
                {
                    "actor_id": 5,
                    "actor_type": "RepositoryRole",
                    "bypass_mode": "always"
                }
            ]

        response = requests.post(url, headers=self.headers, json=ruleset_config)

        if response.status_code in [200, 201]:
            return {"success": True, "ruleset": response.json()}
        else:
            return {"success": False, "error": f"{response.status_code}: {response.text}"}

    def process_repos(self, username: Optional[str] = None, org: Optional[str] = None,
                      apply_ruleset: bool = False, dry_run: bool = False,
                      visibility: str = "public") -> list:
        """Process all repos, check ruleset status, and optionally apply rulesets."""
        # Get authenticated user first (needed for bypass actor)
        self.get_authenticated_user()

        owner = org if org else username
        repos = self.get_repos(username=username, org=org, visibility=visibility)

        print(f"\nChecking ruleset status for {len(repos)} repositories...")
        print("-" * 70)

        for i, repo in enumerate(repos, 1):
            repo_name = repo["name"]
            default_branch = repo.get("default_branch", "main")
            full_name = repo["full_name"]

            print(f"[{i}/{len(repos)}] {full_name} (branch: {default_branch})")

            ruleset_status = self.check_default_branch_ruleset(owner, repo_name, default_branch)

            manifest_entry = {
                "repo_name": repo_name,
                "full_name": full_name,
                "default_branch": default_branch,
                "html_url": repo["html_url"],
                "has_ruleset": ruleset_status.get("has_ruleset"),
                "ruleset_name": ruleset_status.get("ruleset_name"),
                "ruleset_id": ruleset_status.get("ruleset_id"),
                "enforcement": ruleset_status.get("enforcement"),
                "bypass_actors_count": len(ruleset_status.get("bypass_actors", [])),
                "error": ruleset_status.get("error"),
                "action_taken": None,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

            # Apply ruleset if requested and none exists
            if apply_ruleset and ruleset_status.get("has_ruleset") is False:
                if dry_run:
                    print(f"    [DRY RUN] Would create ruleset for {full_name}")
                    manifest_entry["action_taken"] = "dry_run_would_create"
                else:
                    print(f"    Creating ruleset...")
                    result = self.create_default_ruleset(owner, repo_name, is_org=bool(org))
                    if result.get("success"):
                        print(f"    ✓ Ruleset created successfully")
                        manifest_entry["action_taken"] = "ruleset_created"
                        manifest_entry["has_ruleset"] = True
                        manifest_entry["ruleset_name"] = "default-branch-protection"
                    else:
                        print(f"    ✗ Failed: {result.get('error')}")
                        manifest_entry["action_taken"] = "creation_failed"
                        manifest_entry["error"] = result.get("error")
            elif ruleset_status.get("has_ruleset"):
                print(f"    ✓ Has ruleset: {ruleset_status.get('ruleset_name')} ({ruleset_status.get('enforcement')})")
            elif ruleset_status.get("error"):
                print(f"    ⚠ Error: {ruleset_status.get('error')}")
            else:
                print(f"    ✗ No ruleset")

            self.manifest.append(manifest_entry)

        return self.manifest

    def save_manifest(self, output_dir: str = ".") -> tuple:
        """Save the manifest to JSON and CSV files."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        json_path = os.path.join(output_dir, f"ruleset_manifest_{timestamp}.json")
        csv_path = os.path.join(output_dir, f"ruleset_manifest_{timestamp}.csv")

        # Summary stats
        has_ruleset = sum(1 for r in self.manifest if r["has_ruleset"])
        no_ruleset = sum(1 for r in self.manifest if r["has_ruleset"] is False)
        errors = sum(1 for r in self.manifest if r["has_ruleset"] is None)

        # Save JSON
        with open(json_path, "w") as f:
            json.dump({
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "authenticated_user": self.authenticated_user["login"],
                "authenticated_user_id": self.authenticated_user_id,
                "total_repos": len(self.manifest),
                "with_ruleset": has_ruleset,
                "without_ruleset": no_ruleset,
                "errors": errors,
                "repositories": self.manifest,
            }, f, indent=2)

        # Save CSV with apply_protection column for user to edit
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "repo_name", "full_name", "default_branch", "html_url",
                "has_ruleset", "ruleset_name", "enforcement", "action_taken", "error",
                "apply_protection"
            ])
            for entry in self.manifest:
                # Default to YES if no ruleset, NO if already has one
                apply_default = "NO" if entry["has_ruleset"] else "YES"
                writer.writerow([
                    entry["repo_name"],
                    entry["full_name"],
                    entry["default_branch"],
                    entry["html_url"],
                    entry["has_ruleset"],
                    entry["ruleset_name"],
                    entry["enforcement"],
                    entry["action_taken"],
                    entry["error"],
                    apply_default,
                ])

        return json_path, csv_path

    def apply_from_csv(self, csv_path: str, dry_run: bool = False) -> dict:
        """Apply rulesets based on a user-edited CSV file."""
        self.get_authenticated_user()

        results = {"applied": 0, "skipped": 0, "failed": 0, "already_protected": 0}

        print(f"\nReading decisions from: {csv_path}")
        print("-" * 70)

        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        total = len(rows)
        to_apply = [r for r in rows if r.get("apply_protection", "").upper() == "YES"]
        print(f"Total repos in CSV: {total}")
        print(f"Marked for protection: {len(to_apply)}")
        print("-" * 70)

        for i, row in enumerate(rows, 1):
            repo_name = row["repo_name"]
            full_name = row["full_name"]
            apply_protection = row.get("apply_protection", "").upper()

            print(f"[{i}/{total}] {full_name}", end=" ")

            if apply_protection != "YES":
                print("- SKIP (not marked YES)")
                results["skipped"] += 1
                continue

            if row.get("has_ruleset") == "True":
                print("- SKIP (already protected)")
                results["already_protected"] += 1
                continue

            if dry_run:
                print("- [DRY RUN] Would apply ruleset")
                results["applied"] += 1
                continue

            # Extract owner from full_name (e.g., "psenger/repo" -> "psenger")
            owner = full_name.split("/")[0]
            # Detect if this is an org repo (owner != authenticated user)
            is_org = owner != self.authenticated_user["login"]
            result = self.create_default_ruleset(owner, repo_name, is_org=is_org)

            if result.get("success"):
                print("- SUCCESS")
                results["applied"] += 1
            else:
                print(f"- FAILED: {result.get('error', 'Unknown error')[:50]}")
                results["failed"] += 1

        print("\n" + "=" * 70)
        print("APPLY FROM CSV SUMMARY")
        print("=" * 70)
        print(f"Applied:           {results['applied']}")
        print(f"Skipped (NO):      {results['skipped']}")
        print(f"Already protected: {results['already_protected']}")
        print(f"Failed:            {results['failed']}")

        return results

    def print_summary(self):
        """Print a summary of the results."""
        has_ruleset = sum(1 for r in self.manifest if r["has_ruleset"])
        no_ruleset = sum(1 for r in self.manifest if r["has_ruleset"] is False)
        errors = sum(1 for r in self.manifest if r["has_ruleset"] is None)
        created = sum(1 for r in self.manifest if r["action_taken"] == "ruleset_created")

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Authenticated as: {self.authenticated_user['login']} (ID: {self.authenticated_user_id})")
        print(f"\nTotal repositories scanned: {len(self.manifest)}")
        print(f"  ✓ With ruleset:    {has_ruleset}")
        print(f"  ✗ Without ruleset: {no_ruleset}")
        print(f"  ⚠ Errors:          {errors}")

        if created > 0:
            print(f"\n  Rulesets created this run: {created}")

        if no_ruleset > 0:
            unprotected = [e for e in self.manifest if e["has_ruleset"] is False and e["action_taken"] != "ruleset_created"]
            if unprotected:
                print("\nRepositories without rulesets:")
                for entry in unprotected:
                    print(f"  - {entry['full_name']}")

        print("\n" + "=" * 70)
        print("RULESET CONFIGURATION")
        print("=" * 70)
        print(f"Bypass actor: {self.authenticated_user['login']} (you can push/merge freely)")
        print("Rules applied to others:")
        print("  • Cannot delete default branch")
        print("  • Cannot force push")
        print("  • Must open PR with 1 approval")


def main():
    parser = argparse.ArgumentParser(
        description="Audit and enforce branch protection rulesets"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--username", "-u", help="GitHub username")
    group.add_argument("--org", "-o", help="GitHub organization name")
    group.add_argument("--from-csv", "-f", metavar="CSV_FILE",
                        help="Apply rulesets from a user-edited CSV file")

    parser.add_argument("--apply", "-a", action="store_true",
                        help="Create rulesets for repos that don't have them")
    parser.add_argument("--dry-run", "-d", action="store_true",
                        help="Show what would be done without making changes")
    parser.add_argument("--output-dir", default=".",
                        help="Directory to save manifest files (default: current directory)")
    parser.add_argument("--token", "-t",
                        help="GitHub token (or set GITHUB_TOKEN env var)")
    parser.add_argument("--repo", "-r", metavar="REPO_NAME",
                        help="Process only a single repo (for testing)")
    parser.add_argument("--visibility", "-v", choices=["public", "private", "all"],
                        default="public",
                        help="Repository visibility filter (default: public)")

    args = parser.parse_args()

    # Get token
    token = args.token or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GitHub token required.")
        print("\nSet GITHUB_TOKEN environment variable or use --token")
        print("\nToken needs these scopes:")
        print("  • repo (for private repos)")
        print("  • public_repo (for public repos only)")
        print("\nCreate token at: https://github.com/settings/tokens")
        sys.exit(1)

    # Create output directory if needed
    os.makedirs(args.output_dir, exist_ok=True)

    # Run the auditor
    auditor = GitHubRulesetAuditor(token)

    # Mode 1: Apply from user-edited CSV file
    if args.from_csv:
        if not os.path.exists(args.from_csv):
            print(f"Error: CSV file not found: {args.from_csv}")
            sys.exit(1)
        auditor.apply_from_csv(args.from_csv, dry_run=args.dry_run)
        return

    # Mode 2: Process single repo (for testing)
    if args.repo:
        owner = args.username or args.org
        auditor.get_authenticated_user()
        print(f"\nProcessing single repo: {owner}/{args.repo}")
        print("-" * 70)

        # Get repo info
        url = f"{auditor.base_url}/repos/{owner}/{args.repo}"
        response = requests.get(url, headers=auditor.headers)
        if response.status_code != 200:
            print(f"Error: Could not find repo {owner}/{args.repo}")
            sys.exit(1)

        repo = response.json()
        default_branch = repo.get("default_branch", "main")
        print(f"Default branch: {default_branch}")

        # Check current status
        status = auditor.check_default_branch_ruleset(owner, args.repo, default_branch)
        if status.get("has_ruleset"):
            print(f"Status: Already has ruleset '{status.get('ruleset_name')}'")
        else:
            print("Status: No ruleset")

        if args.apply:
            if status.get("has_ruleset"):
                print("\nSkipping - ruleset already exists")
            elif args.dry_run:
                print("\n[DRY RUN] Would create ruleset")
            else:
                print("\nCreating ruleset...")
                result = auditor.create_default_ruleset(owner, args.repo, is_org=bool(args.org))
                if result.get("success"):
                    print("SUCCESS: Ruleset created")
                else:
                    print(f"FAILED: {result.get('error')}")
        return

    # Mode 3: Full scan of all repos
    auditor.process_repos(
        username=args.username,
        org=args.org,
        apply_ruleset=args.apply,
        dry_run=args.dry_run,
        visibility=args.visibility
    )

    # Save manifest
    json_path, csv_path = auditor.save_manifest(args.output_dir)
    print(f"\nManifest saved:")
    print(f"  JSON: {json_path}")
    print(f"  CSV:  {csv_path}")

    # Print summary
    auditor.print_summary()


if __name__ == "__main__":
    main()
