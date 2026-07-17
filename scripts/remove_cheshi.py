#!/usr/bin/env python
"""清理本次调试新增的全部 CHESHI 临时代码（脚本化 remove_cheshi）。

顺序：
  1. 读取配置，获取各工程源码目录。
    2. 不自动暂存或提交用户改动；调用方应在需要时自行建立回退点。
  3. 扫描所有 .c/.h 源文件，移除 CHESHI 条件编译块与宏定义/横幅注释。
  4. 校验无残留 CHESHI 符号。
  5. 输出 JSON 状态，退出码 0=清理成功 / 2=存在残留需处理。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from config_reader import get_projects, load_config  # noqa: E402

CHESHI_GUARD_RE = re.compile(r"^\s*#\s*(?:if|ifdef|ifndef)\b.*\bCHESHI\b", re.IGNORECASE)
CHESHI_DEFINE_RE = re.compile(r"^\s*#\s*define\s+CHESHI\b")
ENDIF_RE = re.compile(r"^\s*#\s*endif\b")
IF_RE = re.compile(r"^\s*#\s*(?:if|ifdef|ifndef)\b")
BANNER_RE = re.compile(r"临时调试宏|上线完整删除|仅调试阶段启用", re.IGNORECASE)
RESIDUAL_RE = re.compile(
    r"\b(CHESHI|Debug_Flush|Debug_Capture|g_dbg_buf|DBG_BUF_SIZE|g_dbg_wr|g_dbg_rd)\b"
)

EXCLUDE_DIRS = {
    ".git", ".copilot", "__pycache__", "node_modules", "Objects",
    "Listings", "Debug", "Release", "RTE", "build", ".embedded-debug-workflow",
    ".test-terminator", "settings",
}
SOURCE_EXTS = {".c", ".h", ".cpp", ".hpp", ".s", ".asm"}


def git_commit_baseline(repo_hint: str) -> None:
    """保留兼容入口，但绝不操作用户的暂存区或提交历史。"""
    print("ℹ️ 跳过自动 Git 基线；清理前请由调用方自行保存可回退副本")


def strip_cheshi(text: str) -> tuple[str, int, int, bool]:
    """返回 (清理后文本, 移除块数, 移除define数, 需要人工处理)。"""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    in_removal = False
    depth = 0
    removed_blocks = 0
    removed_defines = 0
    needs_review = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not in_removal:
            # 横幅块注释（含“临时调试宏”等字样，可能跨多行）
            if "/*" in line:
                if "*/" in line:
                    if BANNER_RE.search(line):
                        i += 1
                        continue
                    out.append(line)
                    i += 1
                    continue
                # 多行注释：收集到 */ 为止，整体判断是否含横幅关键字
                end = i
                while end < len(lines) and "*/" not in lines[end]:
                    end += 1
                if end < len(lines):
                    block = "".join(lines[i:end + 1])
                    if BANNER_RE.search(block):
                        i = end + 1
                        continue
                    for k in range(i, end + 1):
                        out.append(lines[k])
                    i = end + 1
                else:
                    for k in range(i, len(lines)):
                        out.append(lines[k])
                    i = len(lines)
                continue
            if CHESHI_DEFINE_RE.match(stripped):
                needs_review = True
                out.append(line)
                i += 1
                continue
            if CHESHI_GUARD_RE.match(stripped):
                end = i + 1
                depth = 1
                has_else = False
                while end < len(lines) and depth:
                    candidate = lines[end].strip()
                    if IF_RE.match(candidate):
                        depth += 1
                    elif ENDIF_RE.match(candidate):
                        depth -= 1
                    elif depth == 1 and re.match(r"^#\s*(?:else|elif)\b", candidate):
                        has_else = True
                    end += 1
                if depth != 0 or has_else:
                    needs_review = True
                    out.extend(lines[i:end])
                    i = end
                    continue
                # 没有本次插入块的登记/哈希时，无法区分历史调试代码与本次代码。
                # 保留整块并要求人工处理，避免不可逆误删。
                needs_review = True
                out.extend(lines[i:end])
                i = end
                continue
            out.append(line)
            i += 1
        else:
            if IF_RE.match(stripped):
                depth += 1
            elif ENDIF_RE.match(stripped):
                depth -= 1
                if depth <= 0:
                    in_removal = False
            i += 1
    return "".join(out), removed_blocks, removed_defines, needs_review


def collect_sources(project_dir: str) -> list[Path]:
    root = Path(project_dir).resolve()
    files: list[Path] = []
    for current, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d.lower() not in EXCLUDE_DIRS]
        for name in names:
            if Path(name).suffix.lower() in SOURCE_EXTS:
                files.append(Path(current) / name)
    return files


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    parser = argparse.ArgumentParser(description="CHESHI 临时代码清理")
    parser.add_argument("--config-dir", required=True)
    args = parser.parse_args()

    config = load_config(args.config_dir)
    projects = get_projects(config)
    if not projects:
        print(json.dumps({"status": "failed", "error": "配置中无工程"}, ensure_ascii=False))
        return 2

    removed_blocks = 0
    removed_defines = 0
    modified_files: list[str] = []
    residual: list[str] = []

    for proj in projects:
        pdir = proj.get("dir")
        if not pdir or not Path(pdir).is_dir():
            continue
        git_commit_baseline(pdir)
        for src in collect_sources(pdir):
            try:
                text = src.read_text(encoding="utf-8")
            except OSError:
                continue
            except UnicodeDecodeError:
                residual.append(f"{src} (非 UTF-8，未修改)")
                continue
            new_text, b, d, review = strip_cheshi(text)
            if review:
                residual.append(f"{src} (含 #else/#elif 或未闭合 CHESHI 块，需人工处理)")
                continue
            if b or d:
                src.write_text(new_text, encoding="utf-8")
                removed_blocks += b
                removed_defines += d
                modified_files.append(str(src))
            if RESIDUAL_RE.search(new_text):
                residual.append(str(src))

    result = {
        "status": "failed" if residual else "passed",
        "removedBlocks": removed_blocks,
        "removedDefines": removed_defines,
        "modifiedFiles": modified_files,
        "residual": residual,
        "note": "Keil 工程配置(Define/Include Path/源文件)若由 AI 在插入时记录，请按记录恢复；"
                "本脚本仅清理源码块。若 CHESHI 仅由 Keil Define 开启，源码块移除后无引用，宏可保留无害。",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if residual else 0


if __name__ == "__main__":
    raise SystemExit(main())
