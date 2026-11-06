"""Generate c64-contrib/contributions.svg: the last year of GitHub contributions
drawn on the same C64 screen as the header.

Usage:  GITHUB_TOKEN=... python tools/c64_contrib.py [username]
Runs daily from .github/workflows/c64-contrib.yml. Standard library only.
"""

import json
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from retro_header import BLUE, CYAN, GREEN, LIGHT_BLUE, WHITE, YELLOW

USER = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_USER", "NorbertRuff")
OUT = Path(__file__).resolve().parent.parent / "c64-contrib" / "contributions.svg"

# Contribution level -> colour (C64 palette, dim to bright)
LEVELS = {
    "NONE": "#2A1F8A",  # darker than the screen, so empty days read as sockets
    "FIRST_QUARTILE": LIGHT_BLUE,
    "SECOND_QUARTILE": CYAN,
    "THIRD_QUARTILE": GREEN,
    "FOURTH_QUARTILE": WHITE,
}

W = 960
BORDER_X, BORDER_Y = 44, 36
FONT, CHAR_W, LINE_H = 20, 12.0, 28
LEFT = BORDER_X + 22
CELL, GAP = 12, 3
GRID_X = LEFT + 3 * CHAR_W + 6     # room for M/W/F day labels
REVEAL = 2.4                       # seconds to "load" all columns

QUERY = """query($login:String!){user(login:$login){contributionsCollection{
contributionCalendar{totalContributions weeks{contributionDays{
date contributionCount contributionLevel weekday}}}}}}"""


def fetch(user: str, token: str) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "c64-contrib"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def streaks(days: list[dict]) -> tuple[int, int]:
    """(longest, current) streak in days. Today may still be empty without breaking the current one."""
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        longest = max(longest, run)
    current = 0
    for i, d in enumerate(reversed(days)):
        if d["contributionCount"]:
            current += 1
        elif i > 0:
            break
    return longest, current


def text(x: float, y: float, s: str, colour: str = LIGHT_BLUE) -> str:
    return (f'<text x="{x}" y="{y}" fill="{colour}" textLength="{len(s) * CHAR_W:.1f}" '
            f'lengthAdjust="spacingAndGlyphs">{escape(s)}</text>')


def build(cal: dict) -> str:
    weeks = cal["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    total = cal["totalContributions"]
    best = max(days, key=lambda d: d["contributionCount"])
    longest, current = streaks(days)

    y0 = BORDER_Y + 34
    lines = [text(LEFT, y0, 'LOAD "CONTRIBUTIONS",8,1'),
             text(LEFT, y0 + LINE_H, "READY."),
             text(LEFT, y0 + 2 * LINE_H, "RUN")]

    # month labels above the first column of each month
    grid_top = y0 + 3 * LINE_H + 10
    months, last = [], None
    for col, w in enumerate(weeks):
        first = date.fromisoformat(w["contributionDays"][0]["date"])
        if first.month != last and col < len(weeks) - 2:
            months.append(text(GRID_X + col * (CELL + GAP), grid_top, first.strftime("%b").upper(), YELLOW))
            last = first.month
    for wd, label in ((1, "MON"), (3, "WED"), (5, "FRI")):
        lines.append(text(LEFT, grid_top + 10 + wd * (CELL + GAP) + CELL - 1, label))

    cells, css = [], []
    for col, w in enumerate(weeks):
        cells.append(f'<g class="w{col}">')
        for d in w["contributionDays"]:
            x = GRID_X + col * (CELL + GAP)
            y = grid_top + 10 + d["weekday"] * (CELL + GAP)
            tip = f'{d["contributionCount"]} on {d["date"]}'
            cells.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                         f'fill="{LEVELS[d["contributionLevel"]]}"><title>{tip}</title></rect>')
        cells.append("</g>")
        css.append(f".w{col}{{animation-delay:{col * REVEAL / len(weeks):.3f}s}}")

    stats_y = grid_top + 10 + 7 * (CELL + GAP) + 34
    stats = [
        text(LEFT, stats_y, f"{total} CONTRIBUTIONS IN THE LAST YEAR", WHITE),
        text(LEFT, stats_y + LINE_H,
             f"BEST DAY {best['contributionCount']}  LONGEST STREAK {longest}  CURRENT {current}", CYAN),
        text(LEFT, stats_y + 2 * LINE_H, "READY."),
    ]
    cursor_y = stats_y + 3 * LINE_H
    H = cursor_y + BORDER_Y + 10
    sw, sh = W - 2 * BORDER_X, H - 2 * BORDER_Y

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{total} GitHub contributions in the last year">
<title>{total} contributions in the last year</title>
<defs>
  <clipPath id="crt"><rect width="{W}" height="{H}" rx="28"/></clipPath>
  <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="2" fill="#000" opacity=".18"/></pattern>
  <radialGradient id="vig" cx="50%" cy="50%" r="75%"><stop offset="60%" stop-color="#000" stop-opacity="0"/><stop offset="100%" stop-color="#000" stop-opacity=".5"/></radialGradient>
  <filter id="glow" x="-5%" y="-20%" width="110%" height="140%"><feGaussianBlur stdDeviation="1.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<style>
text{{font-family:"Cascadia Mono",Consolas,"DejaVu Sans Mono","Courier New",monospace;font-size:{FONT}px;font-weight:700;white-space:pre}}
@keyframes in{{from{{opacity:0}}to{{opacity:1}}}}
[class^=w]{{opacity:0;animation:in .15s linear forwards}}
{chr(10).join(css)}
.stats{{opacity:0;animation:in .2s linear {REVEAL + 0.3:.1f}s forwards}}
@keyframes blink{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
.cursor{{animation:blink .8s step-end infinite}}
@media (prefers-reduced-motion: reduce){{*{{animation:none!important;opacity:1!important}}}}
</style>
<g clip-path="url(#crt)">
  <rect width="{W}" height="{H}" fill="{LIGHT_BLUE}"/>
  <rect x="{BORDER_X}" y="{BORDER_Y}" width="{sw}" height="{sh}" fill="{BLUE}"/>
  <g filter="url(#glow)">
    {chr(10).join(lines)}
    {chr(10).join(months)}
    {''.join(cells)}
    <g class="stats">{''.join(stats)}</g>
    <rect class="cursor" x="{LEFT}" y="{cursor_y - FONT + 4}" width="{CHAR_W}" height="{FONT}" fill="{LIGHT_BLUE}"/>
  </g>
  <rect width="{W}" height="{H}" fill="url(#scan)"/>
  <rect width="{W}" height="{H}" fill="url(#vig)"/>
</g>
</svg>
"""


if __name__ == "__main__":
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("Set GITHUB_TOKEN (any token that can read public profile data).")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(build(fetch(USER, token)), encoding="utf-8")
    print(f"wrote {OUT}")
