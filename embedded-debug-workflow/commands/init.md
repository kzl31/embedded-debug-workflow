# /kzl 初始化 — 初始化调试配置

> 此命令处理 `/kzl 初始化` / `/kzl 初始化` 和 `/kzl init`。
> 参数 `$1` 为项目目录路径，为空则默认为当前工作目录。

---

## 执行步骤

### Step 1: 初始化问题（必须最先执行）

```yaml
action: ask_user
questions:
	- 工程中有多少项目，配置是否都已完成？【1 个且已完成 / 多个且均已完成 / 配置未完成】
	- 本次需要编译下载吗？【编译+下载（完整流程） / 仅编译不下载 / 暂不编译下载（仅定位问题）】
```

> 配置为**工作区级**：`{工作区}/.copilot/embedded-debug-config.json`，存放各工程的
> 路径 ↔ 串口 ↔ 下载器 对应关系。调试报告/日志则写入各自 `{项目目录}/.copilot/`。

### Step 2: 运行 config_reader.py --init

```yaml
action: run_script
call: python "{skill_dir}/scripts/config_reader.py" --init "{project_dir}" --project-count {projectInfo.projectCount}
说明: 按用户确认的项目数量，在工作区 .copilot/ 生成全参数占位配置
```

运行后脚本会自动执行：
1. 不扫描工作区，不推断工程文件
2. 按 `projectInfo.projectCount` 创建对应数量的项目占位项
3. Keil 路径、工程路径、工程文件、串口和下载器等参数全部留空
4. 用户直接编辑 JSON，填写所有配置参数

### Step 3: 验证配置生成

```yaml
action: check_file
path: "{project_dir}/.copilot/embedded-debug-config.json"
on_success: ✅ 默认配置已生成；用户补全后可以开始调试
on_failure: ⚠️ 配置未生成，请检查脚本输出
```

---

## 完成后

*停止执行后续功能*并告知用户初始化完成，并提示可以直接描述故障现象进入调试流程。
