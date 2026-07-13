# /kzl 新增流程 / 增加流程 — 新增步骤 / 新增阶段

> 此命令处理 `/kzl 新增流程` / `/kzl 增加流程` 和 `/kzl add-flow`。
> 功能：按数据驱动方式，向工作流中新增一个步骤或一整个阶段，**只需编辑 `flow.yaml`，无需改引擎核心代码**。

---

## 执行步骤

### Step 1: 先跑引擎，确认当前状态

```
按 SKILL.md 的规范先 --init（若新对话），再 --mode 0 查看当前 seq / phase，
确认你要新增的内容插在哪个位置（插在哪两个 seq 之间）。
```

### Step 2: 向用户澄清需求

```
question: 你要新增的是？(A) 在某个位置加一个步骤  (B) 新增一整个阶段
说明:
  - 若是 (A)：请用户说明「插在哪两个 seq 之间、什么时机、由引擎自动执行还是 AI 执行、做什么」。
  - 若是 (B)：请用户说明「新阶段的名称、插在现有流程的哪一步之前/之后、包含哪些步骤」。
```

### Step 3: 阅读新增流程指南

```
path: "{skill_dir}/refs/add-flow-guide.md"
说明: 严格按指南的「动作类型」「字段速查」「示例」来构造 flow.yaml 的步骤。
```

### Step 4: 按类型落地修改

```
规则:
  - 新增步骤: 直接在 flow.yaml 的 steps 列表里插入一项，分配连续 seq，填
             what / action / (call|params) / precheck / pre_action / on_success / on_failure。
  - 新增阶段:
      1. 在 flow.yaml 顶部 phases 新增一项（仅用于报告分组 + AI 自检 forbidden）
      2. 在 steps 列表里按 seq 顺序插入该阶段的若干步骤，用 goto 接到前后步骤
      3. 若该步骤 action=run_script，在 scripts/ 新增对应 .py
         （成功 returncode 0，失败非 0，结果打印 stdout）
  - 约束:
      - seq 必须连续唯一（建议插入后整体顺延重排）
      - id 全局唯一、语义化
      - action 必须属于指南列出的动作枚举
      - 自动步骤用 on_success/on_failure 动作列表串联；AI 步骤用 params 描述细节
      - 跳转用 on_success/on_failure 里的 goto: <seq>（或 goto: <id>）
```

### Step 5: 自检与验证

```
步骤:
  - python -m py_compile scripts/workflow_engine.py
  - python "{skill_dir}/scripts/workflow_engine.py" --init --project "<项目目录>"
  - python "{skill_dir}/scripts/workflow_engine.py" --project "<项目目录>" --mode 1
  - （可选）跑一次静态校验：确认 seq 连续、id 唯一、所有 goto 目标存在
说明: 确认引擎按新定义推进、无报错；不要手动改状态文件，一切以引擎输出为准。
```

---

## 完成后

*停止执行后续功能*，向用户汇报：
1. 新增了什么（步骤 / 阶段）；
2. 改了哪些文件（`flow.yaml` / `scripts/*.py`）；
3. 建议用户跑一次 `/kzl 帮助` 或实际走一遍验证。
