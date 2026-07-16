#!/usr/bin/env python3
"""同步 Skill 仓库，并提交、推送报告与调试历史索引。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


DEFAULT_REMOTE = "公司仓库"
DEFAULT_REMOTE_URL = "http://16.16.16.226/Kzl/embedded-debug-workflow.git"
DEFAULT_BRANCH = "workflow/report-memory-sync"


class GitSyncError(RuntimeError):
    """Git 同步失败。"""


def run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise GitSyncError(f"git {' '.join(args)} 失败：{detail}")
    return result


def get_repo(skill_dir: Path) -> Path:
    repo = Path(run_git(skill_dir, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    expected = skill_dir.resolve()
    if repo != expected:
        raise GitSyncError(f"仓库根目录应为 {expected}，实际为 {repo}")
    return repo


def ref_exists(repo: Path, ref: str) -> bool:
    return run_git(repo, "show-ref", "--verify", "--quiet", ref, check=False).returncode == 0


def ensure_clean_for_checkout(repo: Path) -> None:
    if run_git(repo, "status", "--porcelain", "--untracked-files=no").stdout.strip():
        raise GitSyncError("仓库存在未提交的已跟踪文件改动，无法安全切换或更新分支")


def ensure_remote(repo: Path, remote: str, remote_url: str) -> None:
    current = run_git(repo, "remote", "get-url", remote, check=False)
    if current.returncode != 0:
        run_git(repo, "remote", "add", remote, remote_url)


def sync_repository(repo: Path, remote: str, remote_url: str, branch: str) -> dict[str, str]:
    ensure_clean_for_checkout(repo)
    ensure_remote(repo, remote, remote_url)
    run_git(repo, "fetch", remote, "--prune")
    local_ref = f"refs/heads/{branch}"
    remote_ref = f"refs/remotes/{remote}/{branch}"

    if ref_exists(repo, local_ref):
        run_git(repo, "checkout", branch)
    elif ref_exists(repo, remote_ref):
        run_git(repo, "checkout", "--track", "-b", branch, f"{remote}/{branch}")
    else:
        raise GitSyncError(f"远程分支 {remote}/{branch} 不存在，无法获取 Skill 根目录内容")

    run_git(repo, "pull", "--rebase", remote, branch)
    commit = run_git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
    return {"status": "synced", "branch": branch, "commit": commit, "remote": remote}


def publish_report(
    repo: Path, skill_dir: Path, report: Path, title: str, remote: str, branch: str
) -> dict[str, str]:
    current_branch = run_git(repo, "branch", "--show-current").stdout.strip()
    if current_branch != branch:
        raise GitSyncError(f"当前分支为 {current_branch or '分离 HEAD'}，必须先初始化并切换到 {branch}")

    report = report.resolve()
    data_dir = (skill_dir / "data").resolve()
    history = data_dir / "debug-history.yaml"
    try:
        report.relative_to(data_dir)
    except ValueError as exc:
        raise GitSyncError(f"报告必须位于记忆索引目录 {data_dir}") from exc
    if not report.is_file() or not history.is_file():
        raise GitSyncError("报告文件或 data/debug-history.yaml 不存在")

    staged = run_git(repo, "diff", "--cached", "--name-only").stdout.strip()
    if staged:
        raise GitSyncError(f"暂存区已有其他内容，请先处理后再发布：\n{staged}")

    run_git(repo, "fetch", remote, "--prune")
    remote_ref = f"refs/remotes/{remote}/{branch}"
    if ref_exists(repo, remote_ref):
        run_git(repo, "pull", "--rebase", "--autostash", remote, branch)

    report_rel = report.relative_to(repo).as_posix()
    history_rel = history.relative_to(repo).as_posix()
    run_git(repo, "add", "--", report_rel, history_rel)
    if not run_git(repo, "diff", "--cached", "--name-only").stdout.strip():
        raise GitSyncError("报告和记忆索引没有可提交的变更")

    safe_title = " ".join(title.split())[:50] or report.stem
    run_git(repo, "commit", "-m", f"docs(report): 添加{safe_title}调试报告")
    run_git(repo, "push", "-u", remote, branch)
    commit = run_git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
    return {
        "status": "published",
        "branch": branch,
        "commit": commit,
        "remote": remote,
        "report": str(report),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", default=DEFAULT_REMOTE)
    parser.add_argument("--remote-url", default=DEFAULT_REMOTE_URL)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--sync", action="store_true")
    actions.add_argument("--publish-report", type=Path, metavar="REPORT")
    parser.add_argument("--title", default="")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parent.parent
    try:
        repo = get_repo(skill_dir)
        result = (
            sync_repository(repo, args.remote, args.remote_url, args.branch)
            if args.sync
            else publish_report(repo, skill_dir, args.publish_report, args.title, args.remote, args.branch)
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except GitSyncError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())