#!/usr/bin/env python
"""多工程批量编译下载工具。

读取 data/config.json 中的全部工程列表，逐个执行编译 + 下载。

用法：
  python scripts/batch_build.py                          # 编译下载所有工程
  python scripts/batch_build.py --build-only             # 仅编译，不下载
  python scripts/batch_build.py --index 0                # 仅处理索引为 0 的工程
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))
from config_reader import get_keil_path, get_projects, load_config, project_log_path
from keil_build import build_project
from keil_flash import flash_project


def main() -> None:
    parser = argparse.ArgumentParser(description="批量编译下载工具")
    parser.add_argument("--build-only", action="store_true", help="仅编译，不下载")
    parser.add_argument("--flash-only", action="store_true", help="仅下载，不编译")
    parser.add_argument("--index", type=int, help="仅处理指定索引的工程（从 0 开始）")
    parser.add_argument("--target", help="指定 Target 名称")
    parser.add_argument("--config-dir", help="配置文件所在目录（默认自动查找）")
    args = parser.parse_args()

    config = load_config(args.config_dir)

    uv4 = get_keil_path(config)
    if not uv4 or not Path(uv4).exists():
        print("❌ 未找到 UV4.exe，请先配置 keil.uv4_path")
        sys.exit(1)

    projects = get_projects(config)
    if not projects:
        print("❌ config.json 中未配置任何工程")
        sys.exit(1)

    # 筛选工程
    selected_projects = list(enumerate(projects))
    if args.index is not None:
        if args.index < 0 or args.index >= len(projects):
            print(f"❌ 索引 {args.index} 超出范围，有效 0~{len(projects) - 1}")
            sys.exit(1)
        selected_projects = [(args.index, projects[args.index])]

    print(f"📋 共 {len(selected_projects)} 个工程待处理")
    print("=" * 50)

    all_success = True

    for display_index, (project_index, proj) in enumerate(selected_projects):
        name = proj.get("name", f"工程{project_index}")
        proj_dir = proj["dir"]
        proj_file = proj["file"]

        print(f"\n[{display_index + 1}/{len(selected_projects)}] {name}")
        print(f"   目录: {proj_dir}")
        print(f"   文件: {proj_file}")

        # 编译
        if not args.flash_only:
            print(f"   🔨 编译中...")
            build_result = build_project(
                uv4_path=uv4,
                project_dir=proj_dir,
                project_file=proj_file,
                target=args.target,
                log_file=str(project_log_path(
                    args.config_dir, config, project_index, name, "build_log"
                )),
            )
            if build_result["status"] == "failure":
                print(f"   ❌ 编译失败")
                all_success = False
                continue
            print(f"   ✅ 编译成功")

        # 下载
        if not args.build_only:
            print(f"   🔥 下载中...")
            flash_result = flash_project(
                uv4_path=uv4,
                project_dir=proj_dir,
                project_file=proj_file,
                log_file=str(project_log_path(
                    args.config_dir, config, project_index, name, "flash_log"
                )),
            )
            if flash_result["status"] == "failure":
                print(f"   ❌ 下载失败")
                all_success = False
                continue
            print(f"   ✅ 下载成功")

        print(f"   ✅ [{display_index + 1}/{len(selected_projects)}] {name} 完成")

    print("\n" + "=" * 50)
    if all_success:
        print("✅ 全部工程处理完成")
    else:
        print("⚠️ 部分工程处理失败，请检查上述日志")
        sys.exit(1)


if __name__ == "__main__":
    main()
