#!/usr/bin/env python
"""embedded-debug-workflow 的集中运行参数与路径构造器。

所有 Python 脚本必须从本模块读取可变参数，禁止重复硬编码工作区数据目录、
文件名、日志目录名、默认串口参数和超时时间。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_FILE = SCRIPT_DIR / "skill-config.json"


def _load_settings() -> dict[str, Any]:
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Skill 集中配置读取失败: {CONFIG_FILE}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"Skill 集中配置顶层必须是 JSON 对象: {CONFIG_FILE}")
    return data


SETTINGS = _load_settings()
PATHS = SETTINGS["paths"]
DEFAULTS = SETTINGS["defaults"]
TIMEOUTS = SETTINGS["timeouts"]

WORKSPACE_DATA_DIR = Path(PATHS["copilot_dir"]) / PATHS["workspace_data_dir"]
CONFIG_FILENAME = PATHS["config_filename"]
STATE_DIR = WORKSPACE_DATA_DIR / PATHS["state_dir"]
FLOW_GATE_FILENAME = PATHS["flow_gate_filename"]
PROJECT_RESULTS_FILENAME = PATHS["project_results_filename"]
LOGS_DIRNAME = PATHS["logs_dir"]
REPORTS_DIRNAME = PATHS["reports_dir"]

DEFAULT_UV4_PATH = DEFAULTS["keil_uv4_path"]
DEFAULT_BAUD = int(DEFAULTS["serial_baud"])
DEFAULT_DATA_BITS = int(DEFAULTS["serial_data_bits"])
DEFAULT_STOP_BITS = int(DEFAULTS["serial_stop_bits"])
DEFAULT_PARITY = str(DEFAULTS["serial_parity"])
DEFAULT_DEBUGGER_TYPE = str(DEFAULTS["debugger_type"])
DEFAULT_AI_PROGRESS_DISPLAY = bool(DEFAULTS["ai_progress_display"])

BUILD_IDLE_TIMEOUT_SECONDS = float(TIMEOUTS["build_idle_seconds"])
FLASH_TIMEOUT_SECONDS = float(TIMEOUTS["flash_seconds"])


def workspace_data_path(workspace: str | Path, *parts: str) -> Path:
    """在工作区 Skill 专属数据目录下拼接路径。"""
    return Path(workspace).resolve() / WORKSPACE_DATA_DIR.joinpath(*parts)


def resolve_workspace_dir(
    config_dir: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> Path:
    """解析工作区根目录，不根据工程目录向上猜测。"""
    if config and config.get("workspace"):
        return Path(str(config["workspace"])).resolve()
    if config_dir is None:
        return Path.cwd().resolve()

    path = Path(config_dir).resolve()
    if path.is_file() or path.name == CONFIG_FILENAME:
        data_parent = path.parent
        if data_parent.name == WORKSPACE_DATA_DIR.name:
            return data_parent.parent.parent
        if data_parent.name == PATHS["copilot_dir"]:  # 旧版配置兼容
            return data_parent.parent
        return data_parent
    return path


def safe_project_name(name: str) -> str:
    """生成可用于 Windows 文件名的项目标识。"""
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
    """生成工作区内的项目独立日志路径。"""
    workspace = resolve_workspace_dir(config_dir, config)
    filename = (
        f"{safe_project_name(log_type)}_p{project_index}_"
        f"{safe_project_name(project_name)}{suffix}"
    )
    return workspace_data_path(workspace, LOGS_DIRNAME, filename)
