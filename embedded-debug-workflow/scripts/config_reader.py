#!/usr/bin/env python
"""嵌入式调试 Skill 通用配置文件读写器。

核心职责：
    1. `--init <目录> --project-count N` — 按用户确认的项目数量生成可编辑默认配置
  2. `--read/--validate` — 读取/校验配置
  3. 作为模块导入：load_config(config_dir) / save_config(data, config_dir)

配置文件名固定为 `embedded-debug-config.json`，存放在**工作区第一级**的
`.copilot/` 子目录下。初始化时由 `--init <工作区目录>` 在该目录直接生成
（不做向上查找）。

配置为 JSON 文件（不使用空格/竖线对齐的文本表，避免歧义）。每个工程独立携带
自己的串口与下载器参数，从而建立「工程文件路径 ↔ 串口 ↔ 下载器」的对应关系：

{
  "_generated": "2026-07-08 23:44:00",
  "keil": { "uv4_path": "C:\\Keil_v5\\UV4\\UV4.exe" },
  "projects": [
    {
      "name": "RU3主机",
      "dir": "e:\\proj\\MDK-ARM",
      "file": "RU3.uvprojx",
      "serial": { "port": "COM19", "baud": 256000, "data_bits": 8, "stop_bits": 1, "parity": "None" },
      "debugger": { "type": "JLink", "com": "COM9" }
    }
  ]
}
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# ── 常量 ──────────────────────────────────────────────────────────────

CONFIG_FILENAME = "embedded-debug-config.json"
"""配置文件名，固定存放在工作区第一级目录的 `.copilot/` 子目录下。"""

# ── 路径解析 ──────────────────────────────────────────────────────────

def get_skill_dir() -> Path:
    """返回 Skill 根目录（即 scripts/ 的父目录）。"""
    return Path(__file__).resolve().parent.parent


def resolve_config_path(path_or_dir: str | Path | None = None) -> Path:
    """将用户传入的路径解析为实际配置文件路径（不做向上查找）。

    规则：
    - 路径为空 → 当前工作区的 `.copilot/{CONFIG_FILENAME}`
    - 路径指向已存在的文件 → 直接返回
    - 路径指向目录 → 该目录下的 `.copilot/{CONFIG_FILENAME}`（即工作区配置）
    """
    if path_or_dir is None:
        return Path.cwd() / ".copilot" / CONFIG_FILENAME

    p = Path(path_or_dir).resolve()
    if p.is_file():
        return p
    return p / ".copilot" / CONFIG_FILENAME


def get_config_path(save_dir: str | Path | None = None) -> Path:
    """返回配置文件写入路径（工作区第一级 `.copilot/` 下，不向上查找）。"""
    if save_dir:
        path = Path(save_dir).resolve()
        if path.name == CONFIG_FILENAME:
            return path
        return path / ".copilot" / CONFIG_FILENAME
    return resolve_config_path(None)


# ── 核心读写 ──────────────────────────────────────────────────────────

def load_config(config_dir: str | Path | None = None) -> dict[str, Any]:
    """读取配置文件，文件不存在或格式错误时返回空字典。

    config_dir 可以是：
    - None → 当前工作区的 `.copilot/{CONFIG_FILENAME}`
    - 目录路径 → 该目录下的 `.copilot/{CONFIG_FILENAME}`（即工作区配置）
    - 文件路径 → 直接读取该文件
    """
    if config_dir is not None:
        p = Path(config_dir)
        path = p if p.is_file() else (p / ".copilot" / CONFIG_FILENAME)
    else:
        path = resolve_config_path(None)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[config_reader] ⚠️ 配置文件解析失败: {exc}", file=sys.stderr)
        return {}


def save_config(data: dict[str, Any], save_dir: str | Path | None = None) -> Path:
    """保存配置到 JSON 文件到指定项目目录，返回写入的文件路径。"""
    path = get_config_path(save_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[config_reader] ✅ 配置已保存: {path}")
    return path


def find_config_in_project(project_dir: str | Path) -> Path | None:
    """在指定工作区目录的 `.copilot/` 下查找配置文件，找不到返回 None（不向上查找）。"""
    candidate = Path(project_dir).resolve() / ".copilot" / CONFIG_FILENAME
    return candidate if candidate.exists() else None


# ── 便捷访问器 ────────────────────────────────────────────────────────

def get_keil_path(config: dict[str, Any] | None = None) -> str | None:
    """获取 Keil UV4.exe 路径。"""
    if config is None:
        config = load_config()
    keil = config.get("keil", {})
    return keil.get("uv4_path")


def get_projects(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """获取工程列表。"""
    if config is None:
        config = load_config()
    return config.get("projects", [])


def get_first_project(config: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """获取第一个工程。"""
    projects = get_projects(config)
    return projects[0] if projects else None


def _project_field(config: dict, index: int, field: str, default):
    """返回 projects[index][field]，越界或缺失时返回 default。"""
    projects = config.get("projects", [])
    if 0 <= index < len(projects):
        return projects[index].get(field, default)
    return default


def get_serial_config(config: dict[str, Any] | None = None, project_index: int = 0) -> dict[str, Any]:
    """获取指定工程的串口配置（默认第 0 个工程）。

    兼容旧版平铺结构：工程内无 serial 时回退到顶层 serial。
    """
    if config is None:
        config = load_config()
    serial = _project_field(config, project_index, "serial", {})
    if not serial and config.get("serial"):
        serial = config["serial"]
    return {
        "port": serial.get("port", "COM1"),
        "baud": serial.get("baud", 256000),
        "data_bits": serial.get("data_bits", 8),
        "stop_bits": serial.get("stop_bits", 1),
        "parity": serial.get("parity", "None"),
    }


def get_debugger_info(config: dict[str, Any] | None = None, project_index: int = 0) -> dict[str, str]:
    """获取指定工程的下载器信息（默认第 0 个工程）。

    下载器以串口号（com）标识，而非序列号。兼容旧版顶层 debugger。
    """
    if config is None:
        config = load_config()
    deb = _project_field(config, project_index, "debugger", {})
    if not deb and config.get("debugger"):
        deb = config["debugger"]
    return {
        "type": deb.get("type", "JLink"),
        "com": deb.get("com", ""),
    }


# ── 配置完整性校验 ────────────────────────────────────────────────────

def validate_config(config: dict[str, Any] | None = None) -> list[str]:
    """校验配置完整性，返回缺失/错误的字段列表（逐工程校验串口与下载器）。"""
    if config is None:
        config = load_config()
    errors: list[str] = []

    keil = config.get("keil", {})
    if not keil.get("uv4_path"):
        errors.append("keil.uv4_path 缺失")

    projects = config.get("projects", [])
    if not projects:
        errors.append("projects 为空，至少需要一个工程")
    else:
        for i, p in enumerate(projects):
            if not p.get("dir"):
                errors.append(f"projects[{i}].dir 缺失")
            if not p.get("file"):
                errors.append(f"projects[{i}].file 缺失")
            serial = p.get("serial", {})
            if not serial.get("port"):
                errors.append(f"projects[{i}].serial.port 缺失")
            if not serial.get("baud"):
                errors.append(f"projects[{i}].serial.baud 缺失")
            deb = p.get("debugger", {})
            if not deb.get("com"):
                errors.append(f"projects[{i}].debugger.com 缺失")

    return errors


def _ensure_project(config: dict, index: int) -> dict:
    """确保 projects[index] 存在并返回（越界时追加占位工程）。"""
    projects = config.setdefault("projects", [])
    while len(projects) <= index:
        projects.append({"name": f"project{len(projects)}"})
    return projects[index]


# ── 启动初始化（核心） ────────────────────────────────────────────────

def init_project(workspace_dir: str, project_count: int) -> dict[str, Any]:
    """按用户确认的项目数量生成无交互占位配置。"""
    if project_count < 1:
        raise ValueError("project_count 必须大于等于 1")

    root = Path(workspace_dir).resolve()
    print("=" * 50)
    print(f"🔧 嵌入式调试初始化 — 工作区: {root}")
    print("=" * 50)

    config: dict[str, Any] = {
        "_generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "workspace": str(root),
        "project_count": project_count,
        "keil": {"uv4_path": ""},
    }

    projects: list[dict[str, Any]] = []
    for index in range(project_count):
        projects.append({
            "name": f"project{index + 1}",
            "dir": "",
            "file": "",
            "serial": {
            "port": "",
                "baud": "",
                "data_bits": "",
                "stop_bits": "",
                "parity": "",
            },
            "debugger": {
                "type": "",
                "com": "",
            },
        })
    config["projects"] = projects

    print(f"\n按用户确认数量生成 {project_count} 个项目占位项，不扫描工作区")

    # ── 保存 ───────────────────────────────────────────────────────
    save_config(config, save_dir=root)
    print(f"\n✅ 初始化完成！配置文件已生成:")
    print(f"   {root / '.copilot' / CONFIG_FILENAME}")
    print("   请直接编辑该文件，填写其中全部配置参数")

    return config


# ── CLI 入口 ──────────────────────────────────────────────────────────

def main() -> None:
    # 修复 Windows 控制台 GBK 编码导致的 emoji/中文输出崩溃
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="嵌入式调试配置文件管理器")
    parser.add_argument("--init", metavar="工作区目录",
                        help="启动初始化：按项目数量生成可编辑的占位配置")
    parser.add_argument("--project-count", type=int,
                        help="用户确认的项目数量；与 --init 一起使用")
    parser.add_argument("--read", action="store_true", help="读取并打印当前配置")
    parser.add_argument("--validate", action="store_true", help="校验配置完整性")
    parser.add_argument("--get", choices=["keil", "serial", "projects", "debugger"],
                        help="获取指定字段的值（输出为 JSON）")
    parser.add_argument("--project-index", type=int, default=0,
                        help="指定工程下标（多工程时，默认 0）")
    parser.add_argument("--set-port", metavar="COMx", help="快速修改指定工程的串口号")
    parser.add_argument("--set-baud", metavar="波特率", type=int, help="快速修改指定工程的波特率")
    parser.add_argument("--path", help="指定配置文件路径（默认自动查找）")

    args = parser.parse_args()

    if args.init:
        if args.project_count is None:
            parser.error("--init 必须同时提供 --project-count")
        init_project(args.init, args.project_count)
        return

    # 解析实际配置文件路径
    cfg_path = resolve_config_path(args.path) if args.path else None

    # ── 快速修改串口号（按工程下标） ─────────────────────────────
    if args.set_port or args.set_baud:
        data = load_config(cfg_path)
        proj = _ensure_project(data, args.project_index)
        proj.setdefault("serial", {})
        if args.set_port:
            proj["serial"]["port"] = args.set_port.upper()
            print(f"  工程[{args.project_index}] 串口号 → {args.set_port.upper()}")
        if args.set_baud:
            proj["serial"]["baud"] = args.set_baud
            print(f"  工程[{args.project_index}] 波特率 → {args.set_baud}")
        save_config(data, cfg_path)
        return

    if args.get:
        data = load_config(cfg_path)
        if args.get == "keil":
            print(json.dumps({"uv4_path": get_keil_path(data) or ""}, ensure_ascii=False))
        elif args.get == "serial":
            print(json.dumps(get_serial_config(data, args.project_index), ensure_ascii=False))
        elif args.get == "projects":
            print(json.dumps(get_projects(data), ensure_ascii=False, indent=2))
        elif args.get == "debugger":
            print(json.dumps(get_debugger_info(data, args.project_index), ensure_ascii=False))
        return

    if args.validate:
        data = load_config(cfg_path)
        errors = validate_config(data)
        if errors:
            print("❌ 配置不完整:")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
        else:
            print("✅ 配置完整")
        return

    # 默认：读取并打印
    data = load_config(cfg_path)
    if data:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print("⚠️ 配置文件为空或不存在")
        sys.exit(1)


if __name__ == "__main__":
    main()
