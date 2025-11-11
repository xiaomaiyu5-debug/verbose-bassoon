import os
from jinja2 import Environment, FileSystemLoader
import pdfkit

class ReportAgent:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.env = Environment(loader=FileSystemLoader("templates"), autoescape=True)

    def generate_minimal(self, ts: str, brand: str, window_days: int, message: str, logs=None):
        tmpl = self.env.get_template("report_template.html")
        html = tmpl.render(
            ts=ts,
            brand=brand,
            window_days=window_days,
            docs=[],
            insights={},
            synthesis={"core_points": [message]},
            logs=logs or [],
        )
        self._write_outputs(ts, html, md_content=f"# {brand} 舆情报告\n\n{message}\n")

    def generate_full(self, ts: str, brand: str, window_days: int, docs, insights, synthesis, logs=None):
        tmpl = self.env.get_template("report_template.html")
        html = tmpl.render(
            ts=ts,
            brand=brand,
            window_days=window_days,
            docs=docs,
            insights=insights,
            synthesis=synthesis,
            logs=logs or [],
        )
        # 生成MD（简单版）
        md_lines = [
            f"# {brand} 近{window_days}天舆情分析报告",
            "",
            "## 核心洞察",
        ]
        for p in synthesis.get("core_points", []):
            md_lines.append(f"- {p}")
        md_lines.extend([
            "",
            "## 情感分布",
            f"- 正面: {insights.get('sentiment', {}).get('pos', 0)}",
            f"- 负面: {insights.get('sentiment', {}).get('neg', 0)}",
            f"- 中性: {insights.get('sentiment', {}).get('neu', 0)}",
            "",
            "## 关键词",
            ", ".join(insights.get("keywords", [])),
        ])
        md_content = "\n".join(md_lines)
        self._write_outputs(ts, html, md_content)

    def _write_outputs(self, ts: str, html: str, md_content: str):
        html_path = os.path.join(self.output_dir, f"report_{ts}.html")
        md_path = os.path.join(self.output_dir, f"report_{ts}.md")
        pdf_path = os.path.join(self.output_dir, f"report_{ts}.pdf")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        # 生成PDF（wkhtmltopdf优先，失败则跳过）
        try:
            pdfkit.from_file(html_path, pdf_path)
        except Exception:
            # 若未安装wkhtmltopdf，先跳过，后续可用reportlab兜底
            pass