"""
engine/core.py — 引擎核心（CoreMixin）

负责：
  - __init__           加载 flow.yaml / flow-gate，初始化驱动中间态
  - 基础查询           _current_step / _seq_of_id / _is_auto / _phase_forbidden
  - 序号推进           _set_current_seq / _add_completed
  - 对外主入口         run / ack / wake / show_status / reset / init
  - 统一结果构造       _result
"""


import sys


class CoreMixin:
    def __init__(self, project_dir: str):
        # 确保 Windows GBK 控制台下 emoji/中文打印不崩溃
        import sys
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

        import os
        from pathlib import Path
        from engine.constants import SKILL_DIR, AUTO_TYPES
        from engine.utils import load_yaml, now_iso
        from engine.state import (
            load_flow_gate,
            load_progress_display_enabled,
            _default_flow_gate,
        )

        self.project_dir = os.path.abspath(project_dir)
        if not os.path.isdir(self.project_dir):
            raise FileNotFoundError(f"VS Code 工作区目录不存在: {self.project_dir}")

        # 加载流程定义（flow.yaml）
        self.flow = load_yaml(SKILL_DIR / "flow.yaml")
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
        self.next_seq = None
        self.finished = False
        pause_state = self.fg.get("pauseState", {})
        self.waiting = bool(pause_state.get("waiting", False))
        self.wait_msg = str(pause_state.get("reason", "") or "")
        self.progress_display_enabled = load_progress_display_enabled(self.project_dir)
        self.displayed_seqs = set()

        # 引擎可执行文件（用于生成 next_action 指令，指向对外入口）
        self.engine_bin = f'python "{SKILL_DIR / "scripts" / "workflow_engine.py"}"'

    # ── 基础查询 ────────────────────────────────────────────────

    def _current_step(self):
        if 1 <= self.currentSeq <= len(self.steps):
            return self.steps[self.currentSeq - 1]
        return None

    def _seq_of_id(self, step_id: str):
        for s in self.steps:
            if s.get("id") == step_id:
                return s.get("seq")
        return None

    def _is_auto(self, step: dict) -> bool:
        from engine.constants import AUTO_TYPES
        return step.get("action") in AUTO_TYPES

    def _phase_forbidden(self, phase: str) -> list:
        return self.phases.get(phase, {}).get("forbidden", [])

    def _set_current_seq(self, seq: int) -> None:
        from engine.state import save_flow_gate
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
        actions = step.get("on_success") if ok else step.get("on_failure")
        self._run_actions(actions, default_next=True)
        return self._drive()

    def wake(self) -> dict:
        """从 wait_user 暂停恢复，重新执行当前步骤（--wake）。"""
        from engine.state import save_flow_gate
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
            from engine.constants import AI_TYPES
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
        import os
        from pathlib import Path
        from engine.constants import WORKSPACE_DATA_DIR, LOGS_DIRNAME, REPORTS_DIRNAME
        from engine.state import save_flow_gate, _default_flow_gate
        from engine.utils import now_iso
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
