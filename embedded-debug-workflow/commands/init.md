# /kzl 初始化 — 初始化调试配置

> 此命令处理 `/kzl 初始化` / `/kzl 初始化` 和 `/kzl init`。
> 参数 `$1` 为项目目录路径，为空则默认为当前工作目录。

---

## 执行步骤

### Step 1: 自动初始化双项目配置（不询问）

```yaml
action: check_file
path: "{project_dir}/.copilot/embedded-debug-config.json"
on_failure: python "{skill_dir}/scripts/config_reader.py" --init "{project_dir}" --project-count 2
```

> 配置为**工作区级**：`{工作区}/.copilot/embedded-debug-config.json`，存放各工程的
> 路径 ↔ 串口 ↔ 下载器 对应关系。调试报告/日志则写入各自 `{项目目录}/.copilot/`。

### Step 2: 运行 config_reader.py --init

```yaml
action: run_script
call: python "{skill_dir}/scripts/config_reader.py" --init "{project_dir}" --project-count 2
说明: 固定生成两个项目的默认配置；已有配置时保留，不覆盖
```

运行后脚本会自动执行：
1. 不扫描工作区，不推断工程文件
2. 默认创建两个项目配置
3. 默认填入 Keil 路径、串口 256000/8N1、JLink 等通用属性
4. 用户直接编辑 JSON，填写工程路径和文件，并按实际硬件修改 COM 等参数

### Step 3: 按配置实际项目逐项询问

```yaml
action: ask_user
questions:
  - 整份配置是否填写完成？
  - 对 projects 中每个项目分别选择：【编译+下载 / 仅编译 / 不编译不下载】
on_success: 记录 projectModes；后续逐项目按各自模式工作
```

> 用户可自行增加或删除 `projects` 数组元素。实际项目数量始终取数组长度，
> 不依赖初始化时的两个模板项，也不依赖 `project_count` 字段。

---

## 完成后

*停止执行后续功能*并告知用户初始化完成，并提示可以直接描述故障现象进入调试流程。
