import argparse
import hashlib
import shutil
from pathlib import Path

from flask import Flask, render_template, url_for

from .config import CHART_JS_URL
from .snapshot import build_portfolio_snapshot


def _asset_version(asset_name: str) -> str:
    asset_path = Path(app.static_folder) / asset_name
    return hashlib.md5(asset_path.read_bytes()).hexdigest()[:10]


def _asset_url(asset_name: str, static_mode: bool = False) -> str:
    version = _asset_version(asset_name)
    if static_mode:
        return f"static/{asset_name}?v={version}"
    return url_for("static", filename=asset_name, v=version)


def _optional_asset_url(asset_name: str, static_mode: bool = False):
    asset_path = Path(app.static_folder) / asset_name
    if not asset_path.exists():
        return None
    return _asset_url(asset_name, static_mode=static_mode)


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            **build_portfolio_snapshot(),
            styles_url=_asset_url("styles.css"),
            app_js_url=_asset_url("app.js"),
            chart_js_url=CHART_JS_URL,
            favicon_ico_url=_optional_asset_url("favicon.ico"),
            favicon_32_url=_optional_asset_url("favicon-32.png"),
            favicon_16_url=_optional_asset_url("favicon-16.png"),
            favicon_url=_optional_asset_url("favicon.png"),
            apple_touch_icon_url=_optional_asset_url("apple-touch-icon.png"),
            manifest_url=_optional_asset_url("site.webmanifest"),
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()


def render_portfolio_html(static_mode=False):
    with app.app_context():
        return render_template(
            "index.html",
            **build_portfolio_snapshot(),
            styles_url=_asset_url("styles.css", static_mode=static_mode),
            app_js_url=_asset_url("app.js", static_mode=static_mode),
            chart_js_url=CHART_JS_URL,
            favicon_ico_url=_optional_asset_url("favicon.ico", static_mode=static_mode),
            favicon_32_url=_optional_asset_url("favicon-32.png", static_mode=static_mode),
            favicon_16_url=_optional_asset_url("favicon-16.png", static_mode=static_mode),
            favicon_url=_optional_asset_url("favicon.png", static_mode=static_mode),
            apple_touch_icon_url=_optional_asset_url("apple-touch-icon.png", static_mode=static_mode),
            manifest_url=_optional_asset_url("site.webmanifest", static_mode=static_mode),
        )


def _copy_static_assets(destination_directory: Path):
    static_directory = Path(app.static_folder)
    output_static_directory = destination_directory / "static"
    output_static_directory.mkdir(parents=True, exist_ok=True)
    asset_names = [
        "styles.css",
        "app.js",
        "favicon.ico",
        "favicon.png",
        "favicon-192.png",
        "favicon-64.png",
        "favicon-32.png",
        "favicon-16.png",
        "apple-touch-icon.png",
        "site.webmanifest",
    ]
    for asset_name in asset_names:
        asset_path = static_directory / asset_name
        if asset_path.exists():
            shutil.copy2(asset_path, output_static_directory / asset_name)


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
