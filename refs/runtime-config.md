# 集中运行配置

运行时可变参数的唯一配置源为 `scripts/skill-config.json`，Python 统一访问模块为
`scripts/path_config.py`。

## 修改规则

- 修改工作区数据目录、配置文件名、状态目录、日志/报告目录：只修改 `paths`。
- 修改 Keil、串口、下载器和进度展示默认值：只修改 `defaults`。
- 修改编译无输出或下载超时：只修改 `timeouts`。
- Python 脚本禁止再次硬编码这些值，必须从 `path_config.py` 导入常量或路径函数。
- `flow.yaml` 使用 `{settings.<分组>.<字段>}` 引用配置；引擎会在返回 AI 参数前展开。
- Markdown 中出现的完整路径只作为说明示例；发生冲突时始终以
  `scripts/skill-config.json` 为准。

流程步骤、阶段、跳转和迭代条件仍由 `flow.yaml` 管理，不放入运行配置。用户工作区中的
工程列表、串口和下载器实际值仍由工作区配置文件管理，不放入 Skill 默认配置。