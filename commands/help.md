# /kzl 帮助 — 嵌入式调试工作流

> 嵌入式固件调试自动化工作流：编译烧录 → 串口日志 → CHESHI 迭代 → 故障定位 → 报告输出。

---

## 可用命令

| 命令 | 用途 |
|------|------|
| `/kzl 帮助` | 显示本帮助 |
| `/kzl 初始化 [工作区目录]` | 扫描当前工作区的 Keil 工程并生成配置；路径由集中配置解析 |
| `/kzl 编译` | 仅编译当前工程（不下载固件） |
| `/kzl 编译下载` | 编译并下载固件到设备 |
| `/kzl 打印 <要求>` | 按 CHESHI 规范添加调试打印（兼容 `/klz 打印`） |
| `/kzl 报告 [标题/要求]` | 根据当前对话生成详细报告，并更新历史索引与持久记忆 |
| `/kzl 新增流程` | 新增步骤 / 阶段（读 `refs/add-flow-guide.md`） |

## 一键安装

统一仓库地址：<https://github.com/kzl31/embedded-debug-workflow>

```powershell
# GitHub Copilot
npx skills add https://github.com/kzl31/embedded-debug-workflow --skill embedded-debug-workflow --agent github-copilot --global --yes

# Claude Code
npx skills add https://github.com/kzl31/embedded-debug-workflow --skill embedded-debug-workflow --agent claude-code --global --yes

# Codex
npx skills add https://github.com/kzl31/embedded-debug-workflow --skill embedded-debug-workflow --agent codex --global --yes

# Cursor
npx skills add https://github.com/kzl31/embedded-debug-workflow --skill embedded-debug-workflow --agent cursor --global --yes
```

安装后重新加载对应 Agent 或重启编辑器。完整安装与管理说明见 `README.md`。

> 以上命令是独立入口，不运行或推进工作流引擎。`/kzl 编译` 与 `/kzl 编译下载`
> 若发现配置不存在，只提示先执行 `/kzl 初始化`，不会自行初始化。

## 文件路径规则

- 集中配置：`scripts/skill-config.json`
- Python 路径接口：`scripts/path_config.py`
- 工作区配置、加密状态、日志和报告：统一写入集中配置解析出的工作区 Skill 专属数据目录
- 多项目日志：自动使用 `p<项目下标>_<项目名>` 区分，禁止互相覆盖
- Skill 历史索引：使用集中配置中的 `skill_data_dir` 和 `history_filename`
- 持久记忆：使用集中配置中的 `persistent_memory_file`

修改目录或文件名时，只修改 `scripts/skill-config.json`，不要修改命令文件中的路径拼接。

---

## 快速开始

### 首次使用

```text
1. /kzl 初始化        ← 自动按当前工作区工程生成配置
2. 描述故障现象并确认工程配置  ← 自动进入调试流程
```

### 后续调试

描述故障现象并确认工程配置。若配置未完成，修改集中配置解析出的工作区配置文件后再确认，AI 会自动走完 STARTUP → DEBUG_LOOP → VERIFY_AND_REPORT 流程。



---

## 工作流总览

```mermaid
flowchart LR
    A[采集硬件信息] --> B[STARTUP 启动预检]
    B --> C[DEBUG_LOOP 调试循环]
    C -->|找到根因| D[VERIFY_AND_REPORT]
    D --> E[✅ 完成]
    C -->|超过8轮| D

```

---

## 详细文档

| 文档 | 说明 |
|------|------|
| `refs/core-rules.md` | 6 条强制规则 |
| `refs/workflow-diagram.md` | 完整流程图（三阶段 mermaid） |
| `refs/script-commands.md` | 脚本命令参考 |
| `refs/common-faults.md` | 常见故障速查 |
| `refs/cheshi-macro.md` | CHESHI 调试宏规范 |
| `refs/runtime-config.md` | 集中运行参数和路径规则 |
| `templates/checklist.md` | 迭代完成检查清单 |
