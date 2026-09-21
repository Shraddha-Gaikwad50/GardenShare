"""Browser HTML pages for GardenShare list endpoints.

JSON clients (curl, tests, OpenAPI) still receive JSON. Web browsers that
send Accept: text/html receive a formatted page instead of raw JSON.
"""

from __future__ import annotations

import html
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse

NAV_LINKS = [
    ("/", "Home"),
    ("/docs", "API docs"),
    ("/members", "Members"),
    ("/seeds", "Seeds"),
    ("/borrow-requests", "Borrow requests"),
    ("/gardens/plots", "Garden plots"),
]


def prefers_html(request: Request) -> bool:
    """True when the client is a browser asking for HTML first."""

    accept = request.headers.get("accept", "")
    html_at = accept.find("text/html")
    if html_at < 0:
        return False
    json_at = accept.find("application/json")
    if json_at < 0:
        return True
    return html_at < json_at


def html_or_json(
    request: Request,
    payload: Any,
    *,
    title: str,
    subtitle: str,
    columns: list[tuple[str, str]],
    rows: list[dict[str, Any]],
) -> HTMLResponse | JSONResponse:
    """Return a table page for browsers, JSON for everyone else."""

    if prefers_html(request):
        return HTMLResponse(render_table_page(title, subtitle, columns, rows))
    return JSONResponse(content=payload)


def render_status_page(title: str, subtitle: str, fields: list[tuple[str, Any]]) -> str:
    """Simple key/value card used by the health page."""

    rows_html = "".join(
        f"<tr><th>{html.escape(str(label))}</th><td>{html.escape(_format_cell(value))}</td></tr>"
        for label, value in fields
    )
    body = f"""
    <p class="lead">{html.escape(subtitle)}</p>
    <table class="kv"><tbody>{rows_html}</tbody></table>
    """
    return page_shell(title, body)


def render_table_page(
    title: str,
    subtitle: str,
    columns: list[tuple[str, str]],
    rows: list[dict[str, Any]],
) -> str:
    headers = "".join(f"<th>{html.escape(label)}</th>" for _key, label in columns)
    if not rows:
        body_rows = f'<tr><td colspan="{len(columns)}" class="empty">No records yet.</td></tr>'
    else:
        body_rows = ""
        for row in rows:
            cells = "".join(
                f"<td>{html.escape(_format_cell(row.get(key)))}</td>" for key, _label in columns
            )
            body_rows += f"<tr>{cells}</tr>"
    body = f"""
    <p class="lead">{html.escape(subtitle)}</p>
    <p class="count">{len(rows)} record{"s" if len(rows) != 1 else ""}</p>
    <div class="table-wrap">
      <table>
        <thead><tr>{headers}</tr></thead>
        <tbody>{body_rows}</tbody>
      </table>
    </div>
    """
    return page_shell(title, body)


def page_shell(title: str, body: str) -> str:
    nav = "".join(
        f'<a href="{html.escape(href)}">{html.escape(label)}</a>' for href, label in NAV_LINKS
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} · GardenShare</title>
  <style>
    :root {{
      --ink: #1b4332;
      --muted: #52796f;
      --paper: #f7faf4;
      --card: #ffffff;
      --line: #d8e3d3;
      --accent: #2d6a4f;
      --head: #1b4332;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: radial-gradient(circle at top left, #e9f5db 0%, var(--paper) 55%);
      color: var(--ink);
    }}
    header {{
      background: var(--head);
      color: #f1faee;
      padding: 1.25rem 1.5rem 0;
    }}
    header h1 {{ margin: 0 0 0.35rem; font-size: 1.6rem; font-weight: normal; }}
    header p {{ margin: 0 0 1rem; color: #b7e4c7; font-size: 0.95rem; }}
    nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem 1rem;
      padding-bottom: 0.9rem;
    }}
    nav a {{
      color: #d8f3dc;
      text-decoration: none;
      font-size: 0.92rem;
    }}
    nav a:hover {{ text-decoration: underline; color: #fff; }}
    main {{ max-width: 70rem; margin: 0 auto; padding: 1.5rem; }}
    h2 {{ margin: 0 0 0.4rem; font-size: 1.7rem; font-weight: normal; }}
    .lead {{ color: var(--muted); margin: 0 0 0.4rem; }}
    .count {{ color: var(--accent); font-size: 0.9rem; margin: 0 0 1rem; }}
    .table-wrap {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      overflow: auto;
      box-shadow: 0 8px 24px rgba(27, 67, 50, 0.08);
    }}
    table {{ width: 100%; border-collapse: collapse; font-family: "Segoe UI", sans-serif; }}
    th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--line); }}
    th {{ background: #edf5e8; color: var(--accent); font-size: 0.8rem; letter-spacing: 0.04em; text-transform: uppercase; }}
    tbody tr:hover {{ background: #f4faef; }}
    .empty {{ color: var(--muted); font-style: italic; }}
    table.kv {{
      width: auto;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      overflow: hidden;
      font-family: "Segoe UI", sans-serif;
    }}
    table.kv th {{ width: 10rem; }}
  </style>
</head>
<body>
  <header>
    <h1>GardenShare</h1>
    <p>Community seed library</p>
    <nav>{nav}</nav>
  </header>
  <main>
    <h2>{html.escape(title)}</h2>
    {body}
  </main>
</body>
</html>
"""


def dump_models(models: list[Any]) -> list[dict[str, Any]]:
    """Serialize Pydantic models for JSON responses."""

    return [item.model_dump(mode="json") for item in models]


def _format_cell(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    text = str(value)
    if "T" in text and len(text) >= 19 and text[4] == "-":
        return text.replace("T", " ")[:19]
    return text
