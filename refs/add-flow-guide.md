# 新增流程 / 步骤 指南

> 本 Skill 的流程是**数据驱动**的：`flow.yaml` = 唯一真相源（线性序号步骤表），
> 引擎 `workflow_engine.py` = 纯查表 + 序号跳转解析器（零硬编码步骤）。
> 新增步骤/阶段**几乎不用改 Python**，只需编辑 `flow.yaml`。

---

## 1. 架构速览（改哪里）

| 文件 | 作用 | 改它来… |
|------|------|---------|
| `flow.yaml` | 流程唯一真相源（线性 `seq` 步骤表 + `phases` 分组 + `meta` 配置） | 新增/调整**步骤**或**阶段** |
| `scripts/*.py` | `run_script` 步骤实际调用的脚本 | 新增**自动执行的能力** |
| `refs/*.md` | AI 步骤参考文档 | 给 AI 步骤补充规范说明 |

---

## 2. 动作类型（必须先懂）

引擎把所有步骤按 `action` 分成两类：

**A. 引擎自动执行（写进 flow.yaml 即可，引擎自己跑脚本/改状态）**
- `run_script` — 执行 `call:` 指定的命令（编译/下载/串口等，`{project_dir}` 会被替换）
- `check_file` — 检查文件是否存在，分别走 `on_success` / `on_failure`
- `read_config` — 标记配置已读
- `update_state` — 在 `on_success`/`on_failure` 的 do 列表里直接改状态
- `log` — 打印提示（`log: "msg"` 或 `log: {level: info|warning|error, msg: "..."}`）
- `exit` — 标记流程完成（`action: exit`，`on_success` 里 `goto: done`）
- `noop` — 空操作，常用于阶段衔接 / 纯跳转

**B. AI 执行（引擎只输出指令，等 AI 做完再 `--ack`）**
- `ask_user` — 向用户提问（问题模板写在 `params.template`）
- `edit_source` — 改代码（`params.edit_action`: `insert_cheshi` / `remove_cheshi` / `fix_bug`）
- `analyze` — 分析日志/代码，定位可疑点（`params.mode`: `locate` / `root_cause`）
- `report` — 生成报告 + 写记忆（`params.report_template` / `report_path` / `memory_entry`）
- `check_regression` — 回归核对清单（`params.checklist`）
- `wait_user` — 等用户给思路（一般写在 `when` 条件的 `then` 分支里）

---

## 3. 步骤的统一格式

每个 step **格式完全相同**：

```yaml
  - seq: 6                       # 全局唯一、连续的序号（线性编号）
    id: step_compile             # 可选但建议：语义化 id（goto 也可写 goto: step_compile）
    phase: DEBUG_LOOP            # 阶段分组标签（仅用于报告与 AI 自检 forbidden）
    what: "编译固件"             # 给 AI 读的一句话：这一步做什么
    action: run_script           # 动作类型（见第 2 节枚举）
    call: 'python scripts/keil_build.py --config-dir "{project_dir}"'  # 脚本命令（action=run_script 时）
    precheck: []                 # 执行前断言列表（元素 {assert: "条件", on_fail: [动作...]}）
    pre_action: []               # 执行前动作列表（如重试计数 +1）
    on_success: [ ... ]          # 成功后的「动作列表」
    on_failure: [ ... ]          # 失败后的「动作列表」
```

### on_success / on_failure 是「动作列表」

每个元素是一个单键对象，常见动作：

| 动作 | 写法 | 说明 |
|------|------|------|
| 更新状态 | `- update_state: { debugLoopInfo.x: "success" }` | `+1` 表示自增 |
| 执行脚本 | `- run_script: 'python scripts/xxx.py ...'` | 自动步骤里可再调脚本 |
| 打印日志 | `- log: "提示"` 或 `- log: {level: warning, msg: "..."}` | |
| 读配置 | `- read_config: {}` | |
| 跳转 | `- goto: 5` / `- goto: step_add_cheshi` / `- goto: next` / `- goto: done` / `- goto: wait` | 序号 / id / 下一步 / 结束 / 暂停 |
| 结束 | `- exit: COMPLETED` | 标记流程完成 |
| 人工暂停 | `- wait_user: "提示"` | 等用户，`--wake` 恢复 |
| 条件 | `- when: "条件"`<br>&nbsp;&nbsp;`then: [ ... ]`<br>&nbsp;&nbsp;`else: [ ... ]` | 条件成立走 then，否则走 else |

> **要点**：`on_success` / `on_failure` 里的「做什么」和「是否跳转」都在这一个列表里表达。
> 列表里出现 `goto` / `exit` / `wait_user` 即终止（不再执行后续动作）；
> 若列表里**没有**跳转动作，引擎默认推进到 `seq+1`。

---

## 4. 新增一个步骤（最常见）

打开 `flow.yaml`，在 `steps:` 列表里插入一项，分配连续 `seq`，并让前后步骤的 `goto` 接到它。

### 例 4.1：在编译前加一个「上电复位」自动步骤（插在 seq 5 与 seq 6 之间）

