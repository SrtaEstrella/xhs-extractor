"""
统一启动器：在同一浏览器窗口中打开小红书和 Streamlit。
关闭终端时浏览器窗口自动关闭。
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright
from .browser_config import launch_persistent_context, get_user_data_dir


def main():
    print("=" * 60)
    print("小红书笔记提取工具")
    print("=" * 60)

    # 启动 Streamlit（后台）
    project_root = Path(__file__).parent.parent
    web_app = str(project_root / "xhs_extractor_module" / "web_app.py")
    streamlit_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", web_app,
         "--server.headless", "true"],
    )

    print("正在启动 Streamlit...")
    for _ in range(15):
        time.sleep(1)
        try:
            import urllib.request
            urllib.request.urlopen("http://localhost:8501", timeout=1)
            print("Streamlit 已就绪")
            break
        except Exception:
            pass

    # 打开浏览器
    print("正在打开浏览器...")
    try:
        p = sync_playwright().start()
        context = launch_persistent_context(p, headless=False)
        print(f"用户数据目录: {get_user_data_dir()}")

        # 标签页 1：小红书
        page_xhs = context.new_page()
        page_xhs.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded", timeout=60000)

        # 标签页 2：Streamlit
        page_st = context.new_page()
        page_st.goto("http://localhost:8501", wait_until="domcontentloaded", timeout=30000)

        print("\n浏览器已打开，按 Ctrl+C 或关闭终端退出。")

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在关闭...")
    except Exception as e:
        print(f"\n启动失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        streamlit_proc.terminate()
        streamlit_proc.wait()
        print("已退出。")