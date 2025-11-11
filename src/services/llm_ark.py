import httpx
from typing import List, Dict, Any, Optional
from config import LLM_API_KEY, ARK_API_URL, ARK_MODEL_ID


def chat(messages: List[Dict[str, str]], model: Optional[str] = None, temperature: float = 0.2, max_tokens: int = 1024) -> Optional[str]:
    """调用火山引擎 Ark Chat Completions，返回 assistant 文本。
    兼容 OpenAI 风格的请求结构。
    """
    if not LLM_API_KEY:
        return None
    try:
        payload = {
            "model": model or ARK_MODEL_ID,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}",
        }
        with httpx.Client(timeout=20) as client:
            resp = client.post(ARK_API_URL, json=payload, headers=headers)
        if resp.status_code != 200:
            return None
        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return None
        content = choices[0].get("message", {}).get("content")
        return content
    except Exception:
        return None