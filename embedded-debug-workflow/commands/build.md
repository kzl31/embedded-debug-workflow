# /kzl 编译 || /kzl 编译下载 — 编译 / 编译+下载固件

> 本命令处理两类触发：
>   - `/kzl 编译`  / `/kzl 编译`      → **仅编译**（不下载固件）
>   - `/kzl 编译下载` / `/kzl 编译下载` → 编译 + 下载固件
>   （兼容旧别名：`/kzl build` 等效 `/kzl 编译xz`）
>
> 功能：先（按需）修改代码，再执行编译；`byxz` 额外下载固件到设备。
> **两个命令都必须已初始化**，未初始化即判定流程违规，按 `templates/abort-report.md` 退出。

---

## 执行步骤

### ⛔ 前置：引擎预检 / 流程门禁（必须已初始化）

```yaml
action: engine_precheck
说明: 按 SKILL.md 的流程门禁纪律执行：先 --init（新对话），再 --mode 0 确认当前步骤与阶段允许编译/下载
```

### Step 1: 确认需求与范围

```yaml
action: ask_user
question: |
  本次目标确认：
  1) 要改哪些代码？（若代码已改好，只想编译/下载，直接回车跳过）
  2) 是否下载固件？（/kzl 编译 默认不下载，/kzl 编译xz 默认下载；与默认不同请说明）
说明: 改代码为可选步骤；下载与否由命令类型（by / byxz）或用户明确说明决定
```

### Step 2: 分析设计（仅当要改代码时执行）

```yaml
action: analyze
条件: 用户在 Step 1 中提供了要改的代码需求
遵守规范: 本 skill 的强制规则（refs/core-rules.md）
  - 规则2: Git 版本管控 — 修改前先 git commit 当前状态
  - 规则3: CHESHI 宏规范 — 如需加调试打印，统一用 CHESHI 宏
动作: 通读相关源文件、理清逻辑、设计修改方案、覆盖边界情况
```

### Step 3: Git 快照（仅当要改代码时执行）

```yaml
action: git_commit
条件: 用户在 Step 1 中提供了要改的代码需求
message: "temp: 修改前快照 — {description}"
说明: 修改代码前先提交当前状态，方便回退
```

### Step 4: 修改代码（仅当要改代码时执行）

```yaml
action: edit_code
条件: 用户在 Step 1 中提供了要改的代码需求
说明: 按设计方案修改代码，确保功能完整实现
```

### Step 5: 读取配置

```yaml
action: read_config
说明: 读取项目 .copilot/embedded-debug-config.json，获取工程路径和 UV4 路径
```

### Step 6: 编译 [+ 下载]

```yaml
action: run_script
说明: |
  根据命令类型调用对应脚本（编译用独立 keil_build.py，下载用 keil_flash.py）：

  - /kzl 编译（仅编译当前文档所属项目）：
    python "{skill_dir}/scripts/keil_build.py" --config-dir "{project_dir}" --project-index "{current_project_index}"

  - /kzl 编译下载（仅在用户明确确认后执行当前项目）：
    python "{skill_dir}/scripts/build_and_flash.py" --config-dir "{project_dir}" --project-index "{current_project_index}"

  默认针对当前文档所属项目执行增量编译（仅编译修改过的文件，速度快），其他项目默认跳过。
  只有用户明确选择并确认 `full` 模式时，才执行编译后下载；不要将完整编译下载作为默认动作。
  成功后（byxz）自动下载。
  以下情况需使用 --rebuild（全编译）：
  - 修改了 .uvprojx/.uvproj 工程配置
  - 新增或修改了 CHESHI 宏定义
  - 增量编译报错提示需 clean/rebuild
  如遇上述情况，AI 应询问用户是否接受全编译耗时。
```

### Step 7: 检查结果

```yaml
action: check_output
# /kzl 编译（仅编译）
keywords_by: ["0 Error", "0 Warning"]
on_success_by: ✅ 编译完成
# /kzl 编译下载（编译+下载）
keywords_byxz: ["0 Error", "0 Warning", "Flash Load finished", "下载成功"]
on_success_byxz: ✅ 编译下载完成
on_failure: ⚠️ 编译或下载出错，请检查输出日志
```

---

## 完成后

告知用户本次结果（编译成功/失败；byxz 额外说明下载成功/失败），无需进入调试循环。

> 未初始化就执行本命令 → 流程违规，立即停止并输出 `templates/abort-report.md` 中止通告。
