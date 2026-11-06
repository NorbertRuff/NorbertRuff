"""Generate static/retro-header.svg: an animated C64-style boot screen.

Edit SCRIPT below, then run:  python tools/retro_header.py
Pure CSS animation (no JS), so it renders inside GitHub's <img> sandbox.
Every element shares one looping timeline of TOTAL seconds; each element's
keyframes are expressed as percentages of that loop.
"""

from pathlib import Path
from xml.sax.saxutils import escape

# ── VICE C64 palette ─────────────────────────────────────────────
BLUE, LIGHT_BLUE = "#3E31A2", "#7C70DA"
WHITE, CYAN, GREEN, YELLOW = "#FFFFFF", "#75CEC8", "#9AE29B", "#EDF171"
STRIPES = ["#883932", "#67B6BD", "#8B3F96", "#55A049", "#40318D",
           "#BFCE72", "#8B5429", "#574200", "#B86962", "#505050"]

# ── Layout ───────────────────────────────────────────────────────
W, H = 960, 460
BORDER_X, BORDER_Y = 44, 36
FONT = 24
CHAR_W = FONT * 0.6          # monospace advance; enforced with textLength
LINE_H = 31
LEFT = BORDER_X + 22
TOP = BORDER_Y + 34
TOTAL = 20.0                 # seconds per loop

# ── Script ───────────────────────────────────────────────────────
# kind: "static" (always shown), "type" (typed char by char), "show" (pops in)
# (kind, text, start_seconds, colour)
SCRIPT = [
    ("static", "    **** NORBERT RUFF BASIC V2026 ****", 0, LIGHT_BLUE),
    ("static", " 64K RAM SYSTEM  38911 BASIC BYTES FREE", 0, LIGHT_BLUE),
    ("static", "READY.", 0, LIGHT_BLUE),
    ("type", 'LOAD "NORBERT",8,1', 0.8, LIGHT_BLUE),
    ("show", "SEARCHING FOR NORBERT", 2.6, LIGHT_BLUE),
    ("show", "LOADING", 3.4, LIGHT_BLUE),
    ("show", "READY.", 6.6, LIGHT_BLUE),
    ("type", "RUN", 7.2, LIGHT_BLUE),
    ("show", "> SENIOR FULL-STACK DEV & CLOUD ARCHITECT", 8.4, WHITE),
    ("show", "> APEX LAB / AWS CERTIFIED DEVELOPER", 9.0, CYAN),
    ("show", "> ROBOTS, GAME BOY ROMS & SBCS AFTER DARK", 9.6, GREEN),
]
LOADING_WINDOW = (3.4, 6.6)  # border flashes tape-loading stripes
TYPE_SPEED = 0.09            # seconds per typed character


def pct(t: float) -> str:
    return f"{min(max(t / TOTAL * 100, 0), 100):.3f}%"


def text_el(text: str, x: float, y: float, colour: str, extra: str = "") -> str:
    length = len(text) * CHAR_W
    return (f'<text x="{x}" y="{y}" fill="{colour}" textLength="{length:.1f}" '
            f'lengthAdjust="spacingAndGlyphs"{extra}>{escape(text)}</text>')


