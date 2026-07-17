#!/usr/bin/env python
"""按配置文件实际 projects 列表和逐项目模式执行编译、下载或串口监听。"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))

from config_reader import (
    get_keil_path,
    get_projects,
    get_serial_config,
    load_config,
    project_log_path,
    resolve_workspace_dir,
)
from path_config import PROJECT_RESULTS_FILENAME, STATE_DIR
from keil_build import build_project, find_uv4
from keil_flash import flash_project
from serial_monitor import monitor_serial

VALID_MODES = {"full", "compile_flash", "compile_only", "none"}


def parse_modes(raw: str, project_count: int) -> list[str]:
    modes = [item.strip() for item in raw.split(",") if item.strip()]
    if len(modes) != project_count:
        raise ValueError(
            f"模式数量({len(modes)})与配置项目数量({project_count})不一致"
        )
    invalid = [mode for mode in modes if mode not in VALID_MODES]
    if invalid:
        raise ValueError(f"无效模式: {', '.join(invalid)}")
    return modes


def selected_indices(action: str, modes: list[str]) -> list[int]:
    if action == "build":
        return [i for i, mode in enumerate(modes)
                if mode in {"full", "compile_flash", "compile_only"}]
    if action == "flash":
        return [i for i, mode in enumerate(modes) if mode in {"full", "compile_flash"}]
    return [i for i, mode in enumerate(modes) if mode == "full"]


def serial_log_path(
    base: str | None,
    config_dir: str,
    config: dict,
    index: int,
    name: str,
) -> str:
    """生成项目独立串口日志；``base`` 只提供日志类型和扩展名。"""
    base_path = Path(base) if base else Path("serial_log.txt")
    log_type = base_path.stem or "serial_log"
    suffix = base_path.suffix or ".txt"
    return str(project_log_path(
        config_dir, config, index, name, log_type, suffix
    ))


def write_project_results(
    config_dir: str,
    action: str,
    stage: str,
    results: list[dict],
) -> Path:
    """原子写出本次逐项目执行结果，供工作流引擎合并。"""
    config = load_config(config_dir)
    workspace = resolve_workspace_dir(config_dir, config)
    result_path = workspace / STATE_DIR / PROJECT_RESULTS_FILENAME
    result_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict = {"stages": {}}
    if result_path.is_file():
        try:
            existing = json.loads(result_path.read_text(encoding="utf-8"))
            if isinstance(existing.get("stages"), dict):
                payload = existing
        except (json.JSONDecodeError, OSError):
            pass
    previous_projects = {
        item.get("index"): item
        for item in payload["stages"].get(stage, {}).get("projects", [])
        if isinstance(item, dict) and isinstance(item.get("index"), int)
    }
    previous_projects.update({item["index"]: item for item in results})
    payload["latestStage"] = stage
    payload["stages"][stage] = {
        "action": action,
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "projects": [previous_projects[index] for index in sorted(previous_projects)],
    }
    tmp = result_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(result_path)
    return result_path


def successful_indices(config_dir: str, stage: str) -> set[int]:
    """读取同一阶段已成功的项目下标，用于失败重试时只执行失败项目。"""
    config = load_config(config_dir)
    workspace = resolve_workspace_dir(config_dir, config)
    result_path = workspace / STATE_DIR / PROJECT_RESULTS_FILENAME
    if not result_path.is_file():
        return set()
    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()
    return {
        item["index"]
        for item in payload.get("stages", {}).get(stage, {}).get("projects", [])
        if item.get("status") in {"success", "ok"}
        and isinstance(item.get("index"), int)
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="按逐项目模式执行嵌入式任务")
    parser.add_argument("--action", required=True, choices=["build", "flash", "serial"])
    parser.add_argument("--config-dir", required=True, help="工作区或配置文件路径")
    parser.add_argument("--modes", required=True,
                        help="与 projects 顺序一致的逗号分隔模式")
    parser.add_argument("--stage", default="",
                        help="写入逐项目状态时使用的流程阶段标识")
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--delay", type=float, default=0.0,
                        help="串口监听开始前的等待时间（秒），默认不等待")
    parser.add_argument("--save", help="串口日志基础路径；多项目自动附加项目标识")
    args = parser.parse_args()

    config = load_config(args.config_dir)
    projects = get_projects(config)
    if not projects:
        print("❌ 配置中的 projects 为空")
        sys.exit(1)

    try:
        modes = parse_modes(args.modes, len(projects))
    except ValueError as exc:
        print(f"❌ {exc}")
        sys.exit(1)

    stage = args.stage or args.action
    indices = selected_indices(args.action, modes)
    completed_indices = successful_indices(args.config_dir, stage)
    skipped_indices = [index for index in indices if index in completed_indices]
    indices = [index for index in indices if index not in completed_indices]
    if skipped_indices:
        print(f"ℹ️ stage={stage} 跳过已成功项目: {skipped_indices}")
    if not indices:
        print(f"ℹ️ action={args.action} 没有需要执行的项目，已跳过")
        write_project_results(args.config_dir, args.action,
                              stage, [])
        return

    uv4 = None
    if args.action in {"build", "flash"}:
        uv4 = find_uv4(config) or get_keil_path(config)
        if not uv4 or not Path(uv4).is_file():
            print("❌ 未找到 UV4.exe，请检查 keil.uv4_path")
            sys.exit(1)

    # 下载完成后给目标板预留稳定运行时间，再打开串口采集正式日志。
    if args.action == "serial" and args.delay > 0:
        print(f"⏳ 等待 {args.delay:g} 秒后开始串口监听...")
        time.sleep(args.delay)

    failures: list[str] = []
    project_results: list[dict] = []
    for index in indices:
        project = projects[index]
        name = str(project.get("name") or f"project{index + 1}")
        print(f"\n[{index}] {name} — mode={modes[index]} action={args.action}")

        if args.action in {"build", "flash"}:
            project_dir = str(project.get("dir", ""))
            project_file = str(project.get("file", ""))
            if not project_dir or not project_file:
                summary = "dir/file 未配置"
                failures.append(f"[{index}] {name}: {summary}")
                project_results.append({
                    "index": index, "name": name, "mode": modes[index],
                    "status": "failure", "summary": summary,
                })
                continue
            log_path = str(project_log_path(
                args.config_dir, config, index, name,
                "build_log" if args.action == "build" else "flash_log",
            ))
            result = (
                build_project(uv4, project_dir, project_file, log_file=log_path)
                if args.action == "build"
                else flash_project(uv4, project_dir, project_file, log_file=log_path)
            )
        else:
            serial = get_serial_config(config, index)
            save_path = serial_log_path(
                args.save, args.config_dir, config, index, name
            )
            result = monitor_serial(
                port=str(serial["port"]),
                baud=int(serial["baud"]),
                data_bits=int(serial["data_bits"]),
                stop_bits=float(serial["stop_bits"]),
                parity=str(serial["parity"]),
                duration=args.duration,
                save_path=save_path,
            )

        if result.get("status") not in {"success", "ok"}:
            failures.append(f"[{index}] {name}: {result.get('summary') or result.get('error') or '执行失败'}")
        project_results.append({
            "index": index,
            "name": name,
            "mode": modes[index],
            "status": result.get("status", "unknown"),
            "summary": result.get("summary") or result.get("error") or "",
            "artifact": (
                serial_log_path(args.save, args.config_dir, config, index, name)
                if args.action == "serial" else result.get("log_file", log_path)
            ),
        })

    result_path = write_project_results(
        args.config_dir, args.action, stage, project_results)
    print(f"[multi_project_runner] 逐项目结果: {result_path}")

    if failures:
        print("\n❌ 部分项目执行失败:")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)

    print(f"\n✅ {args.action} 已按逐项目模式执行完成")


if __name__ == "__main__":
    main()
