import re


def normalize_text(text: str) -> str:
    text = text or ""
    # 去掉多余空白与控制符
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def translate_to_zh(text: str) -> str:
    """使用 LLM（若已配置）将文本翻译为中文，失败则返回原文。"""
    from config import LLM_PROVIDER, LLM_API_KEY
    if not text:
        return text
    # 无 Key 或非 ark 则直接返回原文
    if not LLM_API_KEY or LLM_PROVIDER != "ark":
        return text
    # 组装翻译提示
    try:
        from src.services.llm_ark import chat
        prompt = (
            "你是一位精准的专业翻译。请将用户提供的文本完整、忠实地翻译为简体中文，"
            "保持原意与风格，不要添加解释或额外信息，仅输出翻译后的中文内容。"
        )
        content = chat([
            {"role": "system", "content": prompt},
            {"role": "user", "content": text[:4000]},
        ])
        return content or text
    except Exception:
        return text