def build() -> str:
    css, body = [], []
    cursor_frames = []  # (time, x, y) — where the blinking cursor sits from that time on
    last_y = TOP
    end_time = 0.0

    for i, (kind, text, start, colour) in enumerate(SCRIPT):
        y = TOP + i * LINE_H
        last_y = y
        cls = f"l{i}"
        if kind == "static":
            body.append(text_el(text, LEFT, y, colour))
            cursor_frames.append((0, LEFT, y + LINE_H))
            continue

        body.append(f'<g class="{cls}">{text_el(text, LEFT, y, colour)}</g>')
        if kind == "show":
            css.append(f"@keyframes k{i}{{0%,{pct(start - 0.001)}{{opacity:0}}"
                       f"{pct(start)},100%{{opacity:1}}}}")
            css.append(f".{cls}{{opacity:0;animation:k{i} {TOTAL}s step-end infinite}}")
            cursor_frames.append((start, LEFT, y + LINE_H))
            end_time = max(end_time, start)
        else:  # typed: clip-path inset shrinks from the right, one char per step
            n = len(text)
            full = n * CHAR_W + 4
            steps = [f"0%,{pct(start)}{{clip-path:inset(-10px {full:.1f}px -10px 0)}}"]
            for c in range(1, n + 1):
                t = start + c * TYPE_SPEED
                right = full - c * CHAR_W
                steps.append(f"{pct(t)}{{clip-path:inset(-10px {max(right, 0):.1f}px -10px 0)}}")
                cursor_frames.append((t, LEFT + c * CHAR_W, y))
            steps.append("100%{clip-path:inset(-10px 0 -10px 0)}")
            css.append(f"@keyframes k{i}{{{''.join(steps)}}}")
            css.append(f".{cls}{{animation:k{i} {TOTAL}s step-end infinite}}")
            cursor_frames.append((start, LEFT, y))
            done = start + n * TYPE_SPEED + 0.25
            cursor_frames.append((done, LEFT, y + LINE_H))
            end_time = max(end_time, done)

    # Cursor: one block that jumps between positions (step-end) and blinks on its own.
    cursor_frames.sort(key=lambda f: f[0])
    kf = []
    for t, x, y in cursor_frames:
        kf.append(f"{pct(t)}{{transform:translate({x:.1f}px,{y - FONT + 4:.1f}px)}}")
    css.append(f"@keyframes cur{{{''.join(kf)}100%{{transform:translate({LEFT}px,{last_y + LINE_H - FONT + 4}px)}}}}")
    css.append(f".cursor{{animation:cur {TOTAL}s step-end infinite}}")
    css.append("@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}")
    css.append(".cursor rect{animation:blink .8s step-end infinite}")

    # Tape-loading stripes in the border, only during LOADING.
    a, b = LOADING_WINDOW
    css.append(f"@keyframes load{{0%,{pct(a - 0.001)}{{opacity:0}}{pct(a)},{pct(b)}{{opacity:1}}"
               f"{pct(b + 0.001)},100%{{opacity:0}}}}")
    css.append(f".stripes{{opacity:0;animation:load {TOTAL}s step-end infinite}}")
    css.append("@keyframes roll{from{transform:translateY(0)}to{transform:translateY(-120px)}}")
    css.append(".stripes g{animation:roll .35s steps(6) infinite}")

    # Reduced motion: final frame, no flashing.
    css.append("@media (prefers-reduced-motion: reduce){"
               "*{animation:none!important}[class^=l]{opacity:1!important;clip-path:none!important}"
               ".stripes{display:none}}")

    stripe_rects = []
    y, k = 0, 0
    while y < H + 240:
        h = 6 + (k * 7) % 14
        stripe_rects.append(f'<rect x="0" y="{y}" width="{W}" height="{h}" fill="{STRIPES[k % len(STRIPES)]}"/>')
        y += h
        k += 1

    sw, sh = W - 2 * BORDER_X, H - 2 * BORDER_Y
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Norbert Ruff - retro boot screen">
<title>Norbert Ruff - READY.</title>
<defs>
  <clipPath id="crt"><rect width="{W}" height="{H}" rx="28"/></clipPath>
  <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="2" fill="#000" opacity=".18"/></pattern>
  <radialGradient id="vig" cx="50%" cy="50%" r="75%"><stop offset="60%" stop-color="#000" stop-opacity="0"/><stop offset="100%" stop-color="#000" stop-opacity=".55"/></radialGradient>
  <filter id="glow" x="-5%" y="-20%" width="110%" height="140%"><feGaussianBlur stdDeviation="1.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<style>
text{{font-family:"Cascadia Mono",Consolas,"DejaVu Sans Mono","Courier New",monospace;font-size:{FONT}px;font-weight:700;white-space:pre}}
{chr(10).join(css)}
</style>
<g clip-path="url(#crt)">
  <rect width="{W}" height="{H}" fill="{LIGHT_BLUE}"/>
  <g class="stripes"><g>{''.join(stripe_rects)}</g></g>
  <rect x="{BORDER_X}" y="{BORDER_Y}" width="{sw}" height="{sh}" fill="{BLUE}"/>
  <g filter="url(#glow)">
    {chr(10).join(body)}
    <g class="cursor"><rect width="{CHAR_W:.1f}" height="{FONT}" fill="{LIGHT_BLUE}"/></g>
  </g>
  <rect width="{W}" height="{H}" fill="url(#scan)"/>
  <rect width="{W}" height="{H}" fill="url(#vig)"/>
</g>
</svg>
"""


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "static" / "retro-header.svg"
    out.write_text(build(), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")
