import httpx
from bs4 import BeautifulSoup
from langdetect import detect
from datetime import datetime, timedelta
import dateparser
import hashlib
import re
import time

from config import SEARXNG_INSTANCES, PREFER_CN_SITES, CN_SITES, TIME_BUDGET_SECONDS, MAX_FETCHES_PER_ANALYSIS
from src.services.search_searx import web_search_combined, web_search_cn_first
from src.services.fetchers import zhihu_fetch
from src.utils.text import normalize_text, translate_to_zh
from src.utils.dedup import near_dedup


class QueryAgent:
    def __init__(self, brand: str, time_window_days: int = 30, expand_keywords: bool = True, max_results: int = 60):
        # 简单规范化品牌/型号，并同时保留原始写法以避免召回损失
        import re
        self.raw_brand = brand
        norm = re.sub(r"([A-Za-z]+)(\d+)", r"\1 \2", brand)
        self.brand = norm
        self.time_window_days = time_window_days
        # 若用户直接输入了 site: 定向查询，则不做扩展，仅按该查询执行，避免卡住
        if "site:" in brand:
            self.expand_keywords = False
            # 对定向查询降低最大抓取数
            self.max_results = min(30, max_results)
        else:
            self.expand_keywords = expand_keywords
            self.max_results = max_results
        self.prefer_cn_sites = PREFER_CN_SITES

    def _build_queries(self):
        terms = [self.brand, self.raw_brand]
        # 同义写法：大小写与空格变体
        variants = set()
        variants.add(self.brand.replace(" ", ""))
        variants.add(self.brand.title())
        variants.add(self.raw_brand.upper())
        terms.extend(list(variants))
        if self.expand_keywords:
            # 非侵入的简单扩展：品牌 + 舆情/口碑/投诉/测评/评测（两种写法都覆盖）
            ext = [
                f"{self.brand} 舆情",
                f"{self.brand} 口碑",
                f"{self.brand} 投诉",
                f"{self.brand} 测评",
                f"{self.brand} 评测",
            ]
            # 国内平台定向：知乎/B站偏评测；微博/贴吧偏口碑与投诉
            site_ext = [
                f"{self.brand} 评测 site:zhihu.com",
                f"{self.brand} 评测 site:bilibili.com",
                f"{self.brand} 口碑 site:weibo.com",
                f"{self.brand} 投诉 site:tieba.baidu.com",
                f"{self.brand} 口碑 site:xiaohongshu.com",
            ]
            terms.extend(ext + site_ext)
        return terms

    def _fetch_and_extract(self, url: str, logs=None):
        try:
            # 基础清洗：去除包裹字符与反引号
            orig_url = url
            url = url.strip().strip("'\"`")
            # 针对搜狗相对链接 '/link?url=' 的补全
            if url.startswith("/link?") and not url.startswith("http"):
                url = "https://www.sogou.com" + url
            # 若链接中已指向知乎，直接用知乎定制抓取
            if "zhihu.com" in url:
                doc = zhihu_fetch(url)
                if not doc:
                    msg = f"[QueryEngine] FETCH_FAIL zhihu {url}"
                    print(msg)
                    if isinstance(logs, list):
                        logs.append(msg)
                    return None
                msg = f"[QueryEngine] FETCH_OK zhihu {url} len={len(doc.get('text',''))}"
                print(msg)
                if isinstance(logs, list):
                    logs.append(msg)
                return doc
            # 其他搜索引擎跳转链接（sogou/360 等），先请求再判断最终落地域名
            r = httpx.get(
                url,
                timeout=8,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                },
            )
            # 如果最终跳转到知乎，则改用知乎定制抓取
            try:
                final_url = str(r.url)
            except Exception:
                final_url = url
            if "zhihu.com" in final_url:
                doc = zhihu_fetch(final_url)
                if not doc:
                    msg = f"[QueryEngine] FETCH_FAIL zhihu {final_url}"
                    print(msg)
                    if isinstance(logs, list):
                        logs.append(msg)
                    return None
                msg = f"[QueryEngine] FETCH_OK zhihu {final_url} len={len(doc.get('text',''))}"
                print(msg)
                if isinstance(logs, list):
                    logs.append(msg)
                return doc

            if r.status_code != 200:
                msg = f"[QueryEngine] FETCH_FAIL {url} status={r.status_code}"
                print(msg)
                if isinstance(logs, list):
                    logs.append(msg)
                return None
            html = r.text
            soup = BeautifulSoup(html, "html.parser")

            # 处理 meta refresh 跳转（常见于搜狗/360的中转页）
            meta_refresh = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
            if meta_refresh and meta_refresh.get("content"):
                cnt = meta_refresh["content"]
                # 形如: "0; URL='https://www.zhihu.com/...'"
                m = re.search(r"url\s*=?\s*([^;]+)", cnt, flags=re.I)
                tgt = None
                if m:
                    tgt = m.group(1).strip().strip("'\"`")
                    if tgt:
                        if "zhihu.com" in tgt:
                            doc = zhihu_fetch(tgt)
                            if not doc:
                                msg = f"[QueryEngine] FETCH_FAIL zhihu {tgt}"
                                print(msg)
                                if isinstance(logs, list):
                                    logs.append(msg)
                                return None
                            msg = f"[QueryEngine] FETCH_OK zhihu {tgt} len={len(doc.get('text',''))}"
                            print(msg)
                            if isinstance(logs, list):
                                logs.append(msg)
                            return doc
                        # 非知乎的 refresh，直接跟进抓取一次
                        rr = httpx.get(tgt, timeout=8, follow_redirects=True, headers={
                            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36",
                            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                        })
                        if rr.status_code == 200:
                            soup = BeautifulSoup(rr.text, "html.parser")
                        else:
                            msg = f"[QueryEngine] FETCH_FAIL {tgt} status={rr.status_code}"
                            print(msg)
                            if isinstance(logs, list):
                                logs.append(msg)
                            return None
            # 去除脚本/样式
            for tag in soup(["script", "style", "noscript"]):
                tag.extract()
            text = soup.get_text("\n")
            text = normalize_text(text)
            # 尝试语言检测与翻译
            try:
                lang = detect(text)
            except Exception:
                lang = "unknown"
            if lang != "zh-cn" and lang != "zh" and lang != "unknown":
                text = translate_to_zh(text)
            # 尝试从页面中解析日期（弱匹配）
            published = dateparser.search.search_dates(text)
            doc = {
                "url": url,
                "text": text,
                "language": lang,
                "published": published[0][1] if published else None,
            }
            msg = f"[QueryEngine] FETCH_OK {doc['url']} len={len(doc['text'])}"
            print(msg)
            if isinstance(logs, list):
                logs.append(msg)
            return doc
        except Exception as e:
            msg = f"[QueryEngine] FETCH_FAIL {orig_url} error={type(e).__name__}"
            print(msg)
            if isinstance(logs, list):
                logs.append(msg)
            return None

    def _within_time_window(self, dt):
        if not dt:
            return True  # 无法解析时间则保留，后续再做细化
        cutoff = datetime.now() - timedelta(days=self.time_window_days)
        return dt >= cutoff

    def run(self, logs=None):
        queries = self._build_queries()
        results = []
        start_ts = time.time()
        total_fetches = 0
        # 统一调用组合检索：SearXNG -> DuckDuckGo -> Bing -> Baidu
        for q in queries:
            # 时间预算：超时直接停止后续检索
            if time.time() - start_ts > TIME_BUDGET_SECONDS:
                msg = f"[QueryEngine] TIME_BUDGET_REACHED after {int(time.time()-start_ts)}s fetches={total_fetches}"
                print(msg)
                if isinstance(logs, list):
                    logs.append(msg)
                break
            per_q = max(10, self.max_results // max(1, len(queries)))
            # 减小每个查询的抓取上限，避免阻塞
            per_q = min(per_q, 6)
            if self.prefer_cn_sites or ("site:" in q):
                hits = web_search_cn_first(q, max_results=per_q)
            else:
                hits = web_search_combined(q, instances=SEARXNG_INSTANCES, max_results=per_q)
            try:
                engine = hits[0].get("engine") if hits else None
            except Exception:
                engine = None
            msg = f"[QueryEngine] SEARCH q='{q}' engine={engine or 'none'} hits={len(hits)}"
            print(msg)
            if isinstance(logs, list):
                logs.append(msg)
            for h in hits:
                if time.time() - start_ts > TIME_BUDGET_SECONDS:
                    msg = f"[QueryEngine] TIME_BUDGET_REACHED during fetch after {int(time.time()-start_ts)}s fetches={total_fetches}"
                    print(msg)
                    if isinstance(logs, list):
                        logs.append(msg)
                    break
                url = h.get("url")
                if not url:
                    continue
                doc = self._fetch_and_extract(url, logs)
                total_fetches += 1
                if total_fetches >= MAX_FETCHES_PER_ANALYSIS:
                    msg = f"[QueryEngine] FETCH_LIMIT_REACHED limit={MAX_FETCHES_PER_ANALYSIS}"
                    print(msg)
                    if isinstance(logs, list):
                        logs.append(msg)
                    break
                if not doc:
                    continue
                if not self._within_time_window(doc.get("published")):
                    continue
                results.append(doc)

        # 去重（跨平台）：按文本近重复
        deduped = near_dedup(results, key=lambda d: d["text"])
        return deduped