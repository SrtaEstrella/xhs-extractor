# ocr.py
"""
OCR 功能模块
支持多种 OCR 方案：PaddleOCR（本地）、API 调用等
"""
from __future__ import annotations

import os
import sys
from typing import List, Optional
import requests

# PaddlePaddle 3.x oneDNN PIR bug workaround: 禁用 PIR API + oneDNN
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False


class OCRProcessor:
    """OCR 处理器"""
    
    def __init__(self, use_paddleocr: bool = True, use_lang: str = 'ch'):
        """
        Args:
            use_paddleocr: 是否使用 PaddleOCR（本地）
            use_lang: PaddleOCR 语言，'ch' 中文，'en' 英文，'ch' + 'en' 中英混合
        """
        self.use_paddleocr = use_paddleocr and PADDLEOCR_AVAILABLE
        self.ocr_engine = None
        
        if self.use_paddleocr:
            try:
                # PP-OCRv4 比 v5 更快，CPU 友好
                self.ocr_engine = PaddleOCR(
                    lang=use_lang,
                    ocr_version="PP-OCRv4",
                    use_textline_orientation=False,
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    text_det_limit_side_len=640,
                )
            except Exception as e:
                import traceback
                print(f"[OCR ERROR] 初始化失败: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                self.use_paddleocr = False
    
    def ocr_image_from_url(self, image_url: str) -> str:
        """
        从图片 URL 识别文字
        
        Returns:
            识别出的文字文本
        """
        if not image_url or not image_url.startswith('http'):
            pass  # debug removed
            return ""
        
        pass  # debug removed

        try:
            # 下载图片（添加更完整的请求头，模拟浏览器）
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://www.xiaohongshu.com/',
            }
            response = requests.get(image_url, headers=headers, timeout=20, stream=True)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '').lower()
            content_length = response.headers.get('Content-Length', 'unknown')
            pass  # debug removed
            
            # 保存临时文件
            import tempfile
            # 根据 Content-Type 确定文件后缀
            content_type = response.headers.get('Content-Type', '').lower()
            if 'png' in content_type:
                suffix = '.png'
            elif 'gif' in content_type:
                suffix = '.gif'
            elif 'webp' in content_type:
                suffix = '.webp'
            else:
                suffix = '.jpg'
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name
            
            try:
                text = self.ocr_image_from_file(tmp_path)
            finally:
                # 确保删除临时文件
                try:
                    os.unlink(tmp_path)
                except:
                    pass
            
            return text
            
        except requests.exceptions.Timeout:
            pass  # debug removed
            return ""
        except requests.exceptions.RequestException as e:
            pass  # debug removed
            return ""
        except Exception as e:
            pass  # debug removed
            return ""
    
    def ocr_image_from_file(self, image_path: str) -> str:
        """
        从本地图片文件识别文字

        Returns:
            识别出的文字文本，如果没有 OCR 引擎或识别失败则返回空字符串
        """
        if self.use_paddleocr and self.ocr_engine:
            try:
                pass  # debug removed
                # 检查文件是否存在且非空
                if not os.path.exists(image_path):
                    pass  # debug removed
                    return ""
                file_size = os.path.getsize(image_path)
                pass  # debug removed
                if file_size < 100:
                    pass  # debug removed
                    return ""

                result = self.ocr_engine.ocr(image_path)

                pass  # debug removed
                if isinstance(result, list):
                    pass  # debug removed
                    if result:
                        first = result[0]
                        pass  # debug removed
                        if first is not None:
                            pass  # debug removed
                        else:
                            pass  # debug removed
                else:
                    pass  # debug removed

                if not result or result == [None] or result == [[]]:
                    pass  # debug removed
                    return ""
                
                texts = []
                
                # 定义噪音文本过滤函数
                def _is_noise_text(text):
                    """判断是否是噪音文本（文件路径、系统关键字等）"""
                    if not text or len(text.strip()) < 1:
                        return True
                    text_lower = text.lower()
                    # 过滤文件路径
                    if text.startswith('/') or text.startswith('\\') or ':/' in text or ':\\' in text:
                        return True
                    # 过滤系统关键字
                    noise_keywords = ['min', 'max', 'general', 'default', 'none', 'null', 'true', 'false']
                    if text_lower.strip() in noise_keywords:
                        return True
                    # 过滤纯数字（可能是坐标）
                    if text.strip().replace('.', '').replace('-', '').isdigit() and len(text.strip()) < 5:
                        return True
                    return False
                
                # PaddleOCR 3.x 的返回格式可能是：
                # 格式1: [[[x1,y1], [x2,y2], [x3,y3], [x4,y4]], ('text', confidence), ...]
                # 格式2: [{'result': [{'text': '...', 'confidence': ...}, ...]}, ...]
                # 格式3: 其他嵌套格式
                
                # 尝试解析不同格式
                def extract_texts(data, depth=0):
                    """递归提取文字"""
                    if depth > 10:  # 防止无限递归
                        return
                    
                    if isinstance(data, dict):
                        # 如果是字典，查找可能的文本字段
                        for key in ['text', 'result', 'content']:
                            if key in data:
                                extract_texts(data[key], depth + 1)
                        # 递归处理所有值
                        for value in data.values():
                            extract_texts(value, depth + 1)
                    elif isinstance(data, (list, tuple)):
                        for item in data:
                            if isinstance(item, tuple) and len(item) >= 1:
                                # 可能是 (text, confidence) 格式
                                if isinstance(item[0], str):
                                    text = item[0]
                                    # 过滤掉文件路径、系统关键字等
                                    if text and not _is_noise_text(text):
                                        texts.append(text)
                                else:
                                    extract_texts(item, depth + 1)
                            elif isinstance(item, str):
                                # 过滤掉文件路径、系统关键字等
                                if not _is_noise_text(item):
                                    texts.append(item)
                            elif isinstance(item, (list, tuple, dict)):
                                extract_texts(item, depth + 1)
                    elif isinstance(data, str) and data:
                        # 过滤掉文件路径、系统关键字等
                        if not _is_noise_text(data):
                            texts.append(data)
                
                extract_texts(result)
                
                pass  # debug removed
                if texts:
                    pass  # debug removed
                
                return "\n".join(texts) if texts else ""
            except Exception as e:
                import traceback
                print(f"[OCR ERROR] OCR 处理失败: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                return ""
        else:
            pass  # debug removed
            return ""
    
    def ocr_images(self, image_urls: List[str]) -> str:
        """批量 OCR，返回合并文本（兼容旧接口）"""
        return "\n\n".join(
            f"[图片 {i} OCR 结果]\n{text}"
            for i, text in self.ocr_images_stream(image_urls)
            if text
        )

    def ocr_images_stream(self, image_urls: List[str]):
        """
        流式 OCR：每识别完一张就 yield (序号, 文字)，不等待全部完成。
        """
        if not image_urls:
            return

        for i, url in enumerate(image_urls, 1):
            try:
                text = self.ocr_image_from_url(url)
                if text and text.strip():
                    yield (i, text)
                else:
                    yield (i, "")
            except Exception:
                yield (i, "")


def extract_ocr_from_note(note, ocr_processor: Optional[OCRProcessor] = None) -> str:
    """
    从 Note 对象的图片中提取 OCR 文本
    
    Args:
        note: Note 对象
        ocr_processor: OCR 处理器，如果为 None 则创建一个新的
    
    Returns:
        OCR 文本
    """
    if not note.images:
        return ""
    
    if ocr_processor is None:
        ocr_processor = OCRProcessor()
    
    return ocr_processor.ocr_images(note.images)


if __name__ == "__main__":
    # 测试 OCR
    if len(sys.argv) > 1:
        processor = OCRProcessor()
        result = processor.ocr_image_from_file(sys.argv[1])
        print(f"OCR 结果:\n{result}")

