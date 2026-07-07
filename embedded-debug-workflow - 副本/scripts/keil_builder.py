#!/usr/bin/env python3
"""
Keil 编译/下载工具
读取 config.json 获取工程配置，调用 Keil UV4 命令行进行编译和下载。

用法:
    python keil_builder.py --project RU3 --action build      # 只编译
    python keil_builder.py --project RU3 --action flash      # 只下载
    python keil_builder.py --project RU3 --action both       # 编译+下载
    python keil_builder.py --list                            # 列出所有工程
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def load_config(config_path="config.json") -> dict:
    """加载配置文件"""
    cfg_file = Path(__file__).parent / config_path
    if not cfg_file.exists():
        print(json.dumps({"status": "error", "message": f"配置文件不存在: {cfg_file}"}))
        sys.exit(1)
    with open(cfg_file, "r", encoding="utf-8") as f:
        return json.load(f)


def find_project(config: dict, name: str) -> dict | None:
    """按名称查找工程"""
    for proj in config.get("keil", {}).get("projects", []):
        if proj["name"].lower() == name.lower():
            return proj
    return None


def list_projects(config: dict):
    """列出所有工程"""
    projects = config.get("keil", {}).get("projects", [])
    print(json.dumps({"status": "ok", "projects": [p["name"] for p in projects]}))


def run_keil(uv4_path: str, project_path: str, project_file: str, action: str) -> dict:
    """运行 Keil UV4 命令行"""
    log_file = f"{action}_log.txt"
    flag = "-b" if action == "build" else "-f"
    if action == "both":
        # 先编译再下载
        cmd_build = [
            uv4_path, "-b", project_file, "-o", f"build_{log_file}"
        ]
        cmd_flash = [
            uv4_path, "-f", project_file, "-o", f"flash_{log_file}"
        ]

        try:
            result_build = subprocess.run(
                cmd_build, cwd=project_path, capture_output=True, text=True, timeout=120
            )
            if result_build.returncode != 0:
                return {
                    "status": "error",
                    "stage": "build",
                    "returncode": result_build.returncode,
                    "stdout": result_build.stdout[-500:],
                    "stderr": result_build.stderr[-500:],
                }

            result_flash = subprocess.run(
                cmd_flash, cwd=project_path, capture_output=True, text=True, timeout=60
            )
            return {
                "status": "success" if result_flash.returncode == 0 else "error",
                "stage": "flash" if result_flash.returncode != 0 else "done",
                "returncode": result_flash.returncode,
                "stdout": result_flash.stdout[-500:],
                "stderr": result_flash.stderr[-500:],
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "stage": action, "message": "执行超时"}
        except FileNotFoundError:
            return {"status": "error", "message": f"UV4 未找到: {uv4_path}"}

    # 单个操作
    try:
        result = subprocess.run(
            [uv4_path, flag, project_file, "-o", log_file],
            cwd=project_path, capture_output=True, text=True, timeout=120
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "action": action,
            "returncode": result.returncode,
            "stdout": result.stdout[-500:],
            "stderr": result.stderr[-500:],
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "action": action, "message": "执行超时"}
    except FileNotFoundError:
        return {"status": "error", "message": f"UV4 未找到: {uv4_path}"}


def main():
    parser = argparse.ArgumentParser(description="Keil 编译/下载工具")
    parser.add_argument("--project", "-p", type=str, help="工程名称")
    parser.add_argument("--action", "-a", type=str,
                        choices=["build", "flash", "both"], default="both",
                        help="操作类型: build=编译, flash=下载, both=编译+下载")
    parser.add_argument("--list", action="store_true", help="列出所有工程")
    args = parser.parse_args()

    config = load_config()

    if args.list:
        list_projects(config)
        return

    if not args.project:
        print(json.dumps({"status": "error", "message": "请指定 --project 参数"}))
        sys.exit(1)

    project = find_project(config, args.project)
    if not project:
        print(json.dumps({
            "status": "error",
            "message": f"未找到工程 '{args.project}'，可用: {[p['name'] for p in config.get('keil', {}).get('projects', [])]}"
        }))
        sys.exit(1)

    uv4_path = config.get("keil", {}).get("uv4_path", "")
    project_path = project["path"]
    project_file = project["file"]

    if not os.path.exists(project_path):
        print(json.dumps({"status": "error", "message": f"工程路径不存在: {project_path}"}))
        sys.exit(1)

    result = run_keil(uv4_path, project_path, project_file, args.action)
    print(json.dumps(result, ensure_ascii=False))

    if result.get("status") == "error":
        sys.exit(1)


if __name__ == "__main__":
    main()
