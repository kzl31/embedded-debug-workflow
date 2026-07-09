#!/usr/bin/env python
"""Keil MDK 命令行固件下载工具。

动态读取 data/config.json 获取 UV4 路径和工程参数。
内部调用 UV4.exe -f 命令执行 Flash 下载。

用法：
  python scripts/keil_flash.py                          # 下载第一个工程
  python scripts/keil_flash.py --project "RU3.uvprojx"  # 指定工程
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))
from config_reader import load_config, get_keil_path, get_first_project


def find_uv4(config: dict | None = None) -> str | None:
    """查找 UV4.exe（与 keil_build.py 保持一致的查找逻辑）。"""
    if config is None:
        config = load_config()
    uv4 = get_keil_path(config)
    if uv4 and Path(uv4).exists():
        return uv4
    import os
    keil_root = os.environ.get("KEIL_ROOT") or os.environ.get("MDK_ROOT")
    if keil_root:
        candidate = Path(keil_root) / "UV4" / "UV4.exe"
        if candidate.exists():
            return str(candidate)
    common_paths = [
        r"C:\Keil_v5\UV4\UV4.exe",
        r"C:\Keil\UV4\UV4.exe",
        r"D:\Keil_v5\UV4\UV4.exe",
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


def flash_project(
    uv4_path: str,
    project_dir: str,
    project_file: str,
    log_file: str | None = None,
) -> dict:
    """执行固件下载，返回结果字典。"""
    proj_dir = Path(project_dir)
    if not proj_dir.exists():
        return {
            "status": "failure",
            "summary": f"工程目录不存在: {project_dir}",
        }

    log_path = log_file or str(_logs_dir(proj_dir) / "flash_log.txt")
    cmd = f'"{uv4_path}" -f "{project_file}" -o "{log_path}"'

    print(f"[keil_flash] 🔥 下载固件: {project_file}")
    print(f"[keil_flash]   命令: {cmd}")

    try:
        result = subprocess.run(
            cmd, cwd=project_dir, shell=True, capture_output=True, text=True, timeout=120
        )
    except subprocess.TimeoutExpired:
        return {"status": "failure", "summary": "下载超时（>120s）"}

    # 读取日志
    log_content = ""
    if Path(log_path).exists():
        log_content = Path(log_path).read_text(encoding="utf-8", errors="replace")

    # 判断结果
    has_error = "error" in log_content.lower() or result.returncode != 0
    status = "success" if not has_error else "failure"

    # 提取关键信息
    summary_parts = []
    for line in log_content.split("\n"):
        low = line.lower()
        if "download" in low:
            summary_parts.append(line.strip())
        if "verify" in low and ("ok" in low or "success" in low):
            summary_parts.append(line.strip())
        if "error" in low:
            summary_parts.append(line.strip())

    result_dict = {
        "status": status,
        "summary": "; ".join(summary_parts[:5]) or ("下载成功" if status == "success" else "下载失败"),
        "project_file": project_file,
        "return_code": result.returncode,
        "flash_cmd": cmd,
    }

    # 检查日志中是否有校验信息
    if "verify" in log_content.lower() and ("ok" in log_content.lower() or "success" in log_content.lower()):
        result_dict["verified"] = True
    else:
        result_dict["verified"] = False

    print(f"[keil_flash] {'✅ 下载成功' if status == 'success' else '❌ 下载失败'}")
    if result_dict["verified"]:
        print("[keil_flash]   ✅ 校验通过")

    return result_dict


def main() -> None:
    parser = argparse.ArgumentParser(description="Keil 固件下载工具")
    parser.add_argument("--project", help="工程文件名（默认读取配置第一个工程）")
    parser.add_argument("--dir", help="工程目录（默认读取配置）")
    parser.add_argument("--log", help="下载日志保存路径")
    parser.add_argument("--config-dir", help="配置文件所在目录（默认自动查找）")
    args = parser.parse_args()

    config = load_config(args.config_dir)

    uv4 = find_uv4(config)
    if not uv4:
        print("❌ 未找到 UV4.exe，请配置 keil.uv4_path")
        print("   运行: python scripts/config_reader.py --collect")
        sys.exit(1)

    project_file = args.project
    project_dir = args.dir

    if not project_file or not project_dir:
        proj = get_first_project(config)
        if not proj:
            print("❌ config.json 中未配置工程信息")
            sys.exit(1)
        project_file = project_file or proj["file"]
        project_dir = project_dir or proj["dir"]

    result = flash_project(
        uv4_path=uv4,
        project_dir=project_dir,
        project_file=project_file,
        log_file=args.log,
    )

    if result["status"] == "failure":
        sys.exit(1)


if __name__ == "__main__":
    main()
