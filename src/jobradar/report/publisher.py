"""GitHub Pages publisher — pushes report HTML to gh-pages branch.

Uses git worktree so it doesn't disturb the working tree on main.
Requires the repo to have GitHub Pages enabled on the gh-pages branch.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


def publish_to_github_pages(
    report_path: Path,
    *,
    repo_dir: Path | None = None,
    branch: str = "gh-pages",
) -> str:
    """Push report HTML to gh-pages branch and return the public URL.

    Args:
        report_path: Path to the generated .html file
        repo_dir: Root of the git repo (auto-detected if None)
        branch: Target branch name (default: gh-pages)

    Returns:
        Public GitHub Pages URL for the report

    Raises:
        RuntimeError: If git operations fail
    """
    repo_dir = repo_dir or _find_repo_root()
    if repo_dir is None:
        raise RuntimeError(
            "Could not find git repository root. "
            "Run from inside the jobradar project directory."
        )

    remote_url = _git(["remote", "get-url", "origin"], cwd=repo_dir).strip()
    repo_slug = _parse_github_slug(remote_url)
    if not repo_slug:
        raise RuntimeError(f"Could not parse GitHub repo from remote: {remote_url}")

    _ensure_gh_pages_branch(repo_dir, branch)

    with tempfile.TemporaryDirectory() as tmpdir:
        wt_path = Path(tmpdir) / "gh-pages-wt"
        try:
            _git(["worktree", "add", "--force", str(wt_path), branch], cwd=repo_dir)
            dest = wt_path / report_path.name
            shutil.copy2(report_path, dest)
            _write_index_redirect(wt_path, report_path.name)
            _git(["add", "."], cwd=wt_path)
            _git(["commit", "--allow-empty", "-m",
                  f"report: update {report_path.name}"], cwd=wt_path)
            _git(["push", "origin", branch], cwd=wt_path)
        finally:
            try:
                _git(["worktree", "remove", "--force", str(wt_path)], cwd=repo_dir)
            except Exception:
                pass

    owner, repo = repo_slug.split("/")
    return f"https://{owner}.github.io/{repo}/{report_path.name}"


def _write_index_redirect(wt_path: Path, report_name: str) -> None:
    """Write/update index.html to redirect to the latest report."""
    index = wt_path / "index.html"
    index.write_text(
        f'<!DOCTYPE html><html><head>'
        f'<meta http-equiv="refresh" content="0;url={report_name}">'
        f'<title>JobRadar Report</title></head>'
        f'<body><a href="{report_name}">View latest report</a></body></html>',
        encoding="utf-8",
    )


def _ensure_gh_pages_branch(repo_dir: Path, branch: str) -> None:
    """Create the gh-pages branch if it doesn't exist yet."""
    existing = _git(["branch", "-a"], cwd=repo_dir)
    if branch in existing:
        return
    # Create orphan branch with a minimal index.html
    with tempfile.TemporaryDirectory() as tmpdir:
        wt = Path(tmpdir) / "init-wt"
        try:
            _git(["worktree", "add", "--orphan", "-b", branch, str(wt)], cwd=repo_dir)
            (wt / "index.html").write_text(
                "<html><body><p>JobRadar reports</p></body></html>",
                encoding="utf-8",
            )
            _git(["add", "index.html"], cwd=wt)
            _git(["commit", "-m", "chore: init gh-pages branch"], cwd=wt)
            _git(["push", "origin", branch], cwd=wt)
        finally:
            try:
                _git(["worktree", "remove", "--force", str(wt)], cwd=repo_dir)
            except Exception:
                pass


def _find_repo_root() -> Path | None:
    """Walk up from cwd looking for a .git directory."""
    here = Path.cwd()
    for parent in [here, *here.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def _git(args: list[str], *, cwd: Path) -> str:
    result = subprocess.run(
        ["git"] + args, cwd=cwd,
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed:\n{result.stderr.strip()}"
        )
    return result.stdout


def _parse_github_slug(remote_url: str) -> str | None:
    """Extract 'owner/repo' from https or ssh GitHub remote URLs."""
    import re
    m = re.search(r'github\.com[:/](.+?)(?:\.git)?$', remote_url)
    return m.group(1) if m else None
