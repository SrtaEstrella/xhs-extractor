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

    st.title("小红书笔记提取工具")

    # 检查登录态
    if not check_login_state_exists():
        st.error("未找到登录态，请先运行一键启动脚本登录")
        st.stop()

    # ---- 输入区域 ----
    url_input = st.text_input(
        "小红书链接",
        placeholder="https://www.xiaohongshu.com/explore/... 或直接粘贴分享文本",
    )

    # 保存目录 + 操作按钮
    btn_col1, btn_col2, btn_col3, btn_col4, btn_col5 = st.columns([2, 1, 1, 1, 3])
    with btn_col1:
        extract_btn = st.button("开始提取", type="primary", width='stretch')
    with btn_col2:
        ocr_btn = st.button("OCR 识别", disabled="note" not in st.session_state, width='stretch')
    with btn_col3:
        download_img_btn = st.button("下载图片", disabled="note" not in st.session_state, width='stretch')
    with btn_col4:
        download_md_btn = st.button("下载正文", disabled="note" not in st.session_state, width='stretch')
    with btn_col5:
        save_dir = Path(st.text_input(
            "保存到",
            value=str(Path.home() / "Downloads" / "xhs_notes"),
            key="save_dir",
            label_visibility="collapsed",
        ))

    # ---- 提取逻辑 ----
    if extract_btn:
        raw = url_input.strip()
        if not raw:
            st.warning("请输入小红书链接或分享文本")
        else:
            try:
                with st.spinner("正在提取..."):
                    url = extract_xhs_url_from_share_text(raw)
                    if url:
                        note = fetch_note_from_url(url)
                    else:
                        note = fetch_note_from_url(raw)
                st.session_state.note = note
                st.rerun()
            except Exception as e:
                st.error(f"提取失败: {e}")

    # ---- 结果展示 ----
    if "note" in st.session_state:
        st.markdown("---")
        note = st.session_state.note

        # 标题 + 作者
        col1, col2 = st.columns([2, 1])
        with col1:
            st.metric("标题", note.title[:50] + ("..." if len(note.title) > 50 else ""))
        with col2:
            author_display = getattr(note, 'author', '') or "(未知作者)"
            st.metric("作者", author_display)

        # 正文
        st.subheader(f"正文（{len(note.text)} 字符）")
        st.markdown(note.text or "(无正文)")

        # OCR 进度 + 结果（正文下方，图片上方）
        ocr_status = st.empty()
        ocr_placeholder = st.empty()

        # ---- OCR 按钮 ----
        if ocr_btn and note.images:
            try:
                from xhs_extractor_module.ocr import OCRProcessor
                ocr_status.info("正在加载 OCR 模型...")
                ocr_processor = OCRProcessor()

                all_results = []
                for idx, text in ocr_processor.ocr_images_stream(note.images):
                    if text:
                        all_results.append(f"[图片 {idx} OCR 结果] {text.replace(chr(10), ' ')}")
                        ocr_status.success(f"已识别 {idx}/{len(note.images)} 张")
                    else:
                        ocr_status.info(f"图片 {idx}/{len(note.images)} 未识别到文字")
                    ocr_placeholder.markdown(
                        '<div style="white-space:pre-wrap; word-wrap:break-word;">'
                        + ("\n".join(all_results) if all_results else "(暂无识别结果)")
                        + '</div>',
                        unsafe_allow_html=True,
                    )

                note.ocr_text = "\n".join(all_results)
                st.session_state.note = note
                if note.ocr_text:
                    ocr_status.success(f"OCR 完成，共识别 {len(all_results)}/{len(note.images)} 张，{len(note.ocr_text)} 字符")
                else:
                    ocr_status.warning("OCR 未识别到文字内容")
            except ImportError:
                st.error("OCR 不可用，请安装: pip install paddleocr paddlepaddle")
            except Exception as e:
                st.error(f"OCR 失败: {e}")

        # 图片预览（水平滚动）
        if note.images:
            st.subheader(f"图片（{len(note.images)} 张）")
            imgs_html = "".join(
                f'<img src="{url}" style="height:320px; margin-right:10px; border-radius:6px;" title="图片 {i+1}">'
                for i, url in enumerate(note.images)
            )
            st.markdown(
                f'<div style="overflow-x:auto; white-space:nowrap; padding:8px 0;">{imgs_html}</div>',
                unsafe_allow_html=True,
            )

        # ---- 下载图片 ----
        if download_img_btn and note.images:
            dst = save_dir / sanitize_filename(note.title)
            dst.mkdir(parents=True, exist_ok=True)
            success = sum(1 for i, u in enumerate(note.images)
                          if download_image(u, dst / f"image_{i+1:03d}.jpg"))
            st.success(f"图片已保存: {success}/{len(note.images)} → {dst}")
            st.rerun()

        # ---- 下载正文 ----
        if download_md_btn:
            dst = save_dir / sanitize_filename(note.title)
            dst.mkdir(parents=True, exist_ok=True)
            md_path = dst / f"{sanitize_filename(note.title)}.md"
            md = f"# {note.title}\n\n**链接**: {note.url}\n\n---\n\n{note.text}\n"
            if note.ocr_text:
                md += f"\n\n---\n\n## OCR 识别结果\n\n{note.ocr_text}\n"
            md_path.write_text(md, encoding='utf-8')
            st.success(f"正文已保存 → {md_path}")
            st.rerun()


    # ---- 底部说明 ----
    # ---- 底部说明 ----
    st.markdown("---")
    st.markdown("""
    ### 使用说明

    1. **输入链接**：输入小红书笔记链接，或直接粘贴 App 分享文本
    2. **开始提取**：点击「开始提取」按钮
    3. **查看结果**：正文和图片即刻展示，无需额外操作
    4. **按需使用**：随时点击「OCR 识别」提取图片文字、「下载图片」保存图片、「下载正文」保存 Markdown

    ### 提示

    - 笔记文件保存到上方「保存到」目录下以标题命名的文件夹中
    - Markdown 正文包含标题、正文文字和 OCR 结果（如有）
    - 图片按顺序命名为 `image_001.jpg` 等
    """)

if __name__ == "__main__":
    # stderr过滤器已在文件顶部设置，这里直接运行main
    # 忽略特定的警告（只过滤Warning类型）
    import warnings
    warnings.filterwarnings("ignore", message=".*torch.classes.*")
    warnings.filterwarnings("ignore", message=".*streamlit.watcher.*")
    
    main()

