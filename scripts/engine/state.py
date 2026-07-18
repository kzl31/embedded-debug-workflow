"""
engine/state.py — 流程状态（flow-gate.json）读写与默认结构

负责：
  - 各类状态/配置/结果文件路径推导
  - 进度展示开关读取
  - flow-gate 的加密读 / 原子写 / 并发保护
  - 默认状态结构定义
"""

import json
import sys
from pathlib import Path

from engine.constants import (
    FLOW_GATE_FILENAME,
    PROJECT_RESULTS_FILENAME,
    STATE_DIR,
    TEMPLATES_DIR,
    WORKSPACE_DATA_DIR,
    CONFIG_FILENAME,
)
from engine.utils import decrypt_json, encrypt_json, load_json, now_iso


def _decode_state(text: str) -> dict:
    """读取引擎统一写入的加密状态。"""
    try:
        data = decrypt_json(text.strip())
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("flow-gate.json 不是有效的加密状态文件") from exc
    if not isinstance(data, dict):
        raise ValueError("flow-gate.json 顶层必须是 JSON 对象")
    return data


def get_flow_gate_path(project_dir: str) -> Path:
    return Path(project_dir) / STATE_DIR / FLOW_GATE_FILENAME


def get_project_results_path(project_dir: str) -> Path:
    return Path(project_dir) / STATE_DIR / PROJECT_RESULTS_FILENAME


def get_config_path(project_dir: str) -> Path:
    return Path(project_dir) / WORKSPACE_DATA_DIR / CONFIG_FILENAME


def load_progress_display_enabled(project_dir: str) -> bool:
    """读取工作区进度展示开关；缺失或配置异常时保持兼容并默认开启。"""
    path = get_config_path(project_dir)
    if not path.is_file():
        return True
    try:
        config = load_json(path)
    except (json.JSONDecodeError, OSError):
        return True
    value = config.get("ai_progress_display", True)
    return value if isinstance(value, bool) else True


def load_flow_gate(project_dir: str) -> dict:
    path = get_flow_gate_path(project_dir)
    if path.exists():
        return _decode_state(path.read_text(encoding="utf-8"))
    template = TEMPLATES_DIR / FLOW_GATE_FILENAME
    if template.exists():
        data = load_json(template)
    else:
        data = _default_flow_gate()
    data["lastUpdated"] = now_iso()
    data["debugSession"]["startTime"] = now_iso()
    save_flow_gate(project_dir, data, force=True)
    return data


def save_flow_gate(project_dir: str, data: dict, force: bool = False) -> None:
    fpath = Path(project_dir) / STATE_DIR / FLOW_GATE_FILENAME
    if fpath.exists() and not force:
        try:
            on_disk = _decode_state(fpath.read_text(encoding="utf-8"))
            disk_ts = on_disk.get("lastUpdated", "")
            mem_ts = data.get("lastUpdated", "")
            if disk_ts and disk_ts != mem_ts:
                print(f"[workflow_engine] ⚠️ flow-gate.json 已被外部修改，跳过保存"
                      f"（磁盘: {disk_ts} ≠ 内存: {mem_ts}）", file=sys.stderr)
                return
        except (ValueError, OSError):
            pass
    data["lastUpdated"] = now_iso()
    fpath.parent.mkdir(parents=True, exist_ok=True)
    tmp = fpath.with_suffix(".tmp")
    tmp.write_text(encrypt_json(data), encoding="utf-8")
    tmp.replace(fpath)


def _default_flow_gate() -> dict:
    return {
        "currentSeq": 1,
        "currentPhase": None,
        "completedPhases": [],
        "lastUpdated": None,
        "pauseState": {
            "waiting": False,
            "reason": "",
            "seq": None,
            "since": None
        },
        "projectInfo": {
            "configFound": False,
            "initialQuestionsAnswered": False,
            "sourcePreAnalyzed": False,
            "sourceQuickReviewed": False,
            "projectCount": 0,
            "currentProjectIndex": None,
            "projectModes": "",
            "configFingerprint": "",
            "configProjects": [],
            "skipBuild": False,
            "skipFlash": False,
            "observeExistingSerial": False,
            "serialCaptureRequested": True,
            "finishRequested": False,
            "hasBuildProjects": False,
            "hasFlashProjects": False,
            "hasSerialProjects": False,
            "projectRuns": [],
            "serialConfirmed": False,
            "hardwareReady": False,
            "faultDescribed": False,
            "configConfirmed": False
        },
        "debugLoopInfo": {
            "iterationCount": 0,
            "iterationExhausted": False,
            "baselineBuildPending": True,
            "iterationExecutionAllowed": True,
            "iterationChangeStatus": "pending",
            "iterationChangeSummary": "",
            "iterationCodeChanged": False,
            "iterationNewEvidence": False,
            "nextObservationPlanned": False,
            "nextObservationSummary": "",
            "compileRetryCount": 0,
            "cheshiAdded": False,
            "lastBuildStatus": None,
            "lastFlashStatus": None,
            "rootCauseFound": False,
            "retryCount": 0,
            "suspiciousLocation": "",
            "askUser": False,
            "askCount": 0
        },
        "verifyReport": {
            "cheshiCleaned": False,
            "fixConfirmed": False
        },
        "debugSession": {
            "startTime": None,
            "endTime": None,
            "faultSummary": "",
            "reportFile": "",
            "memorySaved": False
        }
    }
