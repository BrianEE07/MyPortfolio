import argparse
import shutil
from pathlib import Path

from flask import Flask, render_template, url_for

from .config import CHART_JS_URL
from .snapshot import build_portfolio_snapshot


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            **build_portfolio_snapshot(),
            styles_url=url_for("static", filename="styles.css"),
            app_js_url=url_for("static", filename="app.js"),
            chart_js_url=CHART_JS_URL,
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()


def render_portfolio_html(static_mode=False):
    with app.app_context():
        styles_url = "static/styles.css" if static_mode else url_for("static", filename="styles.css")
        app_js_url = "static/app.js" if static_mode else url_for("static", filename="app.js")
        return render_template(
            "index.html",
            **build_portfolio_snapshot(),
            styles_url=styles_url,
            app_js_url=app_js_url,
            chart_js_url=CHART_JS_URL,
        )


def _copy_static_assets(destination_directory: Path):
    static_directory = Path(app.static_folder)
    output_static_directory = destination_directory / "static"
    output_static_directory.mkdir(parents=True, exist_ok=True)
    for asset_name in ("styles.css", "app.js"):
        shutil.copy2(static_directory / asset_name, output_static_directory / asset_name)


def write_static_output(output_path: Path):
    html = render_portfolio_html(static_mode=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    _copy_static_assets(output_path.parent)
    print(f"Wrote portfolio page to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Portfolio server / static site generator")
    parser.add_argument("--output", help="Write a static HTML snapshot to this path")
    parser.add_argument("--serve", action="store_true", help="Run the Flask server")
    args = parser.parse_args()

    if args.output:
        write_static_output(Path(args.output))
        if not args.serve:
            return

    if args.serve or not args.output:
        import os

        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port, debug=True, use_reloader=True, reloader_type="stat")
