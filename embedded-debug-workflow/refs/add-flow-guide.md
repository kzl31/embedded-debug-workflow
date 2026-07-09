# 新增流程 / 步骤 指南

> 本 Skill 的流程是**数据驱动**的：YAML 门禁 = 流程定义，registry.json = 阶段注册中心，
> 引擎 = 纯解析器（零硬编码步骤）。新增步骤/阶段**几乎不用改 Python**。

---

## 1. 架构速览（改哪里）

| 文件 | 作用 | 改它来… |
|------|------|---------|
| `registry.json` | 阶段注册中心（阶段顺序、门禁文件、禁止操作） | 新增一个**阶段** |
| `gates/*.yaml` | 某阶段的步骤序列（唯一真相源） | 新增/调整**步骤** |
| `scripts/*.py` | `run_script` 步骤实际调用的脚本 | 新增**自动执行的能力** |
| `refs/*.md` | AI 步骤参考文档 | 给 AI 步骤补充规范说明 |

---

## 2. 步骤类型（必须先懂）

引擎把所有步骤分成两类（`scripts/workflow_engine.py` 的 `AUTO_EXEC_TYPES` / `AI_JUDGMENT_TYPES`）：

**A. 引擎自动执行（写进 YAML 即可，引擎自己跑脚本/改状态）**
- `run_script` — 执行 `script:` 指定的 Python 脚本（编译/下载/串口等）
- `check_file` — 检查文件是否存在，触发 `found:` / `missing:` 分支
- `read_config` — 标记配置已读
- `update_state` — 直接改状态字段
- `log_info` / `log_warning` / `log_error` — 打印提示
- `exit_phase` — 阶段切换
- `goto_step` — 跳回/跳到某步骤

**B. AI 执行（引擎只输出指令，等 AI 做完再 `--done`）**
- `ask_user` — 向用户提问（问题由 AI 转述，用户在对话里回答）
- `edit_source` — 改代码（如插入/清理 CHESHI、修 bug）
- `analyze_code` — 分析日志/代码，定位可疑点
- `analyze_result` — 判断是否定位根因
- `check_regression` — 回归核对清单
- `generate_report` — 生成报告 + 写记忆
- `wait_user` — 等用户给思路

---

## 3. 新增一个步骤（最常见）

打开对应的 `gates/<PHASE>.yaml`，在 `steps:` 列表里加一个元素。

### 例 3.1：在 DEBUG_LOOP 编译前加一个「上电复位」自动步骤

```yaml
  - id: step_power_cycle
    description: "给目标板一个硬件复位脉冲"
    type: run_script
    script: 'python scripts/power_cycle.py --config-dir "{project_dir}"'
    on_success:
      - type: update_state
        fields:
          debugLoopInfo.lastPowerCycle: "success"
    on_failure:
      - type: log_warning
        message: "复位失败，继续后续步骤"
```

要点：
- `id` 全局唯一、语义化。
- `type` 决定谁执行（见第 2 节）。
- 自动步骤用 `on_success` / `on_failure` 串联后续动作（`update_state` / `goto_step` / `exit_phase` 等）。

### 例 3.2：新增一个 AI 步骤（让用户确认环境）

```yaml
  - id: step_confirm_env
    description: "确认实验室温箱温度已稳定"
    type: ask_user
    template: |
      请确认当前环境：
        1️⃣ 温箱是否已达设定温度？   【是 / 否，当前温度 __】
    branches:
      confirmed:
        - type: update_state
          fields:
            projectInfo.envConfirmed: true
      not_ready:
        - type: wait_user
          message: "请等待温箱稳定后再继续"
```

---

## 4. 新增一个阶段（registry + 门禁文件）

### Step 1：在 `registry.json` 的 `phases` 加一项

```json
"PRE_FLIGHT": {
  "gateFile": "gates/PRE_FLIGHT.yaml",
  "description": "起飞前检查 — 环境/供电/探针确认",
  "forbiddenOperations": ["compile", "flash"],
  "nextPhase": "STARTUP"
}
```

并把上一阶段（如 `COMPLETED` 之外你想接在谁前面）的 `nextPhase` 改成 `"PRE_FLIGHT"`，
或把 `PRE_FLIGHT` 的 `nextPhase` 指向原首阶段。

### Step 2：新建 `gates/PRE_FLIGHT.yaml`

```yaml
phase: PRE_FLIGHT
description: "起飞前检查"
version: 1
steps:
  - id: step_check_power
    description: "确认供电正常"
    type: check_file
    target: power_ok.flag
    search_paths: ["{project_dir}"]
    found:
      - type: update_state
        fields: { projectInfo.powerOk: true }
    missing:
      - type: ask_user
        template: "未检测到 power_ok.flag，请确认供电后创建标记文件"
  - id: step_exit
    description: "完成 PRE_FLIGHT，进入 STARTUP"
    type: exit_phase
    next_phase: STARTUP
    update_state:
      currentPhase: "STARTUP"
      completedPhases: ["+PRE_FLIGHT"]
      currentGateFile: "gates/STARTUP.yaml"
```

### Step 3（可选）：若阶段里有 `run_script`，在 `scripts/` 加对应 `.py`

脚本约定：
- 通过 `--config-dir "{project_dir}"` 接收项目目录；
- 成功 `returncode == 0`，失败非 0；
- 把关键结果打印到 stdout（引擎会实时转发给 AI 看）。

---

## 5. 通用字段速查

| 字段 | 适用类型 | 说明 |
|------|---------|------|
| `id` | 全部 | 步骤唯一标识 |
| `description` | 全部 | 给人/AI 看的一句话 |
| `type` | 全部 | 见第 2 节 |
| `script` | `run_script` | 要执行的命令，`{project_dir}` 会被替换 |
| `on_success` / `on_failure` | `run_script`/`check_file` | 成功/失败后的动作链 |
| `found` / `missing` | `check_file` | 文件存在/不存在时的动作链 |
| `target` / `search_paths` | `check_file` | 待查文件与搜索路径 |
| `template` / `branches` | `ask_user` | 问题模板与分支动作 |
| `action` / `macro_ref` | `edit_source` | 编辑动作类型与参考文档 |
| `next_phase` / `update_state` | `exit_phase` | 目标阶段与要写的状态 |
| `step` / `gate` | `goto_step` | 目标步骤 id（可跨门禁） |
| `condition` / `on_success` / `on_fail` | `assert` | 条件断言（`retryCount < 2` 等） |

---

## 6. 验证改动

```bash
# 语法检查
python -m py_compile scripts/workflow_engine.py

# 新对话初始化
python scripts/workflow_engine.py --init --project "<项目目录>"

# 推一步看引擎是否按新 YAML 走
python scripts/workflow_engine.py --project "<项目目录>" --mode 1
```

> ⚠️ 新增/修改流程后，**不要**手动改状态文件；一切以引擎输出 JSON 为判据。
