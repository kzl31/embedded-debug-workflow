"""
engine/config_sync.py — 配置与项目模式同步（ConfigSyncMixin）

负责把磁盘上的工作区配置（config）同步进流程状态（flow-gate）：
  - set_state              响应 --set KEY=VALUE
  - reload_config          强制从磁盘重载并校验配置
  - _load_initialized_config  读取交互初始化结果并同步
  - _sync_project_modes    按逐项目模式生成运行状态
  - _config_snapshot_error 校验配置快照是否过期
  - _sync_execution_flags  由模式派生实际可执行能力
"""

import json


class ConfigSyncMixin:
    def set_state(self, pairs: list) -> dict:
        """写入状态字段（--set KEY=VALUE，点号语法）。"""
        from engine.state import save_flow_gate
        from engine.utils import parse_state_value
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
        from config_reader import validate_config
        from engine.state import get_config_path, save_flow_gate
        from engine.utils import load_json, config_fingerprint
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

    def _load_initialized_config(self) -> bool:
        """读取交互初始化结果并同步到流程状态。"""
        import sys
        from config_reader import validate_config
        from engine.state import get_config_path, save_flow_gate
        from engine.utils import load_json, config_fingerprint
        path = get_config_path(self.project_dir)
        try:
            config = load_json(path)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[workflow_engine] ❌ 初始化配置读取失败: {exc}", file=sys.stderr)
            return False
        errors = validate_config(config)
        if errors:
            print(f"[workflow_engine] ❌ 初始化配置校验失败: {'；'.join(errors)}",
                  file=sys.stderr)
            return False

        projects = config.get("projects", [])
        modes = config.get("project_modes", [])
        valid_modes = {"none", "compile_only", "compile_flash", "full"}
        if (not isinstance(modes, list) or len(modes) != len(projects)
                or any(mode not in valid_modes for mode in modes)):
            print("[workflow_engine] ❌ project_modes 缺失、数量不一致或包含无效模式",
                  file=sys.stderr)
            return False

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
        active_indices = [index for index, mode in enumerate(modes) if mode != "none"]
        project_info = self.fg.setdefault("projectInfo", {})
        project_info.update({
            "configFound": True,
            "projectCount": len(projects),
            "currentProjectIndex": active_indices[0] if active_indices else 0,
            "projectModes": ",".join(modes),
            "projectRuns": [
                {"index": index, "mode": mode, "stages": {}}
                for index, mode in enumerate(modes)
            ],
            "configFingerprint": config_fingerprint(config),
            "configProjects": snapshot,
            "configConfirmed": True,
            "initialQuestionsAnswered": True,
        })
        self._sync_execution_flags()
        save_flow_gate(self.project_dir, self.fg)
        print(f"[workflow_engine] ✅ 已同步 {len(projects)} 个项目模式: {','.join(modes)}")
        return True

    def _sync_project_modes(self, raw_modes: str) -> None:
        """根据逐项目模式生成能力标志和独立运行状态。"""
        from engine.state import save_flow_gate
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
        from engine.state import get_config_path
        from engine.utils import load_json, config_fingerprint
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
