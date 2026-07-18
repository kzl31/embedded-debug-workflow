"""
engine/ai_instructions.py — AI 步骤指令与终止态（AIInstructionMixin）

负责：
  - _ai_instruction  生成 AI 步骤需要执行的工作指令
  - _waiting / _completed           暂停态与完成态输出
"""


import sys


class AIInstructionMixin:
    # ── AI 步骤指令 ─────────────────────────────────────────────

    def _ai_instruction(self, step: dict) -> dict:
        params = self._resolve_templates(step.get("params", {}))
        action = step.get("action", "")
        result = self._result("awaiting_ai", step.get("what", ""),
                              seq=step.get("seq"), id=step.get("id"),
                              phase=step.get("phase"), action=step.get("action"),
                              what=step.get("what"),
                              params=params,
                              forbidden=self._phase_forbidden(step.get("phase")))
        # Keep the full execution contract visible to the agent. The short
        # message alone is not sufficient for multi-part AI workflow steps.
        result["ai_step"] = {
            "required": True,
            "action": action,
            "objective": step.get("what", ""),
            "phase": step.get("phase"),
            "instructions": params,
            "completion": "完成本步骤规定的全部动作后才能提交 ack",
            "failure": "无法完成或证据不足时提交 ack failure，不得伪造成功",
        }
        result["next_action"] = (
            f'{self.engine_bin} --project "{self.project_dir}" --ack success'
            f'   （若未达成目标用 --ack failure）')
        return result

    # ── 终止状态 ────────────────────────────────────────────────

    def _waiting(self) -> dict:
        return self._result("awaiting_user", self.wait_msg or "等待用户处理",
                            seq=self.currentSeq, phase=self.currentPhase,
                            next_action=f'{self.engine_bin} --project "{self.project_dir}" --wake')

    def _completed(self) -> dict:
        from engine.state import save_flow_gate
        from engine.utils import now_iso
        self.fg["currentPhase"] = "COMPLETED"
        self.fg.setdefault("completedPhases", [])
        if "VERIFY_AND_REPORT" not in self.fg["completedPhases"]:
            self.fg["completedPhases"].append("VERIFY_AND_REPORT")
        if not self.fg.get("debugSession", {}).get("endTime"):
            self.fg["debugSession"]["endTime"] = now_iso()
        save_flow_gate(self.project_dir, self.fg)
        return self._result("completed", "🎉 所有流程已完成",
                            next_action=f'{self.engine_bin} --project "{self.project_dir}" --reset')
