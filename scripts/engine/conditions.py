"""
engine/conditions.py — 条件求值与状态写入（ConditionMixin）

提供：
  - _get_path      按点号路径读取状态 / 全局配置
  - _resolve_templates  递归展开 AI 参数中的占位符
  - _eval_condition 解析并比较条件表达式（path op value）
  - _cmp           数值/字符串比较
  - _apply_update_state  按点号键写入/自增状态字段
"""


class ConditionMixin:
    # ── 条件与状态工具 ──────────────────────────────────────────

    def _get_path(self, path: str):
        from engine.constants import SETTINGS
        parts = path.split(".")
        if parts and parts[0] == "settings":
            cur = SETTINGS
            parts = parts[1:]
        else:
            cur = self.fg
        for p in parts:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                return ""
        return cur

    def _resolve_templates(self, value):
        """递归展开 AI 参数中的工作区和集中配置占位符。"""
        from engine.utils import resolve_path
        import re
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

    def _expand_placeholder(self, text: str) -> str:
        """展开条件值中的 {meta.xxx} / {settings.xxx} 占位符为实际值。"""
        import re

        def repl(match):
            key = match.group(1)
            if key.startswith("meta."):
                cur = self.meta
                for part in key.split(".")[1:]:
                    if isinstance(cur, dict) and part in cur:
                        cur = cur[part]
                    else:
                        return ""
                return str(cur)
            if key.startswith("settings."):
                return str(self._get_path(key))
            return match.group(0)

        return re.sub(r"\{([\w.]+)\}", repl, text)

    def _eval_condition(self, cond: str) -> bool:
        from engine.utils import parse_state_value
        import re
        cond = (cond or "").strip()
        if not cond:
            return True
        m = re.match(r'^([\w.]+)\s*(==|!=|<=|>=|<|>)\s*(.+)$', cond)
        if not m:
            return True
        path, op, raw = m.group(1), m.group(2), m.group(3).strip()
        raw = self._expand_placeholder(raw)
        if ((raw.startswith('"') and raw.endswith('"'))
                or (raw.startswith("'") and raw.endswith("'"))):
            raw_val = raw[1:-1]
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
    def _cmp(op: str, a, b) -> bool:
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
        from engine.utils import now_iso
        from engine.state import save_flow_gate
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
