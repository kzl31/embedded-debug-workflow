#!/usr/bin/env python
"""回归核对清单（脚本化 check_regression）— 确定性检查。

确定性检查（脚本判定，失败则整体失败）：
  1. config_reader --validate 通过（keil/projects/serial/debugger 齐全）
  2. 各工程 build_log 0 Error（无阻塞性 warning）
  3. 各 flash 工程 flash_log 含 Flash Load finished / Verify OK
  4. 各 full 工程 verify_log 已生成
  5. CHESHI 符号已整段清理（源码 grep）

AI 复核项（脚本只标记，不判失败）：
  - 业务修改仅影响目标模块，无连锁副作用
  - 原故障现象消失，其它模块正常
  - 调试打印信息充分，可支撑故障定位
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from config_reader import get_projects, load_config, validate_config  # noqa: E402
from path_config import project_log_path  # noqa: E402

ERROR_RE = re.compile(r"(\d+)\s+Error\(s\)", re.IGNORECASE)
WARNING_RE = re.compile(r"(\d+)\s+Warning\(s\)", re.IGNORECASE)
CHESHI_SYMBOL_RE = re.compile(
    r"\b(CHESHI|Debug_Flush|Debug_Capture|g_dbg_buf|DBG_BUF_SIZE|g_dbg_wr|g_dbg_rd)\b"
)
EXCLUDE_DIRS = {
    ".git", ".copilot", "__pycache__", "node_modules", "Objects", "Listings",
    "Debug", "Release", "RTE", "build", ".embedded-debug-workflow", ".test-terminator",
}
SOURCE_EXTS = {".c", ".h", ".cpp", ".hpp", ".s", ".asm"}


def parse_build_errors(log_path: Path) -> tuple[int, bool]:
    if not log_path.is_file():
        return 0, False
    text = log_path.read_text(encoding="utf-8", errors="replace")
    matches = ERROR_RE.findall(text)
    if not matches:
        has_error_kw = bool(re.search(r"\berror\b\s*[:)]", text, re.IGNORECASE))
        return (1 if has_error_kw else 0), True
    last = int(matches[-1])
    return last, last > 0


def check_build_logs(config, config_dir) -> list[dict]:
    checks = []
    for idx, proj in enumerate(config.get("projects", [])):
        name = str(proj.get("name") or f"project{idx + 1}")
        log = project_log_path(config_dir, config, idx, name, "build_log")
        if not log.is_file():
            checks.append({"item": f"[{idx}]{name} 构建日志", "pass": False,
                           "detail": "日志不存在（可能未编译）"})
            continue
        errs, bad = parse_build_errors(log)
        warning_match = WARNING_RE.findall(log.read_text(encoding="utf-8", errors="replace"))
        warnings = int(warning_match[-1]) if warning_match else None
        checks.append({"item": f"[{idx}]{name} 构建 0 Error", "pass": not bad,
                   "detail": f"Error(s)={errs}; Warning(s)={warnings if warnings is not None else '未知'}"})
    return checks


def check_flash_logs(config, config_dir) -> list[dict]:
    checks = []
    modes = config.get("project_modes", [])
    for idx, proj in enumerate(config.get("projects", [])):
        mode = modes[idx] if idx < len(modes) else "none"
        if mode not in {"full", "compile_flash"}:
            continue
        name = str(proj.get("name") or f"project{idx + 1}")
        log = project_log_path(config_dir, config, idx, name, "flash_log")
        if not log.is_file():
            checks.append({"item": f"[{idx}]{name} 下载日志", "pass": False,
                           "detail": "日志不存在"})
            continue
        text = log.read_text(encoding="utf-8", errors="replace")
        ok = ("Flash Load finished" in text) and ("Verify OK" in text)
        checks.append({"item": f"[{idx}]{name} 下载成功", "pass": ok,
                       "detail": "Flash Load finished/Verify OK" if ok else "缺失成功标志"})
    return checks


def check_verify_logs(config, config_dir) -> list[dict]:
    checks = []
    modes = config.get("project_modes", [])
    for idx, proj in enumerate(config.get("projects", [])):
        mode = modes[idx] if idx < len(modes) else "none"
        if mode != "full":
            continue
        name = str(proj.get("name") or f"project{idx + 1}")
        log = project_log_path(config_dir, config, idx, name, "verify_log")
        checks.append({"item": f"[{idx}]{name} 验证日志", "pass": log.is_file(),
                       "detail": str(log) if log.is_file() else "未生成"})
    return checks


def check_cheshi_clean(config, config_dir) -> list[dict]:
    residual_files: list[str] = []
    for proj in config.get("projects", []):
        pdir = proj.get("dir")
        if not pdir or not Path(pdir).is_dir():
            continue
        for current, dirs, names in os.walk(Path(pdir)):
            dirs[:] = [d for d in dirs if d.lower() not in EXCLUDE_DIRS]
            for name in names:
                if Path(name).suffix.lower() in SOURCE_EXTS:
                    f = Path(current) / name
                    try:
                        t = f.read_text(encoding="utf-8")
                    except OSError:
                        continue
                    except UnicodeDecodeError:
                        residual_files.append(f"{f} (非 UTF-8，无法确认清理状态)")
                        continue
                    if CHESHI_SYMBOL_RE.search(t):
                        residual_files.append(str(f))
    return [{"item": "CHESHI 代码已整段清理", "pass": not residual_files,
             "detail": "；".join(residual_files) if residual_files else "无残留"}]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    parser = argparse.ArgumentParser(description="嵌入式回归核对")
    parser.add_argument("--config-dir", required=True)
    args = parser.parse_args()

    config = load_config(args.config_dir)
    all_checks: list[dict] = []
    errors = validate_config(config)
    all_checks.append({"item": "配置完整(keil/projects/serial/debugger)",
                       "pass": not errors, "detail": "；".join(errors) if errors else "配置完整"})
    all_checks += check_build_logs(config, args.config_dir)
    all_checks += check_flash_logs(config, args.config_dir)
    all_checks += check_verify_logs(config, args.config_dir)
    all_checks += check_cheshi_clean(config, args.config_dir)

    failed = [c for c in all_checks if c["pass"] is False]
    result = {
        "status": "failed" if failed else "passed",
        "checks": all_checks,
        "ai_review_needed": [
            "业务修改仅影响目标模块，无连锁副作用（长度/偏移/缓冲区边界已复核）",
            "原故障现象消失，其它模块（通信/定时器/中断/外设）正常",
            "调试打印信息充分，可支撑故障定位",
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
