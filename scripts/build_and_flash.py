#!/usr/bin/env python
"""一键编译 + 下载固件组合工具。

先执行 keil_build 编译，成功后自动执行 keil_flash 下载。
所有参数动态读取 data/config.json。

用法：
  python scripts/build_and_flash.py                       # 默认工程
  python scripts/build_and_flash.py --project "RU3.uvprojx"
  python scripts/build_and_flash.py --rebuild             # 先 Clean 再编译
    python scripts/build_and_flash.py --skip-build          # 跳过编译，下载已有固件
    python scripts/build_and_flash.py --skip-flash          # 只编译，不下载
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))
from config_reader import get_project, load_config, project_log_path
from keil_build import find_uv4 as find_uv4_build, build_project
from keil_flash import find_uv4 as find_uv4_flash, flash_project


def main() -> None:
    parser = argparse.ArgumentParser(description="一键编译+下载")
    parser.add_argument("--project", help="工程文件名")
    parser.add_argument("--dir", help="工程目录")
    parser.add_argument("--target", help="指定 Target 名称")
    parser.add_argument("--rebuild", action="store_true", help="先 Clean 再编译")
    parser.add_argument("--skip-build", action="store_true",
                        help="跳过编译，直接下载已有固件")
    parser.add_argument("--skip-flash", action="store_true",
                        help="跳过下载，只执行编译")
    parser.add_argument("--build-log", help="编译日志路径")
    parser.add_argument("--flash-log", help="下载日志路径")
    parser.add_argument("--config-dir", help="配置文件所在目录（默认自动查找）")
    parser.add_argument("--project-index", type=int, default=0,
                        help="projects 数组下标（默认 0；调用方应传入当前文档所属项目）")
    args = parser.parse_args()

    config = load_config(args.config_dir)

    # 确定 UV4 路径
    uv4 = find_uv4_build(config)
    if not uv4:
        print("❌ 未找到 UV4.exe，请先配置 keil.uv4_path")
        print("   运行: python scripts/config_reader.py --collect")
        sys.exit(1)

    # 确定工程参数
    project_file = args.project
    project_dir = args.dir
    if not project_file or not project_dir:
        proj = get_project(config, args.project_index)
        if not proj:
            print(f"❌ config.json 中未配置工程[{args.project_index}]信息")
            sys.exit(1)
        project_file = project_file or proj["file"]
        project_dir = project_dir or proj["dir"]

    project = get_project(config, args.project_index) or {}
    project_name = str(project.get("name") or Path(project_file).stem)
    build_log = args.build_log or str(project_log_path(
        args.config_dir, config, args.project_index, project_name, "build_log"
    ))
    flash_log = args.flash_log or str(project_log_path(
        args.config_dir, config, args.project_index, project_name, "flash_log"
    ))

    print("=" * 50)
    if args.skip_build and args.skip_flash:
        operation = "跳过编译和下载"
    elif args.skip_build:
        operation = "仅下载"
    elif args.skip_flash:
        operation = "仅编译"
    else:
        operation = "编译 + 下载"
    print(f"🔨🔥 {operation}")
    print(f"   工程: {project_file}")
    print(f"   目录: {project_dir}")
    print("=" * 50)

    build_result = None
    if not args.skip_build:
        print("\n[编译] 编译固件...")
        build_result = build_project(
            uv4_path=uv4,
            project_dir=project_dir,
            project_file=project_file,
            target=args.target,
            rebuild=args.rebuild,
            log_file=build_log,
        )

        if build_result["status"] == "failure":
            print("\n❌ 编译失败，终止后续流程")
            print(f"   错误数: {build_result.get('errors', '?')}")
            if build_result.get("error_lines"):
                print("\n   错误信息（前 5 条）:")
                for line in build_result["error_lines"][:5]:
                    print(f"     {line}")
            sys.exit(1)
    else:
        print("\n[编译] 已按参数跳过，使用现有固件产物")

    flash_result = None
    if not args.skip_flash:
        print("\n[下载] 下载固件...")
        uv4f = find_uv4_flash(config)
        flash_result = flash_project(
            uv4_path=uv4f or uv4,
            project_dir=project_dir,
            project_file=project_file,
            log_file=flash_log,
        )

        if flash_result["status"] == "failure":
            print("\n❌ 下载失败")
            sys.exit(1)
    else:
        print("\n[下载] 已按参数跳过")

    # 汇总结果
    print("\n" + "=" * 50)
    print(f"✅ {operation}完成")
    if build_result and build_result.get("program_size"):
        ps = build_result["program_size"]
        print(f"   Flash: ~{ps['total_flash']} bytes  RAM: ~{ps['total_ram']} bytes")
    if flash_result and flash_result.get("verified"):
        print("   ✅ 固件校验通过")


if __name__ == "__main__":
    main()
