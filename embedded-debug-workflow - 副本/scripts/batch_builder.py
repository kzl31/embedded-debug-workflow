#!/usr/bin/env python3
"""
批量编译下载工具
按 config.json 配置顺序，批量编译下载多个工程。

用法:
    python batch_builder.py                              # 编译下载所有工程
    python batch_builder.py --projects RU2,RU3           # 编译下载指定工程
    python batch_builder.py --action build               # 只编译，不下载
"""

import argparse
import json
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


def run_single(uv4_path: str, project_path: str, project_file: str,
               action: str) -> dict:
    """执行单个工程的编译或下载"""
    flag = "-b" if action == "build" else "-f"
    log_name = f"{action}_batch_log.txt"

    try:
        result = subprocess.run(
            [uv4_path, flag, project_file, "-o", log_name],
            cwd=project_path, capture_output=True, text=True, timeout=120
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "action": action,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "action": action, "message": "超时"}
    except FileNotFoundError:
        return {"status": "error", "message": f"UV4 未找到: {uv4_path}"}


def main():
    parser = argparse.ArgumentParser(description="批量编译下载工具")
    parser.add_argument("--projects", "-p", type=str, default=None,
                        help="工程名称列表，逗号分隔（默认全部）")
    parser.add_argument("--action", "-a", type=str,
                        choices=["build", "flash", "both"], default="both",
                        help="操作类型: build=编译, flash=下载, both=编译+下载")
    args = parser.parse_args()

    config = load_config()
    projects = config.get("keil", {}).get("projects", [])
    uv4_path = config.get("keil", {}).get("uv4_path", "")

    # 过滤工程
    if args.projects:
        names = [n.strip() for n in args.projects.split(",")]
        projects = [p for p in projects if p["name"] in names]

    if not projects:
        print(json.dumps({"status": "error", "message": "没有需要处理的工程"}))
        sys.exit(1)

    results = []
    for proj in projects:
        print(f"=== 处理: {proj['name']} ===")

        if args.action in ("build", "both"):
            r = run_single(uv4_path, proj["path"], proj["file"], "build")
            results.append({**proj, "action": "build", **r})
            if r["status"] == "error":
                print(f"  ❌ 编译失败: {proj['name']}")
                continue
            print(f"  ✅ 编译成功: {proj['name']}")

        if args.action in ("flash", "both"):
            r = run_single(uv4_path, proj["path"], proj["file"], "flash")
            results.append({**proj, "action": "flash", **r})
            if r["status"] == "error":
                print(f"  ❌ 下载失败: {proj['name']}")
                continue
            print(f"  ✅ 下载成功: {proj['name']}")

    # 输出汇总
    print("\n=== 批量结果汇总 ===")
    success = all(r["status"] == "success" for r in results)
    print(json.dumps({"status": "success" if success else "partial",
                       "results": results}, ensure_ascii=False))

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
