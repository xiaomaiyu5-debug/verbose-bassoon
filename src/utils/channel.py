def classify(url: str) -> str:
    url = (url or "").lower()
    if "weibo.com" in url:
        return "微博"
    if "xiaohongshu.com" in url or "xhslink" in url:
        return "小红书"
    if "douyin.com" in url or "iesdouyin" in url:
        return "抖音"
    if "bilibili.com" in url:
        return "B站"
    if "zhihu.com" in url:
        return "知乎"
    if "toutiao.com" in url:
        return "头条"
    if "weixin.qq.com" in url or "mp.weixin.qq.com" in url:
        return "微信公众号"
    if "news" in url or "sina.com" in url or "sohu.com" in url or "qq.com" in url:
        return "新闻"
    return "其他"