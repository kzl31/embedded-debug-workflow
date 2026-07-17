"""
engine — 嵌入式调试工作流引擎包

将原单文件 workflow_engine.py 按职责拆分为：
  - constants.py    常量与路径
  - utils.py        纯工具函数（IO / 加密 / 解析）
  - state.py        流程状态读写与默认结构
  - conditions.py   条件求值与状态写入（ConditionMixin）
  - executors.py    外部脚本与文件检查（ExecutorMixin）
  - auto_steps.py   自动步骤驱动与流向控制（AutoStepMixin）
  - ai_instructions.py  AI 指令与终止态（AIInstructionMixin）
  - config_sync.py  配置与项目模式同步（ConfigSyncMixin）
  - core.py         初始化 / 查询 / 主入口（CoreMixin）
  - workflow.py     WorkflowEngine 组合类
  - cli.py          argparse 入口 main()
"""

from engine.workflow import WorkflowEngine
from engine.cli import main

__all__ = ["WorkflowEngine", "main"]
