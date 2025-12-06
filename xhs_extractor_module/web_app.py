#!/usr/bin/env python3
"""
小红书笔记提取 Web 前端
使用 Streamlit 构建
"""
from __future__ import annotations

import os
import re
import json
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径，确保可以导入模块
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 在导入Streamlit之前设置stderr过滤器，过滤PyTorch相关错误
_original_stderr = sys.stderr

class FilteredStderr:
    """过滤PyTorch相关错误的stderr包装器"""
    def __init__(self, original):
        self.original = original
    
    def write(self, text):
        # 过滤掉PyTorch相关的错误信息（这些是Streamlit扫描模块时的已知问题）
        text_str = str(text)
        # 检查是否包含PyTorch相关的错误关键词（更全面的匹配）
        py_torch_keywords = [
            "torch.classes",
            "torch/_classes.py",
            "streamlit.watcher",
            "local_sources_watcher.py",
            "RuntimeError: Tried to instantiate class '__path__._path'",
            "RuntimeError: no running event loop",
            "Examining the path of torch.classes raised",
            "During handling of the above exception",
            "get_custom_class_python_wrapper",
            "extract_paths(module)",
            "bootstrap.py",
            "asyncio.get_running_loop"
        ]
        
        # 如果包含任何PyTorch相关关键词，则过滤掉
        if any(keyword in text_str for keyword in py_torch_keywords):
            return  # 忽略这些非致命错误
        
        self.original.write(text)
    
    def flush(self):
        self.original.flush()
    
    def __getattr__(self, name):
        return getattr(self.original, name)

# 设置stderr过滤器（在导入Streamlit之前）
sys.stderr = FilteredStderr(_original_stderr)

import streamlit as st

