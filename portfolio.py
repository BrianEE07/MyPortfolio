# -*- coding: utf-8 -*-
"""
Usage:
  pip install -r requirements.txt
  python portfolio.py --serve
  python portfolio.py --output docs/index.html

Local preview: http://127.0.0.1:5000/
"""

from portfolio_app.web import app, main

__all__ = ["app", "main"]


if __name__ == "__main__":
    main()
