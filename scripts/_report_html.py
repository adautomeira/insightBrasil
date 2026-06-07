"""Self-contained HTML report building blocks shared by generate_report.py.

Not a standalone script (leading underscore). Mirrors the "printed document"
card style used for FPA reports elsewhere — gradient header, centered card,
CSS-only tabs (radio-button pattern, no JS needed for navigation), inline SVG
charts, dark/light toggle, and print support — just applied to this project's
analyses instead of function-point data.
"""

import html


def esc(value):
    return html.escape(str(value))


def fmt_money(value):
    return f"R$ {value:,.2f}"


def fmt_number(value, decimals=2):
    return f"{value:,.{decimals}f}"


# ---------------------------------------------------------------------------
# Inline SVG horizontal bar chart — works well for long, label-heavy lists
# (27 states, top-N purposes/creditors) where a vertical chart would crowd.
# ---------------------------------------------------------------------------

def svg_bar_chart(rows, *, label_key, value_key, value_fmt=fmt_number, highlight=None,
                  width=720, bar_height=22, gap=6, label_width=160, zero_centered=False):
    """Horizontal bar chart from a list of dicts.

    `highlight(row) -> bool` bolds a bar (and its label) to call out a row.

    Set `zero_centered=True` for data that can be negative (e.g. correlation
    coefficients, which range from -1 to +1) — bars then grow left or right
    from a vertical zero axis instead of all growing rightward from the
    label edge. Without this, a value like -0.09 and +0.09 would render as
    visually identical bars (same length, same direction), which misrepresents
    the sign. Only use the plain (non-centered) mode for values that are
    always >= 0 — money totals, counts, percentages, ratios.
    """
    if not rows:
        return ""

    values = [row[value_key] for row in rows]
    max_value = max(abs(v) for v in values) or 1
    chart_width = width - label_width - 90
    height = len(rows) * (bar_height + gap) + gap
    zero_x = label_width + chart_width / 2

    bars = []
    if zero_centered:
        bars.append(f'<line x1="{zero_x:.1f}" y1="0" x2="{zero_x:.1f}" y2="{height}" '
                    f'stroke="var(--border)" stroke-width="1"/>')

    for i, row in enumerate(rows):
        y = gap + i * (bar_height + gap)
        value = row[value_key]
        is_hl = highlight(row) if highlight else False
        fill = "var(--bar-highlight)" if is_hl else "var(--bar-fill)"
        label_class = " bar-label-hl" if is_hl else ""

        if zero_centered:
            half_width = chart_width / 2
            bar_len = max(1, abs(value) / max_value * half_width)
            rect_x = zero_x if value >= 0 else zero_x - bar_len
            value_x = rect_x + bar_len + (8 if value >= 0 else -8)
            value_anchor = "start" if value >= 0 else "end"
        else:
            bar_len = max(1, abs(value) / max_value * chart_width)
            rect_x = label_width
            value_x = label_width + bar_len + 8
            value_anchor = "start"

        bars.append(
            f'<text x="{label_width - 10}" y="{y + bar_height * 0.7}" text-anchor="end" '
            f'class="bar-label{label_class}">{esc(row[label_key])}</text>'
            f'<rect x="{rect_x:.1f}" y="{y}" width="{bar_len:.1f}" height="{bar_height}" '
            f'rx="3" fill="{fill}"/>'
            f'<text x="{value_x:.1f}" y="{y + bar_height * 0.7}" text-anchor="{value_anchor}" '
            f'class="bar-value">{esc(value_fmt(value))}</text>'
        )

    return (
        f'<svg viewBox="0 0 {width} {height}" class="bar-chart" role="img" '
        f'aria-label="bar chart">{"".join(bars)}</svg>'
    )


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def table(columns, rows, *, row_class=None):
    """Render a list of dicts as an HTML table.

    `columns` is a list of `(header, accessor, formatter)` triples, one per
    column — this lets generate_report.py describe a table declaratively
    instead of hand-writing <td> tags for every analysis:
      - `header`: the column's <th> text
      - `accessor`: either a dict key (e.g. "uf") to read directly off each
        row, or a function `row -> value` for derived/combined values (e.g.
        `lambda r: r["highest"]` to pull a (uf, ratio) tuple out for the
        formatter to render as "SP: 0.1234")
      - `formatter`: a function `value -> display string`, or None to just
        str() the value as-is (e.g. plain integers like a year or a count)

    `row_class(row) -> str`, if given, sets each <tr>'s CSS class — used to
    highlight rows that meet some condition (e.g. "flag-extraordinary" for a
    year with an unusually large swing). All text is HTML-escaped via `esc`.
    """
    head = "".join(f"<th>{esc(header)}</th>" for header, _, _ in columns)
    body_rows = []
    for row in rows:
        cls = f' class="{esc(row_class(row))}"' if row_class else ""
        cells = []
        for _, accessor, formatter in columns:
            value = accessor(row) if callable(accessor) else row[accessor]
            cells.append(f"<td>{esc(formatter(value) if formatter else value)}</td>")
        body_rows.append(f"<tr{cls}>{''.join(cells)}</tr>")
    return f'<table><thead><tr>{head}</tr></thead><tbody>{"".join(body_rows)}</tbody></table>'