from xhs_extractor_module.xhs_fetch import fetch_note_from_url, fetch_note_from_share_text
from xhs_extractor_module.xhs_share import extract_xhs_url_from_share_text
from xhs_extractor_module.xhs_login import check_login_state_exists, STATE_PATH
# OCR模块延迟导入，避免Streamlit启动时扫描PyTorch相关模块导致错误
# from xhs_extractor_module.ocr import OCRProcessor, extract_ocr_from_note
from xhs_extractor_module.models import Note


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除非法字符"""
    # 移除或替换非法字符
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # 移除前后空格和点
    filename = filename.strip('. ')
    # 限制长度
    if len(filename) > 200:
        filename = filename[:200]
    # 如果为空，使用默认名称
    if not filename:
        filename = "未命名笔记"
    return filename


def download_image(image_url: str, save_path: Path) -> bool:
    """下载单张图片"""
    try:
        import requests
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://www.xiaohongshu.com/',
        }
        
        response = requests.get(image_url, headers=headers, timeout=30, stream=True)
        response.raise_for_status()
        
        # 确定文件扩展名
        content_type = response.headers.get('Content-Type', '').lower()
        if 'png' in content_type:
            ext = '.png'
        elif 'gif' in content_type:
            ext = '.gif'
        elif 'webp' in content_type:
            ext = '.webp'
        else:
            ext = '.jpg'
        
        # 从URL提取文件名（如果有）
        url_filename = os.path.basename(image_url).split('?')[0]
        if url_filename and '.' in url_filename:
            ext = os.path.splitext(url_filename)[1]
        
        # 保存文件
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True
    except Exception as e:
        st.error(f"下载图片失败 {image_url[:50]}...: {e}")
        return False


def save_note_to_local(
    note: Note,
    base_dir: Path,
    download_images: bool = False,
    use_ocr: bool = False
) -> dict:
    """
    保存笔记到本地
    
    Returns:
        dict: 包含保存结果的字典
    """
    # 清理标题作为文件夹名
    folder_name = sanitize_filename(note.title)
    save_dir = base_dir / folder_name
    save_dir.mkdir(parents=True, exist_ok=True)
    
    results = {
        "success": True,
        "folder": str(save_dir),
        "files": [],
        "errors": []
    }
    
    # 1. 保存笔记正文为MD文件
    md_filename = sanitize_filename(note.title) + ".md"
    md_path = save_dir / md_filename
    
    try:
        md_content = f"# {note.title}\n\n"
        md_content += f"**链接**: {note.url}\n\n"
        md_content += f"**笔记ID**: {note.id}\n\n"
        md_content += "---\n\n"
        md_content += "## 正文\n\n"
        md_content += note.text + "\n\n"
        
        # 如果有OCR文本，添加
        if use_ocr and note.ocr_text:
            md_content += "---\n\n"
            md_content += "## 图片文字识别\n\n"
            md_content += note.ocr_text + "\n\n"
        
        # 如果有图片，添加图片引用
        if note.images:
            md_content += "---\n\n"
            md_content += "## 图片\n\n"
            for i, img_url in enumerate(note.images, 1):
                if download_images:
                    img_filename = f"image_{i:03d}.jpg"
                    md_content += f"![图片 {i}]({img_filename})\n\n"
                else:
                    md_content += f"- [图片 {i}]({img_url})\n\n"
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        results["files"].append(str(md_path))
        st.success(f"✅ 笔记正文已保存: {md_filename}")
        
    except Exception as e:
        results["success"] = False
        results["errors"].append(f"保存MD文件失败: {e}")
        st.error(f"❌ 保存MD文件失败: {e}")
    
    # 2. 下载图片（如果启用）
    if download_images and note.images:
        st.info(f"正在下载 {len(note.images)} 张图片...")
        
        progress_bar = st.progress(0)
        success_count = 0
        
        for i, img_url in enumerate(note.images):
            try:
                # 确定文件扩展名
                img_filename = f"image_{i+1:03d}.jpg"
                img_path = save_dir / img_filename
                
                if download_image(img_url, img_path):
                    results["files"].append(str(img_path))
                    success_count += 1
                
                # 更新进度
                progress_bar.progress((i + 1) / len(note.images))
                
            except Exception as e:
                results["errors"].append(f"下载图片 {i+1} 失败: {e}")
        
        progress_bar.empty()
        st.success(f"✅ 图片下载完成: {success_count}/{len(note.images)} 张")
    
    return results


def main():
    """主函数"""
    st.set_page_config(
        page_title="小红书笔记提取工具",
        page_icon="📱",
        layout="wide"
    )
    
    st.title("📱 小红书笔记提取工具")
    st.markdown("---")
    
    # 检查登录态
    if not check_login_state_exists():
        st.error("❌ 未找到登录态文件")
        st.info("请先运行以下命令进行登录：")
        st.code("python -m xhs_extractor_module.xhs_login", language="bash")
        st.stop()
    
    # 侧边栏：配置选项
    with st.sidebar:
        st.header("⚙️ 设置")
        
        use_ocr = st.checkbox(
            "🔤 OCR识别图片文字",
            value=False,
            help="识别图片中的文字内容（需要安装paddleocr）"
        )
        
        download_images = st.checkbox(
            "🖼️ 下载图片到本地",
            value=False,
            help="将笔记中的图片下载到本地文件夹"
        )
        
        download_content = st.checkbox(
            "📝 下载笔记正文",
            value=True,
            help="将笔记正文保存为Markdown文件"
        )
        
        st.markdown("---")
        st.header("📁 保存位置")
        
        # 保存目录选择
        default_dir = Path.home() / "Downloads" / "xhs_notes"
        save_dir_input = st.text_input(
            "保存目录",
            value=str(default_dir),
            help="笔记将保存到此目录下的以标题命名的文件夹中"
        )
        
        save_dir = Path(save_dir_input)
    
    # 主界面
    st.header("📥 输入小红书链接")
    
    # 输入方式选择
    input_method = st.radio(
        "输入方式",
        ["直接输入URL", "粘贴分享文本"],
        horizontal=True
    )
    
    if input_method == "直接输入URL":
        url_input = st.text_input(
            "小红书链接",
            placeholder="https://www.xiaohongshu.com/explore/... 或 http://xhslink.com/...",
            help="支持完整链接或短链接"
        )
        share_text = None
    else:
        share_text_input = st.text_area(
            "分享文本",
            placeholder="算法面经：字节大模型Agent 11.16 一面： 请介绍 Tran... http://xhslink.com/o/ABC123 复制后打开【小红书】查看笔记！",
            height=100,
            help="粘贴完整的小红书分享文本"
        )
        url_input = None
        share_text = share_text_input if share_text_input.strip() else None
    
    # 提取按钮
    col1, col2 = st.columns([1, 4])
    with col1:
        extract_button = st.button("🚀 开始提取", type="primary", use_container_width=True)
    
    # 处理提取
    if extract_button:
        if not url_input and not share_text:
            st.warning("⚠️ 请输入小红书链接或分享文本")
        else:
            try:
                with st.spinner("正在提取笔记内容..."):
                    # 提取笔记
                    if url_input:
                        note = fetch_note_from_url(url_input)
                    else:
                        note = fetch_note_from_share_text(share_text)
                
                # 显示提取结果
                st.success("✅ 笔记提取成功！")
                
                # 显示笔记信息
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("标题长度", f"{len(note.title)} 字符")
                with col2:
                    st.metric("正文长度", f"{len(note.text)} 字符")
                with col3:
                    st.metric("图片数量", len(note.images))
                
                # 显示标题和正文预览
                st.subheader("📝 笔记内容")
                st.markdown(f"**标题**: {note.title}")
                st.markdown(f"**链接**: {note.url}")
                
                with st.expander("查看正文", expanded=False):
                    st.markdown(note.text)
                
                # OCR处理
                if use_ocr and note.images:
                    with st.spinner(f"正在识别 {len(note.images)} 张图片中的文字..."):
                        try:
                            # 延迟导入OCR模块，避免启动时扫描PyTorch相关模块
                            from xhs_extractor_module.ocr import OCRProcessor, extract_ocr_from_note
                            ocr_processor = OCRProcessor()
                            note.ocr_text = extract_ocr_from_note(note, ocr_processor)
                            if note.ocr_text:
                                st.success(f"✅ OCR识别完成，识别到 {len(note.ocr_text)} 字符")
                                with st.expander("查看OCR识别结果", expanded=False):
                                    st.markdown(note.ocr_text)
                            else:
                                st.warning("⚠️ OCR未识别到文字内容")
                        except ImportError:
                            st.error("❌ OCR功能不可用：未安装 paddleocr")
                            st.info("安装方法: `pip install paddleocr paddlepaddle`")
                        except Exception as e:
                            st.error(f"❌ OCR识别失败: {e}")
                
                # 显示图片
                if note.images:
                    st.subheader("🖼️ 图片预览")
                    num_cols = 3
                    cols = st.columns(num_cols)
                    for i, img_url in enumerate(note.images[:9]):  # 只显示前9张
                        with cols[i % num_cols]:
                            st.image(img_url, caption=f"图片 {i+1}", use_container_width=True)
                    
                    if len(note.images) > 9:
                        st.info(f"还有 {len(note.images) - 9} 张图片未显示")
                
                # 保存到本地
                if download_content or download_images:
                    st.subheader("💾 保存到本地")
                    
                    if not save_dir.exists():
                        save_dir.mkdir(parents=True, exist_ok=True)
                        st.info(f"📁 创建目录: {save_dir}")
                    
                    try:
                        results = save_note_to_local(
                            note,
                            save_dir,
                            download_images=download_images,
                            use_ocr=use_ocr
                        )
                        
                        if results["success"]:
                            st.success(f"✅ 保存完成！")
                            st.info(f"📁 保存位置: {results['folder']}")
                            st.info(f"📄 文件数量: {len(results['files'])}")
                            
                            # 显示文件列表
                            with st.expander("查看保存的文件", expanded=False):
                                for file_path in results["files"]:
                                    st.text(file_path)
                            
                            if results["errors"]:
                                st.warning("⚠️ 部分文件保存失败:")
                                for error in results["errors"]:
                                    st.text(error)
                        else:
                            st.error("❌ 保存失败")
                            for error in results["errors"]:
                                st.error(error)
                    
                    except Exception as e:
                        st.error(f"❌ 保存失败: {e}")
                        import traceback
                        st.code(traceback.format_exc())
            
            except ValueError as e:
                st.error(f"❌ 错误: {e}")
            except Exception as e:
                st.error(f"❌ 提取失败: {e}")
                import traceback
                with st.expander("查看错误详情"):
                    st.code(traceback.format_exc())
    
    # 底部说明
    st.markdown("---")
    st.markdown("""
    ### 📖 使用说明
    
    1. **输入链接**: 可以直接输入URL或粘贴分享文本
    2. **选择选项**: 在侧边栏选择需要的功能
    3. **开始提取**: 点击"开始提取"按钮
    4. **查看结果**: 提取完成后可以预览内容
    5. **保存文件**: 如果启用了下载选项，文件会自动保存到指定目录
    
    ### 💡 提示
    
    - 笔记会保存到指定目录下的以标题命名的文件夹中
    - Markdown文件包含标题、正文、OCR文本（如果启用）和图片引用
    - 图片会按顺序命名为 `image_001.jpg`, `image_002.jpg` 等
    """)


if __name__ == "__main__":
    # stderr过滤器已在文件顶部设置，这里直接运行main
    # 忽略特定的警告（只过滤Warning类型）
    import warnings
    warnings.filterwarnings("ignore", message=".*torch.classes.*")
    warnings.filterwarnings("ignore", message=".*streamlit.watcher.*")
    
    main()

