#!/usr/bin/env python
"""串口单次读取工具。

用于调试循环中快速抓取一段串口输出，分析设备运行状态。
动态读取 data/config.json 获取串口参数。

用法：
  python scripts/serial_read.py                          # 默认配置
  python scripts/serial_read.py --port COM3 --baud 115200
  python scripts/serial_read.py --timeout 5              # 超时 5 秒
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))
from config_reader import load_config, get_serial_config


def read_serial_once(
    port: str,
    baud: int,
    data_bits: int = 8,
    stop_bits: int = 1,
    parity: str = "None",
    timeout: float = 3.0,
) -> dict:
    """单次读取串口，返回数据字典。"""
    try:
        import serial
    except ImportError:
        return {
            "status": "error",
            "error": "pyserial 未安装，请执行: pip install pyserial",
            "data": "",
        }

    # 映射 parity
    parity_map = {"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN,
                   "Odd": serial.PARITY_ODD}
    stopbits_map = {1: serial.STOPBITS_ONE, 2: serial.STOPBITS_TWO}

    try:
        ser = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=data_bits,
            parity=parity_map.get(parity, serial.PARITY_NONE),
            stopbits=stopbits_map.get(stop_bits, serial.STOPBITS_ONE),
            timeout=timeout,
        )
    except serial.SerialException as exc:
        return {
            "status": "error",
            "error": f"串口打开失败: {exc}",
            "data": "",
        }

    print(f"[serial_read] 📡 读取串口 {port} @ {baud} baud...")
    time.sleep(0.5)  # 等待数据稳定

    try:
        raw = ser.read(ser.in_waiting or 1024)
        data_str = raw.decode("utf-8", errors="replace")
    except Exception as exc:
        data_str = ""
        print(f"[serial_read] ⚠️ 读取异常: {exc}")
    finally:
        ser.close()

    lines = [l for l in data_str.split("\n") if l.strip()]
    result = {
        "status": "success",
        "port": port,
        "baud": baud,
        "raw_length": len(raw) if 'raw' in dir() else 0,
        "line_count": len(lines),
        "data": data_str,
        "lines": lines,
    }

    print(f"[serial_read] ✅ 读取完成，{result['line_count']} 行，{result['raw_length']} 字节")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="串口单次读取")
    parser.add_argument("--port", help="串口号")
    parser.add_argument("--baud", type=int, help="波特率")
    parser.add_argument("--data-bits", type=int, default=8, help="数据位")
    parser.add_argument("--stop-bits", type=int, default=1, help="停止位")
    parser.add_argument("--parity", default="None", help="校验位")
    parser.add_argument("--timeout", type=float, default=3.0, help="读取超时（秒）")
    parser.add_argument("--config-dir", help="配置文件所在目录（默认自动查找）")
    args = parser.parse_args()

    # 读取配置
    config = load_config(args.config_dir)
    serial_cfg = get_serial_config(config)

    port = args.port or serial_cfg["port"]
    baud = args.baud or serial_cfg["baud"]

    result = read_serial_once(
        port=port,
        baud=baud,
        data_bits=args.data_bits,
        stop_bits=args.stop_bits,
        parity=args.parity,
        timeout=args.timeout,
    )

    if result["status"] == "error":
        print(f"❌ {result['error']}")
        sys.exit(1)

    # 输出内容
    if result["data"]:
        print("\n" + "─" * 50)
        print(result["data"])
        print("─" * 50)


if __name__ == "__main__":
    main()
