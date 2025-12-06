#!/usr/bin/env python3
"""
News Scraper Daemon for Hong Kong Fire Documentary
Runs 24/7 on a machine, syncs with upstream, scrapes URLs, creates PRs.

Requirements:
    - gh CLI installed and authenticated (run: gh auth login)
    - Git configured with push access to your fork

Environment Variables Required:
    FORK_REPO    - Your fork's repo path (e.g., 'username/repo-name')

Optional Environment Variables:
    UPSTREAM_REPO - Upstream repo (default: Hong-Kong-Emergency-Coordination-Hub/...)
    MAIN_BRANCH   - Main branch name (default: main)

Usage:
    python daemon.py              # Run daemon (runs forever)
    python daemon.py --once       # Run one cycle and exit (for testing)
"""

import argparse
import functools
import json
import logging
import os
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")


def retry_on_failure(max_retries: int = 3, delay: float = 5, backoff: float = 2, exceptions: tuple = (Exception,)):
    """
    Decorator for retrying operations with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry on
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logging.warning(f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                        logging.info(f"Retrying in {current_delay:.1f}s...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logging.error(f"{func.__name__} failed after {max_retries + 1} attempts: {e}")

            raise last_exception

        return wrapper

    return decorator


# Project paths
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent  # scripts/scrapers/content_scraper -> project root
LOGS_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOGS_DIR / "scraper.log"

# GitHub configuration - set via environment variables or defaults
UPSTREAM_REPO = os.environ.get("UPSTREAM_REPO", "adminlby/Hong-Kong-Fire-Documentary")
FORK_REPO = os.environ.get("FORK_REPO", "hk-hack-007/Hong-Kong-Fire-Documentary-i")  # Required - no default
UPSTREAM_URL = f"https://github.com/adminlby/Hong-Kong-Fire-Documentary.git"
MAIN_BRANCH = os.environ.get("MAIN_BRANCH", "main")

# Timing configuration
SYNC_INTERVAL_MINUTES = 10
PR_INTERVAL_MINUTES = 60

# Stats tracking file for cumulative PR statistics
STATS_FILE = SCRIPT_DIR / "pr_stats.json"


def load_stats() -> dict:
    """Load cumulative scraping statistics from file"""
    if STATS_FILE.exists():
        try:
            with open(STATS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"success": 0, "failed": 0, "failed_urls": [], "cycles": 0, "started_at": None}


def save_stats(stats: dict):
    """Save cumulative scraping statistics to file"""
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)


def reset_stats():
    """Reset stats file when PR is merged or new PR cycle starts"""
    if STATS_FILE.exists():
        STATS_FILE.unlink()
    logging.info("Stats reset for new PR cycle")


def setup_logging():
    """Set up logging to both file and console"""
    LOGS_DIR.mkdir(exist_ok=True)

    # Create formatter
    formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # File handler (append mode)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def run_cmd(cmd: list[str], cwd: Path = None, check: bool = True, env: dict = None) -> subprocess.CompletedProcess:
    """Run a shell command and return the result"""
    # Merge environment, unsetting GITHUB_TOKEN to let gh use its own auth
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    # Unset GITHUB_TOKEN so gh CLI uses its own authentication
    run_env.pop("GITHUB_TOKEN", None)

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=check,
            env=run_env,
        )
        return result
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {' '.join(cmd)}")
        logging.error(f"stderr: {e.stderr}")
        raise


def get_fork_repo() -> str:
    """Get fork repo from environment variable"""
    if not FORK_REPO:
        logging.error("FORK_REPO environment variable not set!")
        logging.error("Please set it: export FORK_REPO='username/repo-name'")
        sys.exit(1)
    return FORK_REPO


def get_fork_owner() -> str:
    """Get the owner/username from FORK_REPO"""
    return get_fork_repo().split("/")[0]


def check_gh_auth() -> bool:
    """Check if gh CLI is authenticated"""
    try:
        result = run_cmd(["gh", "auth", "status"], check=False)
        if result.returncode != 0:
            logging.error("gh CLI is not authenticated!")
            logging.error("Please run: gh auth login")
            return False
        logging.info("gh CLI authenticated")
        return True
    except FileNotFoundError:
        logging.error("gh CLI not found! Please install it: https://cli.github.com/")
        return False


def setup_git_remotes():
    """Ensure git remotes are configured correctly"""
    logging.info("Setting up git remotes...")

    # Check current remotes
    result = run_cmd(["git", "remote", "-v"], check=False)

    # Add upstream if not exists
    if "upstream" not in result.stdout:
        run_cmd(["git", "remote", "add", "upstream", UPSTREAM_URL])
        logging.info(f"Added upstream remote: {UPSTREAM_URL}")

    # Ensure origin points to fork (use gh for auth)
    fork_repo = get_fork_repo()
    fork_url = f"https://github.com/{fork_repo}.git"
    run_cmd(["git", "remote", "set-url", "origin", fork_url])
    logging.info("Configured origin remote")


def recover_git_state():
    """
    Recover from bad git state (merge conflicts, detached HEAD, etc.).
    This is a nuclear option that resets everything to a clean state.
    """
    logging.warning("Recovering git state...")

    # Abort any in-progress operations
    run_cmd(["git", "merge", "--abort"], check=False)
    run_cmd(["git", "rebase", "--abort"], check=False)
    run_cmd(["git", "cherry-pick", "--abort"], check=False)

    # Clear any stashes to avoid conflicts
    run_cmd(["git", "stash", "clear"], check=False)

    # Fetch latest from remotes
    run_cmd(["git", "fetch", "origin"], check=False)
    run_cmd(["git", "fetch", "upstream"], check=False)

    # Force checkout main branch
    run_cmd(["git", "checkout", "-f", MAIN_BRANCH], check=False)

    # Reset to origin/main (our fork's main)
    run_cmd(["git", "reset", "--hard", f"origin/{MAIN_BRANCH}"], check=False)

    # Clean untracked files (but not ignored ones like logs/)
    run_cmd(["git", "clean", "-fd"], check=False)

    logging.info("Git state recovered - reset to origin/main")


def push_to_origin_with_retry() -> bool:
    """
    Push to origin, handling rejections by pulling first.
    Returns True on success, False on failure.
    """
    max_attempts = 3

    for attempt in range(max_attempts):
        result = run_cmd(["git", "push", "origin", MAIN_BRANCH], check=False)

        if result.returncode == 0:
            logging.info("Pushed to origin successfully")
            return True

        stderr = result.stderr.lower()

        # Check if rejection is due to diverged history
        if "rejected" in stderr or "fetch first" in stderr or "non-fast-forward" in stderr:
            logging.warning(f"Push rejected (attempt {attempt + 1}/{max_attempts}), pulling and merging...")

            # Pull with merge strategy
            pull_result = run_cmd(
                ["git", "pull", "origin", MAIN_BRANCH, "--no-rebase", "--no-edit"],
                check=False,
            )

            if pull_result.returncode != 0:
                # Pull failed, might be merge conflict
                if "conflict" in pull_result.stderr.lower():
                    logging.error("Merge conflict during pull, recovering...")
                    recover_git_state()
                    return False

            # Small delay before retry
            time.sleep(2**attempt)
        else:
            # Some other error (network, auth, etc.)
            logging.error(f"Push failed with unexpected error: {result.stderr}")
            time.sleep(2**attempt)

    logging.error(f"Failed to push after {max_attempts} attempts")
    return False


def validate_and_repair_registry() -> bool:
    """
    Check if the registry JSON is valid, repair if corrupted.
    Returns True if registry is valid (or was repaired), False if repair failed.
    """
    registry_file = SCRIPT_DIR / "scraped_urls.json"

    # Check if file exists
    if not registry_file.exists():
        logging.info("Registry file doesn't exist, will be created on first scrape")
        return True

    # Try to load as JSON
    try:
        with open(registry_file, encoding="utf-8") as f:
            content = f.read()

        # Check for merge conflict markers
        if "<<<<<<" in content or "======" in content or ">>>>>>" in content:
            raise ValueError("Merge conflict markers found in registry")

        json.loads(content)
        return True

    except (json.JSONDecodeError, ValueError) as e:
        logging.warning(f"Registry corrupted: {e}")
        logging.info("Attempting to repair by fetching from upstream...")

        try:
            # Fetch upstream first
            run_cmd(["git", "fetch", "upstream", MAIN_BRANCH], check=False)

            # Try to get the file from upstream
            result = run_cmd(
                ["git", "show", f"upstream/{MAIN_BRANCH}:scripts/scraper/scraped_urls.json"],
                check=False,
            )

            if result.returncode == 0 and result.stdout:
                # Validate the upstream version
                json.loads(result.stdout)

                # Write it
                with open(registry_file, "w", encoding="utf-8") as f:
                    f.write(result.stdout)

                logging.info("Registry repaired from upstream")
                return True

        except Exception as repair_error:
            logging.error(f"Failed to repair registry: {repair_error}")

        # Last resort: backup corrupted file and create empty registry
        backup_file = registry_file.with_suffix(".json.corrupted")
        registry_file.rename(backup_file)
        logging.warning(f"Corrupted registry backed up to {backup_file}")

        with open(registry_file, "w", encoding="utf-8") as f:
            json.dump({"scraped_urls": {}, "last_updated": datetime.now().isoformat()}, f, indent=2)

        logging.info("Created new empty registry")
        return True


def health_check() -> bool:
    """
    Verify the daemon can operate properly.
    Returns True if all checks pass, False otherwise.
    """
    checks_passed = True

    # Check gh CLI authentication
    if not check_gh_auth():
        logging.error("Health check failed: gh CLI not authenticated")
        checks_passed = False

    # Check git status is clean enough to operate
    result = run_cmd(["git", "status", "--porcelain"], check=False)
    if result.returncode != 0:
        logging.error("Health check failed: git status command failed")
        checks_passed = False

    # Check we're on the main branch
    result = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], check=False)
    if result.returncode == 0:
        current_branch = result.stdout.strip()
        if current_branch != MAIN_BRANCH:
            logging.warning(f"Health check: on branch '{current_branch}', expected '{MAIN_BRANCH}'")
            run_cmd(["git", "checkout", MAIN_BRANCH], check=False)

    # Check registry is valid
    if not validate_and_repair_registry():
        logging.error("Health check failed: registry invalid and could not be repaired")
        checks_passed = False

    # Check remotes are configured
    result = run_cmd(["git", "remote", "-v"], check=False)
    if "origin" not in result.stdout or "upstream" not in result.stdout:
        logging.warning("Health check: remotes not configured, setting up...")
        setup_git_remotes()

    return checks_passed


@retry_on_failure(max_retries=3, delay=5, backoff=2)
def sync_with_upstream() -> bool:
    """
    Sync local repo with upstream.
    Returns True if there were changes, False otherwise.
    """
    logging.info("Syncing with upstream...")

    # Fetch upstream
    run_cmd(["git", "fetch", "upstream", MAIN_BRANCH])

    # Check if we're behind upstream
    result = run_cmd(["git", "rev-list", "--count", f"HEAD..upstream/{MAIN_BRANCH}"])
    commits_behind = int(result.stdout.strip())

    if commits_behind > 0:
        logging.info(f"Behind upstream by {commits_behind} commits, merging...")

        # Stash any local changes
        run_cmd(["git", "stash", "--include-untracked"], check=False)

        # Checkout main and merge upstream
        run_cmd(["git", "checkout", MAIN_BRANCH])

        # Try to merge
        merge_result = run_cmd(["git", "merge", f"upstream/{MAIN_BRANCH}", "--no-edit"], check=False)

        if merge_result.returncode != 0:
            # Merge failed, likely conflict
            stderr = merge_result.stderr.lower()
            if "conflict" in stderr or "merge" in stderr:
                logging.error("Merge conflict detected, aborting and recovering...")
                run_cmd(["git", "merge", "--abort"], check=False)
                run_cmd(["git", "stash", "pop"], check=False)
                # Re-raise to trigger retry or recovery
                raise RuntimeError(f"Merge conflict during upstream sync: {merge_result.stderr}")

        # Pop stash if exists
        stash_result = run_cmd(["git", "stash", "pop"], check=False)
        if stash_result.returncode != 0 and "No stash" not in stash_result.stderr:
            # Stash pop failed (conflict with stashed changes)
            logging.warning("Stash pop failed, dropping stash to continue")
            run_cmd(["git", "stash", "drop"], check=False)

        logging.info("Synced with upstream successfully")
        return True
    else:
        logging.info("Already up to date with upstream")
        return False


def run_scraper() -> tuple[int, int]:
    """
    Run the scraper to detect and scrape new URLs.
    Returns (success_count, fail_count) and updates cumulative stats.
    """
    logging.info("Running scraper...")

    try:
        # Import and run scraper
        sys.path.insert(0, str(SCRIPT_DIR))
        from scraper import (
            filter_new_urls,
            get_all_urls,
            load_registry,
        )
        from scraper import (
            run_scraper as scrape,
        )

        # Check for new URLs first
        registry = load_registry()
        all_urls = get_all_urls()
        new_urls = filter_new_urls(all_urls, registry)

        if not new_urls:
            logging.info("No new URLs to scrape")
            return 0, 0

        logging.info(f"Found {len(new_urls)} new URLs to scrape")

        # Run the scraper and get results
        results = scrape(dry_run=False, verbose=False)

        success_count = results.get("success", 0) if results else 0
        fail_count = results.get("failed", 0) if results else 0
        failed_urls = results.get("failed_urls", []) if results else []

        # Update cumulative stats
        stats = load_stats()
        if stats["started_at"] is None:
            stats["started_at"] = datetime.now().isoformat()
        stats["success"] += success_count
        stats["failed"] += fail_count
        stats["cycles"] += 1
        # Add new failed URLs (deduplicate)
        existing_failed = set(stats.get("failed_urls", []))
        for url in failed_urls:
            if url not in existing_failed:
                stats["failed_urls"].append(url)
        save_stats(stats)

        logging.info(f"Updated cumulative stats: {stats['success']} success, {stats['failed']} failed across {stats['cycles']} cycles")

        return success_count, fail_count

    except Exception as e:
        logging.error(f"Scraper error: {e}")
        return 0, 0


def has_local_changes() -> bool:
    """Check if there are uncommitted changes"""
    result = run_cmd(["git", "status", "--porcelain"])
    return bool(result.stdout.strip())


def commit_changes() -> bool:
    """Commit any local changes"""
    if not has_local_changes():
        return False

    logging.info("Committing changes...")

    try:
        # Stage all changes
        run_cmd(["git", "add", "-A"])

        # Create commit message with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        msg = f"chore(scraper): auto-scrape {timestamp}"

        run_cmd(["git", "commit", "-m", msg])
        logging.info(f"Committed: {msg}")
        return True

    except Exception as e:
        logging.error(f"Failed to commit: {e}")
        return False


@retry_on_failure(max_retries=2, delay=3, backoff=2)
def get_open_pr() -> dict | None:
    """Check if there's an existing open PR from fork's main branch using gh CLI"""
    fork_owner = get_fork_owner()

    # Search by author and filter by head branch name
    # (--head with fork:branch format doesn't work reliably for cross-fork PRs)
    result = run_cmd(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            UPSTREAM_REPO,
            "--author",
            fork_owner,
            "--state",
            "open",
            "--json",
            "number,url,headRefName",
        ],
        check=False,
    )

    if result.returncode == 0 and result.stdout.strip():
        prs = json.loads(result.stdout)
        # Filter to PRs from main branch
        for pr in prs:
            if pr.get("headRefName") == MAIN_BRANCH:
                return {"number": pr["number"], "url": pr["url"]}
    return None


def close_pr(pr_number: int) -> bool:
    """Close an existing PR using gh CLI"""
    try:
        run_cmd(["gh", "pr", "close", str(pr_number), "--repo", UPSTREAM_REPO])
        logging.info(f"Closed PR #{pr_number}")
        return True

    except Exception as e:
        logging.error(f"Failed to close PR #{pr_number}: {e}")
        return False


def generate_pr_body() -> tuple[str, str]:
    """Generate PR title and body with current stats. Returns (title, body)."""
    # Fetch upstream to ensure we have latest refs
    run_cmd(["git", "fetch", "upstream", MAIN_BRANCH], check=False)

    # Get NEW articles compared to upstream using git diff
    new_article_counts = {}
    try:
        # Get list of new index.html files in archive directories
        result = run_cmd(
            ["git", "diff", "--name-only", f"upstream/{MAIN_BRANCH}", "--", "content/news/*/archive/*/index.html"],
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                # Parse path: content/news/SOURCE/archive/ARTICLE/index.html
                parts = line.split("/")
                if len(parts) >= 4:
                    source_name = parts[2]  # e.g., "hk01", "bbc"
                    new_article_counts[source_name] = new_article_counts.get(source_name, 0) + 1
    except Exception as e:
        logging.warning(f"Failed to count new articles: {e}")

    # Build new articles breakdown
    if new_article_counts:
        new_source_lines = "\n".join(f"  - **{name}**: +{count}" for name, count in sorted(new_article_counts.items()))
        total_new_articles = sum(new_article_counts.values())
        total_new_sources = len(new_article_counts)
        new_articles_section = f"""### New Articles in This PR
