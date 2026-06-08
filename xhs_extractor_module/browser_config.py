"""
浏览器自动检测与 fallback 模块
优先级: Edge → Chrome → Playwright Chromium
可通过环境变量 XHS_BROWSER 手动指定: edge | chrome | chromium
"""
from __future__ import annotations

import os
import sys
import shutil
from pathlib import Path

# 各平台已知安装路径
_BROWSER_PATHS: dict[str, list[str]] = {
    "msedge": [],
    "chrome": [],
}

if sys.platform == "win32":
    _BROWSER_PATHS["msedge"] = [
        "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
        "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    ]
    _BROWSER_PATHS["chrome"] = [
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    ]
elif sys.platform == "darwin":
    _BROWSER_PATHS["msedge"] = [
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ]
    _BROWSER_PATHS["chrome"] = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
else:
    _BROWSER_PATHS["msedge"] = [
        "/usr/bin/microsoft-edge",
        "/usr/bin/microsoft-edge-stable",
    ]
    _BROWSER_PATHS["chrome"] = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
    ]

_channel_names = {
    "msedge": "Microsoft Edge",
    "chrome": "Google Chrome",
    None: "Playwright Chromium",
}

_cached_channel: str | None | None = None  # None = not yet detected, "not_found" sentinel handled separately

# 持久化用户数据目录（避免 InPrivate，登录态天然持久化）
_USER_DATA_DIR = Path(__file__).parent / "browser_data"


def _find_browser_exe(channel: str) -> bool:
    """检查指定 channel 的浏览器是否存在"""
    for path in _BROWSER_PATHS.get(channel, []):
        if os.path.isfile(path):
            return True
    exe_name = _BROWSER_PATHS.get(channel, [None])[0]
    if exe_name:
        base = os.path.basename(exe_name)
        if shutil.which(base):
            return True
    return False


def detect_browser_channel() -> str | None:
    """
    按优先级检测可用浏览器，返回 Playwright channel 名称。

    优先级: Edge → Chrome → Playwright Chromium
    可通过环境变量 XHS_BROWSER 覆盖: edge | chrome | chromium

    Returns:
        Playwright channel 名称 ("msedge", "chrome") 或 None (使用默认 Chromium)
    """
    global _cached_channel

    if _cached_channel is not None:
        # _cached_channel 可以是 "msedge", "chrome", 或 ""  (空字符串 = 已检测过, 无系统浏览器, 用默认 chromium)
        return _cached_channel if _cached_channel != "" else None

    env_override = os.environ.get("XHS_BROWSER", "").strip().lower()
    if env_override == "edge":
        env_override = "msedge"
    elif env_override == "chromium":
        _cached_channel = ""
        return None

    if env_override in ("msedge", "chrome"):
        if _find_browser_exe(env_override):
            _cached_channel = env_override
        else:
            print(f"[警告] 环境变量指定了 {env_override}，但未找到该浏览器，将自动检测")
            _cached_channel = ""

    if _cached_channel is None:
        for channel in ("msedge", "chrome"):
            if _find_browser_exe(channel):
                _cached_channel = channel
                break
        if _cached_channel is None:
            _cached_channel = ""

    return _cached_channel if _cached_channel != "" else None


def launch_browser(playwright_instance, **kwargs):
    """
    自动检测可用浏览器并启动。

    Args:
        playwright_instance: sync_playwright() 返回的 Playwright 实例

    Returns:
        Browser 对象
    """
    channel = detect_browser_channel()
    name = _channel_names[channel]
    print(f"[浏览器] 使用 {name}")

    if channel:
        return playwright_instance.chromium.launch(channel=channel, **kwargs)
    else:
        return playwright_instance.chromium.launch(**kwargs)


def get_user_data_dir() -> Path:
    """返回持久化用户数据目录"""
    return _USER_DATA_DIR


_CDP_PORT = 9222
_CDP_URL = f"http://127.0.0.1:{_CDP_PORT}"


def launch_persistent_context(playwright_instance, **kwargs):
    """
    使用持久化用户目录启动浏览器上下文，优先复用已运行的浏览器。
    登录态自动保留在磁盘上，不会开 InPrivate 窗口。

    Args:
        playwright_instance: sync_playwright() 返回的 Playwright 实例
        **kwargs: 传递给 launch_persistent_context 的参数 (如 headless)

    Returns:
        BrowserContext 对象（可直接 new_page）
    """
    channel = detect_browser_channel()
    name = _channel_names[channel]
    user_data_dir = str(_USER_DATA_DIR)
    os.makedirs(user_data_dir, exist_ok=True)

    headless = kwargs.pop("headless", False)

    # 非 headless 模式（登录）：尝试连接已运行的浏览器
    if not headless:
        try:
            browser = playwright_instance.chromium.connect_over_cdp(_CDP_URL)
            contexts = browser.contexts
            if contexts:
                print(f"[浏览器] 复用已运行的 {name}")
                return contexts[0]
        except Exception:
            pass

    # 启动新浏览器
    print(f"[浏览器] 使用 {name}")
    launch_options: dict = {"args": [f"--remote-debugging-port={_CDP_PORT}"]}
    if not headless:
        launch_options["args"].append("--start-maximized")
        launch_options["no_viewport"] = True
    if channel:
        launch_options["channel"] = channel

    return playwright_instance.chromium.launch_persistent_context(
        user_data_dir,
        headless=headless,
        **launch_options,
        **kwargs,
    )


def get_browser_name() -> str:
    """返回当前检测到的浏览器名称（用于显示）"""
    channel = detect_browser_channel()
    return _channel_names[channel]
