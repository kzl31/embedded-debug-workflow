#!/usr/bin/env python
"""嵌入式调试 Skill 通用配置文件读写器。

核心职责：
    1. `--init <目录>` — 扫描工作区内的 Keil 工程并生成默认配置
  2. `--read/--validate` — 读取/校验配置
  3. 作为模块导入：load_config(config_dir) / save_config(data, config_dir)

配置文件名固定为 `embedded-debug-config.json`，存放在**工作区第一级**的
`.copilot/` 子目录下。初始化时由 `--init <工作区目录>` 在该目录直接生成
（不做向上查找）。

配置为 JSON 文件（不使用空格/竖线对齐的文本表，避免歧义）。每个工程独立携带
自己的串口与下载器参数，从而建立「工程文件路径 ↔ 串口 ↔ 下载器」的对应关系：

{
  "_generated": "2026-07-08 23:44:00",
    "ai_progress_display": true,
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

DEFAULT_UV4_PATH = r"C:\Keil_v5\UV4\UV4.exe"
DEFAULT_BAUD = 256000
DEFAULT_DATA_BITS = 8
DEFAULT_STOP_BITS = 1
DEFAULT_PARITY = "None"
DEFAULT_DEBUGGER_TYPE = "JLink"


def resolve_workspace_dir(
    config_dir: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> Path:
    """解析工作区根目录，不使用工程目录或当前目录的启发式向上查找。

    优先采用配置内初始化时记录的 ``workspace``；其次根据 ``config_dir``
    （工作区目录或配置文件路径）确定。调用方应尽量显式传入 ``config_dir``。
    """
    if config and config.get("workspace"):
        return Path(str(config["workspace"])).resolve()
    if config_dir is not None:
        path = Path(config_dir).resolve()
        if path.is_file() or path.name == CONFIG_FILENAME:
            return path.parent.parent if path.parent.name == ".copilot" else path.parent
        return path
    return Path.cwd().resolve()


def safe_project_name(name: str) -> str:
    """生成可用于 Windows 日志文件名的项目标识。"""
    safe = "".join(char if char.isalnum() or char in "-_" else "_" for char in name)
    return safe.strip("_.") or "project"


def project_log_path(
    config_dir: str | Path | None,
    config: dict[str, Any],
    project_index: int,
    project_name: str,
    log_type: str,
    suffix: str = ".txt",
) -> Path:
    """返回项目独立日志路径：``{工作区}/.copilot/logs/{类型}_pN_{名称}.txt``。"""
    workspace = resolve_workspace_dir(config_dir, config)
    filename = f"{safe_project_name(log_type)}_p{project_index}_{safe_project_name(project_name)}{suffix}"
    return workspace / ".copilot" / "logs" / filename
DEFAULT_AI_PROGRESS_DISPLAY = True

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


def get_project(config: dict[str, Any], project_index: int = 0) -> dict[str, Any] | None:
    """按下标获取工程；下标越界时返回 None。"""
    projects = get_projects(config)
    return projects[project_index] if 0 <= project_index < len(projects) else None


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

    if "ai_progress_display" in config and not isinstance(config["ai_progress_display"], bool):
        errors.append("ai_progress_display 必须是 true 或 false")

    keil = config.get("keil", {})
    if not keil.get("uv4_path"):
        errors.append("keil.uv4_path 缺失")

    projects = config.get("projects", [])
    if not projects:
        errors.append("projects 为空，至少需要一个工程")
    else:
        for i, p in enumerate(projects):
            if not p.get("name"):
                errors.append(f"projects[{i}].name 缺失")
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
            if not deb.get("type"):
                errors.append(f"projects[{i}].debugger.type 缺失")
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

def discover_keil_projects(root: str | Path) -> list[Path]:
    """递归扫描工作区中的 Keil 工程文件。

    扩展名按大小写不敏感处理；同一目录下同时存在同名 ``.uvprojx`` 和
    ``.uvproj`` 时只保留新版 ``.uvprojx``。依赖、缓存及 Skill 运行目录不会扫描。
    """
    workspace = Path(root).resolve()
    if not workspace.is_dir():
        raise NotADirectoryError(f"工作区目录不存在或不是目录: {workspace}")

    ignored_dirs = {
        ".git", ".copilot", ".venv", "venv", "__pycache__", "node_modules",
    }
    candidates: list[Path] = []
    for current_dir_text, dir_names, file_names in os.walk(workspace):
        dir_names[:] = [name for name in dir_names if name.lower() not in ignored_dirs]
        current_dir = Path(current_dir_text)
        for file_name in file_names:
            path = current_dir / file_name
            if path.suffix.lower() in {".uvprojx", ".uvproj"}:
                candidates.append(path.resolve())

    # 先排序可确保新版 .uvprojx 优先，再按“目录 + 文件主名”去重旧格式工程。
    candidates.sort(key=lambda path: (
        str(path.parent).lower(), path.stem.lower(), path.suffix.lower() != ".uvprojx"
    ))
    unique: dict[tuple[str, str], Path] = {}
    for path in candidates:
        key = (str(path.parent).casefold(), path.stem.casefold())
        unique.setdefault(key, path)
    return list(unique.values())


def _new_project_config(project_file: Path) -> dict[str, Any]:
    """为扫描到的工程生成默认配置项。"""
    return {
        "name": project_file.stem,
        "dir": str(project_file.parent),
        "file": project_file.name,
        "serial": {
            "port": "COM1",
            "baud": DEFAULT_BAUD,
            "data_bits": DEFAULT_DATA_BITS,
            "stop_bits": DEFAULT_STOP_BITS,
            "parity": DEFAULT_PARITY,
        },
        "debugger": {
            "type": DEFAULT_DEBUGGER_TYPE,
            "com": "COM1",
        },
    }


def init_project(workspace_dir: str, project_count: int | None = None) -> dict[str, Any]:
    """扫描工作区并生成或增量更新 Keil 工程配置。"""
    root = Path(workspace_dir).resolve()
    config_path = root / ".copilot" / CONFIG_FILENAME
    print("=" * 50)
    print(f"🔧 嵌入式调试初始化 — 工作区: {root}")
    print("=" * 50)

    print("🔍 正在递归扫描 .uvprojx / .uvproj 工程文件……")
    discovered = discover_keil_projects(root)
    print(f"🔍 扫描完成，共发现 {len(discovered)} 个 Keil 工程")
    if not discovered:
        print(f"❌ 当前工作区未找到 .uvprojx 或 .uvproj 工程文件: {root}")
        raise FileNotFoundError("当前工作区没有可初始化的 Keil 工程")

    config = load_config(config_path) if config_path.is_file() else {}
    existing_projects = config.get("projects", [])
    existing_paths = {
        str((Path(item.get("dir", "")) / item.get("file", "")).resolve()).casefold()
        for item in existing_projects
        if item.get("dir") and item.get("file")
    }
    added = 0
    for project_file in discovered:
        if str(project_file).casefold() not in existing_paths:
            existing_projects.append(_new_project_config(project_file))
            added += 1

    config["_generated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    config["workspace"] = str(root)
    config["project_count"] = len(existing_projects)
    config.setdefault("ai_progress_display", DEFAULT_AI_PROGRESS_DISPLAY)
    config.setdefault("keil", {"uv4_path": DEFAULT_UV4_PATH})
    config["projects"] = existing_projects

    print(f"\n发现 {len(discovered)} 个 Keil 工程：")
    for project_file in discovered:
        print(f"  - {project_file}")
    if config_path.is_file():
        print(f"\n♻️ 已保留原有工程参数，新增 {added} 个扫描到的工程")

    # ── 保存 ───────────────────────────────────────────────────────
    save_config(config, save_dir=root)
    print(f"\n✅ 初始化完成！配置文件已生成:")
    print(f"   {root / '.copilot' / CONFIG_FILENAME}")
    print("   工程路径已按当前工作区生成；Keil、串口和下载器等参数保持默认值")

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
                        help="启动初始化：扫描工作区并生成 Keil 工程配置")
    parser.add_argument("--scan", metavar="工作区目录",
                        help="只扫描并输出工作区中的 Keil 工程，不修改配置")
    parser.add_argument("--project-count", type=int,
                        help="兼容旧调用，初始化时忽略，项目数量以扫描结果为准")
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

    if args.scan:
        projects = discover_keil_projects(args.scan)
        print(json.dumps({
            "workspace": str(Path(args.scan).resolve()),
            "count": len(projects),
            "projects": [str(path) for path in projects],
        }, indent=2, ensure_ascii=False))
        if not projects:
            sys.exit(1)
        return

    if args.init:
        try:
            init_project(args.init, args.project_count)
        except (FileNotFoundError, NotADirectoryError) as exc:
            print(f"[config_reader] ❌ {exc}", file=sys.stderr)
            sys.exit(1)
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
