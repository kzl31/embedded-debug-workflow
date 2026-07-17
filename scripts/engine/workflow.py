"""
engine/workflow.py — WorkflowEngine 组合类

通过多继承把单一职责拆分到各 Mixin，对外接口与行为与原单文件引擎完全一致：
  - CoreMixin          初始化 / 基础查询 / 主入口 / 结果构造
  - AutoStepMixin      自动步骤驱动与流向控制
  - ExecutorMixin      外部脚本与文件检查
  - AIInstructionMixin AI 步骤指令与终止态
  - ConfigSyncMixin    配置与项目模式同步
  - ConditionMixin     条件求值与状态写入
"""


from engine.core import CoreMixin
from engine.auto_steps import AutoStepMixin
from engine.executors import ExecutorMixin
from engine.ai_instructions import AIInstructionMixin
from engine.config_sync import ConfigSyncMixin
from engine.conditions import ConditionMixin


class WorkflowEngine(
    CoreMixin,
    AutoStepMixin,
    ExecutorMixin,
    AIInstructionMixin,
    ConfigSyncMixin,
    ConditionMixin,
):
    """嵌入式调试工作流「线性序号驱动」引擎。"""
    pass
