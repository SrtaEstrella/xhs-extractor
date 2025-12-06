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

# 抑制 urllib3 和运行时警告
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", message=".*urllib3.*")
warnings.filterwarnings("ignore", message=".*OpenSSL.*")


# 登录态文件路径（保存在模块目录下）
STATE_PATH = Path(__file__).parent / "xhs_state.json"


def login_xhs_and_save_state(state_path: str = None):
    """
    第一次运行时调用：
    - 打开带 UI 的 Chromium
    - 访问小红书官网
    - 用户手工扫码 / 输入手机号登录
    - 登录完后在终端按回车，脚本会把当前登录态写入 xhs_state.json
    
    Args:
        state_path: 登录态保存路径，默认为模块目录下的 xhs_state.json
    """
    if state_path is None:
        state_path = str(STATE_PATH)
    
    print("=" * 60)
    print("小红书登录助手")
    print("=" * 60)
    print(f"登录态将保存到: {state_path}")
    print("\n正在打开浏览器...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context()
        page = context.new_page()
        
        print("\n正在访问小红书官网...")
        page.goto("https://www.xiaohongshu.com", wait_until="networkidle")
        
        print("\n" + "=" * 60)
        print("请在打开的浏览器里完成小红书登录：")
        print("  - 可以使用手机号登录")
        print("  - 也可以使用扫码登录")
        print("  - 登录成功后，回到终端按回车继续...")
        print("=" * 60)
        
        input("\n登录完成后按回车：")
        
        # 持久化当前 context 的 cookie / localStorage 等
        context.storage_state(path=state_path)
        
        print(f"\n✅ 登录状态已保存到: {state_path}")
        print("下次使用时将自动使用此登录态，无需再次登录。")
        
        browser.close()


def check_login_state_exists(state_path: str = None) -> bool:
    """
    检查登录态文件是否存在
    
    Args:
        state_path: 登录态文件路径，默认为模块目录下的 xhs_state.json
    
    Returns:
        如果文件存在返回True，否则返回False
    """
    if state_path is None:
        state_path = str(STATE_PATH)
    
    return os.path.exists(state_path) and os.path.getsize(state_path) > 0


def verify_login_state(state_path: str = None) -> bool:
    """
    验证登录状态是否有效
    通过访问小红书探索页面来检查登录状态是否仍然有效
    
    Args:
        state_path: 登录态文件路径，默认为模块目录下的 xhs_state.json
    
    Returns:
        如果登录状态有效返回True，否则返回False
    """
    if state_path is None:
        state_path = str(STATE_PATH)
    
    # 检查文件是否存在
    if not check_login_state_exists(state_path):
        return False
    
    # 抑制验证过程中的警告信息（已在文件顶部设置，这里确保完全抑制）
    warnings.filterwarnings("ignore")
    
    print("正在验证登录状态...")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=state_path)
            page = context.new_page()
            
            # 访问探索页面
            try:
                page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=30000)
            except PlaywrightTimeoutError:
                browser.close()
                return False
            
            # 等待页面加载完成
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except PlaywrightTimeoutError:
                # 如果networkidle超时，继续检查
                pass
            
            # 获取页面内容
            page_text = page.inner_text("body").lower()
            page_url = page.url.lower()
            
            # 检查是否被重定向到登录页面
            if "login" in page_url or "signin" in page_url:
                browser.close()
                return False
            
            # 检查页面文本中是否包含登录相关的关键词
            login_keywords = ['登录', '注册', '发现发布通知登录我', '请登录', '登录查看', '立即登录']
            has_login_keyword = any(keyword in page_text for keyword in login_keywords)
            
            # 检查页面是否有正常内容（登录页面通常内容较少）
            # 如果页面文本太短，可能是登录页面
            if len(page_text) < 100:
                browser.close()
                return False
            
            # 如果包含登录关键词且内容较少，可能未登录
            if has_login_keyword and len(page_text) < 500:
                browser.close()
                return False
            
            # 尝试检查是否有登录弹窗或登录按钮（通过检查特定元素）
            try:
                # 检查常见的登录相关元素
                login_selectors = [
                    "text=登录",
                    "text=注册",
                    "text=立即登录",
                    "text=请登录",
                    "[class*='login']",
                    "[class*='signin']",
                    "[id*='login']",
                    "[id*='signin']"
                ]
                login_count = 0
                for selector in login_selectors:
                    try:
                        elements = page.query_selector_all(selector)
                        login_count += len(elements)
                    except Exception:
                        pass
                # 如果找到太多登录相关元素，可能是未登录状态
                if login_count > 5:
                    browser.close()
                    return False
            except Exception:
                # 如果查询失败，继续使用其他方法判断
                pass
            
            browser.close()
            return True
            
    except Exception as e:
        print(f"验证登录状态时出错: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    # 如果传入参数 "--verify"，则只验证登录状态
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        is_valid = verify_login_state()
        sys.exit(0 if is_valid else 1)
    else:
        login_xhs_and_save_state()

