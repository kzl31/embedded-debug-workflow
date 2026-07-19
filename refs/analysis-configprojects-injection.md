# 历史问题记录：seq3 的 `configProjects` 未注入 AI 指令

> 本文件是未验证的维护者问题记录，不是当前 Skill 规则，也不应作为 AI 执行依据。现行行为以
> `flow.yaml`、引擎返回的 `ai_step.instructions` 和 `refs/core-rules.md` 为准。

> 状态：**待评审，尚未修改代码**（用户要求先出文档审阅，确认后再实施）

## 现象

`flow.yaml` 的 `seq3`（`step_collect_fault_details`，`action: ask_user`）要求 AI：

- 第 126 行：`影响项目：从 projectInfo.configProjects 动态生成选项（多选）；禁止用旧配置、固定项目名或自行猜测。`
- 第 133 行 note：`影响项目选项须来自最新 configProjects；“请问还有什么补充？”必须独立询问并等待回答。`

但 AI 实际收到的指令里**不包含 `configProjects` 的实际值**，只有一句静态文本指令。

## 根因

1. 引擎 `scripts/engine/core.py` 的 `_result`（第 242–253 行）只返回
   `status / seq / phase / total_steps / message / next_action`，**不注入 `projectInfo`**。
2. `scripts/engine/ai_instructions.py` 的 `_ai_instruction` 也未注入 `configProjects` / `projectInfo`
   （已搜索确认该模块不含 `configProjects` / `projectInfo` / `self.fg` / `injected`）。
3. `scripts/engine/conditions.py` 的 `_resolve_templates` 仅展开 `{settings.xxx}` 与 `{project_dir}`，
   不展开 `{projectInfo.xxx}`。
4. `SKILL.md` 规则 2 禁止 AI 直接读取状态文件（`flow-gate.json`）。

→ AI 执行 seq3 时既拿不到 `configProjects`，又被禁止读文件，只能靠运行
`python scripts/config_reader.py --get projects` 变通，或直接猜测（正是 seq3 note 禁止的）。

## 影响

AI 无法正确生成"影响项目"的多选选项，可能退化为固定项目名 / 旧配置 / 自行猜测，
违背 seq3 的强制约束，并可能导致后续 `multi_project_runner.py --modes` 与真实项目不匹配。

## 建议方案（待定，未实施）

- **方案 A（推荐）**：在 `_ai_instruction` 中，对 `ask_user` 类步骤把
  `projectInfo.configProjects`（只读快照：index/name/dir/file/serial/debugger）注入指令 `params`，
  使 AI 能直接生成选项。
- **方案 B**：扩展 `_resolve_templates` 支持 `{projectInfo.configProjects}` 占位符，
  seq3 模板改用占位符，由引擎展开。
- **方案 C**：明确允许 AI 在 seq3 运行 `config_reader.py --get projects` 获取列表
  （需在 `SKILL.md` 规则 2 的边界说明中放宽，避免与"禁止读状态文件"冲突）。

## 关联文件

- `flow.yaml` seq3（第 116–144 行）
- `scripts/engine/core.py` → `_result`
- `scripts/engine/ai_instructions.py` → `_ai_instruction`
- `scripts/engine/conditions.py` → `_resolve_templates`
- `SKILL.md` 规则 2、条件语法示例（第 166 行）
- `scripts/engine/config_sync.py` → `_load_initialized_config` / `_sync_project_modes`
  （已确认 `projectInfo.configProjects` 由引擎正确写入 flow-gate，数据源没问题，只是没交给 AI）
