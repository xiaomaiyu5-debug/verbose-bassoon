from collections import Counter
import re


class InsightAgent:
    def __init__(self, n_clusters: int = 5):
        self.n_clusters = n_clusters

    def analyze(self, docs):
        texts = [d["text"] for d in docs]
        if not texts:
            return {
                "clusters": [],
                "keywords": [],
                "sentiment": {"pos": 0, "neg": 0, "neu": 0},
                "trend": [],
                "channels": {},
            }

        # 关键词（粗略）：基于简单分词规则统计高频词
        tokens_list = []
        word_counter = Counter()
        for t in texts:
            tokens = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", t)
            tokens_list.append(tokens)
            for w in tokens:
                if len(w) >= 2:
                    word_counter[w] += 1
        keywords = [w for w, _ in word_counter.most_common(20)]

        # 简易聚类：按关键词命中进行粗分组
        key_set = set(keywords[:min(10, len(keywords))])
        clusters_map = {}
        for idx, tokens in enumerate(tokens_list):
            hit = key_set.intersection(tokens)
            label = next(iter(hit), None)
            if label is None:
                label = "其它"
            clusters_map.setdefault(label, []).append(idx)
        clusters = []
        for c_label, idxs in clusters_map.items():
            clusters.append({
                "label": c_label,
                "size": len(idxs),
                "samples": [docs[i]["text"][:300] for i in idxs[:3]],
            })

        # 情感（占位）：简单按词典规则估计（LLM Key提供后可替换）
        pos_words = {"好", "优秀", "点赞", "满意", "推荐", "不错", "很棒"}
        neg_words = {"差", "糟糕", "投诉", "失望", "不行", "问题", "吐槽", "差评"}
        pos = sum(any(p in t for p in pos_words) for t in texts)
        neg = sum(any(n in t for n in neg_words) for t in texts)
        neu = max(len(texts) - pos - neg, 0)

        # 趋势：按发布日期做日粒度统计
        from collections import defaultdict
        from datetime import datetime
        daily = defaultdict(int)
        for d in docs:
            dt = d.get("published")
            if not dt:
                continue
            try:
                date_str = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)[:10]
            except Exception:
                date_str = str(dt)[:10]
            if date_str:
                daily[date_str] += 1
        trend = [{"date": k, "count": v} for k, v in sorted(daily.items())]

        # 渠道分布：按 URL 识别来源平台
        from collections import defaultdict as dd
        try:
            from src.utils.channel import classify
        except Exception:
            def classify(_):
                return "其他"
        ch_counter = dd(int)
        for d in docs:
            ch = classify(d.get("url", ""))
            ch_counter[ch] += 1

        return {
            "clusters": clusters,
            "keywords": keywords,
            "sentiment": {"pos": pos, "neg": neg, "neu": neu},
            "trend": trend,
            "channels": dict(ch_counter),
        }