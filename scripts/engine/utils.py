"""
engine/utils.py — 纯工具函数（无状态、无副作用）

包含：
  - JSON / YAML 读取
  - 模板路径替换（{project_dir}）
  - 时间、值解析
  - 轻量加密 / 解密（XOR + base64）
  - 配置内容指纹
"""

import base64
import hashlib
import json
import re
from typing import Any

from engine.constants import _ENCRYPT_KEY


def load_json(path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_yaml(path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return __import__("yaml").safe_load(f)


def resolve_path(template: str, project_dir: str) -> str:
    return (template or "").replace("{project_dir}", project_dir)


def now_iso() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_state_value(raw: str) -> Any:
    """按 JSON 语义解析 --set 值；普通文本保持字符串。"""
    text = raw.strip()
    if not text:
        return raw
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return raw
    return value


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(d ^ key[i % len(key)] for i, d in enumerate(data))


def encrypt_json(data: dict) -> str:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    return base64.b64encode(_xor_bytes(text.encode("utf-8"), _ENCRYPT_KEY)).decode("ascii")


def decrypt_json(encrypted: str) -> dict:
    raw = base64.b64decode(encrypted.encode("ascii"))
    return json.loads(_xor_bytes(raw, _ENCRYPT_KEY).decode("utf-8"))


def config_fingerprint(config: dict) -> str:
    """生成配置内容指纹，用于阻止 AI 使用过期 projects 快照。"""
    canonical = json.dumps(config, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
