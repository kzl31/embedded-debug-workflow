# /kzl 增加流程 — 新增步骤 / 新增阶段

> 此命令处理 `/kzl 增加流程` 和 `/kzl add-flow`。
> 功能：按数据驱动方式，向工作流中新增一个步骤或一整个阶段，无需改引擎核心代码。

---

## 执行步骤

### Step 1: 先跑引擎，确认当前状态

```yaml
type: flow_gate_precheck
说明: 按 SKILL.md 的规范先 `--init`（若新对话），再 `--mode 0` 查看当前阶段与步骤，
     确认你要新增的内容插在哪个位置。
```

### Step 2: 向用户澄清需求

```yaml
type: ask_user
question: 你要新增的是？(A) 在某个阶段里加一个步骤  (B) 新增一整个阶段
说明: |
  - 若是 (A)：请用户说明「加到哪个阶段、什么时机、由引擎自动执行还是 AI 执行、做什么」。
  - 若是 (B)：请用户说明「新阶段的名称、插在现有流程的哪一步之前/之后、包含哪些步骤」。
```

### Step 3: 阅读新增流程指南

```yaml
type: read_doc
path: "{skill_dir}/refs/add-flow-guide.md"
说明: 严格按指南的「步骤类型」「字段速查」「示例」来构造 YAML / registry 条目 / 脚本。
```

### Step 4: 按类型落地修改

```yaml
type: edit_files
规则:
  - 新增步骤: 编辑对应 gates/<PHASE>.yaml 的 steps 列表（参考指南 第3节）
  - 新增阶段:
      1. 在 registry.json 的 phases 新增一项并接好 nextPhase 链
      2. 新建 gates/<NEWPHASE>.yaml（参考指南 第4节）
      3. 若该阶段含 run_script，在 scripts/ 新增对应 .py（成功 returncode 0，失败非0，结果打印 stdout）
  - 约束:
      - id 全局唯一、语义化
      - type 必须属于指南第2节列出的类型
      - 自动步骤用 on_success/on_failure 串联；AI 步骤用 template/branches/action 描述
```

### Step 5: 自检与验证

```yaml
type: verify
步骤:
  - python -m py_compile scripts/workflow_engine.py
  - python "{skill_dir}/scripts/workflow_engine.py" --init --project "<项目目录>"
  - python "{skill_dir}/scripts/workflow_engine.py" --project "<项目目录>" --mode 1
说明: 确认引擎按新定义推进、无报错；不要手动改状态文件，一切以引擎输出为准。
```

---

## 完成后

*停止执行后续功能*，向用户汇报：
1. 新增了什么（步骤 / 阶段）；
2. 改了哪些文件（`registry.json` / `gates/*.yaml` / `scripts/*.py`）；
3. 建议用户跑一次 `/kzl 帮助` 或实际走一遍验证。
