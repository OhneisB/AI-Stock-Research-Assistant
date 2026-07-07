"""Optionales lokales Web-UI (Flask).

Start:  python -m stock_research.webapp   (benoetigt: pip install .[web])
Dann im Browser: http://127.0.0.1:5000
"""

from __future__ import annotations

import html

from .analysis.pipeline import make_analyst, run_pipeline
from .config import get_settings
from .data.collect import collect
from .report import render_markdown

PAGE = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>AI Stock Research Assistant</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
  form {{ display: flex; gap: .5rem; margin-bottom: 1.5rem; }}
  input[type=text] {{ flex: 1; padding: .5rem; font-size: 1rem; }}
  button {{ padding: .5rem 1.25rem; font-size: 1rem; cursor: pointer; }}
  pre {{ white-space: pre-wrap; background: #f6f6f6; padding: 1rem; border-radius: 8px; }}
  .error {{ color: #b00020; }}
  .hint {{ color: #666; font-size: .9rem; }}
</style>
</head>
<body>
<h1>AI Stock Research Assistant</h1>
<p class="hint">Keine Anlageberatung &ndash; jeder Report enthaelt einen Disclaimer.</p>
<form method="post">
  <input type="text" name="ticker" placeholder="Ticker, z. B. AAPL" value="{ticker}" required>
  <label><input type="checkbox" name="deep" {deep_checked}> deep</label>
  <label><input type="checkbox" name="offline" {offline_checked}> offline</label>
  <button type="submit">Analysieren</button>
</form>
{body}
</body>
</html>"""


def create_app():
    from flask import Flask, request  # lazy import (optionales Extra)

    app = Flask(__name__)

    @app.route("/", methods=["GET", "POST"])
    def index():
        ticker, body, deep, offline = "", "", False, False
        if request.method == "POST":
            ticker = (request.form.get("ticker") or "").strip().upper()
            deep = bool(request.form.get("deep"))
            offline = bool(request.form.get("offline"))
            settings = get_settings()
            try:
                bundle = collect(ticker, settings, offline=offline)
                analyst = make_analyst(settings, bundle, force_template=offline)
                result = run_pipeline(bundle, analyst, deep=deep)
                body = f"<pre>{html.escape(render_markdown(bundle, result))}</pre>"
            except Exception as exc:
                body = f'<p class="error">Fehler: {html.escape(str(exc))}</p>'
        return PAGE.format(
            ticker=html.escape(ticker),
            deep_checked="checked" if deep else "",
            offline_checked="checked" if offline else "",
            body=body,
        )

    return app


def main() -> None:
    create_app().run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
