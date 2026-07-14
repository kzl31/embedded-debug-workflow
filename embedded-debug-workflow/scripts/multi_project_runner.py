#!/usr/bin/env python
"""按配置文件实际 projects 列表和逐项目模式执行编译、下载或串口监听。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))

from config_reader import get_keil_path, get_projects, get_serial_config, load_config
from keil_build import build_project, find_uv4
from keil_flash import flash_project
from serial_monitor import monitor_serial

VALID_MODES = {"full", "compile_only", "none"}


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
        return [i for i, mode in enumerate(modes) if mode in {"full", "compile_only"}]
    return [i for i, mode in enumerate(modes) if mode == "full"]


def project_log_path(base: str | None, index: int, name: str) -> str | None:
    if not base:
        return None
    path = Path(base)
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    return str(path.with_name(f"{path.stem}_p{index}_{safe_name}{path.suffix}"))


def main() -> None:
    parser = argparse.ArgumentParser(description="按逐项目模式执行嵌入式任务")
    parser.add_argument("--action", required=True, choices=["build", "flash", "serial"])
    parser.add_argument("--config-dir", required=True, help="工作区或配置文件路径")
    parser.add_argument("--modes", required=True,
                        help="与 projects 顺序一致的逗号分隔模式")
    parser.add_argument("--duration", type=float, default=30.0)
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

    indices = selected_indices(args.action, modes)
    if not indices:
        print(f"ℹ️ action={args.action} 没有需要执行的项目，已跳过")
        return

    uv4 = None
    if args.action in {"build", "flash"}:
        uv4 = find_uv4(config) or get_keil_path(config)
        if not uv4 or not Path(uv4).is_file():
            print("❌ 未找到 UV4.exe，请检查 keil.uv4_path")
            sys.exit(1)

    failures: list[str] = []
    for index in indices:
        project = projects[index]
        name = str(project.get("name") or f"project{index + 1}")
        print(f"\n[{index}] {name} — mode={modes[index]} action={args.action}")

        if args.action in {"build", "flash"}:
            project_dir = str(project.get("dir", ""))
            project_file = str(project.get("file", ""))
            if not project_dir or not project_file:
                failures.append(f"[{index}] {name}: dir/file 未配置")
                continue
            result = (
                build_project(uv4, project_dir, project_file)
                if args.action == "build"
                else flash_project(uv4, project_dir, project_file)
            )
        else:
            serial = get_serial_config(config, index)
            save_path = project_log_path(args.save, index, name)
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

    if failures:
        print("\n❌ 部分项目执行失败:")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)

    print(f"\n✅ {args.action} 已按逐项目模式执行完成")


if __name__ == "__main__":
    main()