# ---------------------------------------------------------------------------
# Page shell — header, tabs, dark/light + print support
# ---------------------------------------------------------------------------

def badge(text):
    return f'<span class="badge">{esc(text)}</span>'


def panel(tab_id, label, chip, body_html):
    return {"id": tab_id, "label": label, "chip": chip, "body": body_html}


def render_tabs(panels):
    """Build the four pieces of the CSS-only tab widget from a list of `panel()` dicts.

    The whole thing works without a single line of JavaScript, using a classic
    trick: one hidden radio button per tab (only one can be ":checked" at a
    time — that's the browser's native exclusive-selection behaviour), each
    paired with a <label> that the user actually clicks. CSS then uses the
    "~" general-sibling selector to say "when radio #tab-X is checked, style
    the label for X as active, and show panel X" — entirely declarative, no
    click handlers needed. See PAGE_TEMPLATE below for how these four pieces
    fit into the page (the inputs must come first so "~" can reach forward to
    the tab bar and panels that follow them in the HTML).

    Returns `(radio_inputs_html, tab_bar_html, panel_sections_html, css_rules)`.
    """
    inputs = "".join(
        f'<input type="radio" name="tabs" id="tab-{p["id"]}"'
        f'{" checked" if i == 0 else ""}>'
        for i, p in enumerate(panels)
    )
    bar = "".join(
        f'<label for="tab-{p["id"]}" class="tab">{esc(p["label"])}'
        f'<span class="chip">{esc(p["chip"])}</span></label>'
        for p in panels
    )
    bodies = "".join(f'<section class="panel" id="panel-{p["id"]}">{p["body"]}</section>' for p in panels)

    # One pair of rules per tab: "while this tab's radio is checked, ..."
    #   1. ...highlight its label (and the chip inside it) as the active tab
    #   2. ...make its panel visible (panels are `display: none` by default —
    #      see `.panels .panel` in PAGE_TEMPLATE — so only the active one shows)
    css_rules = []
    for p in panels:
        active_label = f'#tab-{p["id"]}:checked ~ .tab-bar label[for="tab-{p["id"]}"]'
        css_rules.append(
            f'{active_label} {{ background: var(--accent); color: #fff; }}'
            f'{active_label} .chip {{ background: rgba(255,255,255,.25); color: #fff; }}'
        )
        css_rules.append(
            f'#tab-{p["id"]}:checked ~ .panels #panel-{p["id"]} {{ display: block; }}'
        )

    return inputs, bar, bodies, "\n".join(css_rules)


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{
  --accent: #4F46E5;
  --bg: #ffffff;
  --bg-card: #ffffff;
  --text: #1f2330;
  --muted: #6b7280;
  --border: #e5e7eb;
  --bar-fill: #c7d2fe;
  --bar-highlight: #4F46E5;
  --table-stripe: #f9fafb;
}}
body.dark {{
  --accent: #818CF8;
  --bg: #0f0f1a;
  --bg-card: #171723;
  --text: #e5e7eb;
  --muted: #9ca3af;
  --border: #2a2a3a;
  --bar-fill: #383a5c;
  --bar-highlight: #818CF8;
  --table-stripe: #1c1c2b;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  transition: background .2s, color .2s;
}}
.page {{ max-width: 980px; margin: 0 auto; padding: 24px 20px 80px; }}
.header {{
  background: linear-gradient(135deg, #4F46E5, #818CF8);
  color: #fff;
  border-radius: 16px;
  padding: 28px 32px;
  margin-bottom: 20px;
  box-shadow: 0 8px 24px rgba(79,70,229,.25);
}}
.header h1 {{ margin: 0 0 6px; font-size: 1.6rem; }}
.header p {{ margin: 0; opacity: .9; }}
.badge {{
  display: inline-block; background: rgba(255,255,255,.18);
  border-radius: 999px; padding: 4px 14px; font-size: .8rem;
  margin-top: 12px; margin-right: 8px;
}}
.toolbar {{ position: fixed; top: 16px; right: 16px; display: flex; gap: 8px; z-index: 10; }}
.toolbar button {{
  border: 1px solid var(--border); background: var(--bg-card); color: var(--text);
  border-radius: 8px; padding: 8px 14px; cursor: pointer; font-size: .85rem;
}}
.toolbar button:hover {{ border-color: var(--accent); color: var(--accent); }}
.tab-bar {{
  display: flex; gap: 6px; overflow-x: auto; scrollbar-width: none;
  margin-bottom: 16px; padding-bottom: 4px;
}}
.tab-bar::-webkit-scrollbar {{ display: none; }}
.tab {{
  flex: none; cursor: pointer; padding: 8px 16px; border-radius: 999px;
  border: 1px solid var(--border); font-size: .85rem; white-space: nowrap;
  display: flex; align-items: center; gap: 8px; background: var(--bg-card);
}}
.tab .chip {{
  background: var(--border); border-radius: 999px; padding: 1px 9px;
  font-size: .72rem; color: var(--muted);
}}
.panels .panel {{ display: none; }}
.panel {{
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 14px;
  padding: 22px 26px; margin-bottom: 16px;
}}
.panel h2 {{ margin-top: 0; font-size: 1.2rem; }}
.panel h3 {{ font-size: 1rem; color: var(--accent); margin: 26px 0 10px; }}
.panel p.note {{ color: var(--muted); font-size: .88rem; line-height: 1.5; }}
table {{ width: 100%; border-collapse: collapse; font-size: .85rem; margin: 10px 0 4px; }}
th, td {{ text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--border); }}
th {{ color: var(--muted); font-weight: 600; font-size: .78rem; text-transform: uppercase; letter-spacing: .03em; }}
tbody tr:nth-child(even) {{ background: var(--table-stripe); }}
tr.flag-extraordinary td {{ color: #d97706; font-weight: 600; }}
tr.flag-pandemic td {{ background: rgba(217, 119, 6, .12); font-weight: 600; }}
tr.flag-up td:first-child {{ border-left: 3px solid #16a34a; }}
tr.flag-down td:first-child {{ border-left: 3px solid #dc2626; }}
.bar-chart {{ width: 100%; height: auto; margin: 8px 0 18px; }}
.bar-label {{ font-size: 11px; fill: var(--text); }}
.bar-label-hl {{ font-weight: 700; fill: var(--accent); }}
.bar-value {{ font-size: 11px; fill: var(--muted); }}
.metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin: 14px 0; }}
.metric-card {{
  border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px;
  background: var(--table-stripe);
}}
.metric-card .label {{ font-size: .78rem; color: var(--muted); text-transform: uppercase; letter-spacing: .03em; }}
.metric-card .value {{ font-size: 1.3rem; font-weight: 700; margin: 4px 0; }}
.metric-card .value.up {{ color: #16a34a; }}
.metric-card .value.down {{ color: #dc2626; }}
.metric-card .extra {{ font-size: .8rem; color: var(--muted); }}
.metric-card.flag {{ border-color: #d97706; box-shadow: 0 0 0 1px #d97706 inset; }}
.metric-card.flag .label::after {{ content: " ⚠"; }}
@media print {{
  :root, body.dark {{
    --accent: #4F46E5; --bg: #fff; --bg-card: #fff; --text: #1f2330;
    --muted: #555; --border: #ccc; --bar-fill: #c7d2fe; --bar-highlight: #4F46E5;
    --table-stripe: #f4f4f6;
  }}
  .toolbar, .tab-bar {{ display: none !important; }}
  .panels .panel {{ display: block !important; box-shadow: none; page-break-before: always; }}
  .panels .panel:first-child {{ page-break-before: auto; }}
  tr {{ break-inside: avoid; }}
  .header {{ box-shadow: none; }}
}}
</style>
</head>
<body>
<div class="toolbar">
  <button onclick="toggleTheme()" id="theme-btn">🌙 Dark</button>
  <button onclick="window.print()">🖨 Print</button>
</div>
<div class="page">
  <div class="header">
    <h1>{title}</h1>
    <p>{subtitle}</p>
    {badges}
  </div>
  <form class="tabs">
    {tab_inputs}
    <div class="tab-bar">{tab_bar}</div>
    <div class="panels">{panels}</div>
  </form>
</div>
<script>
function toggleTheme() {{
  document.body.classList.toggle('dark');
  document.getElementById('theme-btn').textContent =
    document.body.classList.contains('dark') ? '☀️ Light' : '🌙 Dark';
}}
</script>
</body>
</html>
"""


def render_page(*, title, subtitle, badges, panels):
    """Assemble the full self-contained HTML document from a list of `panel()` dicts.

    `PAGE_TEMPLATE` covers everything that's the same on every report (styles,
    header, toolbar, dark-mode script); `render_tabs` generates the parts that
    depend on *which* tabs this particular report has. The per-tab CSS rules
    can't go in `PAGE_TEMPLATE` itself — they don't exist until `render_tabs`
    runs — so they're spliced in just before `</style>` as a final step here,
    after the template's own `.format()` placeholders are filled in.
    """
    tab_inputs, tab_bar, panels_html, tab_css = render_tabs(panels)
    page = PAGE_TEMPLATE.format(
        title=esc(title),
        subtitle=esc(subtitle),
        badges="".join(badges),
        tab_inputs=tab_inputs,
        tab_bar=tab_bar,
        panels=panels_html,
    )
    return page.replace("</style>", f"{tab_css}\n</style>")
