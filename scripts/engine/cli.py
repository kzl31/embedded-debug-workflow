"""
engine/cli.py — 命令行入口（argparse / main）

保留与原 workflow_engine.py 完全一致的 CLI 行为：
    python workflow_engine.py --project <dir> --init
    python workflow_engine.py --project <dir> --mode 0
    python workflow_engine.py --project <dir> --mode 1
    python workflow_engine.py --project <dir> --ack success|failure
    python workflow_engine.py --project <dir> --done
    python workflow_engine.py --project <dir> --wake
    python workflow_engine.py --project <dir> --reset
    python workflow_engine.py --project <dir> --set KEY=VALUE
    python workflow_engine.py --project <dir> --reload-config
"""

import argparse
import json
import sys

try:
    import yaml
except ImportError:
    print(json.dumps({
        "error": "缺少 pyyaml 依赖",
        "fix": "pip install pyyaml",
        "status": "fatal"
    }, ensure_ascii=False, indent=2))
    sys.exit(1)

from engine.workflow import WorkflowEngine


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="嵌入式调试工作流 · 单文件线性序号驱动引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python workflow_engine.py --project "e:\\proj" --init            # 新对话初始化
  python workflow_engine.py --project "e:\\proj" --mode 0          # 只读状态
  python workflow_engine.py --project "e:\\proj" --mode 1          # 执行/推进当前步骤
  python workflow_engine.py --project "e:\\proj" --ack success     # AI 步骤成功
  python workflow_engine.py --project "e:\\proj" --ack failure     # AI 步骤失败
  python workflow_engine.py --project "e:\\proj" --done            # = --ack success
  python workflow_engine.py --project "e:\\proj" --wake            # 从暂停恢复
  python workflow_engine.py --project "e:\\proj" --reset           # 重置
    python workflow_engine.py --project "e:\\proj" --set projectInfo.projectModes=full,compile_only
        """)
    parser.add_argument(
        "--project", "-p", required=True,
        help="VS Code 工作区根目录（参数名仅为历史兼容；禁止传 Skill 仓库或单个 Keil 工程目录）",
    )
    parser.add_argument("--init", action="store_true", help="初始化工作流（新对话必须先执行）")
    parser.add_argument("--reset", action="store_true", help="重置为新任务")
    parser.add_argument("--mode", type=int, choices=[0, 1], default=None,
                        help="0=只读状态 1=执行/推进当前步骤")
    parser.add_argument("--ack", choices=["success", "failure"], help="AI 步骤结果提交")
    parser.add_argument("--done", action="store_true", help="= --ack success")
    parser.add_argument("--wake", action="store_true", help="从 wait_user 暂停恢复")
    parser.add_argument("--reload-config", action="store_true",
                        help="从磁盘重载配置并清除旧项目模式")
    parser.add_argument("--set", action="append", metavar="KEY=VALUE",
                        help="设置状态字段，可多次")

    args = parser.parse_args()

    try:
        engine = WorkflowEngine(args.project)
    except FileNotFoundError as e:
        print(json.dumps({"error": str(e), "status": "fatal"},
                         ensure_ascii=False, indent=2))
        sys.exit(1)

    try:
        if args.init:
            result = engine.init()
        elif args.reset:
            result = engine.reset()
        elif args.set:
            result = engine.set_state(args.set)
        elif args.reload_config:
            result = engine.reload_config()
        elif args.wake:
            result = engine.wake()
        elif args.ack:
            result = engine.ack(args.ack == "success")
        elif args.done:
            result = engine.ack(True)
        elif args.mode == 0:
            result = engine.show_status()
        elif args.mode == 1:
            result = engine.run()
        else:
            result = engine.run()
    except ValueError as exc:
        result = engine._result(
            "error", str(exc),
            next_action=(
                f'{engine.engine_bin} --project "{engine.project_dir}" '
                '--reload-config'))

    print(json.dumps(result, ensure_ascii=False, indent=2))
