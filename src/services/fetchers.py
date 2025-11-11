import httpx
from bs4 import BeautifulSoup
import dateparser
from langdetect import detect

from src.utils.text import normalize_text, translate_to_zh


def zhihu_fetch(url: str):
    """尽量从知乎页面（问题/文章/回答）提取可读正文。
    - 跟随跳转并使用浏览器头，降低 403/重定向影响
    - 优先抓取 RichText/文章段落，其次退化为整页文本
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Referer": "https://www.zhihu.com/",
    }
    try:
        r = httpx.get(url, timeout=12, follow_redirects=True, headers=headers)
        if r.status_code != 200:
            # 尝试通过 r.jina.ai 代理抓取可读文本（去除原始协议，按 http://<host>/<path> 拼接）
            stripped = url
            if stripped.startswith("https://"):
                stripped = stripped[len("https://"):]
            elif stripped.startswith("http://"):
                stripped = stripped[len("http://"):]
            proxy = f"https://r.jina.ai/http://{stripped}"
            try:
                pr = httpx.get(proxy, timeout=12, headers=headers)
                if pr.status_code == 200 and len(pr.text) > 100:
                    text = normalize_text(pr.text)
                    try:
                        lang = detect(text)
                    except Exception:
                        lang = "unknown"
                    if lang != "zh-cn" and lang != "zh" and lang != "unknown":
                        text = translate_to_zh(text)
                    published = dateparser.search.search_dates(text)
                    return {
                        "url": url,
                        "text": text,
                        "language": lang,
                        "published": published[0][1] if published else None,
                    }
            except Exception:
                pass
            return None
        html = r.text
        soup = BeautifulSoup(html, "html.parser")

        # 标题
        title = None
        for sel in [
            "h1.QuestionHeader-title",
            "h1.Post-Title",
            "h1.ContentItem-title",
        ]:
            node = soup.select_one(sel)
            if node:
                title = node.get_text(strip=True)
                break
        if not title:
            meta = soup.find("meta", attrs={"property": "og:title"})
            if meta and meta.get("content"):
                title = meta["content"].strip()

        # 正文（问题回答/文章内容）
        parts = []
        # 文章正文
        for p in soup.select("article p"):
            txt = p.get_text(" ", strip=True)
            if txt:
                parts.append(txt)
        # RichText 内容（回答/评论）
        for p in soup.select(".RichText p, .RichContent-inner p"):
            txt = p.get_text(" ", strip=True)
            if txt:
                parts.append(txt)

        text = "\n".join(parts)
        if not text or len(text) < 100:
            # 退化：去除脚本/样式后取整页文本
            for tag in soup(["script", "style", "noscript"]):
                tag.extract()
            text = normalize_text(soup.get_text("\n"))
            if not text or len(text) < 100:
                # 最后兜底：r.jina.ai 代理可读文本（同样去除协议）
                stripped = url
                if stripped.startswith("https://"):
                    stripped = stripped[len("https://"):]
                elif stripped.startswith("http://"):
                    stripped = stripped[len("http://"):]
                proxy = f"https://r.jina.ai/http://{stripped}"
                try:
                    pr = httpx.get(proxy, timeout=12, headers=headers)
                    if pr.status_code == 200 and len(pr.text) > 100:
                        text = normalize_text(pr.text)
                except Exception:
                    pass

        # 语言与翻译
        try:
            lang = detect(text)
        except Exception:
            lang = "unknown"
        if lang != "zh-cn" and lang != "zh" and lang != "unknown":
            text = translate_to_zh(text)

        # 尝试解析日期
        published = dateparser.search.search_dates(text)
        return {
            "url": url,
            "text": text,
            "language": lang,
            "published": published[0][1] if published else None,
        }
    except Exception:
        return None