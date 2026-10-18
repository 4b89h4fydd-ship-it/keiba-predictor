"""Git rebase auto-stash preserves uncommitted collection inputs and archive writes."""
import subprocess
from pathlib import Path


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()


def test_prefetch_archive_rebase_preserves_unstaged_workfiles(tmp_path):
    remote = tmp_path / "remote.git"
    remote.mkdir()
    git(remote, "init", "--bare")
    one = tmp_path / "one"
    two = tmp_path / "two"
    git(tmp_path, "clone", str(remote), str(one))
    git(one, "config", "user.name", "test")
    git(one, "config", "user.email", "test@example.invalid")
    (one / "runtime.txt").write_text("original\n")
    (one / "archive.json").write_text("original\n")
    git(one, "add", ".")
    git(one, "commit", "-m", "initial")
    git(one, "push", "origin", "HEAD:main")
    git(tmp_path, "clone", "--branch", "main", str(remote), str(two))
    git(two, "config", "user.name", "other")
    git(two, "config", "user.email", "other@example.invalid")
    (two / "other.txt").write_text("new upstream record\n")
    git(two, "add", "other.txt")
    git(two, "commit", "-m", "unrelated concurrent commit")
    git(two, "push", "origin", "main")

    # A long-running prefetch leaves unrelated tracked files dirty.
    (one / "runtime.txt").write_text("unsaved collector intermediate\n")
    (one / "archive.json").write_text("verified frozen facts\n")
    git(one, "add", "archive.json")
    git(one, "commit", "-m", "preserve pre-off archive")
    git(one, "-c", "rebase.autoStash=true", "pull", "--rebase", "origin", "main")
    assert (one / "runtime.txt").read_text() == "unsaved collector intermediate\n"
    assert (one / "other.txt").read_text() == "new upstream record\n"
    git(one, "push", "origin", "HEAD:main")
    assert git(two, "fetch", "origin", "main") is not None
    assert git(two, "show", "origin/main:archive.json") == "verified frozen facts"


def test_prefetch_workflow_enables_autostash_and_retains_audit_steps():
    data=Path(".github/workflows/arvexq-prefetch.yml").read_text()
    assert "git -c rebase.autoStash=true pull --rebase origin main" in data
    assert "D1_STORED_EVIDENCE_VERIFIED" in data
    assert "git push origin HEAD:main" in data
