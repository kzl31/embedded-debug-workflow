#!/usr/bin/env python
"""
workflow_engine.py — 嵌入式调试工作流「单文件线性序号驱动」引擎

核心理念：
  flow.yaml      = 唯一真相源（线性序号步骤表，含 phase 分组标签）
  flow-gate.json = 唯一状态源（当前 seq + 流程状态）
  本引擎         = 纯查表 + 序号跳转解析器（零硬编码步骤）

用法：
    python workflow_engine.py --project <VS Code 工作区根目录> --init
      新对话初始化：干净状态 + 阶段置 STARTUP(seq=1) + 生成配置

    python workflow_engine.py --project <VS Code 工作区根目录> --mode 0
      只读当前状态快照（不执行、不推进）

    python workflow_engine.py --project <VS Code 工作区根目录> --mode 1
      执行/推进当前步骤：
        - 自动步骤（run_script/check_file/...）引擎直接执行并按结果跳转
        - AI 步骤（ask_user/edit_source/analyze/report/...）输出指令，不推进

  python workflow_engine.py --project <项目目录> --ack success
  python workflow_engine.py --project <项目目录> --ack failure
      AI 步骤执行完毕后提交结果，引擎据此走 on_success/on_failure 并继续

  python workflow_engine.py --project <项目目录> --done
      --ack success 的兼容别名

  python workflow_engine.py --project <项目目录> --wake
      从 wait_user（人工暂停）恢复，重新执行当前步骤

  python workflow_engine.py --project <项目目录> --reset
      重置为新任务

  python workflow_engine.py --project <项目目录> --set KEY=VALUE
      写入状态字段（点号语法，如 --set projectInfo.projectModes=full,compile_only）

  python workflow_engine.py --project <项目目录> --reload-config
      从磁盘重新读取并校验配置，清除依赖旧 projects 的模式状态

依赖：pip install pyyaml
"""

from __future__ import annotations

import argparse
import json
import base64
import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from config_reader import validate_config

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

try:
    import yaml
except ImportError:
    print(json.dumps({
        "error": "缺少 pyyaml 依赖",
        "fix": "pip install pyyaml",
        "status": "fatal"
    }, ensure_ascii=False, indent=2))
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════════
# 常量
# ══════════════════════════════════════════════════════════════════════

SKILL_DIR = Path(__file__).resolve().parent.parent
FLOW_YAML_PATH = SKILL_DIR / "flow.yaml"
TEMPLATES_DIR = SKILL_DIR / "templates"

# 动作类型分类
AUTO_TYPES = {"run_script", "check_file", "read_config", "noop", "exit", "update_state"}
AI_TYPES = {"ask_user", "edit_source", "analyze", "report", "check_regression", "wait_user"}

# 流向终止动作（执行后停止后续动作列表）
TERMINATE_ACTIONS = {"goto", "exit", "wait_user"}


# ══════════════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════════════

