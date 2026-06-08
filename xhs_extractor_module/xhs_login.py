# xhs_login.py
"""
小红书登录模块
使用 Playwright 进行网页登录并保存登录态
"""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from .browser_config import launch_persistent_context, get_user_data_dir

# 抑制 urllib3 和运行时警告
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", message=".*urllib3.*")
warnings.filterwarnings("ignore", message=".*OpenSSL.*")


# 登录态持久化目录（Playwright persistent context 自动管理）
STATE_PATH = Path(__file__).parent / "xhs_state.json"  # 向后兼容，新方案使用 browser_data 目录


def login_xhs_and_save_state(state_path: str = None):
    """
    第一次运行时调用：
    - 打开带 UI 的浏览器（持久化用户目录，不会开 InPrivate）
    - 访问小红书官网
    - 用户手工扫码 / 输入手机号登录
    - 登录态自动保留在磁盘上，无需手动保存

    Args:
        state_path: 已废弃，保留用于向后兼容
    """
    user_data_dir = str(get_user_data_dir())

    print("=" * 60)
    print("小红书登录助手")
    print("=" * 60)
    print(f"用户数据目录: {user_data_dir}")
    print("\n正在打开浏览器...")

    p = sync_playwright().start()
    context = launch_persistent_context(p, headless=False, slow_mo=100)
    page = context.new_page()

    print("\n正在访问小红书官网...")
    page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded", timeout=60000)

    print("\n" + "=" * 60)
    print("请在打开的浏览器里完成小红书登录：")
    print("  - 可以使用手机号登录")
    print("  - 也可以使用扫码登录")
    print("  - 登录成功后，回到终端按回车继续...")
    print("=" * 60)

    input("\n登录完成后按回车：")

    print(f"\n[OK] 登录状态已保存到: {user_data_dir}")
    print("下次使用时将自动使用此登录态，无需再次登录。")
    print("浏览器窗口将保持打开，关闭终端后自动关闭。")


def check_login_state_exists(state_path: str = None) -> bool:
    """
    检查登录态是否存在（检查持久化浏览器数据目录）

    Args:
        state_path: 已废弃，保留用于向后兼容

    Returns:
        如果用户数据目录存在返回True
    """
    return get_user_data_dir().is_dir() and any(get_user_data_dir().iterdir())


def verify_login_state(state_path: str = None) -> bool:
    """
    验证登录状态是否有效
    通过访问小红书探索页面来检查登录状态是否仍然有效

    Args:
        state_path: 已废弃，保留用于向后兼容

    Returns:
        如果登录状态有效返回True，否则返回False
    """
    if not check_login_state_exists():
        return False

    warnings.filterwarnings("ignore")

    print("正在验证登录状态...")

    def _safe_close(ctx):
        try:
            ctx.close()
        except Exception:
            pass

    try:
        with sync_playwright() as p:
            context = launch_persistent_context(p, headless=True)
            page = context.new_page()

            try:
                page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=30000)
            except PlaywrightTimeoutError:
                _safe_close(context)
                return False

            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except PlaywrightTimeoutError:
                pass

            page_text = page.inner_text("body").lower()
            page_url = page.url.lower()

            if "login" in page_url or "signin" in page_url:
                _safe_close(context)
                return False

            login_keywords = ['登录', '注册', '发现发布通知登录我', '请登录', '登录查看', '立即登录']
            has_login_keyword = any(keyword in page_text for keyword in login_keywords)

            if len(page_text) < 100:
                _safe_close(context)
                return False

            if has_login_keyword and len(page_text) < 500:
                _safe_close(context)
                return False

            try:
                login_selectors = [
                    "text=登录", "text=注册", "text=立即登录", "text=请登录",
                    "[class*='login']", "[class*='signin']",
                    "[id*='login']", "[id*='signin']"
                ]
                login_count = 0
                for selector in login_selectors:
                    try:
                        elements = page.query_selector_all(selector)
                        login_count += len(elements)
                    except Exception:
                        pass
                if login_count > 5:
                    _safe_close(context)
                    return False
            except Exception:
                pass

            _safe_close(context)
            return True

    except Exception as e:
        print(f"验证登录状态时出错: {e}")
        return False


def browse_xhs():
    """打开已登录的小红书页面供用户浏览。"""
    import time
    print("正在打开小红书...")
    p = sync_playwright().start()
    context = launch_persistent_context(p, headless=False)

    # 标签页 1：小红书
    page_xhs = context.new_page()
    page_xhs.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded", timeout=60000)

    # 标签页 2：Streamlit（等它启动）
    page_st = context.new_page()
    for _ in range(15):
        try:
            page_st.goto("http://localhost:8501", wait_until="domcontentloaded", timeout=5000)
            break
        except Exception:
            time.sleep(1)

    # 关闭初始 about:blank 标签页
    for p in context.pages:
        if p.url == "about:blank":
            p.close()

    print("浏览器窗口将保持打开，按 Ctrl+C 或关闭终端退出。")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


def delete_login_state():
    """删除登录态。"""
    import shutil
    user_data_dir = str(get_user_data_dir())
    if os.path.exists(user_data_dir):
        shutil.rmtree(user_data_dir)
        print(f"[OK] 登录信息已清除")
    else:
        print("没有已保存的登录信息")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "--verify":
            is_valid = verify_login_state()
            sys.exit(0 if is_valid else 1)
        elif sys.argv[1] == "--browse":
            browse_xhs()
        elif sys.argv[1] == "--logout":
            delete_login_state()
        else:
            print(f"未知参数: {sys.argv[1]}")
    else:
        login_xhs_and_save_state()

