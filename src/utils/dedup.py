from typing import List, Callable
from simhash import Simhash


def near_dedup(items: List[dict], key: Callable[[dict], str], threshold: int = 8) -> List[dict]:
    """简单近重复去重：基于Simhash的汉明距离阈值。"""
    kept = []
    fingerprints = []
    for it in items:
        text = key(it) or ""
        fp = Simhash(text)
        is_dup = False
        for prev_fp in fingerprints:
            dist = fp.distance(prev_fp)
            if dist <= threshold:
                is_dup = True
                break
        if not is_dup:
            kept.append(it)
            fingerprints.append(fp)
    return kept