- **Sources with new articles**: {total_new_sources}
- **Total new articles**: {total_new_articles}

{new_source_lines}

"""
    else:
        new_articles_section = """### New Articles in This PR
No new articles added yet.

"""

    # Load cumulative scraping stats
    stats = load_stats()
    stats_section = f"""### Scraping Statistics (since PR opened)
- **Cycles completed**: {stats["cycles"]}
- **Successfully scraped**: {stats["success"]}
- **Failed to scrape**: {stats["failed"]}

"""

    # Build failed URLs section (cap at 10)
    failed_urls = stats.get("failed_urls", [])
    if failed_urls:
        displayed_urls = failed_urls[:10]
        failed_lines = "\n".join(f"- {url}" for url in displayed_urls)
        if len(failed_urls) > 10:
            failed_lines += f"\n- ... and {len(failed_urls) - 10} more"
        failed_section = f"""### Failed URLs
{failed_lines}

"""
    else:
        failed_section = ""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    title = f"[Auto-Scraper] News archives update - {timestamp}"
    body = f"""## Automated News Archive Update

This PR was automatically generated by the news scraper daemon.

{new_articles_section}{stats_section}{failed_section}---
*Last updated: {timestamp}*
"""

    return title, body


@retry_on_failure(max_retries=2, delay=3, backoff=2)
def create_pr() -> str | None:
    """Create a new PR to upstream using gh CLI. Returns 'created', 'exists', or None on failure."""
    fork_owner = get_fork_owner()
    title, body = generate_pr_body()

    result = run_cmd(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            UPSTREAM_REPO,
            "--head",
            f"{fork_owner}:{MAIN_BRANCH}",
            "--base",
            MAIN_BRANCH,
            "--title",
            title,
            "--body",
            body,
        ],
        check=False,
    )

    if result.returncode == 0:
        pr_url = result.stdout.strip()
        logging.info(f"Created PR: {pr_url}")
        return "created"
    elif "already exists" in result.stderr.lower():
        logging.info("PR already exists")
        return "exists"
    else:
        logging.error(f"Failed to create PR: {result.stderr}")
        return None


def update_pr(pr_number: int) -> bool:
    """Update an existing PR's title and body with fresh stats."""
    title, body = generate_pr_body()

    result = run_cmd(
        [
            "gh",
            "pr",
            "edit",
            str(pr_number),
            "--repo",
            UPSTREAM_REPO,
            "--title",
            title,
            "--body",
            body,
        ],
        check=False,
    )

    if result.returncode == 0:
        logging.info(f"Updated PR #{pr_number} with fresh stats")
        return True
    else:
        logging.error(f"Failed to update PR #{pr_number}: {result.stderr}")
        return False