原 seq 5（step_add_cheshi）的 `on_success` 本为 `goto: 6`，改为 `goto: 6_新序号`（假设新序号 6，原 6 顺延为 7…）。
为清晰，可直接在任何位置插入并改相关 `goto`：

```yaml
  - seq: 6
    id: step_power_cycle
    phase: DEBUG_LOOP
    what: "给目标板一个硬件复位脉冲"
    action: run_script
    call: 'python scripts/power_cycle.py --config-dir "{project_dir}"'
    precheck: []
    pre_action: []
    on_success:
      - update_state: { debugLoopInfo.lastPowerCycle: "success" }
      - goto: 7          # 原 step_compile 已顺延为 seq 7
    on_failure:
      - log: { level: warning, msg: "复位失败，继续后续步骤" }
      - goto: 7
```

并把原 `step_add_cheshi`（seq 5）的 `on_success` 里 `goto: 6` 改为 `goto: 6`（指向本步骤）。

### 例 4.2：新增一个 AI 步骤（让用户确认环境）

```yaml
  - seq: 50
    id: step_confirm_env
    phase: DEBUG_LOOP
    what: "确认实验室温箱温度已稳定"
    action: ask_user
    params:
      template: |
        请确认当前环境：
          1️⃣ 温箱是否已达设定温度？   【是 / 否，当前温度 __】
    precheck: []
    pre_action: []
    on_success:
      - update_state: { projectInfo.envConfirmed: true }
      - goto: 51
    on_failure:
      - wait_user: "请等待温箱稳定后再继续"
```

> AI 步骤执行完后调 `--ack success`（走 `on_success`）或 `--ack failure`（走 `on_failure`）。

---

## 5. 新增一个阶段

阶段在 `flow.yaml` 里只是 **`phases` 列表里的一项标签**（用于报告分组与 AI 自检），
真正的流程靠 `steps` 的 `seq` 顺序 + `goto` 衔接。

### Step 1：在 `phases` 加一项（可选，纯标签）

```yaml
phases:
  - name: PRE_FLIGHT
    description: "起飞前检查 — 环境/供电/探针确认"
    forbidden: [compile, flash]
```

### Step 2：在 `steps` 里按 seq 插入该阶段的步骤，用 `goto` 接到前后

```yaml
  - seq: 1
    id: step_check_power
    phase: PRE_FLIGHT
    what: "确认供电正常"
    action: check_file
    params:
      target: power_ok.flag
      search_paths: ["{project_dir}"]
    precheck: []
    pre_action: []
    on_success:
      - update_state: { projectInfo.powerOk: true }
      - goto: 2
    on_failure:
      - ask_user: "未检测到 power_ok.flag，请确认供电后创建标记文件"   # 实际用 action: ask_user 步骤更规范
      - goto: 2
```

> `phase` 字段切换时，引擎会自动把「上一个 phase」记入 `completedPhases`，无需手动维护。

### Step 3（可选）：若步骤 `action: run_script`，在 `scripts/` 加对应 `.py`

脚本约定：
- 通过 `--config-dir "{project_dir}"` 接收项目目录；
- 成功 `returncode == 0`，失败非 0；
- 把关键结果打印到 stdout（引擎会实时转发给 AI 看）。

---

## 6. 字段速查

| 字段 | 适用 | 说明 |
|------|------|------|
| `seq` | 全部 | 连续唯一的全局序号（线性编号） |
| `id` | 全部 | 语义化唯一标识（goto 可写 `goto: <id>`） |
| `phase` | 全部 | 阶段分组标签（STARTUP/DEBUG_LOOP/VERIFY_AND_REPORT…） |
| `what` | 全部 | 给 AI 看的一句话说明 |
| `action` | 全部 | 见第 2 节枚举 |
| `call` | `run_script` | 要执行的命令，`{project_dir}` 会被替换 |
| `params` | `ask_user`/`edit_source`/`analyze`/`report`/`check_regression`/`check_file` | 该动作的详细参数 |
| `precheck` | 全部 | 执行前断言 `{assert: "条件", on_fail: [动作...]}` |
| `pre_action` | 全部 | 执行前动作列表（如 `update_state: {debugLoopInfo.retryCount: "+1"}`） |
| `on_success` / `on_failure` | 全部 | 成功/失败后的「动作列表」（见第 3 节） |

---

## 7. 验证改动

```bash
# 语法检查
python -m py_compile scripts/workflow_engine.py

# 静态校验：seq 连续、id 唯一、所有 goto 目标存在
python -c "import yaml; d=yaml.safe_load(open('flow.yaml',encoding='utf-8')); s=d['steps']; assert [x['seq'] for x in s]==list(range(1,len(s)+1))"

# 新对话初始化
python scripts/workflow_engine.py --init --project "<项目目录>"

# 推一步看引擎是否按新 flow.yaml 走
python scripts/workflow_engine.py --project "<项目目录>" --mode 1
```

> ⚠️ 新增/修改流程后，**不要**手动改状态文件；一切以引擎输出 JSON 为判据。
