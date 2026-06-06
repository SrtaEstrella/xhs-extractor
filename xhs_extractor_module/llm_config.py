"""
LLM API 配置管理
API key 加密存储在模块目录的 .apikey 文件中，不会被提交到仓库。
"""
from __future__ import annotations

import base64
import hashlib
import os
import platform
import secrets
from pathlib import Path

_APIKEY_FILE = Path(__file__).parent / ".apikey"
_SALT_FILE = Path(__file__).parent / ".apikey.salt"


def _machine_id() -> bytes:
    """基于本机信息派生一个标识，用于加密密钥派生。"""
    info = f"{platform.node()}-{os.environ.get('USERNAME', '')}-{os.environ.get('COMPUTERNAME', '')}"
    return hashlib.sha256(info.encode()).digest()


def _derive_key() -> bytes:
    """从本机标识 + 随机盐派生对称加密密钥。"""
    if not _SALT_FILE.exists():
        salt = secrets.token_bytes(32)
        _SALT_FILE.write_bytes(salt)
    else:
        salt = _SALT_FILE.read_bytes()
    return hashlib.pbkdf2_hmac("sha256", _machine_id(), salt, 100_000, dklen=32)


def _xor_encrypt(plain: str) -> str:
    """简单 XOR 加密（结合密钥派生），输出 base64。"""
    key = _derive_key()
    data = plain.encode("utf-8")
    encrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return base64.urlsafe_b64encode(encrypted).decode()


def _xor_decrypt(encrypted: str) -> str:
    """解密 base64 → XOR → 明文。"""
    key = _derive_key()
    data = base64.urlsafe_b64decode(encrypted.encode())
    decrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return decrypted.decode("utf-8")


def get_api_key() -> str:
    """读取已保存的 API key，未配置则返回空字符串。"""
    if _APIKEY_FILE.exists():
        try:
            return _xor_decrypt(_APIKEY_FILE.read_text(encoding="utf-8").strip())
        except Exception:
            return ""
    return ""


def save_api_key(key: str) -> None:
    """加密保存 API key 到本地文件。"""
    _APIKEY_FILE.write_text(_xor_encrypt(key.strip()), encoding="utf-8")


def delete_api_key() -> None:
    """删除已保存的 API key。"""
    if _APIKEY_FILE.exists():
        _APIKEY_FILE.unlink()
