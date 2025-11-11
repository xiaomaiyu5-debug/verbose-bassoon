import os
import time
import threading
import json
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, jsonify

from config import DEFAULT_BRAND, DEFAULT_TIME_WINDOW_DAYS, OUTPUT_DIR
from src.pipeline import run_analysis_pipeline

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "dev-secret")
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html", default_brand=DEFAULT_BRAND, default_window=DEFAULT_TIME_WINDOW_DAYS)


@app.route("/analyze", methods=["POST"])
def analyze():
    brand = request.form.get("brand", DEFAULT_BRAND).strip()
    try:
        window_days = int(request.form.get("window_days", DEFAULT_TIME_WINDOW_DAYS))
    except Exception:
        window_days = DEFAULT_TIME_WINDOW_DAYS

    # 异步任务：立即返回处理中页面，后台生成报告
    ts = time.strftime("%Y%m%d-%H%M%S")

    # 预写入状态文件，供任务页展示基本信息
    status_path = os.path.join(OUTPUT_DIR, f"status_{ts}.json")
    try:
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump({"ts": ts, "brand": brand, "window_days": window_days, "done": False}, f, ensure_ascii=False)
    except Exception:
        pass

    def _bg_task():
        try:
            run_analysis_pipeline(brand=brand, time_window_days=window_days, timestamp=ts)
        finally:
            # 标记完成（报告生成由 pipeline 负责），这里仅更新状态
            try:
                with open(status_path, "w", encoding="utf-8") as f:
                    json.dump({"ts": ts, "brand": brand, "window_days": window_days, "done": True}, f, ensure_ascii=False)
            except Exception:
                pass

    threading.Thread(target=_bg_task, daemon=True).start()
    return redirect(url_for("task", ts=ts))


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if not f:
        flash("请选择要上传的文件")
        return redirect(url_for("index"))
    name = f.filename or "input.dat"
    save_path = os.path.join(UPLOAD_DIR, name)
    try:
        f.save(save_path)
        flash("上传成功（暂未参与分析，后续版本将支持数据融合）")
    except Exception:
        flash("上传失败，请重试")
    return redirect(url_for("index"))


@app.route("/report/<ts>")
def report(ts):
    html_path = os.path.join(OUTPUT_DIR, f"report_{ts}.html")
    md_path = os.path.join(OUTPUT_DIR, f"report_{ts}.md")
    pdf_path = os.path.join(OUTPUT_DIR, f"report_{ts}.pdf")
    if not os.path.exists(html_path):
        flash("报告不存在或尚未生成")
        return redirect(url_for("index"))
    # 直接返回静态报告文件，避免将完整 HTML 嵌入到 base 模板导致样式或脚本失效
    return send_file(html_path)


@app.route("/download/<ts>/<fmt>")
def download(ts, fmt):
    path = os.path.join(OUTPUT_DIR, f"report_{ts}.{fmt}")
    if not os.path.exists(path):
        flash("文件不存在")
        return redirect(url_for("report", ts=ts))
    return send_file(path, as_attachment=True)


@app.route("/task/<ts>")
def task(ts):
    # 加载初始状态，展示“处理中”页面
    status_path = os.path.join(OUTPUT_DIR, f"status_{ts}.json")
    brand = DEFAULT_BRAND
    window_days = DEFAULT_TIME_WINDOW_DAYS
    if os.path.exists(status_path):
        try:
            with open(status_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                brand = data.get("brand", brand)
                window_days = data.get("window_days", window_days)
        except Exception:
            pass
    return render_template("task.html", ts=ts, brand=brand, window_days=window_days)

@app.route("/status/<ts>")
def status(ts):
    # 完成判断：报告文件是否存在 或 状态文件标记完成
    html_path = os.path.join(OUTPUT_DIR, f"report_{ts}.html")
    status_path = os.path.join(OUTPUT_DIR, f"status_{ts}.json")
    done = os.path.exists(html_path)
    info = {"ts": ts, "done": done}
    if os.path.exists(status_path):
        try:
            with open(status_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                info.update({"brand": data.get("brand"), "window_days": data.get("window_days")})
        except Exception:
            pass
    return jsonify(info)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)