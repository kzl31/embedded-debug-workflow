"""
engine/executors.py — 具体执行器（ExecutorMixin）

负责把 flow.yaml 中的原子动作真正落地：
  - _resolve_script_file  定位脚本绝对路径
  - _exec_subprocess      运行外部 Python 脚本并回收逐项目结果
  - _merge_project_results 合并多项目执行器写出的阶段结果
  - _check_file           检查工作区内是否存在目标文件
"""


import json
import sys


class ExecutorMixin:
    # ── 具体执行器 ──────────────────────────────────────────────

    def _resolve_script_file(self, cmd_str: str):
        import re
        from pathlib import Path
        from engine.constants import SKILL_DIR
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
        import re
        import subprocess
        import os
        from engine.constants import SKILL_DIR
        from engine.utils import resolve_path
        from engine.state import get_project_results_path, load_json, save_flow_gate
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
            interactive = "--interactive" in cmd
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=str(SKILL_DIR),
                timeout=600,
                env=child_env,
                stdin=None if interactive else subprocess.DEVNULL,
            )
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
        from engine.state import get_project_results_path, load_json, save_flow_gate
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
        from pathlib import Path
        from engine.utils import resolve_path
        target = params.get("target", "")
        search_paths = [resolve_path(p, self.project_dir)
                        for p in params.get("search_paths", ["{project_dir}"])]
        for sp in search_paths:
            if (Path(sp) / target).exists():
                print(f"[check_file] ✅ 找到 {target} @ {sp}", file=sys.stdout)
                return True
        print(f"[check_file] ⚠ 未找到 {target}", file=sys.stdout)
        return False
