"""
engine/constants.py — 引擎常量与路径配置

集中存放：
  - 仓库/Skill 目录推导
  - 动作类型分类（自动 / AI / 终止）
  - 加密密钥
"""

from pathlib import Path

from path_config import (
    CONFIG_FILENAME,
    FLOW_GATE_FILENAME,
    LOGS_DIRNAME,
    PROJECT_RESULTS_FILENAME,
    REPORTS_DIRNAME,
    SETTINGS,
    STATE_DIR,
    WORKSPACE_DATA_DIR,
)

# workflow_engine.py 位于 scripts/，其上级即为仓库（Skill）根目录
SKILL_DIR = Path(__file__).resolve().parent.parent.parent
FLOW_YAML_PATH = SKILL_DIR / "flow.yaml"
TEMPLATES_DIR = SKILL_DIR / "templates"

# 动作类型分类
AUTO_TYPES = {"run_script", "check_file", "read_config", "noop", "exit", "update_state", "log"}
AI_TYPES = {"ask_user", "edit_source", "analyze", "report", "check_regression", "wait_user"}

# 流向终止动作（执行后停止后续动作列表）
TERMINATE_ACTIONS = {"goto", "exit", "wait_user"}

# 状态文件加密密钥（轻量 XOR + base64，仅防止误编辑，非安全加密）
_ENCRYPT_KEY = b"CodexFlowGate"

# 供其他模块复用 path_config 中的常量，避免重复 import
__all__ = [
    "SKILL_DIR",
    "FLOW_YAML_PATH",
    "TEMPLATES_DIR",
    "AUTO_TYPES",
    "AI_TYPES",
    "TERMINATE_ACTIONS",
    "CONFIG_FILENAME",
    "FLOW_GATE_FILENAME",
    "LOGS_DIRNAME",
    "PROJECT_RESULTS_FILENAME",
    "REPORTS_DIRNAME",
    "SETTINGS",
    "STATE_DIR",
    "WORKSPACE_DATA_DIR",
]