def load_json(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_path(template: str, project_dir: str) -> str:
    return (template or "").replace("{project_dir}", project_dir)


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_state_value(raw: str) -> Any:
    """按 JSON 语义解析 --set 值；普通文本保持字符串。"""
    text = raw.strip()
    if not text:
        return raw
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return raw
    return value


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(d ^ key[i % len(key)] for i, d in enumerate(data))

_ENCRYPT_KEY = b"CodexFlowGate"

def _encrypt_json(data: dict) -> str:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    return base64.b64encode(_xor_bytes(text.encode("utf-8"), _ENCRYPT_KEY)).decode("ascii")

def _decrypt_json(encrypted: str) -> dict:
    raw = base64.b64decode(encrypted.encode("ascii"))
    return json.loads(_xor_bytes(raw, _ENCRYPT_KEY).decode("utf-8"))


def _decode_state(text: str) -> dict:
    """读取引擎统一写入的加密状态。"""
    try:
        data = _decrypt_json(text.strip())
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("flow-gate.json 不是有效的加密状态文件") from exc
    if not isinstance(data, dict):
        raise ValueError("flow-gate.json 顶层必须是 JSON 对象")
    return data

# ══════════════════════════════════════════════════════════════════════
# 状态管理
# ══════════════════════════════════════════════════════════════════════

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


def config_fingerprint(config: dict) -> str:
    """生成配置内容指纹，用于阻止 AI 使用过期 projects 快照。"""
    canonical = json.dumps(config, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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
    fpath = get_flow_gate_path(project_dir)
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
    tmp.write_text(_encrypt_json(data), encoding="utf-8")
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


# ══════════════════════════════════════════════════════════════════════
# 引擎核心
# ══════════════════════════════════════════════════════════════════════

class WorkflowEngine:
    def __init__(self, project_dir: str):
        # 确保 Windows GBK 控制台下 emoji/中文打印不崩溃
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

        self.project_dir = os.path.abspath(project_dir)
        if not os.path.isdir(self.project_dir):
            raise FileNotFoundError(f"VS Code 工作区目录不存在: {self.project_dir}")

        # 加载流程定义（flow.yaml）
        self.flow = load_yaml(FLOW_YAML_PATH)
        self.steps = self.flow.get("steps", [])
        self.meta = self.flow.get("meta", {})
        self.phases = {p["name"]: p for p in self.flow.get("phases", [])}

        # 状态
        self.fg = load_flow_gate(self.project_dir)
        self.currentSeq = self.fg.get("currentSeq", 1)
        self.currentPhase = self.fg.get("currentPhase")
        if not self.currentPhase and self.steps:
            self.currentPhase = self.steps[0].get("phase")

        # 单步驱动的中间状态
        self.next_seq: Optional[int] = None
        self.finished: bool = False
        pause_state = self.fg.get("pauseState", {})
        self.waiting: bool = bool(pause_state.get("waiting", False))
        self.wait_msg: str = str(pause_state.get("reason", "") or "")
        self.progress_display_enabled = load_progress_display_enabled(self.project_dir)
        self.displayed_seqs: set[int] = set()

        self.engine_bin = f'python "{Path(__file__).resolve()}"'

    # ── 基础查询 ────────────────────────────────────────────────

    def _current_step(self) -> Optional[dict]:
        if 1 <= self.currentSeq <= len(self.steps):
            return self.steps[self.currentSeq - 1]
        return None

    def _seq_of_id(self, step_id: str) -> Optional[int]:
        for s in self.steps:
            if s.get("id") == step_id:
                return s.get("seq")
        return None

    def _is_auto(self, step: dict) -> bool:
        return step.get("action") in AUTO_TYPES

    def _phase_forbidden(self, phase: str) -> list:
        return self.phases.get(phase, {}).get("forbidden", [])

    def _set_current_seq(self, seq: int) -> None:
        seq = int(seq)
        if 1 <= seq <= len(self.steps):
            new_phase = self.steps[seq - 1].get("phase")
            if self.currentPhase and new_phase and self.currentPhase != new_phase:
                self._add_completed(self.currentPhase)
            self.currentPhase = new_phase
        self.currentSeq = seq
        self.fg["currentSeq"] = seq
        self.fg["currentPhase"] = self.currentPhase
        save_flow_gate(self.project_dir, self.fg)

    def _add_completed(self, phase: str) -> None:
        if phase and phase not in self.fg.get("completedPhases", []):
            self.fg.setdefault("completedPhases", []).append(phase)

    # ── 主入口 ──────────────────────────────────────────────────

    def run(self) -> dict:
        """执行当前步骤（--mode 1）。自动步骤执行并链式推进，AI 步骤输出指令。"""
        if self.waiting:
            return self._waiting()
        step = self._current_step()
        if step is None:
            return self._completed()
        if self._is_auto(step):
            self._execute_auto(step)
            return self._drive()
        return self._ai_instruction(step)

    def ack(self, ok: bool) -> dict:
        """AI 步骤提交结果（--ack success|failure / --done）。"""
        if self.waiting:
            return self._result(
                "error", "流程处于人工暂停状态，请先使用 --wake 恢复",
                next_action=f'{self.engine_bin} --project "{self.project_dir}" --wake')
        step = self._current_step()
        if step is None:
            return self._completed()
        if self._is_auto(step):
            return self._result("error", "当前步骤为自动步骤，无需 --ack；请使用 --mode 1")
        if ok and step.get("id") == "step_confirm_config":
            error = self._validate_confirmed_config_state()
            if error:
                return self._result(
                    "error", error,
                    next_action=(
                        f'{self.engine_bin} --project "{self.project_dir}" '
                        '--reload-config'))
        actions = step.get("on_success") if ok else step.get("on_failure")
        self._run_actions(actions, default_next=True)
        return self._drive()

    def wake(self) -> dict:
        """从 wait_user 暂停恢复，重新执行当前步骤（--wake）。"""
        if not self.waiting:
            return self._result("error", "当前流程未处于人工暂停状态，无需 --wake")
        self.waiting = False
        self.wait_msg = ""
        self.fg["pauseState"] = {
            "waiting": False,
            "reason": "",
            "seq": None,
            "since": None,
        }
        save_flow_gate(self.project_dir, self.fg)
        step = self._current_step()
        if step is None:
            return self._completed()
        if self._is_auto(step):
            self._execute_auto(step)
            return self._drive()
        return self._ai_instruction(step)

    def show_status(self) -> dict:
        """只读快照（--mode 0）。"""
        if self.waiting:
            result = self._waiting()
            result["state"] = {
                "currentPhase": self.currentPhase,
                "completedPhases": self.fg.get("completedPhases", []),
                "pauseState": self.fg.get("pauseState", {}),
                "projectInfo": self.fg.get("projectInfo", {}),
                "debugLoopInfo": self.fg.get("debugLoopInfo", {}),
                "verifyReport": self.fg.get("verifyReport", {}),
            }
            return result
        step = self._current_step()
        total = len(self.steps)
        result = {
            "status": "state_read",
            "message": "当前状态快照（只读，未推进）",
            "seq": self.currentSeq,
            "id": step.get("id", "") if step else "",
            "phase": self.currentPhase,
            "total_steps": total,
            "next_action": f'{self.engine_bin} --project "{self.project_dir}" --mode 1',
        }
        if step:
            atype = step.get("action")
            if atype in AI_TYPES:
                result["status"] = "awaiting_ai"
                result["message"] = f"当前需 AI 执行: {step.get('what', '')}"
            else:
                result["status"] = "auto_pending"
                result["message"] = f"下一步由引擎自动执行: {step.get('what', '')}"
            result["current_step"] = {
                "seq": step.get("seq"), "id": step.get("id"),
                "phase": step.get("phase"), "action": atype,
                "what": step.get("what", ""),
            }
        result["state"] = {
            "currentPhase": self.currentPhase,
            "completedPhases": self.fg.get("completedPhases", []),
            "pauseState": self.fg.get("pauseState", {}),
            "projectInfo": self.fg.get("projectInfo", {}),
            "debugLoopInfo": self.fg.get("debugLoopInfo", {}),
            "verifyReport": self.fg.get("verifyReport", {}),
        }
        return result

    def reset(self) -> dict:
        return self.init(fresh=True)

    def init(self, fresh: bool = False) -> dict:
        """初始化 / 重置流程；配置缺失时由 flow.yaml 第 1 步按工作区工程生成。"""
        data = _default_flow_gate()
        data["currentSeq"] = 1
        data["currentPhase"] = self.steps[0].get("phase") if self.steps else None
        data["lastUpdated"] = now_iso()
        data["debugSession"]["startTime"] = now_iso()
        save_flow_gate(self.project_dir, data, force=True)
        self.fg = data
        self.currentSeq = 1
        self.currentPhase = data["currentPhase"]
        self.next_seq = None
        self.finished = False
        self.waiting = False

        # 预创建日志与报告目录：UV4 / 串口脚本不会自动创建目录，
        # 若目录不存在会直接报"创建文件失败"，导致编译/监听日志无法落盘。
        try:
            data_dir = Path(self.project_dir) / WORKSPACE_DATA_DIR
            logs_dir = data_dir / LOGS_DIRNAME
            report_dir = data_dir / REPORTS_DIRNAME
            os.makedirs(logs_dir, exist_ok=True)
            os.makedirs(report_dir, exist_ok=True)
            print(f"[init] 📁 已预创建目录: {logs_dir}")
            print(f"[init] 📁 已预创建目录: {report_dir}")
        except Exception as exc:
            print(f"[init] ⚠️ 日志/报告目录创建失败: {exc}", file=sys.stderr)

        return self._result("initialized",
            f"✅ 调试工作流已初始化（VS Code 工作区: {self.project_dir}）",
            seq=1, phase=self.currentPhase,
            next_action=f'{self.engine_bin} --project "{self.project_dir}" --mode 1')

    def set_state(self, pairs: list) -> dict:
        """写入状态字段（--set KEY=VALUE，点号语法）。"""
        applied = {}
        for item in pairs:
            if "=" not in item:
                continue
            key, raw_value = item.split("=", 1)
            value = parse_state_value(raw_value)
            if key == "projectInfo.projectModes":
                self._sync_project_modes(str(value))
            elif key in {
                "projectInfo.skipBuild", "projectInfo.skipFlash",
                "projectInfo.observeExistingSerial", "projectInfo.finishRequested",
            }:
                if not isinstance(value, bool):
                    raise ValueError(f"{key} 必须是 true 或 false")
                self._apply_update_state({key: value})
                self._sync_execution_flags()
                save_flow_gate(self.project_dir, self.fg)
            else:
                self._apply_update_state({key: value})
            applied[key] = value
        return self._result("state_set", f"已更新状态: {applied}", applied=applied)

    def reload_config(self) -> dict:
        """强制从磁盘重载配置，并清除所有依赖旧 projects 的运行状态。"""
        path = get_config_path(self.project_dir)
        try:
            config = load_json(path)
        except (json.JSONDecodeError, OSError) as exc:
            return self._result("error", f"配置读取失败: {exc}")
        if not config:
            return self._result("error", f"配置不存在或为空: {path}")
        errors = validate_config(config)
        if errors:
            return self._result("error", "配置校验失败", errors=errors,
                                config_path=str(path))

        projects = config.get("projects", [])
        snapshot = [
            {
                "index": index,
                "name": project.get("name", ""),
                "dir": project.get("dir", ""),
                "file": project.get("file", ""),
                "serial": project.get("serial", {}),
                "debugger": project.get("debugger", {}),
            }
            for index, project in enumerate(projects)
        ]
        project_info = self.fg.setdefault("projectInfo", {})
        project_info.update({
            "projectCount": len(snapshot),
            "currentProjectIndex": None,
            "projectModes": "",
            "projectRuns": [],
            "configFingerprint": config_fingerprint(config),
            "configProjects": snapshot,
            "configConfirmed": False,
            "initialQuestionsAnswered": False,
        })
        self._sync_execution_flags()
        save_flow_gate(self.project_dir, self.fg)
        return self._result(
            "config_reloaded",
            f"已从磁盘重新读取并校验配置，共 {len(snapshot)} 个项目；旧项目模式已清除",
            config_path=str(path), projects=snapshot,
            required_action="仅针对本次返回的 projects 逐项询问模式")

    def _sync_project_modes(self, raw_modes: str) -> None:
        """根据逐项目模式生成能力标志和独立运行状态。"""
        snapshot_error = self._config_snapshot_error()
        if snapshot_error:
            raise ValueError(snapshot_error)
        modes = [item.strip() for item in raw_modes.split(",") if item.strip()]
        valid_modes = {"none", "compile_only", "compile_flash", "full"}
        invalid = [mode for mode in modes if mode not in valid_modes]
        if invalid:
            raise ValueError(f"无效项目模式: {', '.join(invalid)}")
        project_count = int(self.fg.get("projectInfo", {}).get("projectCount") or 0)
        if project_count and len(modes) != project_count:
            raise ValueError(
                f"项目模式数量({len(modes)})与 projectCount({project_count})不一致")

        project_info = self.fg.setdefault("projectInfo", {})
        project_info["projectModes"] = raw_modes
        project_info["projectRuns"] = [
            {
                "index": index,
                "mode": mode,
                "stages": {},
            }
            for index, mode in enumerate(modes)
        ]
        self._sync_execution_flags()
        save_flow_gate(self.project_dir, self.fg)

    def _config_snapshot_error(self) -> str:
        """确认状态中的配置快照仍与磁盘文件完全一致。"""
        path = get_config_path(self.project_dir)
        try:
            config = load_json(path)
        except (json.JSONDecodeError, OSError) as exc:
            return f"配置读取失败，请先 --reload-config: {exc}"
        expected = self.fg.get("projectInfo", {}).get("configFingerprint", "")
        if not expected:
            return "尚未由引擎重新加载配置，请先执行 --reload-config"
        if config_fingerprint(config) != expected:
            return "磁盘配置已修改，旧项目列表失效；请先执行 --reload-config"
        return ""

    def _validate_confirmed_config_state(self) -> str:
        """seq 2 硬门禁：禁止以旧配置或不完整模式推进。"""
        error = self._config_snapshot_error()
        if error:
            return error
        info = self.fg.get("projectInfo", {})
        projects = info.get("configProjects", [])
        modes = [item.strip() for item in str(info.get("projectModes", "")).split(",")
                 if item.strip()]
        if not projects or len(modes) != len(projects):
            return "必须针对引擎最新返回的全部 projects 逐项设置 projectModes"
        current_index = info.get("currentProjectIndex")
        if not isinstance(current_index, int) or not 0 <= current_index < len(projects):
            return "currentProjectIndex 未按最新配置设置或已越界"
        if info.get("projectCount") != len(projects):
            return "projectCount 与引擎最新配置快照不一致"
        return ""

    def _sync_execution_flags(self) -> None:
        """由逐项目模式和全局跳过参数派生实际可执行能力。"""
        project_info = self.fg.setdefault("projectInfo", {})
        modes = [
            item.strip()
            for item in str(project_info.get("projectModes", "")).split(",")
            if item.strip()
        ]
        skip_build = bool(project_info.get("skipBuild", False))
        skip_flash = bool(project_info.get("skipFlash", False))
        observe_existing_serial = bool(
            project_info.get("observeExistingSerial", False))
        finish_requested = bool(project_info.get("finishRequested", False))
        project_info["hasBuildProjects"] = (
            not skip_build and any(mode != "none" for mode in modes)
        )
        project_info["hasFlashProjects"] = (
            not skip_flash
            and any(mode in {"compile_flash", "full"} for mode in modes)
        )
        project_info["hasSerialProjects"] = (
            not finish_requested
            and (observe_existing_serial or (not skip_build and not skip_flash))
            and any(mode == "full" for mode in modes)
        )

    # ── 驱动循环 ────────────────────────────────────────────────

    def _drive(self) -> dict:
        """根据 next_seq / finished / waiting 链式推进，直到遇到 AI 步骤或完成。"""
        guard = 0
        while True:
            guard += 1
            if guard > 300:
                return self._result("error", "驱动循环次数过多，可能存在跳转死循环")

            if self.finished:
                return self._completed()
            if self.waiting:
                return self._waiting()

            if self.next_seq is None:
                self.next_seq = self.currentSeq + 1
            if self.next_seq < 1 or self.next_seq > len(self.steps):
                self.finished = True
                return self._completed()

            self._set_current_seq(self.next_seq)
            step = self.steps[self.currentSeq - 1]
            if self._is_auto(step):
                self._execute_auto(step)
                continue
            return self._ai_instruction(step)

    # ── 自动步骤执行 ────────────────────────────────────────────

    def _execute_auto(self, step: dict) -> None:
        self._emit_progress(step)
        action = step.get("action")

        # 1) 前置断言
        for pc in step.get("precheck", []) or []:
            cond = pc.get("assert")
            if not self._eval_condition(cond):
                self._run_actions(pc.get("on_fail", []), default_next=False)
                if self.next_seq is None and not self.finished and not self.waiting:
                    self.next_seq = self.currentSeq  # 断言失败且无跳转则停留
                return

        # 2) 执行前动作
        self._run_actions(step.get("pre_action", []), default_next=False)

        # 3) 执行主动作
        if action == "run_script":
            success = self._exec_subprocess(step.get("call", ""))
        elif action == "check_file":
            success = self._check_file(step.get("params", {}))
        elif action == "read_config":
            success = True
        elif action == "noop":
            success = True
        elif action == "exit":
            self._do_exit("COMPLETED")
            success = True
        else:
            success = True

        # 4) 走结果分支
        branch = step.get("on_success") if success else step.get("on_failure")
        self._run_actions(branch, default_next=True)

    # ── 动作列表执行 ────────────────────────────────────────────

    def _run_actions(self, actions: list, default_next: bool = True) -> None:
        for act in (actions or []):
            if self._run_action(act) == "terminate":
                return
        if default_next and self.next_seq is None and not self.finished and not self.waiting:
            self.next_seq = self.currentSeq + 1

    def _run_action(self, action: Any) -> Optional[str]:
        if not isinstance(action, dict):
            return None

        # 条件动作（when / then / else 同级）
        if "when" in action:
            if self._eval_condition(action.get("when")):
                self._run_actions(action.get("then", []), default_next=False)
            else:
                self._run_actions(action.get("else", []), default_next=False)
            return "terminate"

        for atype, aval in action.items():
            if atype == "update_state":
                self._apply_update_state(aval)
            elif atype == "run_script":
                self._exec_subprocess(aval)
            elif atype == "log":
                self._do_log(aval)
            elif atype == "read_config":
                pass
            elif atype == "goto":
                self._set_next(aval)
                return "terminate"
            elif atype == "exit":
                self._do_exit(aval)
                return "terminate"
            elif atype == "wait_user":
                self._do_wait(aval)
                return "terminate"
            elif atype in ("edit_source", "analyze", "report", "ask_user"):
                # 一般不出现在 do 列表，忽略
                pass
        return None

    def _set_next(self, val: Any) -> None:
        if val == "next":
            self.next_seq = self.currentSeq + 1
        elif val == "done":
            self.finished = True
        elif val == "wait":
            self._do_wait("等待用户处理")
        elif isinstance(val, int):
            self.next_seq = val
        elif isinstance(val, str):
            seq = self._seq_of_id(val)
            if seq:
                self.next_seq = seq

    def _do_exit(self, phase: str) -> None:
        self._add_completed(self.currentPhase)
        self.currentPhase = phase
        self.finished = True

    def _do_wait(self, msg: str) -> None:
        self.waiting = True
        self.wait_msg = msg or ""
        self.next_seq = self.currentSeq
        self.fg["pauseState"] = {
            "waiting": True,
            "reason": self.wait_msg,
            "seq": self.currentSeq,
            "since": now_iso(),
        }
        save_flow_gate(self.project_dir, self.fg)

    def _do_log(self, aval: Any) -> None:
        if isinstance(aval, dict):
            level = aval.get("level", "info")
            msg = aval.get("msg", "")
        else:
            level = "info"
            msg = str(aval)
        emoji = {"info": "ℹ", "warning": "⚠", "error": "❌"}.get(level, "ℹ")
        print(f"[{level}] {emoji} {msg}", file=sys.stdout)

    # ── 具体执行器 ──────────────────────────────────────────────

    def _resolve_script_file(self, cmd_str: str) -> Optional[str]:
        m = re.search(r'python\s+["\']?([^\s"\']+\.py)["\']?', cmd_str, re.IGNORECASE)
        if not m:
            return None
        script_rel = m.group(1)
        candidate = SKILL_DIR / script_rel
        if candidate.exists():
            return str(candidate)
        abs_candidate = Path(script_rel)
        if abs_candidate.is_absolute() and abs_candidate.exists():
            return str(abs_candidate)
        return None

    def _exec_subprocess(self, cmd_template: str) -> bool:
        cmd = resolve_path(cmd_template, self.project_dir)
        cmd = re.sub(
            r"\{([\w.]+)\}",
            lambda match: str(self._get_path(match.group(1))),
            cmd,
        )
        script_file = self._resolve_script_file(cmd)
        if script_file is None:
            print(f"[exec] ❌ 脚本文件不存在: {cmd}", file=sys.stderr)
            return False
        print(f"[exec] 🚀 {cmd}", file=sys.stdout)
        try:
            child_env = os.environ.copy()
            child_env["PYTHONIOENCODING"] = "utf-8"
            result = subprocess.run(cmd, shell=True, cwd=str(SKILL_DIR),
                                    timeout=600, env=child_env,
                                    stdin=subprocess.DEVNULL)
            self._merge_project_results()
            ok = result.returncode == 0
            print(f"[exec] {'✅' if ok else '❌'} 退出码 {result.returncode}", file=sys.stdout)
            return ok
        except subprocess.TimeoutExpired:
            print("[exec] ⏱ 超时", file=sys.stderr)
            return False
        except Exception as e:
            print(f"[exec] ❌ 异常: {e}", file=sys.stderr)
            return False

    def _merge_project_results(self) -> None:
        """将多项目执行器写出的逐项目阶段结果合并到流程状态。"""
        result_path = get_project_results_path(self.project_dir)
        if not result_path.is_file():
            return
        try:
            payload = load_json(result_path)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[workflow_engine] ⚠️ 逐项目结果读取失败: {exc}", file=sys.stderr)
            return
        stage = payload.get("latestStage", "unknown")
        stage_result = payload.get("stages", {}).get(stage, {})
        results = stage_result.get("projects", [])
        runs = self.fg.setdefault("projectInfo", {}).setdefault("projectRuns", [])
        by_index = {item.get("index"): item for item in runs if isinstance(item, dict)}
        for result in results:
            index = result.get("index")
            if not isinstance(index, int):
                continue
            run = by_index.setdefault(index, {
                "index": index,
                "mode": result.get("mode", "none"),
                "stages": {},
            })
            run["name"] = result.get("name", run.get("name", ""))
            run.setdefault("stages", {})[stage] = {
                "action": stage_result.get("action", ""),
                "status": result.get("status", "unknown"),
                "summary": result.get("summary", ""),
                "artifact": result.get("artifact"),
            }
        self.fg["projectInfo"]["projectRuns"] = [by_index[key] for key in sorted(by_index)]
        save_flow_gate(self.project_dir, self.fg)

    def _check_file(self, params: dict) -> bool:
        target = params.get("target", "")
        search_paths = [resolve_path(p, self.project_dir)
                        for p in params.get("search_paths", ["{project_dir}"])]
        for sp in search_paths:
            if (Path(sp) / target).exists():
                print(f"[check_file] ✅ 找到 {target} @ {sp}", file=sys.stdout)
                return True
        print(f"[check_file] ⚠ 未找到 {target}", file=sys.stdout)
        return False

    # ── AI 步骤指令 ─────────────────────────────────────────────

    def _ai_instruction(self, step: dict) -> dict:
        result = self._result("awaiting_ai", step.get("what", ""),
                              seq=step.get("seq"), id=step.get("id"),
                              phase=step.get("phase"), action=step.get("action"),
                              what=step.get("what"),
                              params=self._resolve_templates(step.get("params", {})),
                              forbidden=self._phase_forbidden(step.get("phase")))
        result["next_action"] = (
            f'{self.engine_bin} --project "{self.project_dir}" --ack success'
            f'   （若未达成目标用 --ack failure）')
        if self.progress_display_enabled:
            result["user_display"] = self._user_display(step)
        return result

    def _emit_progress(self, step: dict) -> None:
        """为每个步骤生成一次可展示进度；关闭开关时不要求 AI 输出。"""
        seq = step.get("seq")
        if not isinstance(seq, int) or seq in self.displayed_seqs:
            return
        self.displayed_seqs.add(seq)
        if self.progress_display_enabled:
            print(json.dumps({"user_display": self._user_display(step)},
                             ensure_ascii=False), file=sys.stdout)

    def _user_display(self, step: dict) -> dict:
        """生成简短进度展示；仅告知正在做什么，不构成分析或结果汇报。"""
        current_step = f'步骤 {step.get("seq")}/{len(self.steps)}：{step.get("what", "")}'
        display = {
            "type": "progress_only",
            "current_step": current_step,
            "text": f'> {current_step}',
            "instruction": "仅展示 text 字段；不得展开分析、日志、根因、结论或报告内容。",
        }
        iteration = int(self._get_path("debugLoopInfo.iterationCount") or 0)
        if step.get("phase") == "DEBUG_LOOP":
            loop_count = iteration + 1
            reason = self._get_path("debugLoopInfo.loopReason") or "首次进入调试循环，开始定位和采集证据"
            display["loop"] = {
                "count": loop_count,
                "reason": reason,
                "text": f"调试循环第 {loop_count} 轮：{reason}",
            }
            display["text"] = (
                f'> 调试循环第 {loop_count} 轮：{reason}；{current_step}'
            )
        return display

    # ── 终止状态 ────────────────────────────────────────────────

    def _waiting(self) -> dict:
        return self._result("awaiting_user", self.wait_msg or "等待用户处理",
                            seq=self.currentSeq, phase=self.currentPhase,
                            next_action=f'{self.engine_bin} --project "{self.project_dir}" --wake')

    def _completed(self) -> dict:
        self.fg["currentPhase"] = "COMPLETED"
        self.fg.setdefault("completedPhases", [])
        if "VERIFY_AND_REPORT" not in self.fg["completedPhases"]:
            self.fg["completedPhases"].append("VERIFY_AND_REPORT")
        if not self.fg.get("debugSession", {}).get("endTime"):
            self.fg["debugSession"]["endTime"] = now_iso()
        save_flow_gate(self.project_dir, self.fg)
        return self._result("completed", "🎉 所有流程已完成",
                            next_action=f'{self.engine_bin} --project "{self.project_dir}" --reset')

    # ── 条件与状态工具 ──────────────────────────────────────────

    def _get_path(self, path: str) -> Any:
        parts = path.split(".")
        if parts and parts[0] == "settings":
            cur: Any = SETTINGS
            parts = parts[1:]
        else:
            cur = self.fg
        for p in parts:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                return ""
        return cur

    def _resolve_templates(self, value: Any) -> Any:
        """递归展开 AI 参数中的工作区和集中配置占位符。"""
        if isinstance(value, str):
            text = resolve_path(value, self.project_dir)
            return re.sub(
                r"\{(settings\.[\w.]+)\}",
                lambda match: str(self._get_path(match.group(1))),
                text,
            )
        if isinstance(value, list):
            return [self._resolve_templates(item) for item in value]
        if isinstance(value, dict):
            return {key: self._resolve_templates(item) for key, item in value.items()}
        return value

    def _eval_condition(self, cond: str) -> bool:
        cond = (cond or "").strip()
        if not cond:
            return True
        m = re.match(r'^([\w.]+)\s*(==|!=|<=|>=|<|>)\s*(.+)$', cond)
        if not m:
            return True
        path, op, raw = m.group(1), m.group(2), m.group(3).strip()
        if ((raw.startswith('"') and raw.endswith('"'))
                or (raw.startswith("'") and raw.endswith("'"))):
            raw_val: Any = raw[1:-1]
        else:
            raw_val = parse_state_value(raw)
        actual = self._get_path(path)
        try:
            a = float(actual)
            b = float(raw_val)
            return self._cmp(op, a, b)
        except (ValueError, TypeError):
            pass
        return self._cmp(op, actual, raw_val)

    @staticmethod
    def _cmp(op: str, a: Any, b: Any) -> bool:
        if op == "==":
            return a == b
        if op == "!=":
            return a != b
        if op == "<":
            return a < b
        if op == ">":
            return a > b
        if op == "<=":
            return a <= b
        if op == ">=":
            return a >= b
        return True

    def _apply_update_state(self, fields: dict) -> None:
        for key, value in (fields or {}).items():
            if key == "{now}":
                self._apply_update_state({"debugSession.endTime": now_iso()})
                continue
            if "." in key:
                section, field = key.split(".", 1)
                if section in self.fg and isinstance(self.fg[section], dict):
                    if isinstance(value, str) and value == "+1":
                        self.fg[section][field] = self.fg[section].get(field, 0) + 1
                    else:
                        self.fg[section][field] = value
                else:
                    self.fg[key] = value
            elif key in self.fg and isinstance(self.fg[key], dict) and isinstance(value, dict):
                self.fg[key].update(value)
            elif isinstance(value, str) and value == "+1":
                self.fg[key] = self.fg.get(key, 0) + 1
            else:
                self.fg[key] = value
        save_flow_gate(self.project_dir, self.fg)

    def _result(self, status: str, message: str, **kwargs) -> dict:
        result = {
            "status": status,
            "seq": self.currentSeq,
            "phase": self.currentPhase,
            "total_steps": len(self.steps),
            "message": message,
            "next_action": kwargs.pop("next_action",
                f'{self.engine_bin} --project "{self.project_dir}" --mode 1'),
        }
        result.update(kwargs)
        return result


# ══════════════════════════════════════════════════════════════════════
# CLI 入口
# ══════════════════════════════════════════════════════════════════════

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="嵌入式调试工作流 · 单文件线性序号驱动引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python workflow_engine.py --project "e:\\proj" --init            # 新对话初始化
  python workflow_engine.py --project "e:\\proj" --mode 0          # 只读状态
  python workflow_engine.py --project "e:\\proj" --mode 1          # 执行/推进当前步骤
  python workflow_engine.py --project "e:\\proj" --ack success     # AI 步骤成功
  python workflow_engine.py --project "e:\\proj" --ack failure     # AI 步骤失败
  python workflow_engine.py --project "e:\\proj" --done            # = --ack success
  python workflow_engine.py --project "e:\\proj" --wake            # 从暂停恢复
  python workflow_engine.py --project "e:\\proj" --reset           # 重置
    python workflow_engine.py --project "e:\\proj" --set projectInfo.projectModes=full,compile_only
        """)
    parser.add_argument(
        "--project", "-p", required=True,
        help="VS Code 工作区根目录（参数名仅为历史兼容；禁止传 Skill 仓库或单个 Keil 工程目录）",
    )
    parser.add_argument("--init", action="store_true", help="初始化工作流（新对话必须先执行）")
    parser.add_argument("--reset", action="store_true", help="重置为新任务")
    parser.add_argument("--mode", type=int, choices=[0, 1], default=None,
                        help="0=只读状态 1=执行/推进当前步骤")
    parser.add_argument("--ack", choices=["success", "failure"], help="AI 步骤结果提交")
    parser.add_argument("--done", action="store_true", help="= --ack success")
    parser.add_argument("--wake", action="store_true", help="从 wait_user 暂停恢复")
    parser.add_argument("--reload-config", action="store_true",
                        help="从磁盘重载配置并清除旧项目模式")
    parser.add_argument("--set", action="append", metavar="KEY=VALUE",
                        help="设置状态字段，可多次")

    args = parser.parse_args()

    try:
        engine = WorkflowEngine(args.project)
    except FileNotFoundError as e:
        print(json.dumps({"error": str(e), "status": "fatal"},
                         ensure_ascii=False, indent=2))
        sys.exit(1)

    try:
        if args.init:
            result = engine.init()
        elif args.reset:
            result = engine.reset()
        elif args.set:
            result = engine.set_state(args.set)
        elif args.reload_config:
            result = engine.reload_config()
        elif args.wake:
            result = engine.wake()
        elif args.ack:
            result = engine.ack(args.ack == "success")
        elif args.done:
            result = engine.ack(True)
        elif args.mode == 0:
            result = engine.show_status()
        elif args.mode == 1:
            result = engine.run()
        else:
            result = engine.run()
    except ValueError as exc:
        result = engine._result(
            "error", str(exc),
            next_action=(
                f'{engine.engine_bin} --project "{engine.project_dir}" '
                '--reload-config'))

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
