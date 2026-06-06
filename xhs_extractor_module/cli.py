#!/usr/bin/env python3
"""
小红书笔记提取 CLI 客户端
输入分享链接，输出完整文字内容
"""
from __future__ import annotations

import sys
import argparse
from pathlib import Path
from typing import Optional

from xhs_extractor_module.xhs_fetch import fetch_note_from_share_text, fetch_note_from_url
from xhs_extractor_module.xhs_share import extract_xhs_url_from_share_text
from xhs_extractor_module.xhs_login import check_login_state_exists, STATE_PATH
from xhs_extractor_module.ocr import OCRProcessor, extract_ocr_from_note


def print_note_content(note, include_ocr: bool = True, include_images: bool = False):
    """
    打印笔记内容
    
    Args:
        note: Note对象
        include_ocr: 是否包含OCR文本
        include_images: 是否包含图片URL列表
    """
    print("\n" + "=" * 80)
    print("📝 笔记内容")
    print("=" * 80)
    
    # 标题
    if note.title:
        print(f"\n【标题】\n{note.title}\n")
    
    # 正文
    if note.text:
        print("【正文】")
        print(note.text)
        print()
    
    # OCR文本
    if include_ocr and note.ocr_text:
        print("【图片文字识别】")
        print(note.ocr_text)
        print()
    
    # 合并的完整文本
    full_text = note.text
    if include_ocr and note.ocr_text:
        full_text += "\n\n[图片文字识别]\n" + note.ocr_text
    
    print("=" * 80)
    print("📊 统计信息")
    print("=" * 80)
    print(f"笔记ID: {note.id}")
    print(f"链接: {note.url}")
    print(f"标题长度: {len(note.title)} 字符")
    print(f"正文长度: {len(note.text)} 字符")
    if include_ocr:
        print(f"OCR文本长度: {len(note.ocr_text)} 字符")
        print(f"总文本长度: {len(full_text)} 字符")
    print(f"图片数量: {len(note.images)}")
    
    if include_images and note.images:
        print("\n【图片URL列表】")
        for i, img_url in enumerate(note.images, 1):
            print(f"{i}. {img_url}")
    
    print("\n" + "=" * 80)
    print("📄 完整文本内容")
    print("=" * 80)
    print(full_text)
    print("=" * 80)


