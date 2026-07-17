#!/usr/bin/env python
"""
workflow_engine.py — 嵌入式调试工作流「线性序号驱动」引擎（入口）

本文件仅作为命令行入口，引擎逻辑已拆分到 engine/ 包：
    engine/constants.py          常量与路径
    engine/utils.py              纯工具函数（IO / 加密 / 解析）
    engine/state.py              流程状态读写与默认结构
    engine/conditions.py         条件求值与状态写入
    engine/executors.py          外部脚本与文件检查
    engine/auto_steps.py         自动步骤驱动与流向控制
    engine/ai_instructions.py    AI 步骤指令与终止态
    engine/config_sync.py        配置与项目模式同步
    engine/core.py               初始化 / 查询 / 主入口
    engine/workflow.py           WorkflowEngine 组合类
    engine/cli.py                argparse 入口

核心理念：
  flow.yaml      = 唯一真相源（线性序号步骤表，含 phase 分组标签）
  flow-gate.json = 唯一状态源（当前 seq + 流程状态）
  本引擎         = 纯查表 + 序号跳转解析器（零硬编码步骤）

用法：
    python workflow_engine.py --project <VS Code 工作区根目录> --init
    python workflow_engine.py --project <VS Code 工作区根目录> --mode 0
    python workflow_engine.py --project <VS Code 工作区根目录> --mode 1
    python workflow_engine.py --project <项目目录> --ack success|failure
    python workflow_engine.py --project <项目目录> --done
    python workflow_engine.py --project <项目目录> --wake
    python workflow_engine.py --project <项目目录> --reset
    python workflow_engine.py --project <项目目录> --set KEY=VALUE
    python workflow_engine.py --project <项目目录> --reload-config

依赖：pip install pyyaml
"""

from engine.cli import main

if __name__ == "__main__":
    main()
