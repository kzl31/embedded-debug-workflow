#!/usr/bin/env python
"""
workflow_engine.py — 嵌入式调试工作流状态机引擎

核心理念：
  YAML 门禁文件 = 唯一真相源（流程定义）
  flow-gate.json  = 唯一状态源（进度追踪）
  本引擎         = 纯解析器 + 分发器（零硬编码步骤）

用法：
  python workflow_engine.py --project <项目目录>
      显示当前阶段/步骤状态，输出下一步指令（JSON）

  python workflow_engine.py --project <项目目录> --done
      标记当前步骤完成，自动推进到下一步

  python workflow_engine.py --project <项目目录> --reset
      重置 flow-gate.json 为新任务

  python workflow_engine.py --project <项目目录> --jump <PHASE>
      强制跳转到指定阶段

依赖：pip install pyyaml

扩展方式（无需改 Python 代码）：
  1. registry.json 注册新阶段
  2. gates/ 下创建对应的 .yaml 门禁文件
  3. 引擎自动识别新阶段和步骤类型
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# ── 尝试导入 yaml ────────────────────────────────────────────────────
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
REGISTRY_PATH = SKILL_DIR / "registry.json"
GATES_DIR = SKILL_DIR / "gates"
SCRIPTS_DIR = SKILL_DIR / "scripts"
FLOW_GATE_FILENAME = "flow-gate.json"

# 状态目录（固定）：<project_dir>/.copilot/.54188/flow-gate.json
STATE_DIR = ".copilot/.54188"

# 步骤类型 → 执行模式映射
AUTO_EXEC_TYPES = {"run_script", "check_file", "read_config", "update_state",
                   "log_info", "log_warning", "log_error", "exit_phase", "goto_step"}
AI_JUDGMENT_TYPES = {"ask_user", "edit_source", "analyze_code", "analyze_result",
                     "check_regression", "generate_report", "wait_user"}


# ══════════════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════════════

def load_json(path: Path) -> dict:
    """加载 JSON 文件，不存在则返回 {}"""
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path: Path, data: dict) -> None:
    """保存 JSON 文件，原子写入"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def load_yaml(path: Path) -> dict:
    """加载 YAML 门禁文件"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_path(template: str, project_dir: str) -> str:
    """替换路径模板中的变量"""
    return template.replace("{project_dir}", project_dir)


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ══════════════════════════════════════════════════════════════════════
# 状态管理
# ══════════════════════════════════════════════════════════════════════

def get_flow_gate_path(project_dir: str) -> Path:
    """状态文件路径：<project_dir>/.copilot/.54188/flow-gate.json

    固定目录名，状态文件统一存放于 .copilot/.54188 下，便于定位。
    """
    return Path(project_dir) / STATE_DIR / FLOW_GATE_FILENAME


def load_flow_gate(project_dir: str) -> dict:
    """加载 flow-gate.json，不存在则从模板创建"""
    path = get_flow_gate_path(project_dir)
    if path.exists():
        return load_json(path)

    # 从模板创建
    template = SKILL_DIR / "templates" / "flow-gate.json"
    if template.exists():
        data = load_json(template)
    else:
        data = _default_flow_gate()

    data["lastUpdated"] = now_iso()
    data["debugSession"]["startTime"] = now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    save_json(path, data)
    return data


def save_flow_gate(project_dir: str, data: dict, force: bool = False) -> None:
    """保存 flow-gate.json，带手动修改保护。

    如果文件已被外部（用户）手动修改（比内存中的 lastUpdated 更新），
    除非 force=True，否则跳过保存并打印警告。
    """
    fpath = get_flow_gate_path(project_dir)
    if fpath.exists() and not force:
        try:
            on_disk = json.loads(fpath.read_text(encoding="utf-8"))
            disk_ts = on_disk.get("lastUpdated", "")
            mem_ts = data.get("lastUpdated", "")
            if disk_ts and disk_ts != mem_ts:
                print(f"[workflow_engine] ⚠️ flow-gate.json 已被外部修改跳过保存"
                      f"（磁盘: {disk_ts} ≠ 内存: {mem_ts}）", file=sys.stderr)
                print(f"[workflow_engine] 💡 如需覆盖请手动删除文件或设置 force=True",
                      file=sys.stderr)
                return
        except (json.JSONDecodeError, OSError):
            pass  # 文件损坏或无法读取时仍继续保存

    data["lastUpdated"] = now_iso()
    save_json(fpath, data)


def _default_flow_gate() -> dict:
    return {
        "currentPhase": None,
        "completedPhases": [],
        "currentGateFile": None,
        "currentStepIndex": 0,
        "currentStepId": None,
        "lastUpdated": None,
        "projectInfo": {
            "configFound": False,
            "serialConfirmed": False,
            "hardwareReady": False,
            "faultDescribed": False,
            "buildMode": "full"
        },
        "debugLoopInfo": {
            "iterationCount": 0,
            "cheshiAdded": False,
            "lastBuildStatus": None,
            "lastFlashStatus": None,
            "rootCauseFound": False,
            "retryCount": 0
        },
        "verifyReport": {
            "cheshiCleaned": False
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
# 流程引擎核心
# ══════════════════════════════════════════════════════════════════════

class WorkflowEngine:
    """工作流状态机引擎"""

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.registry = load_json(REGISTRY_PATH)
        self.fg = load_flow_gate(project_dir)

        # 确保必要字段存在
        self.fg.setdefault("currentStepIndex", 0)
        self.fg.setdefault("currentStepId", None)
        self.fg["debugLoopInfo"].setdefault("retryCount", 0)
        self.fg.setdefault("verifyReport", {"cheshiCleaned": False})

        # 解析当前阶段
        phase = self.fg.get("currentPhase") or "STARTUP"
        if phase not in self.registry.get("phases", {}):
            phase = "STARTUP"

        self.current_phase = phase
        phase_def = self.registry["phases"][phase]
        self.current_gate_file = phase_def.get("gateFile")

        # 加载门禁 YAML
        self.gate_def = None
        self.steps = []
        if self.current_gate_file:
            gate_path = SKILL_DIR / self.current_gate_file
            if gate_path.exists():
                self.gate_def = load_yaml(gate_path)
                self.steps = self.gate_def.get("steps", [])

        self.step_index = self.fg.get("currentStepIndex", 0)

    # ── 主入口 ────────────────────────────────────────────────────

    def run(self) -> dict:
        """执行当前步骤，返回结果 JSON"""
        if not self.steps:
            return self._result("completed", "所有步骤已完成",
                                next_action="流程结束或使用 --reset 开始新任务")

        if self.step_index >= len(self.steps):
            return self._handle_phase_end()

        step = self.steps[self.step_index]
        self.fg["currentStepId"] = step.get("id", "")
        save_flow_gate(self.project_dir, self.fg)

        step_type = step.get("type", "unknown")
        step_desc = step.get("description", step.get("id", "未知步骤"))

        if step_type in AUTO_EXEC_TYPES:
            return self._auto_execute(step)
        else:
            return self._ai_instruction(step)

    def advance(self) -> dict:
        """标记当前步骤完成，推进到下一步，返回新步骤的指令"""
        self.step_index += 1
        self.fg["currentStepIndex"] = self.step_index
        save_flow_gate(self.project_dir, self.fg)

        if self.step_index >= len(self.steps):
            return self._handle_phase_end()

        return self.run()

    def show_status(self) -> dict:
        """只读当前状态快照，不执行任何步骤、不推进、不写文件。
        供 AI 在不改变进度的情况下查看当前位置（--mode 0）。
        """
        total = len(self.steps)
        step = None
        if self.steps and 0 <= self.step_index < total:
            step = self.steps[self.step_index]

        result = {
            "status": "state_read",
            "message": "当前状态快照（只读，未推进）",
            "phase": self.current_phase,
            "step_index": self.step_index,
            "step_id": self.fg.get("currentStepId", "") or (step.get("id", "") if step else ""),
            "total_steps": total,
            "next_action": f'python workflow_engine.py --project "{self.project_dir}" --mode 1',
        }

        if step:
            stype = step.get("type", "")
            result["current_step"] = {
                "id": step.get("id", ""),
                "type": stype,
                "description": step.get("description", ""),
            }
            if stype in AI_JUDGMENT_TYPES:
                result["status"] = "awaiting_ai"
                result["message"] = f"当前需 AI 执行: {step.get('description', '')}"
            elif stype in AUTO_EXEC_TYPES:
                result["status"] = "auto_pending"
                result["message"] = f"下一步将由引擎自动执行: {step.get('description', '')}"

        # 附加关键状态字段，作为 AI 判据（AI 无需读取外部状态文件）
        result["state"] = {
            "currentPhase": self.fg.get("currentPhase"),
            "completedPhases": self.fg.get("completedPhases", []),
            "projectInfo": self.fg.get("projectInfo", {}),
            "debugLoopInfo": self.fg.get("debugLoopInfo", {}),
            "verifyReport": self.fg.get("verifyReport", {}),
        }
        return result

    def reset(self) -> dict:
        """重置 flow-gate.json"""
        tmp = _default_flow_gate()
        tmp["lastUpdated"] = now_iso()
        tmp["debugSession"]["startTime"] = now_iso()
        self.fg = tmp
        save_flow_gate(self.project_dir, self.fg, force=True)
        self.__init__(self.project_dir)
        return self._result("reset", "已重置为新任务", phase="STARTUP",
                            next_action=f"python workflow_engine.py --project \"{self.project_dir}\"")

    def set_state(self, pairs: list) -> dict:
        """通过 --set KEY=VALUE 写入状态字段（点号语法，如 projectInfo.buildMode=full）"""
        applied = {}
        for item in pairs:
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            self._apply_update_state({key: value})
            applied[key] = value
        return self._result("state_set", f"已更新状态: {applied}", applied=applied)

    def jump(self, target_phase: str) -> dict:
        """强制跳转到指定阶段"""
        phases = self.registry.get("phases", {})
        if target_phase not in phases:
            return self._result("error", f"未知阶段: {target_phase}",
                                available=list(phases.keys()))

        phase_def = phases[target_phase]
        self.fg["currentPhase"] = target_phase
        self.fg["currentGateFile"] = phase_def.get("gateFile")
        self.fg["currentStepIndex"] = 0
        self.fg["currentStepId"] = None
        save_flow_gate(self.project_dir, self.fg)
        self.__init__(self.project_dir)
        return self.run()

    def init(self) -> dict:
        """
        显式初始化 — AI 在每次新对话开始时必须显式调用。
        区别于 reset（重置已有任务），init 是全新开始。
        初始化同时生成/确认调试配置文件 embedded-debug-config.json。
        """
        data = _default_flow_gate()
        data["currentPhase"] = "STARTUP"
        data["currentGateFile"] = "gates/STARTUP.yaml"
        data["lastUpdated"] = now_iso()
        data["debugSession"]["startTime"] = now_iso()
        save_flow_gate(self.project_dir, data, force=True)

        # 初始化时同步生成调试配置文件（已存在则跳过，保持幂等）
        try:
            # 确保子模块（config_reader）输出 emoji 时不因 GBK 控制台崩溃
            try:
                sys.stdout.reconfigure(encoding="utf-8")
                sys.stderr.reconfigure(encoding="utf-8")
            except Exception:
                pass
            from config_reader import init_project, find_config_in_project
            cfg = find_config_in_project(self.project_dir)
            if cfg:
                print(f"[init] ℹ️ 配置文件已存在，跳过生成: {cfg}")
            else:
                print("[init] 🔧 未检测到配置文件，开始初始化配置（交互式采集）...")
                init_project(self.project_dir)
        except Exception as exc:
            print(f"[init] ⚠️ 配置文件初始化失败: {exc}", file=sys.stderr)

        self.__init__(self.project_dir)
        return self._result("initialized",
            f"✅ 调试工作流已初始化（项目: {self.project_dir}）",
            phase="STARTUP",
            step_index=0,
            next_action=f"python workflow_engine.py --project \"{self.project_dir}\"")

    def set_state(self, pairs: list) -> dict:
        """通过 --set KEY=VALUE 写入状态字段（点号语法，如 projectInfo.buildMode=full）"""
        applied = {}
        for item in pairs:
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            self._apply_update_state({key: value})
            applied[key] = value
        return self._result("state_set", f"已更新状态: {applied}", applied=applied)

    # ── 步骤分发 ──────────────────────────────────────────────────

    def _auto_execute(self, step: dict) -> dict:
        """自动执行步骤（编译/下载/状态更新等）"""
        step_type = step.get("type")
        step_id = step.get("id", "")
        step_desc = step.get("description", step_id)

        handlers = {
            "run_script": self._handle_run_script,
            "check_file": self._handle_check_file,
            "read_config": self._handle_read_config,
            "update_state": self._handle_update_state,
            "log_info": self._handle_log,
            "log_warning": self._handle_log,
            "log_error": self._handle_log,
            "exit_phase": self._handle_exit_phase,
            "goto_step": self._handle_goto_step,
            "assert": self._handle_assert,
        }

        handler = handlers.get(step_type)
        if handler:
            result = handler(step)
            # run_script 已在 handler 内自行实时打印脚本输出；
            # 其余自动步骤在此把结果打印到命令行，让 AI 直接可见
            if step_type != "run_script":
                print(f"[auto:{step_id}] {result.get('message', '')}", file=sys.stdout)
            if result.get("auto_advance", True):
                return self.advance()
            return result

        return self._result("error", f"未知自动步骤类型: {step_type}")

    def _ai_instruction(self, step: dict) -> dict:
        """AI 需要执行的步骤，输出指令"""
        step_type = step.get("type")
        step_id = step.get("id", "")
        step_desc = step.get("description", step_id)

        base = self._result("awaiting_ai", step_desc,
                            step_type=step_type,
                            step_id=step_id,
                            details=step)

        if step_type == "ask_user":
            base["template"] = step.get("template", "")
            base["branches"] = step.get("branches", {})
            base["note"] = step.get("note", "")
        elif step_type == "analyze_code":
            base["inputs"] = step.get("inputs", [])
            base["output"] = step.get("output", {})
        elif step_type == "edit_source":
            base["action"] = step.get("action", "")
            base["macro_ref"] = step.get("macro_ref", "")
            base["compile_verify"] = step.get("compile_verify", False)
        elif step_type == "analyze_result":
            base["iteration_ref"] = step.get("iteration_ref", "")
            base["max_iterations"] = step.get("max_iterations", 8)
        elif step_type == "check_regression":
            base["checklist"] = step.get("checklist", [])
        elif step_type == "generate_report":
            base["report_template"] = step.get("report_template", "")
            base["report_path"] = step.get("report_path", "")
            base["report_fields"] = step.get("report_fields", [])
            base["memory_entry"] = step.get("memory_entry", {})
        elif step_type == "wait_user":
            base["message"] = step.get("message", "")

        return base

    # ── 具体处理器 ────────────────────────────────────────────────

    def _resolve_script_file(self, cmd_str: str) -> str | None:
        """从命令字符串中提取脚本文件路径，解析为绝对路径。"""
        # 匹配 python /path/to/script.py 或 python scripts/name.py
        import re
        m = re.search(r'python\s+["\']?([^\s"\']+\.py)["\']?', cmd_str, re.IGNORECASE)
        if m:
            script_rel = m.group(1)
            candidate = SKILL_DIR / script_rel
            if candidate.exists():
                return str(candidate)
            # 如果是相对路径且 skill 目录找不到，尝试当作绝对路径
            abs_candidate = Path(script_rel)
            if abs_candidate.is_absolute() and abs_candidate.exists():
                return str(abs_candidate)
        return None

    def _handle_run_script(self, step: dict) -> dict:
        """执行脚本 — 输出实时进入命令行，AI 可直接读取"""
        script_template = step.get("script", "")
        script_path = resolve_path(script_template, self.project_dir)
        wait = step.get("wait", True)
        desc = step.get("description", script_path)
        step_id = step.get("id", "")

        # ⛔ 预检：确认脚本文件存在
        script_file = self._resolve_script_file(script_path)
        if script_file is None:
            err_msg = f"脚本文件不存在: 从命令中提取的 .py 文件未找到（SKILL_DIR={SKILL_DIR})"
            print(f"[auto:{step_id}] ❌ {err_msg}\n命令: {script_path}", file=sys.stderr)
            return self._result("script_missing", err_msg,
                                auto_advance=False,
                                command=script_path)

        # 执行前检查
        precheck = step.get("precheck")
        if precheck:
            for _pc in precheck:
                pc_result = self._handle_assert({"type": "assert", **_pc})
                if pc_result.get("status") == "blocked":
                    print(f"[auto:{step_id}] ⛔ 前置检查未通过，跳过执行", file=sys.stdout)
                    return {**pc_result, "auto_advance": False}

        # 更新重试计数
        pre_action = step.get("pre_action", [])
        for pa in pre_action:
            if pa.get("type") == "update_state":
                self._apply_update_state(pa.get("fields", {}))

        # 实时打印将要执行的命令，让 AI 在命令行直接看到
        print(f"[auto:{step_id}] 🚀 执行: {script_path}", file=sys.stdout)

        try:
            child_env = os.environ.copy()
            child_env["PYTHONIOENCODING"] = "utf-8"
            # 直接继承 stdout/stderr：脚本输出实时进入命令行，AI 可直接读取
            # stdin=DEVNULL 避免子脚本等待输入而无限挂起（进程堆积/卡死）
            result = subprocess.run(
                script_path, shell=True,
                cwd=str(SKILL_DIR), timeout=120, env=child_env,
                stdin=subprocess.DEVNULL
            )
            success = result.returncode == 0

            if success:
                print(f"[auto:{step_id}] ✅ {desc} 成功 (exit={result.returncode})",
                      file=sys.stdout)
                for action in step.get("on_success", []):
                    act_result = self._apply_action(action)
                    if act_result and act_result.get("auto_advance") == False:
                        return act_result  # 终止性 action（exit_phase/goto_step）
                return self._result("auto_executed",
                    f"{desc} — ✅ 成功",
                    exit_code=result.returncode)
            else:
                print(f"[auto:{step_id}] ❌ {desc} 失败 (exit={result.returncode})",
                      file=sys.stderr)
                for action in step.get("on_failure", []):
                    act_result = self._apply_action(action)
                    if act_result and act_result.get("auto_advance") == False:
                        act_result["script_error"] = f"{desc} — ❌ 失败"
                        return act_result  # 终止性 action（exit_phase/goto_step/blocked）
                # ⛔ 脚本失败后默认不自动推进
                return self._result("auto_executed",
                    f"{desc} — ❌ 失败",
                    auto_advance=False,
                    exit_code=result.returncode)

        except subprocess.TimeoutExpired:
            print(f"[auto:{step_id}] ⏱ 超时", file=sys.stderr)
            return self._result("auto_executed", f"{desc} — ⏱ 超时", exit_code=-1)
        except Exception as e:
            print(f"[auto:{step_id}] ❌ 异常: {e}", file=sys.stderr)
            return self._result("auto_executed", f"{desc} — ❌ 异常: {e}", exit_code=-1)

    def _handle_check_file(self, step: dict) -> dict:
        """检查文件是否存在"""
        target = step.get("target", "")
        search_paths = [resolve_path(p, self.project_dir)
                       for p in step.get("search_paths", ["{project_dir}"])]

        found = False
        found_path = None
        for sp in search_paths:
            candidate = Path(sp) / target
            if candidate.exists():
                found = True
                found_path = str(candidate)
                break

        if found:
            for action in step.get("found", []):
                self._apply_action(action)
            return self._result("auto_executed", f"✅ 找到 {target}", path=found_path)
        else:
            for action in step.get("missing", []):
                self._apply_action(action)
            return self._result("auto_executed", f"⚠ 未找到 {target}，已触发缺失处理",
                                searched=search_paths)

    def _handle_read_config(self, step: dict) -> dict:
        """读取配置文件（标记已读，实际由 AI 在后续步骤中读取）"""
        return self._result("auto_executed", "配置文件已标记为已读取")

    def _handle_update_state(self, step: dict) -> dict:
        """更新 flow-gate.json 字段"""
        self._apply_update_state(step.get("fields", {}))
        return self._result("auto_executed", "状态已更新")

    def _handle_log(self, step: dict) -> dict:
        """日志输出"""
        level = step.get("type", "log_info")
        msg = step.get("message", "")
        emoji = {"log_info": "ℹ", "log_warning": "⚠", "log_error": "❌"}.get(level, "ℹ")
        return self._result("auto_executed", f"{emoji} {msg}")

    def _handle_exit_phase(self, step: dict) -> dict:
        """退出当前阶段，进入下一阶段"""
        next_phase = step.get("next_phase", "COMPLETED")
        print(f"[auto] 阶段切换 → {next_phase}", file=sys.stdout)
        update = step.get("update_state", {})

        # 处理 completedPhases 的 "+" 追加语法
        if "completedPhases" in update and isinstance(update["completedPhases"], list):
            for item in update["completedPhases"]:
                if isinstance(item, str) and item.startswith("+"):
                    phase_name = item[1:]
                    if phase_name not in self.fg.get("completedPhases", []):
                        self.fg.setdefault("completedPhases", []).append(phase_name)
            del update["completedPhases"]

        self._apply_update_state(update)

        # 阶段转换
        phases = self.registry.get("phases", {})
        if next_phase in phases:
            phase_def = phases[next_phase]
            self.fg["currentPhase"] = next_phase
            self.fg["currentGateFile"] = phase_def.get("gateFile")
            self.fg["currentStepIndex"] = 0
            self.fg["currentStepId"] = None
        else:
            self.fg["currentPhase"] = next_phase
            self.fg["currentGateFile"] = None
            self.fg["currentStepIndex"] = 0
            self.fg["currentStepId"] = None

        if next_phase == "COMPLETED":
            self.fg["debugSession"]["endTime"] = now_iso()

        save_flow_gate(self.project_dir, self.fg)

        # 重新同步内存状态（current_phase / step 列表等），
        # 否则 self.current_phase 仍是旧阶段，导致返回 JSON 的 phase 字段与
        # 已存盘的 currentPhase 矛盾（如误报 VERIFY_AND_REPORT 而非 COMPLETED）
        self.__init__(self.project_dir)

        # ⛔ 不自动推进：让 AI 重新调用引擎查看新阶段的第一步
        return self._result("phase_changed",
            f"阶段切换: → {next_phase}",
            next_phase=next_phase,
            auto_advance=False,
            next_action=f"python workflow_engine.py --project \"{self.project_dir}\"")

    def set_state(self, pairs: list) -> dict:
        """通过 --set KEY=VALUE 写入状态字段（点号语法，如 projectInfo.buildMode=full）"""
        applied = {}
        for item in pairs:
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            self._apply_update_state({key: value})
            applied[key] = value
        return self._result("state_set", f"已更新状态: {applied}", applied=applied)

    def _handle_goto_step(self, step: dict) -> dict:
        """跳转到指定步骤"""
        target_step = step.get("step", "")
        print(f"[auto] 跳转 → {target_step}", file=sys.stdout)
        target_gate = step.get("gate")

        if target_gate:
            # 跨门禁跳转
            self.fg["currentGateFile"] = target_gate
            phases = self.registry.get("phases", {})
            for pname, pdef in phases.items():
                if pdef.get("gateFile") == target_gate:
                    self.fg["currentPhase"] = pname
                    break

        # 在当前门禁中查找步骤索引
        for i, s in enumerate(self.steps):
            if s.get("id") == target_step:
                self.fg["currentStepIndex"] = i
                self.fg["currentStepId"] = target_step
                break

        save_flow_gate(self.project_dir, self.fg)
        self.__init__(self.project_dir)
        return self._result("goto_step", f"跳转到: {target_step}",
                            auto_advance=False,
                            next_action=f"python workflow_engine.py --project \"{self.project_dir}\"")

    def set_state(self, pairs: list) -> dict:
        """通过 --set KEY=VALUE 写入状态字段（点号语法，如 projectInfo.buildMode=full）"""
        applied = {}
        for item in pairs:
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            self._apply_update_state({key: value})
            applied[key] = value
        return self._result("state_set", f"已更新状态: {applied}", applied=applied)

    def _handle_assert(self, step: dict) -> dict:
        """断言检查 — 同时处理 on_success 和 on_fail"""
        condition = step.get("condition", "")
        passed = self._eval_condition(condition)

        if passed:
            # 条件满足 → 执行 on_success（如 "retryCount>=2 → 退出流程"）
            for action in step.get("on_success", []):
                self._apply_action(action)
            return {"status": "passed", "auto_advance": True}
        else:
            # 条件不满足 → 执行 on_fail（如 "retryCount<2 → 阻止继续"）
            for action in step.get("on_fail", []):
                self._apply_action(action)
            if step.get("on_fail"):
                return {"status": "blocked", "message": f"断言失败: {condition}",
                        "auto_advance": False}
            return {"status": "passed", "auto_advance": True}

    # ── 辅助方法 ──────────────────────────────────────────────────

    def _handle_phase_end(self) -> dict:
        """当前阶段所有步骤完成"""
        phase_def = self.registry.get("phases", {}).get(self.current_phase, {})
        next_phase = phase_def.get("nextPhase")

        if next_phase:
            # 自动转换阶段
            next_def = self.registry["phases"].get(next_phase, {})
            self.fg["currentPhase"] = next_phase
            self.fg["currentGateFile"] = next_def.get("gateFile")
            self.fg["currentStepIndex"] = 0
            self.fg["currentStepId"] = None
            completed = self.fg.get("completedPhases", [])
            if self.current_phase not in completed:
                completed.append(self.current_phase)
            self.fg["completedPhases"] = completed
            save_flow_gate(self.project_dir, self.fg)
            self.__init__(self.project_dir)
            return self._result("phase_completed",
                f"阶段 {self.current_phase} 完成，自动进入 {next_phase}",
                next_phase=next_phase,
                auto_advance=False,
                next_action=f"python workflow_engine.py --project \"{self.project_dir}\"")

    def set_state(self, pairs: list) -> dict:
        """通过 --set KEY=VALUE 写入状态字段（点号语法，如 projectInfo.buildMode=full）"""
        applied = {}
        for item in pairs:
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            self._apply_update_state({key: value})
            applied[key] = value
        return self._result("state_set", f"已更新状态: {applied}", applied=applied)

        return self._result("all_completed", "所有阶段已完成 ✅",
                            auto_advance=False,
                            next_action="使用 --reset 开始新任务")

    def _apply_action(self, action: dict) -> Optional[dict]:
        """执行单个 action"""
        atype = action.get("type")
        if atype == "update_state":
            self._apply_update_state(action.get("fields", {}))
        elif atype == "run_script":
            return self._handle_run_script(action)
        elif atype == "goto_step":
            return self._handle_goto_step(action)
        elif atype == "exit_phase":
            return self._handle_exit_phase(action)
        elif atype in ("log_info", "log_warning", "log_error"):
            return self._handle_log(action)
        elif atype == "assert":
            return self._handle_assert(action)
        elif atype == "wait_user":
            return {"status": "blocked", "message": action.get("message", ""),
                    "auto_advance": False}
        return None

    def _apply_update_state(self, fields: dict) -> None:
        """将 fields 字典合并到 flow-gate.json（支持点号语法如 projectInfo.configFound）"""
        for key, value in fields.items():
            if "." in key:
                # 点号语法：projectInfo.configFound → fg["projectInfo"]["configFound"]
                parts = key.split(".", 1)
                section = parts[0]
                field = parts[1]
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

    def _eval_condition(self, condition: str) -> bool:
        """简单条件求值（仅支持 retryCount < N 模式）"""
        if not condition:
            return True
        # 解析 "flow-gate.json / debugLoopInfo / retryCount < 2"
        parts = condition.replace("flow-gate.json / ", "").split(" / ")
        if len(parts) >= 2:
            section = parts[0].strip()
            field_op = parts[-1].strip()
            import re
            # 字符串比较: projectInfo / buildMode == "full"
            m_str = re.match(r'(\w+)\s*(==|!=)\s*"?([\w]+)"?', field_op)
            if m_str:
                fname = m_str.group(1)
                op = m_str.group(2)
                expected = m_str.group(3)
                actual = self.fg.get(section, {}).get(fname, "")
                if op == "==":
                    return str(actual) == expected
                elif op == "!=":
                    return str(actual) != expected
            # 数值比较: debugLoopInfo / retryCount < 2
            m = re.match(r'(\w+)\s*([<>=!]+)\s*(\d+)', field_op)
            if m:
                fname = m.group(1)
                op = m.group(2)
                threshold = int(m.group(3))
                actual = self.fg.get(section, {}).get(fname, 0)
                if op == "<":
                    return actual < threshold
                elif op == ">=":
                    return actual >= threshold
                elif op == "==":
                    return actual == threshold
        return True

    def _result(self, status: str, message: str, **kwargs) -> dict:
        """构建标准输出 JSON"""
        result = {
            "status": status,
            "phase": self.current_phase,
            "step_index": self.step_index,
            "step_id": self.fg.get("currentStepId", ""),
            "total_steps": len(self.steps),
            "message": message,
            "next_action": kwargs.pop("next_action",
                f"python workflow_engine.py --project \"{self.project_dir}\" --done")
        }
        result.update(kwargs)
        return result


# ══════════════════════════════════════════════════════════════════════
# CLI 入口
# ══════════════════════════════════════════════════════════════════════

def main():
    # 修复 Windows 控制台 GBK 编码导致的 emoji/中文输出崩溃
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="嵌入式调试工作流状态机引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python workflow_engine.py --project "e:\\proj" --mode 0 # 只读当前状态(不推进)
  python workflow_engine.py --project "e:\\proj" --mode 1 # 推进当前步骤
  python workflow_engine.py --project "e:\\proj" --init   # 新对话时先初始化
  python workflow_engine.py --project "e:\\proj" --done   # 标记完成并推进
  python workflow_engine.py --project "e:\\proj" --reset  # 重置
  python workflow_engine.py --project "e:\\proj" --jump DEBUG_LOOP
        """)
    parser.add_argument("--project", "-p", required=True, help="项目根目录")
    parser.add_argument("--init", action="store_true", help="初始化调试工作流（新对话必须先执行）")
    parser.add_argument("--done", action="store_true", help="标记当前步骤完成，推进到下一步")
    parser.add_argument("--reset", action="store_true", help="重置为新任务")
    parser.add_argument("--jump", help="跳转到指定阶段 (STARTUP/DEBUG_LOOP/VERIFY_AND_REPORT)")
    parser.add_argument("--set", action="append", metavar="KEY=VALUE",
                        help="设置状态字段，可多次，如 --set projectInfo.buildMode=full")
    parser.add_argument("--mode", type=int, choices=[0, 1], default=None,
                        help="0=只读当前状态(不推进) 1=推进当前步骤(执行)")

    args = parser.parse_args()
    project_dir = os.path.abspath(args.project)

    if not os.path.isdir(project_dir):
        print(json.dumps({
            "error": f"项目目录不存在: {project_dir}",
            "status": "fatal"
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    engine = WorkflowEngine(project_dir)

    if args.init:
        result = engine.init()
    elif args.reset:
        result = engine.reset()
    elif args.jump:
        result = engine.jump(args.jump.upper())
    elif args.set:
        result = engine.set_state(args.set)
    elif args.mode == 0:
        result = engine.show_status()
    elif args.done:
        result = engine.advance()
    elif args.mode == 1:
        result = engine.run()
    else:
        result = engine.run()

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
