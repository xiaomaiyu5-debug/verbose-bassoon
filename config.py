import os

# 默认主题与时间窗
DEFAULT_BRAND = os.environ.get("DEFAULT_BRAND", "vivo")
DEFAULT_TIME_WINDOW_DAYS = int(os.environ.get("TIME_WINDOW_DAYS", 60))

# 输出目录
OUTPUT_DIR = os.path.join(os.getcwd(), "reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 是否启用关键词扩展/保存缓存
ENABLE_KEYWORD_EXPANSION = True
ENABLE_CACHE_SAVE = True

# SearXNG公共实例（按顺序尝试，若失败自动切换）
SEARXNG_INSTANCES = [
    "https://searx.tiekoetter.com/search",
    "https://searxng.site/search",
    "https://searx.juancarra.cc/search",
]

# 国内站点优先策略与站点列表
PREFER_CN_SITES = True
CN_SITES = [
    "zhihu.com",
    "bilibili.com",
    "weibo.com",
    "tieba.baidu.com",
    "xiaohongshu.com",
]

# LLM配置（已对接火山引擎 Ark Chat Completions）
# 你也可以通过环境变量覆盖这些配置
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ark")  # ark/openai/qwen/kimi/ollama
LLM_API_KEY = os.environ.get("LLM_API_KEY", "b6edbf47-382a-497b-8743-3b837de6ff80")
ARK_API_URL = os.environ.get("ARK_API_URL", "https://ark.cn-beijing.volces.com/api/v3/chat/completions")
ARK_MODEL_ID = os.environ.get("ARK_MODEL_ID", "ep-20251030163647-nln45")

# PDF生成配置
PDF_GENERATOR = os.environ.get("PDF_GENERATOR", "wkhtmltopdf")  # wkhtmltopdf or reportlab

# 演示模式：当外部检索为空时，用内置示例数据生成可视化报告
# 默认开启，若需关闭可设置环境变量 DEMO_MODE=false
DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() in ("1", "true", "yes")

# 运行时预算（避免前端长时间卡住）
# 总时长预算（秒），到达后会提前结束检索并进入 DEMO 或已有结果渲染
TIME_BUDGET_SECONDS = int(os.environ.get("TIME_BUDGET_SECONDS", 25))
# 单次分析最大抓取文档数（包含失败尝试），防止过多请求导致阻塞
MAX_FETCHES_PER_ANALYSIS = int(os.environ.get("MAX_FETCHES_PER_ANALYSIS", 50))