def extract_note(share_text: str, use_ocr: bool = False, include_images: bool = False) -> Optional[object]:
    """
    提取笔记内容
    
    Args:
        share_text: 小红书分享文本或URL
        use_ocr: 是否进行OCR识别
        include_images: 是否在输出中包含图片URL
    
    Returns:
        Note对象，如果失败返回None
    """
    # 检查登录态
    if not check_login_state_exists():
        print("\n[X] 错误: 未找到登录态文件")
        print(f"   请先运行登录脚本: python -m xhs_extractor_module.xhs_login")
        return None
    
    try:
        # 判断输入是URL还是分享文本
        if share_text.startswith("http://") or share_text.startswith("https://"):
            # 直接是URL
            print(f"正在提取笔记: {share_text}")
            note = fetch_note_from_url(share_text)
        else:
            # 是分享文本
            print("正在解析分享文本...")
            note = fetch_note_from_share_text(share_text)
        
        # OCR处理
        if use_ocr and note.images:
            print(f"\n正在识别 {len(note.images)} 张图片中的文字...")
            try:
                ocr_processor = OCRProcessor()
                note.ocr_text = extract_ocr_from_note(note, ocr_processor)
                if note.ocr_text:
                    print(f"[OK] OCR识别完成，识别到 {len(note.ocr_text)} 字符")
                else:
                    print("[!] OCR未识别到文字内容")
            except ImportError:
                print("[X] OCR功能不可用：未安装 paddleocr")
                print("   安装方法: pip install paddleocr paddlepaddle")
            except Exception as e:
                print(f"[!] OCR识别失败: {e}")
                print("   继续使用已提取的文本内容")
        elif note.images and not use_ocr:
            # 提示用户可以使用OCR
            print(f"\n[!] 提示: 检测到 {len(note.images)} 张图片")
            print("   使用 --ocr 参数可以识别图片中的文字")
            print("   例如: python -m xhs_extractor_module.cli --ocr \"分享文本...\"")
        
        return note
        
    except ValueError as e:
        print(f"\n[X] 错误: {e}")
        return None
    except Exception as e:
        print(f"\n[X] 提取失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def interactive_mode():
    """交互式模式"""
    print("=" * 80)
    print("📱 小红书笔记提取工具")
    print("=" * 80)
    print("\n使用说明:")
    print("  - 直接粘贴小红书分享文本（包含链接）")
    print("  - 或输入完整的小红书URL")
    print("  - 输入 'quit' 或 'exit' 退出")
    print("  - 输入 'ocr' 切换OCR模式（识别图片文字）")
    print("-" * 80)
    
    use_ocr = False
    
    while True:
        try:
            print("\n请输入分享文本或URL:")
            user_input = input("> ").strip()
            
            if not user_input:
                continue
            
            # 退出命令
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 再见！")
                break
            
            # OCR切换命令
            if user_input.lower() == 'ocr':
                use_ocr = not use_ocr
                status = "开启" if use_ocr else "关闭"
                print(f"\n[OK] OCR模式已{status}")
                if use_ocr:
                    print("   注意: OCR需要安装 paddleocr，首次使用可能需要下载模型")
                continue
            
            # 提取笔记
            note = extract_note(user_input, use_ocr=use_ocr)
            
            if note:
                print_note_content(note, include_ocr=use_ocr)
            
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except EOFError:
            print("\n\n👋 再见！")
            break


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="小红书笔记提取工具 - 输入分享链接，输出完整文字内容",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 交互式模式
  python -m xhs_extractor_module.cli
  
  # 直接提取
  python -m xhs_extractor_module.cli "算法面经... http://xhslink.com/o/ABC123 复制后打开"
  
  # 使用OCR识别图片文字
  python -m xhs_extractor_module.cli --ocr "分享文本..."
  
  # 从URL提取
  python -m xhs_extractor_module.cli --url "http://xhslink.com/o/ABC123"
  
  # 保存到文件
  python -m xhs_extractor_module.cli "分享文本..." > output.txt
        """
    )
    
    parser.add_argument(
        'input',
        nargs='?',
        help='小红书分享文本或URL（如果不提供，进入交互式模式）'
    )
    
    parser.add_argument(
        '--url', '-u',
        action='store_true',
        help='输入的是URL而不是分享文本'
    )
    
    parser.add_argument(
        '--ocr', '-o',
        action='store_true',
        help='启用OCR识别图片中的文字（需要安装paddleocr）'
    )
    
    parser.add_argument(
        '--images', '-i',
        action='store_true',
        help='在输出中包含图片URL列表'
    )
    
    parser.add_argument(
        '--output', '-O',
        type=str,
        help='保存完整文本到文件'
    )
    
    parser.add_argument(
        '--text-only', '-t',
        action='store_true',
        help='只输出文本内容，不包含统计信息'
    )
    
    args = parser.parse_args()
    
    # 如果没有提供输入，进入交互式模式
    if not args.input:
        interactive_mode()
        return
    
    # 提取笔记
    input_text = args.input
    if args.url:
        # 如果指定了--url，直接使用输入作为URL
        note = extract_note(input_text, use_ocr=args.ocr, include_images=args.images)
    else:
        # 否则作为分享文本处理
        note = extract_note(input_text, use_ocr=args.ocr, include_images=args.images)
    
    if not note:
        sys.exit(1)
    
    # 准备输出内容
    full_text = note.text
    if args.ocr and note.ocr_text:
        full_text += "\n\n[图片文字识别]\n" + note.ocr_text
    
    # 输出
    if args.text_only:
        # 只输出文本
        print(full_text)
    else:
        # 输出完整信息
        print_note_content(note, include_ocr=args.ocr, include_images=args.images)
    
    # 保存到文件
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(f"标题: {note.title}\n\n")
                f.write(f"正文:\n{note.text}\n\n")
                if args.ocr and note.ocr_text:
                    f.write(f"图片文字识别:\n{note.ocr_text}\n")
                f.write(f"\n链接: {note.url}\n")
            print(f"\n[OK] 内容已保存到: {args.output}")
        except Exception as e:
            print(f"\n[X] 保存文件失败: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()

