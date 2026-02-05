"""
汎用スクレイピング Web UI
URL またはキーワードから複数サイトを取得し、Excel / CSV / Text / JSON でダウンロード
"""

import io
from flask import Flask, render_template, request, send_file, flash, redirect, url_for

from scraper.job import run_job, MAX_URLS
from scraper.export import export_excel, export_csv, export_text, export_json
from scraper import ScraperError


app = Flask(__name__)
app.secret_key = "scraping-ui-secret-change-in-production"


OUTPUT_OPTIONS = [
    ("excel", "Excel (.xlsx)"),
    ("csv", "CSV (.csv)"),
    ("text", "テキスト (.txt)"),
    ("json", "JSON (.json)"),
]


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template(
            "index.html",
            output_options=OUTPUT_OPTIONS,
            max_urls=MAX_URLS,
        )

    mode = request.form.get("mode", "url").strip()
    output_format = request.form.get("output_format", "excel").strip()
    delay = float(request.form.get("delay", "1.5"))
    check_robots = request.form.get("check_robots") == "on"

    urls = None
    keyword = None
    if mode == "url":
        raw = request.form.get("urls", "")
        urls = [u.strip() for u in raw.splitlines() if u.strip()]
    else:
        keyword = request.form.get("keyword", "").strip()
        max_results = min(int(request.form.get("max_results", "10") or "10"), MAX_URLS)

    try:
        if mode == "keyword":
            items = run_job(
                keyword=keyword,
                max_results=max_results,
                delay_seconds=delay,
                check_robots=check_robots,
            )
        else:
            items = run_job(
                urls=urls,
                delay_seconds=delay,
                check_robots=check_robots,
            )
    except ScraperError as e:
        flash(str(e), "error")
        return redirect(url_for("index"))

    if not items:
        flash("取得できたデータがありません。", "error")
        return redirect(url_for("index"))

    # エクスポート
    filename_base = "scrape_result"
    if output_format == "excel":
        buf = io.BytesIO(export_excel(items))
        return send_file(
            buf,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"{filename_base}.xlsx",
        )
    if output_format == "csv":
        buf = io.BytesIO(export_csv(items).encode("utf-8-sig"))
        buf.seek(0)
        return send_file(
            buf,
            mimetype="text/csv; charset=utf-8",
            as_attachment=True,
            download_name=f"{filename_base}.csv",
        )
    if output_format == "text":
        buf = io.BytesIO(export_text(items).encode("utf-8"))
        buf.seek(0)
        return send_file(
            buf,
            mimetype="text/plain; charset=utf-8",
            as_attachment=True,
            download_name=f"{filename_base}.txt",
        )
    if output_format == "json":
        buf = io.BytesIO(export_json(items).encode("utf-8"))
        buf.seek(0)
        return send_file(
            buf,
            mimetype="application/json; charset=utf-8",
            as_attachment=True,
            download_name=f"{filename_base}.json",
        )

    flash("不明な出力形式です。", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
