import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


def searx_search(query: str, instances, max_results: int = 20):
    """调用 SearXNG 公共实例进行搜索，返回结果列表；若全部失败则回退到 DuckDuckGo。
    - 增加 User-Agent 与 Accept-Language，提高命中率与兼容性
    - 失败时尝试简易 DuckDuckGo HTML 抓取作为兜底
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    params = {
        "q": query,
        "format": "json",
        "language": "zh-CN",
    }
    for base in instances:
        try:
            r = httpx.get(base, params=params, headers=headers, timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()
            results = []
            for item in data.get("results", [])[:max_results]:
                results.append({
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "content": item.get("content"),
                    "engine": item.get("engine") or "searx",
                })
            if results:
                return results
        except Exception:
            continue
    # Fallback: DuckDuckGo HTML 简易抓取
    try:
        ddg_url = "https://duckduckgo.com/html/"
        r = httpx.get(ddg_url, params={"q": query}, headers=headers, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            links = []
            for a in soup.select(".result__a"):
                href = a.get("href")
                if not href:
                    continue
                links.append({
                    "title": a.get_text(strip=True),
                    "url": href,
                    "content": None,
                    "engine": "duckduckgo_fallback",
                })
                if len(links) >= max_results:
                    break
            return links
    except Exception:
        pass
    return []


def _ddg_html_search(query: str, max_results: int, headers):
    links = []
    try:
        ddg_url = "https://duckduckgo.com/html/"
        r = httpx.get(ddg_url, params={"q": query}, headers=headers, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.select(".result__a"):
                href = a.get("href")
                if not href:
                    continue
                links.append({
                    "title": a.get_text(strip=True),
                    "url": href,
                    "content": None,
                    "engine": "duckduckgo",
                })
                if len(links) >= max_results:
                    break
    except Exception:
        pass
    return links


def _bing_html_search(query: str, max_results: int, headers):
    links = []
    try:
        url = "https://www.bing.com/search"
        r = httpx.get(url, params={"q": query}, headers=headers, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.select("li.b_algo h2 a"):
                href = a.get("href")
                if not href:
                    continue
                # 规范化链接
                href = href.strip().strip("'\"`")
                if href.startswith("//"):
                    href = "https:" + href
                elif not urlparse(href).scheme:
                    href = urljoin("https://www.bing.com/", href)
                title = a.get_text(strip=True)
                links.append({"title": title, "url": href, "content": None, "engine": "bing"})
                if len(links) >= max_results:
                    break
    except Exception:
        pass
    return links


def _baidu_html_search(query: str, max_results: int, headers):
    links = []
    try:
        url = "https://www.baidu.com/s"
        r = httpx.get(url, params={"wd": query}, headers=headers, timeout=15)
        print(f"[Search] Baidu status={r.status_code} q='{query}'")
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            # 选择通用结果卡片标题链接
            for a in soup.select("h3 a, .result h3 a, .c-container h3 a"):
                href = a.get("href")
                if not href:
                    continue
                href = href.strip().strip("'\"`")
                if href.startswith("//"):
                    href = "https:" + href
                elif not urlparse(href).scheme:
                    href = urljoin("https://www.baidu.com/", href)
                title = a.get_text(strip=True)
                links.append({"title": title, "url": href, "content": None, "engine": "baidu"})
                if len(links) >= max_results:
                    break
    except Exception:
        pass
    return links


def web_search_combined(query: str, instances, max_results: int = 20):
    """组合搜索：优先 SearXNG，失败则依次回退到 DuckDuckGo / Bing / Baidu。"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    # 1) SearXNG JSON
    res = searx_search(query, instances=instances, max_results=max_results)
    if res:
        return res
    # 2) DuckDuckGo
    res = _ddg_html_search(query, max_results=max_results, headers=headers)
    if res:
        return res
    # 3) Bing
    res = _bing_html_search(query, max_results=max_results, headers=headers)
    if res:
        return res
    # 4) Baidu
    res = _baidu_html_search(query, max_results=max_results, headers=headers)
    return res


def _sogou_html_search(query: str, max_results: int, headers):
    links = []
    try:
        url = "https://www.sogou.com/web"
        r = httpx.get(url, params={"query": query}, headers=headers, timeout=15)
        print(f"[Search] Sogou status={r.status_code} q='{query}'")
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.select(".vrTitle a, h3 a"):
                href = a.get("href")
                if not href:
                    continue
                href = href.strip().strip("'\"`")
                # 规范化为绝对链接，避免 '/link?url=...' 导致 UnsupportedProtocol
                if href.startswith("//"):
                    href = "https:" + href
                elif not urlparse(href).scheme:
                    href = urljoin("https://www.sogou.com/", href)
                title = a.get_text(strip=True)
                links.append({"title": title, "url": href, "content": None, "engine": "sogou"})
                if len(links) >= max_results:
                    break
    except Exception:
        pass
    return links


def _so_html_search(query: str, max_results: int, headers):
    links = []
    try:
        url = "https://www.so.com/s"
        r = httpx.get(url, params={"q": query}, headers=headers, timeout=15)
        print(f"[Search] 360so status={r.status_code} q='{query}'")
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.select("h3 a, .res-list h3 a"):
                href = a.get("href")
                if not href:
                    continue
                href = href.strip().strip("'\"`")
                if href.startswith("//"):
                    href = "https:" + href
                elif not urlparse(href).scheme:
                    href = urljoin("https://www.so.com/", href)
                title = a.get_text(strip=True)
                links.append({"title": title, "url": href, "content": None, "engine": "360so"})
                if len(links) >= max_results:
                    break
    except Exception:
        pass
    return links


def web_search_cn_first(query: str, max_results: int = 20):
    """国内站点优先的搜索链路。
    - 普通查询：Baidu -> Sogou -> 360so -> Bing -> DuckDuckGo
    - 含 site: 的查询：优先 Bing（对站点过滤更稳定）-> Baidu -> Sogou -> 360so -> DuckDuckGo
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    if "site:" in query:
        # 站点过滤场景：先 Bing，再国内引擎
        res = _bing_html_search(query, max_results=max_results, headers=headers)
        if res:
            return res
        res = _baidu_html_search(query, max_results=max_results, headers=headers)
        if res:
            return res
        res = _sogou_html_search(query, max_results=max_results, headers=headers)
        if res:
            return res
        res = _so_html_search(query, max_results=max_results, headers=headers)
        if res:
            return res
        res = _ddg_html_search(query, max_results=max_results, headers=headers)
        return res
    else:
        # 普通查询：国内优先
        res = _baidu_html_search(query, max_results=max_results, headers=headers)
        if res:
            return res
        res = _sogou_html_search(query, max_results=max_results, headers=headers)
        if res:
            return res
        res = _so_html_search(query, max_results=max_results, headers=headers)
        if res:
            return res
        res = _bing_html_search(query, max_results=max_results, headers=headers)
        if res:
            return res
        res = _ddg_html_search(query, max_results=max_results, headers=headers)
        return res