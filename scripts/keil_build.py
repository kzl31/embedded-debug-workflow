#!/usr/bin/env python
"""Keil MDK 命令行编译工具。

动态读取 data/config.json 获取 UV4 路径和工程参数，无需硬编码。
支持单工程编译、指定 Target、编译日志提取。

用法：
  python scripts/keil_build.py                              # 编译第一个工程
  python scripts/keil_build.py --project "RU3.uvprojx"      # 指定工程文件
  python scripts/keil_build.py --target "Release"           # 指定 Target
  python scripts/keil_build.py --rebuild                    # 重新编译（先 Clean）
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# 引入 config_reader
_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))
from config_reader import load_config, get_keil_path, get_project


def find_uv4(config: dict | None = None) -> str | None:
    """查找 UV4.exe，优先级：配置 > 环境变量 > 常见路径。"""
    if config is None:
        config = load_config()

    # 1. 配置文件
    uv4 = get_keil_path(config)
    if uv4 and Path(uv4).exists():
        return uv4

    # 2. 环境变量
    keil_root = os.environ.get("KEIL_ROOT") or os.environ.get("MDK_ROOT")
    if keil_root:
        candidate = Path(keil_root) / "UV4" / "UV4.exe"
        if candidate.exists():
            return str(candidate)

    # 3. 常见路径
    common_paths = [
        r"C:\Keil_v5\UV4\UV4.exe",
        r"C:\Keil\UV4\UV4.exe",
        r"D:\Keil_v5\UV4\UV4.exe",
        r"D:\Keil\UV4\UV4.exe",
    ]
    for p in common_paths:
        if Path(p).exists():
            return p

    return None


def _logs_dir(proj_dir: Path) -> Path:
    """定位 <workspace>/.copilot/logs：从工程目录向上查找含 .copilot 的目录。"""
    p = proj_dir.resolve()
    for cand in [p, *p.parents]:
        if (cand / ".copilot").is_dir():
            return cand / ".copilot" / "logs"
    return p.parent / ".copilot" / "logs"


def build_project(
    uv4_path: str,
    project_dir: str,
    project_file: str,
    target: str | None = None,
    rebuild: bool = False,
    log_file: str | None = None,
) -> dict:
    """执行 Keil 编译，返回结果字典。

    UV4 的 ``-o`` 参数会在编译过程中写入日志文件。直接等待编译进程
    结束，不设置总编译时限；若日志连续 3 分钟没有新增内容，则认为
    编译卡死/失败并终止 UV4。
    """
    proj_dir = Path(project_dir)
    if not proj_dir.exists():
        return {
            "status": "failure",
            "summary": f"工程目录不存在: {project_dir}",
            "errors": 1,
            "warnings": 0,
        }

    # 构建命令
    log_path = log_file or str(_logs_dir(proj_dir) / "build_log.txt")
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    # 每次编译使用空日志，避免上一次残留内容被误判为本次实时输出。
    Path(log_path).write_text("", encoding="utf-8")
    if rebuild:
        cmd = f'"{uv4_path}" -r "{project_file}" -o "{log_path}"'
    else:
        cmd = f'"{uv4_path}" -b "{project_file}" -o "{log_path}"'
    if target:
        cmd += f' -t "{target}"'

    print(f"[keil_build] 🔨 编译: {project_file}")
    print(f"[keil_build]   命令: {cmd}")

    # 日志无输出看门狗：用于识别 UV4 启动后卡死、等待不可见对话框等情况。
    idle_timeout = 180.0
    start_time = time.monotonic()
    last_output_time = start_time
    previous_log_state: tuple[int, int] | None = None
    timed_out = False

    try:
        # 不捕获 stdout/stderr，避免子进程输出管道满后阻塞；编译详情以 -o 日志为准。
        process = subprocess.Popen(
            cmd,
            cwd=project_dir,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        while process.poll() is None:
            now = time.monotonic()
            try:
                stat = Path(log_path).stat()
                log_state = (stat.st_size, stat.st_mtime_ns)
            except FileNotFoundError:
                log_state = None

            if log_state != previous_log_state:
                previous_log_state = log_state
                last_output_time = now
                if log_state:
                    print(
                        f"[keil_build]   编译日志已更新: {log_state[0]} bytes",
                        flush=True,
                    )

            if now - last_output_time >= idle_timeout:
                timed_out = True
                print(
                    f"[keil_build] ❌ 编译连续 {int(idle_timeout)} 秒无日志输出，判定失败",
                    flush=True,
                )
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                break
            time.sleep(0.5)

        return_code = process.returncode
    except OSError as exc:
        return {
            "status": "failure",
            "summary": f"无法启动编译进程: {exc}",
            "errors": 1,
            "warnings": 0,
        }

    # 读取编译日志
    log_content = ""
    if Path(log_path).exists():
        log_content = Path(log_path).read_text(encoding="utf-8", errors="replace")

    # 解析错误/警告数
    errors = 0
    warnings = 0
    error_lines: list[str] = []
    for line in log_content.split("\n"):
        lower = line.lower()
        if "error:" in lower or "error(" in lower:
            if "0 error" not in lower and "0 error(s)" not in lower:
                errors += 1
                error_lines.append(line.strip())
        if "warning:" in lower:
            warnings += 1

    # 提取编译结果摘要行
    summary_line = ""
    for line in log_content.split("\n"):
        if "0 error" in line.lower() or "0 warning" in line.lower():
            summary_line = line.strip()
            break

    # 必须同时满足：进程正常退出、没有错误、没有被无输出看门狗终止。
    status = "success" if return_code == 0 and errors == 0 and not timed_out else "failure"

    result_dict = {
        "status": status,
        "summary": summary_line or f"错误: {errors}  警告: {warnings}",
        "project_file": project_file,
        "target_name": target or "默认",
        "errors": errors,
        "warnings": warnings,
        "build_cmd": cmd,
        "return_code": return_code,
    }

    if errors > 0:
        result_dict["error_lines"] = error_lines[:20]  # 最多前20条错误

    if timed_out and not summary_line:
        result_dict["summary"] = "编译失败：日志连续180秒无新增输出"
    elif return_code != 0 and not summary_line:
        result_dict["summary"] = f"编译进程异常退出，返回码: {return_code}"

    # 提取固件大小
    size_pattern = re.compile(r"Program Size:\s*Code=\s*(\d+)\s+RO-data=\s*(\d+)\s+RW-data=\s*(\d+)\s+ZI-data=\s*(\d+)")
    for line in log_content.split("\n"):
        m = size_pattern.search(line)
        if m:
            result_dict["program_size"] = {
                "code": int(m.group(1)),
                "ro_data": int(m.group(2)),
                "rw_data": int(m.group(3)),
                "zi_data": int(m.group(4)),
                "total_flash": int(m.group(1)) + int(m.group(2)) + int(m.group(3)),
                "total_ram": int(m.group(3)) + int(m.group(4)),
            }
            break

    print(f"[keil_build] {'✅ 编译成功' if status == 'success' else '❌ 编译失败'}")
    print(f"[keil_build]   结果: {result_dict['summary']}")
    if result_dict.get("program_size"):
        ps = result_dict["program_size"]
        print(f"[keil_build]   Flash: ~{ps['total_flash']} bytes  RAM: ~{ps['total_ram']} bytes")

    return result_dict


def main() -> None:
    parser = argparse.ArgumentParser(description="Keil 编译工具")
    parser.add_argument("--project", help="工程文件名（默认读取配置第一个工程）")
    parser.add_argument("--dir", help="工程目录（默认读取配置）")
    parser.add_argument("--target", help="指定 Target 名称")
    parser.add_argument("--rebuild", action="store_true", help="重新编译（Clean + Build）")
    parser.add_argument("--log", help="编译日志保存路径")
    parser.add_argument("--find-uv4", action="store_true", help="仅探测 UV4 路径并退出")
    parser.add_argument("--config-dir", help="配置文件所在目录（默认自动查找）")
    parser.add_argument("--project-index", type=int, default=0,
                        help="使用配置中的工程下标（默认 0）")
    args = parser.parse_args()

    # 仅探测 UV4
    if args.find_uv4:
        uv4 = find_uv4()
        if uv4:
            print(uv4)
        else:
            print("❌ 未找到 UV4.exe")
            sys.exit(1)
        return

    config = load_config(args.config_dir)

    # 检查 UV4
    uv4 = find_uv4(config)
    if not uv4:
        print("❌ 未找到 UV4.exe，请配置 keil.uv4_path")
        print("   运行: python scripts/config_reader.py --collect")
        sys.exit(1)

    # 确定工程参数
    project_file = args.project
    project_dir = args.dir

    if project_file and not project_dir:
        # --project 是带路径的文件名 → 自动提取目录
        p = Path(project_file)
        if p.parent.name:
            project_dir = str(p.parent.resolve())
            project_file = p.name
        # 否则 project_file 只是文件名，仍需要从配置或 --dir 获取目录

    if not project_file or not project_dir:
        proj = get_project(config, args.project_index)
        if not proj:
            print(f"❌ 未找到工程[{args.project_index}]信息，请提供:")
            print("   python keil_build.py --dir <工程目录> --project <工程文件>")
            print("   或使用 --config-dir 指定项目根目录（内需含 embedded-debug-config.json）")
            sys.exit(1)
        project_file = project_file or proj["file"]
        project_dir = project_dir or proj["dir"]

    # 执行编译
    result = build_project(
        uv4_path=uv4,
        project_dir=project_dir,
        project_file=project_file,
        target=args.target,
        rebuild=args.rebuild,
        log_file=args.log,
    )

    if result["status"] == "failure":
        sys.exit(1)


if __name__ == "__main__":
    main()
