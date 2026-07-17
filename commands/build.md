# /kzl 编译 || /kzl 编译下载 — 独立编译命令

> 本命令处理：
> - `/kzl 编译` / `/kzl build`：仅编译，不下载。
> - `/kzl 编译下载` / `/kzl build-flash`：编译成功后下载。
> - `/kzl 编译下载 --skip-build`：跳过编译，直接下载已有固件。
> - `/kzl 编译下载 --skip-flash`：跳过下载，只执行编译。
>
> 这是独立快捷命令，不启动、不初始化、不检查、不推进工作流引擎；直接调用 Python 脚本。

---

## 执行步骤

### Step 1: 确定工作区与配置

```yaml
action: check_file
path: "由 scripts/path_config.py 根据 workspace_dir 解析的工作区配置文件"
规则:
  - workspace_dir 默认取当前 VS Code 工作区根目录
  - 多根工作区优先取当前活动文件所属工作区
  - 只检查配置文件是否存在，禁止调用 workflow_engine.py
  - 禁止自动调用 config_reader.py --init
on_failure:
  stop: true
  message: "尚未初始化，请先执行 /kzl 初始化"
```

### Step 2: 确定目标工程

```yaml
action: select_project
规则:
  - projects 仅有一个：直接使用 project-index 0
  - projects 有多个：优先匹配当前活动文件所在目录与 projects[*].dir
  - 无法唯一匹配：列出项目名称，让用户选择
  - 不修改配置，不改变流程状态
```

### Step 3: 直接调用脚本

```yaml
action: run_script
commands:
  /kzl 编译: >-
    python "{skill_dir}/scripts/keil_build.py"
    --config-dir "{workspace_dir}"
    --project-index "{current_project_index}"
  /kzl 编译下载: >-
    python "{skill_dir}/scripts/build_and_flash.py"
    --config-dir "{workspace_dir}"
    --project-index "{current_project_index}"
规则:
  - 默认增量编译
  - 用户明确要求全量编译时追加 --rebuild
  - 用户要求跳过编译时追加 --skip-build
  - 用户要求跳过下载时追加 --skip-flash
  - 两个参数可同时使用，此时只校验配置和目标工程，不执行编译或下载
  - 不调用 workflow_engine.py，不执行 --init/--mode/--ack
```

### Step 4: 报告脚本结果

```yaml
action: check_output
编译成功: 脚本退出码为 0 且输出编译成功
编译下载成功: 脚本退出码为 0 且输出编译和下载均成功
on_failure: 原样概括错误，不自动进入调试流程
```

---

## 完成后

只报告目标工程、编译结果，以及下载结果（若有）；随后停止，不推进工作流。
