#!/usr/bin/env python
"""串口持续监听工具。

用于抓取完整启动日志、持续监视设备输出。支持：
- 持续监听并保存到文件
- 指定时长抓取（常用于捕获启动日志）
- 等待特定关键字后退出
- 错误/警告模式检测

用法：
  python scripts/serial_monitor.py --duration 15          # 监听 15 秒
  python scripts/serial_monitor.py --save logs/output.log # 保存到文件
  python scripts/serial_monitor.py --wait "system ready"  # 等待关键字
  python scripts/serial_monitor.py --continuous           # 持续模式（Ctrl+C 退出）
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from threading import Event

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))
from config_reader import load_config, get_serial_config

# 错误/警告模式（用于日志分析）
ERROR_PATTERNS = [
    re.compile(r, re.IGNORECASE) for r in [
        r"\[error\]", r"\berror\b", r"\bfault\b",
        r"\bpanic\b", r"\bassert\b", r"\bexception\b", r"\bfail(?:ed)?\b",
    ]
]
WARNING_PATTERNS = [
    re.compile(r, re.IGNORECASE) for r in [
        r"\[warn(?:ing)?\]", r"\bwarning\b",
    ]
]
STARTUP_PATTERNS = [
    re.compile(r, re.IGNORECASE) for r in [
        r"system start", r"\bboot\b", r"reset reason",
        r"firmware version", r"build:", r"starting",
    ]
]


def monitor_serial(
    port: str,
    baud: int,
    data_bits: int = 8,
    stop_bits: int = 1,
    parity: str = "None",
    duration: float | None = None,
    save_path: str | None = None,
    wait_for: str | None = None,
    continuous: bool = False,
) -> dict:
    """串口持续监听，返回结果字典。"""
    try:
        import serial
    except ImportError:
        return {"status": "error", "error": "pyserial 未安装，请执行: pip install pyserial"}

    parity_map = {"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN,
                   "Odd": serial.PARITY_ODD}
    stopbits_map = {1: serial.STOPBITS_ONE, 2: serial.STOPBITS_TWO}

    try:
        ser = serial.Serial(
            port=port, baudrate=baud, bytesize=data_bits,
            parity=parity_map.get(parity, serial.PARITY_NONE),
            stopbits=stopbits_map.get(stop_bits, serial.STOPBITS_ONE),
            timeout=0.5,
        )
    except serial.SerialException as exc:
        return {"status": "error", "error": f"串口打开失败: {exc}"}

    print(f"[serial_monitor] 📡 监听串口 {port} @ {baud} baud")
    if duration:
        print(f"[serial_monitor]   时长: {duration} 秒")
    if save_path:
        print(f"[serial_monitor]   保存: {save_path}")
    if wait_for:
        print(f"[serial_monitor]   等待关键字: {wait_for}")

    collected_lines: list[str] = []
    found_errors: list[str] = []
    found_warnings: list[str] = []
    found_startup: list[str] = []
    matched_keyword = False
    stop_event = Event()
    start_time = time.time()

    try:
        while not stop_event.is_set():
            # 时间限制
            if duration and (time.time() - start_time) >= duration:
                break
            if continuous:
                # 持续模式无时间限制，但需要处理 Ctrl+C
                pass

            try:
                line_bytes = ser.readline()
                if not line_bytes:
                    continue
                line = line_bytes.decode("utf-8", errors="replace").rstrip("\r\n")
            except serial.SerialException:
                break

            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:12]
            log_line = f"[{timestamp}] {line}"
            print(log_line)

            collected_lines.append(log_line)

            # 模式检测
            for p in ERROR_PATTERNS:
                if p.search(line):
                    found_errors.append(line)
                    break
            for p in WARNING_PATTERNS:
                if p.search(line):
                    found_warnings.append(line)
                    break
            for p in STARTUP_PATTERNS:
                if p.search(line):
                    found_startup.append(line)
                    break

            # 等待关键字
            if wait_for and wait_for.lower() in line.lower():
                matched_keyword = True
                print(f"[serial_monitor] ✅ 检测到目标关键字: {wait_for}")
                break

    except KeyboardInterrupt:
        print("\n[serial_monitor] ⏹ 用户中断")
    finally:
        ser.close()

    elapsed = time.time() - start_time

    # 保存到文件
    if save_path and collected_lines:
        save_file = Path(save_path)
        save_file.parent.mkdir(parents=True, exist_ok=True)
        save_file.write_text("\n".join(collected_lines), encoding="utf-8")
        print(f"[serial_monitor] 💾 日志已保存: {save_file} ({len(collected_lines)} 行)")

    result = {
        "status": "success",
        "port": port,
        "baud": baud,
        "duration": round(elapsed, 1),
        "line_count": len(collected_lines),
        "error_count": len(found_errors),
        "warning_count": len(found_warnings),
        "startup_count": len(found_startup),
        "matched_keyword": matched_keyword,
        "lines": collected_lines,
        "errors": found_errors,
        "warnings": found_warnings,
        "startup_lines": found_startup,
    }

    print(f"\n[serial_monitor] 📊 统计:")
    print(f"   监听时长: {result['duration']} 秒")
    print(f"   日志行数: {result['line_count']}")
    print(f"   错误: {result['error_count']}  警告: {result['warning_count']}")
    if found_startup:
        print(f"   启动信息: {len(found_startup)} 条")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="串口持续监听工具")
    parser.add_argument("--port", help="串口号")
    parser.add_argument("--baud", type=int, help="波特率")
    parser.add_argument("--data-bits", type=int, default=8)
    parser.add_argument("--stop-bits", type=int, default=1)
    parser.add_argument("--parity", default="None")
    parser.add_argument("--duration", type=float, default=10.0,
                        help="监听时长（秒），默认 10 秒")
    parser.add_argument("--continuous", action="store_true",
                        help="持续模式，不限时长（Ctrl+C 退出）")
    parser.add_argument("--save", help="日志保存路径")
    parser.add_argument("--wait", help="等待关键字后停止")
    parser.add_argument("--config-dir", help="配置文件所在目录（默认自动查找）")
    args = parser.parse_args()

    config = load_config(args.config_dir)
    serial_cfg = get_serial_config(config)

    port = args.port or serial_cfg["port"]
    baud = args.baud or serial_cfg["baud"]

    result = monitor_serial(
        port=port, baud=baud,
        data_bits=args.data_bits, stop_bits=args.stop_bits, parity=args.parity,
        duration=None if args.continuous else args.duration,
        save_path=args.save, wait_for=args.wait,
        continuous=args.continuous,
    )

    if result["status"] == "error":
        print(f"❌ {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
