"""LLM 文档规整：将 OCR 碎片文本整理为连贯文章。"""
from __future__ import annotations

from openai import OpenAI

from .llm_config import get_api_key

_BASE_URL = "https://api.deepseek.com/v1"
_MODEL = "deepseek-chat"

_SYSTEM_PROMPT = """你是一个文档整理助手。用户会提供多张图片的 OCR 识别结果，每张图片的结果以 "[图片 N OCR 结果]" 开头。

请将全部 OCR 碎片整理为一篇连贯的文档，遵循以下规则：

1. 去重：不同图片可能截到了相同段落，合并重复内容
2. 补全：OCR 可能导致断句、漏字、错别字，根据上下文修正
3. 分段：按语义将内容组织为自然段落，段落之间用空行分隔
4. 保留原意：不添加原文没有的信息，不改变作者观点

直接输出整理后的文本，不要添加任何解释、前言或后缀。可使用 Markdown 排版（标题、列表、加粗等）以增强可读性。"""


def organize_ocr_text(ocr_text: str):
    """
    将 OCR 碎片文本发送给 LLM 整理为连贯文档。
    返回生成器，逐 chunk yield 增量文本，支持流式渲染。

    Args:
        ocr_text: 完整的 OCR 文本（包含 [图片 N OCR 结果] 标签）

    Yields:
        增量文本片段
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("未配置 API key，请在界面中设置")

    client = OpenAI(api_key=api_key, base_url=_BASE_URL)

    stream = client.chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": ocr_text},
        ],
        temperature=0.3,
        max_tokens=8192,
        stream=True,
    )

    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