def manage_pr():
    """Create or update PR from fork's main to upstream's main"""
    logging.info("Managing PR...")

    # Check for existing open PR
    existing_pr = get_open_pr()
    if existing_pr:
        pr_number = existing_pr["number"]
        logging.info(f"PR #{pr_number} exists, updating description with fresh stats...")
        update_pr(pr_number)
        return

    # No existing PR - create one
    result = create_pr()
    if result == "created":
        # Only reset stats after successfully creating a NEW PR
        # Stats will now track from the start of this new PR
        reset_stats()


def run_daemon(run_once: bool = False):
    """Main daemon loop with robust error handling for 24/7 operation"""
    logger = setup_logging()

    logger.info("=" * 60)
    logger.info("News Scraper Daemon Starting")
    logger.info(f"Fork: {get_fork_repo()}")
    logger.info(f"Upstream: {UPSTREAM_REPO}")
    logger.info(f"Sync interval: {SYNC_INTERVAL_MINUTES} minutes")
    logger.info(f"PR interval: {PR_INTERVAL_MINUTES} minutes")
    logger.info("=" * 60)

    # Verify gh CLI auth and fork repo
    if not check_gh_auth():
        sys.exit(1)
    get_fork_repo()

    # Setup git remotes
    setup_git_remotes()

    # Initial health check
    if not health_check():
        logging.warning("Initial health check failed, attempting recovery...")
        recover_git_state()

    last_sync = datetime.min
    last_pr = datetime.min
    last_health_check = datetime.min
    consecutive_failures = 0
    max_consecutive_failures = 5

    while True:
        try:
            now = datetime.now()

            # Periodic health check (every 6 hours)
            if now - last_health_check >= timedelta(hours=6):
                logging.info("-" * 40)
                logging.info("Running periodic health check...")
                if health_check():
                    logging.info("Health check passed")
                    consecutive_failures = 0
                else:
                    logging.warning("Health check failed, recovering...")
                    recover_git_state()
                last_health_check = now

            # Check if it's time to sync (every 10 minutes)
            if now - last_sync >= timedelta(minutes=SYNC_INTERVAL_MINUTES):
                logging.info("-" * 40)
                logging.info("Starting sync cycle...")

                try:
                    # Validate registry before scraping
                    validate_and_repair_registry()

                    # Sync with upstream
                    sync_with_upstream()

                    # Run scraper
                    success, failed = run_scraper()
                    if success > 0 or failed > 0:
                        logging.info(f"Scraper results: {success} success, {failed} failed")

                    # Commit any changes
                    commit_changes()

                    # Push to origin to keep fork in sync with upstream
                    push_to_origin_with_retry()

                    last_sync = now
                    consecutive_failures = 0
                    logging.info("Sync cycle complete")

                except Exception as e:
                    consecutive_failures += 1
                    logging.error(f"Sync cycle failed: {e}")

                    if consecutive_failures >= max_consecutive_failures:
                        logging.error(f"Too many consecutive failures ({consecutive_failures}), recovering git state...")
                        recover_git_state()
                        consecutive_failures = 0

            # Check if it's time to create/update PR (every hour)
            if now - last_pr >= timedelta(minutes=PR_INTERVAL_MINUTES):
                logging.info("-" * 40)
                logging.info("Starting PR cycle...")

                try:
                    # Ensure fork is up to date before PR check
                    push_to_origin_with_retry()

                    # Create PR from fork:main to upstream:main if needed
                    manage_pr()

                    last_pr = now
                    logging.info("PR cycle complete")

                except Exception as e:
                    logging.error(f"PR cycle failed: {e}")
                    # Don't increment consecutive_failures for PR issues
                    # PR failures are less critical than sync failures

            if run_once:
                logging.info("Run once mode, exiting...")
                break

            # Sleep for 1 minute between checks
            time.sleep(60)

        except KeyboardInterrupt:
            logging.info("Daemon stopped by user")
            break
        except Exception as e:
            # Catch any unexpected errors and try to recover
            consecutive_failures += 1
            logging.error(f"Unexpected daemon error: {e}")

            if consecutive_failures >= max_consecutive_failures:
                logging.error("Too many failures, attempting full recovery...")
                try:
                    recover_git_state()
                    consecutive_failures = 0
                except Exception as recovery_error:
                    logging.critical(f"Recovery failed: {recovery_error}")
                    # Sleep longer before retrying after recovery failure
                    time.sleep(300)

            # Continue running instead of crashing
            time.sleep(60)


def main():
    parser = argparse.ArgumentParser(description="News Scraper Daemon - runs 24/7, syncs and scrapes")
    parser.add_argument("--once", action="store_true", help="Run one sync+scrape+PR cycle and exit")

    args = parser.parse_args()
    run_daemon(run_once=args.once)


if __name__ == "__main__":
    main()
