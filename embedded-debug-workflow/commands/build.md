# /kzl 编译 — 修改代码 → 编译 → 下载固件

> 此命令处理 `/kzl 编译` 和 `/kzl build`。
> 功能：先根据用户需求修改代码，再编译并下载固件到设备，完成后结束。

---

## 执行步骤

### ⛔ 前置：Flow Gate 预检

```yaml
type: flow_gate_precheck
说明: 按 SKILL.md 的 Flow Gate 门禁预检步骤执行，确保流程合规
```

### Step 1: 理解需求

```yaml
type: ask_user
question: 要实现什么功能？请描述完整的业务需求
说明: 不局限于"改哪里"，而是明确"要达到什么效果"
```

### Step 2: 分析并设计

```yaml
type: analyze
遵守规范: 本 skill 的强制规则（refs/core-rules.md）
  - 规则2: Git 版本管控 — 修改前先 git commit 当前状态，修改走本地提交
  - 规则3: CHESHI 宏规范 — 如需加调试打印，统一用 CHESHI 宏
  - 其他: 涉及的相关规范按需读取 refs/ 对应文档
动作:
  - 找到涉及的相关源文件，通读上下文
  - 理清现有逻辑流程
  - 设计符合功能需求的修改方案
  - 确认覆盖所有边界情况
说明: 确保修改符合本 skill 规范，完整、正确，不遗漏任何关联逻辑
```

### Step 3: Git 快照

```yaml
type: git_commit
message: "temp: 修改前快照 — {description}"
说明: 修改代码前先提交当前状态，方便回退
```

### Step 4: 修改代码

```yaml
type: edit_code
说明: 按设计方案修改代码，确保功能完整实现
```

### Step 5: 读取配置

```yaml
type: read_config
说明: 读取项目 .copilot/embedded-debug-config.json，获取工程路径和 UV4 路径
```

### Step 6: 编译 + 下载

```yaml
type: run_script
script: python "{skill_dir}/scripts/build_and_flash.py" --config-dir "{project_dir}"
说明: |
  默认增量编译（仅编译修改过的文件，速度快），成功后自动下载。
  
  以下情况需使用 --rebuild（全编译，速度慢）：
  - 修改了 .uvprojx/.uvproj 工程配置
  - 新增或修改了 CHESHI 宏定义
  - 增量编译报错提示需 clean/rebuild
  如遇上述情况，AI 应询问用户是否接受全编译耗时。
```

### Step 7: 检查结果

```yaml
type: check_output
keywords: ["0 Error", "0 Warning", "Flash Load finished", "下载成功"]
on_success: ✅ 编译下载完成
on_failure: ⚠️ 编译或下载出错，请检查输出日志
```

---

## 完成后

告知用户编译下载结果（成功/失败及简要信息），无需进入调试循环。
