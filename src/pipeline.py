import os
import time
from typing import Optional

from config import OUTPUT_DIR, ENABLE_KEYWORD_EXPANSION
from src.agents.query_agent import QueryAgent
from src.agents.insight_agent import InsightAgent
from src.agents.forum_engine import ForumEngine
from src.agents.report_agent import ReportAgent
from config import DEMO_MODE
from datetime import datetime, timedelta


def run_analysis_pipeline(brand: str, time_window_days: int = 30, timestamp: Optional[str] = None) -> bool:
    ts = timestamp or time.strftime("%Y%m%d-%H%M%S")
    logs = []

    # Agent 初始化
    query_agent = QueryAgent(brand=brand, time_window_days=time_window_days, expand_keywords=ENABLE_KEYWORD_EXPANSION)
    insight_agent = InsightAgent()
    forum_engine = ForumEngine()
    report_agent = ReportAgent(output_dir=OUTPUT_DIR)

    # 1) 检索与清洗
    logs.append(f"[QueryEngine] START brand={brand} window={time_window_days}d ts={ts}")
    docs = query_agent.run(logs)
    logs.append(f"[QueryEngine] DONE docs={len(docs)}")
    if not docs:
        if DEMO_MODE:
            logs.append("[ReportEngine] DEMO mode enabled -> use built-in sample data")
            # 生成演示数据
            demo_docs = [
                {"url": "https://weibo.com/sample1", "text": f"{brand} 续航不错，拍照提升明显，系统更流畅。", "language": "zh", "published": None},
                {"url": "https://www.zhihu.com/sample2", "text": f"用户反馈 {brand} 夜景成像好，但快充时有轻微发热。", "language": "zh", "published": None},
                {"url": "https://www.bilibili.com/sample3", "text": f"测评视频显示 {brand} 屏幕色彩观感讨喜，扬声器表现中规中矩。", "language": "zh", "published": None},
            ]
            # 趋势数据：最近14天的示例声量
            today = datetime.now()
            demo_trend = []
            base = 20
            for i in range(14):
                d = (today - timedelta(days=13-i)).strftime("%Y-%m-%d")
                demo_trend.append({"date": d, "count": base + (i%5)*3})
            demo_channels = {"微博": 36, "知乎": 22, "小红书": 18, "B站": 14}
            demo_clusters = [
                {"label": "拍照与影像", "size": 42, "samples": ["夜景表现好", "人像清晰", "视频防抖稳"]},
                {"label": "续航与充电", "size": 38, "samples": ["续航提升", "充电速度快", "快充发热控制需优化"]},
                {"label": "系统与体验", "size": 31, "samples": ["系统更流畅", "UI 更简洁", "应用兼容性良好"]},
            ]
            demo_insights = {
                "keywords": ["续航", "拍照", "发热", "系统", "屏幕"],
                "clusters": demo_clusters,
                "trend": demo_trend,
                "channels": demo_channels,
                "sentiment": {"pos": 62, "neg": 19, "neu": 19},
            }
            demo_synthesis = {
                "core_points": [
                    f"{brand} 在近两周内的讨论集中在影像与续航，整体口碑偏正面。",
                    "快充场景下的温度控制是用户反复提及的风险点。",
                    "围绕影像优势进行种草内容强化，可与续航卖点组合传达。",
                ],
                "risk": ["发热相关投诉", "个别机型电池寿命反馈"],
                "advice": ["优化快充热管理", "加强夜景样张传播", "围绕系统流畅度做对比评测"],
            }
            report_agent.generate_full(ts, brand, time_window_days, demo_docs, demo_insights, demo_synthesis, logs=logs)
            logs.append("[ReportEngine] DEMO report generated")
            return True
        else:
            # 生成一个空报告以提示用户，并显示过程日志
            report_agent.generate_minimal(
                ts,
                brand,
                time_window_days,
                message="未检索到有效数据，请稍后重试或更换关键词",
                logs=logs,
            )
            return True

    # 2) 分析：情感、关键词、聚类（轻量版）
    logs.append("[InsightEngine] START basic analysis")
    insights = insight_agent.analyze(docs)
    logs.append("[InsightEngine] DONE")

    # 3) 论坛整合（无Key时降级占位）
    logs.append("[ForumEngine] START synthesize")
    synthesis = forum_engine.summarize(brand, insights)
    logs.append("[ForumEngine] DONE")

    # 4) 报告生成（HTML/MD，并尝试PDF）
    logs.append("[ReportEngine] START render & export")
    report_agent.generate_full(ts, brand, time_window_days, docs, insights, synthesis, logs=logs)
    logs.append("[ReportEngine] DONE")
    return True