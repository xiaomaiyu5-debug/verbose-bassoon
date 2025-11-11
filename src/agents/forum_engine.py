class ForumEngine:
    def summarize(self, brand: str, insights: dict) -> dict:
        """整合结论：优先使用 LLM（Ark），否则回退到规则化总结。"""
        clusters = insights.get("clusters", [])
        sentiment = insights.get("sentiment", {"pos": 0, "neg": 0, "neu": 0})

        # 优先尝试 LLM
        try:
            from config import LLM_PROVIDER, LLM_API_KEY
            if LLM_PROVIDER == "ark" and LLM_API_KEY:
                from src.services.llm_ark import chat
                import json
                # 构造精简上下文，避免超长
                brief_clusters = [
                    {"label": c.get("label"), "size": c.get("size"), "samples": c.get("samples", [])[:2]}
                    for c in clusters[:6]
                ]
                sys_prompt = (
                    "你是品牌舆情分析专家。请根据提供的关键词、聚类与情感数据，"
                    "生成结构化的总结，严格输出 JSON：{\n"
                    "  \"core_points\": [string...],\n"
                    "  \"risk\": [string...],\n"
                    "  \"advice\": [string...]\n"
                    "}。语言使用简体中文，句子简洁。")
                user_content = json.dumps({
                    "brand": brand,
                    "keywords": insights.get("keywords", [])[:12],
                    "clusters": brief_clusters,
                    "sentiment": sentiment,
                }, ensure_ascii=False)
                out = chat([
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_content},
                ])
                if out:
                    try:
                        data = json.loads(out)
                        return {
                            "brand": brand,
                            "core_points": data.get("core_points", []),
                            "sentiment": sentiment,
                            "risk": data.get("risk", []),
                            "advice": data.get("advice", []),
                        }
                    except Exception:
                        # 若非JSON，按行切分提取
                        lines = [x.strip("- • ") for x in out.splitlines() if x.strip()]
                        cp = lines[:5]
                        return {
                            "brand": brand,
                            "core_points": cp,
                            "sentiment": sentiment,
                            "risk": ["关注负面高频议题，及时响应用户投诉"],
                            "advice": ["围绕正面主题加强内容运营与口碑传播"],
                        }
        except Exception:
            pass

        # 回退：规则化总结
        core_points = []
        for c in clusters[:5]:
            core_points.append(f"主题{c.get('label')}（样本{c.get('size')}）：样例——" + " | ".join(c.get("samples", [])))
        return {
            "brand": brand,
            "core_points": core_points,
            "sentiment": sentiment,
            "risk": [
                "关注负面高频议题，及时响应用户投诉",
                "对话题热度提升的主题进行重点监控",
            ],
            "advice": [
                "提升客服响应速度与问题闭环",
                "围绕正面主题加强内容运营与口碑传播",
            ],
        }