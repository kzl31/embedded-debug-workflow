"""
engine/auto_steps.py — 自动步骤驱动（AutoStepMixin）

负责：
  - _drive          链式推进，直到遇到 AI 步骤 / 完成 / 暂停
  - _execute_auto   执行单个自动步骤（前置断言 → 动作 → 分支）
  - _run_actions    顺序执行动作列表（支持 when/then/else 与终止）
  - _run_action     单个动作分发
  - _set_next / _do_exit / _do_wait / _do_log  流向控制原语
"""


import sys

from engine.utils import now_iso


class AutoStepMixin:
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

    def _run_action(self, action) -> "str | None":
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
                if not self._load_initialized_config():
                    self._do_wait("初始化配置或项目模式读取失败，请重新运行初始化。")
                    return "terminate"
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

    def _set_next(self, val) -> None:
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
        from engine.state import save_flow_gate
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

    def _do_log(self, aval) -> None:
        if isinstance(aval, dict):
            level = aval.get("level", "info")
            msg = aval.get("msg", "")
        else:
            level = "info"
            msg = str(aval)
        emoji = {"info": "ℹ", "warning": "⚠", "error": "❌"}.get(level, "ℹ")
        print(f"[{level}] {emoji} {msg}", file=sys.stdout)
