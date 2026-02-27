"""Минимальный FastAPI — показывает данные аутентификации от Nginx."""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI(title="SPNEGO Demo Minimal")


def render_page(rows: list[tuple[str, str]], title: str = "SPNEGO Demo Minimal") -> str:
    table_rows = "\n".join(
        f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows
    )
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         max-width: 700px; margin: 36px auto; padding: 0 16px; color: #222;
         font-size: 14px; line-height: 1.35; }}
  h1 {{ border-bottom: 2px solid #0078d4; padding-bottom: 8px; margin: 0; font-size: 24px; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
  th, td {{ border: 1px solid #ccc; padding: 7px 10px; text-align: left; font-size: 13px; }}
  th {{ background: #f0f0f0; width: 200px; white-space: nowrap; }}
  td {{ word-break: break-all; }}
</style>
</head>
<body>
  <h1>{title}</h1>
  <p style="color:green;font-weight:bold">Аутентификация успешна!</p>
  <table>{table_rows}</table>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    headers = dict(request.headers)
    remote_user = headers.get("x-remote-user", headers.get("X-Remote-User", "—"))

    rows = [
        ("X-Remote-User", remote_user),
        ("", ""),
    ]

    for name, value in sorted(headers.items()):
        if name.lower() not in ("x-remote-user",):
            rows.append((name, value))

    return HTMLResponse(content=render_page(rows))
