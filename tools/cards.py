#!/usr/bin/env python3
"""Build the profile card as two SVGs (dark and light), no dependencies.

    python tools/cards.py                 # writes profile-card-{dark,light}.svg
    python tools/cards.py --variant a     # the neofetch layout, if you want to switch back

The card is a terminal transcript: a prompt, an isometric 3x3x3 cube whose sticker colour
spells the initials on its two side faces, and the facts underneath. The only live number is
the contribution count, read from the GitHub GraphQL API (last 12 months, the window GitHub
exposes without paginating year by year). Without a token it falls back to the number baked
into FALLBACK.
"""

import argparse
import json
import math
import os
import random
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

GITHUB_LOGIN = "1cadumagalhaes"
FALLBACK_CONTRIBUTIONS = 3682

FACTS = {
    "role": "data engineer",
    "work": "tech lead @ retize",
    "stack": "airflow · dbt · bigquery · k8s · python",
    "portfolio": "cadumagalhaes.dev",
}

MONO = "Consolas, Menlo, 'DejaVu Sans Mono', monospace"
CW = 0.602                      # monospace advance width, in em
UX, UY = math.cos(math.radians(30)), math.sin(math.radians(30))

# Initials drawn with the cube's own stickers, one glyph per side face.
GLYPHS = {
    "C": ["###", "#..", "###"],
    "M": ["#.#", "###", "#.#"],
}


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# --- the cube -------------------------------------------------------------
def cube(x, y, edge, tones, letters=("C", "M"), seed=7):
    """Isometric 3x3x3 cube, bounding box top-left at (x, y).

    The two side faces carry a 3x3 pixel glyph in the accent colour, so the initials are
    built from the stickers themselves rather than laid over the cube as text. The
    remaining stickers are shuffled through the three face tones, which is what makes it
    read as a cube waiting to be solved.
    """
    rnd = random.Random(seed)
    bag = [tones["top"], tones["left"], tones["right"]]
    masks = {"left": GLYPHS[letters[0]], "right": GLYPHS[letters[1]]}
    hw, hh = UX * edge, UY * edge
    top = (0.0, -edge)
    right = (hw, -edge + hh)
    left = (-hw, -edge + hh)
    faces = {
        "top": (top, (hw, hh), (-hw, hh)),
        "left": (left, (hw, hh), (0.0, edge)),
        "right": (right, (-hw, hh), (0.0, edge)),
    }
    ox, oy = x + hw, y + edge
    out = []
    for name, (origin, a, b) in faces.items():
        au, bu = (a[0] / 3, a[1] / 3), (b[0] / 3, b[1] / 3)
        glyph = masks.get(name)
        for j in range(3):
            for i in range(3):
                p = (origin[0] + i * au[0] + j * bu[0], origin[1] + i * au[1] + j * bu[1])
                quad = [p, (p[0] + au[0], p[1] + au[1]),
                        (p[0] + au[0] + bu[0], p[1] + au[1] + bu[1]), (p[0] + bu[0], p[1] + bu[1])]
                cx = sum(q[0] for q in quad) / 4
                cy = sum(q[1] for q in quad) / 4
                quad = [(q[0] + (cx - q[0]) * 0.16 + ox, q[1] + (cy - q[1]) * 0.16 + oy) for q in quad]
                lit = glyph is not None and glyph[j][i] == "#"
                fill = tones["accent"] if lit else rnd.choice(bag)
                points = " ".join(f"{px:.1f},{py:.1f}" for px, py in quad)
                out.append(f'<polygon points="{points}" fill="{fill}"/>')
    return "\n".join(out), 2 * hw, 2 * edge


# --- layouts --------------------------------------------------------------
def transcript(theme, contributions):
    """The shipped layout: prompt, cube, key/value rows."""
    pad, size = 26, 10.6
    rows = [
        ("role", FACTS["role"]),
        ("work", FACTS["work"]),
        ("stack", FACTS["stack"]),
        ("portfolio", FACTS["portfolio"]),
        ("contributions", f"{contributions:,}"),
    ]
    key_col = max(len(k) for k, _ in rows)
    row_px = (key_col + 2 + max(len(v) for _, v in rows)) * size * CW
    edge = 122
    cube_w, cube_h = 2 * UX * edge, 2 * edge
    width = int(max(cube_w, row_px) + pad * 2)
    prompt_y, cube_top = 38, 54
    out = [
        f'<text x="{pad}" y="{prompt_y}" font-family="{MONO}" font-size="12.5" fill="{theme["dim"]}" '
        f'xml:space="preserve"><tspan fill="{theme["prompt"]}">carlos@magalhaes</tspan> ~ '
        f'<tspan fill="{theme["accent"]}">$</tspan> whoami</text>',
        cube((width - cube_w) / 2, cube_top, edge, theme["cube"])[0],
    ]
    y = cube_top + cube_h + 22
    for i, (key, value) in enumerate(rows):
        out.append(
            f'<text x="{pad}" y="{y + i * 17:.0f}" font-family="{MONO}" font-size="{size}" '
            f'xml:space="preserve"><tspan fill="{theme["dim"]}">{esc(key.ljust(key_col))}</tspan>  '
            f'<tspan fill="{theme["ink"]}">{esc(value)}</tspan></text>'
        )
    height = int(y + len(rows) * 17 + pad)
    return width, height, "\n".join(out)


def neofetch(theme, contributions):
    """Alternative: cube on the left, dot-leader table on the right."""
    pad, ts, value_col, row_h = 26, 12.2, 13, 25
    rows = [
        ("role", "data engineer · tech lead @ retize"),
        ("stack", FACTS["stack"]),
        ("portfolio", FACTS["portfolio"]),
        ("contributions", f"{contributions:,}"),
    ]
    width, edge = 828, 128
    cube_w, cube_h = 2 * UX * edge, 2 * edge
    xk = 344
    block = 20 + row_h + len(rows) * row_h
    y0 = int(44 + max(0, (cube_h - block) / 2) + 16)
    out = [
        cube(pad, 44, edge, theme["cube"])[0],
        f'<text x="{xk}" y="{y0}" font-family="{MONO}" font-size="13" fill="{theme["prompt"]}">'
        f'carlos@magalhaes</text>',
        f'<text x="{xk}" y="{y0 + 20}" font-family="{MONO}" font-size="11" fill="{theme["cube"]["left"]}">'
        f'{"-" * 36}</text>',
    ]
    for i, (key, value) in enumerate(rows):
        leader = " " + "." * max(2, value_col - len(key) - 2) + " "
        out.append(
            f'<text x="{xk}" y="{y0 + 46 + i * row_h}" font-family="{MONO}" font-size="{ts}" '
            f'xml:space="preserve"><tspan fill="{theme["prompt"]}">{esc(key)}</tspan>'
            f'<tspan fill="{theme["cube"]["right"]}">{esc(leader)}</tspan>'
            f'<tspan fill="{theme["ink"]}">{esc(value)}</tspan></text>'
        )
    height = int(max(44 + cube_h + 30, y0 + block + pad))
    return width, height, "\n".join(out)


LAYOUTS = {"c": transcript, "a": neofetch}

# --- themes ---------------------------------------------------------------
THEMES = {
    "dark": {
        "bg": "#0f1317",
        "ink": "#d5dbdf",
        "dim": "#7d8590",
        "prompt": "#7ee787",
        "accent": "#79c0ff",
        "cube": {"top": "#d7dde3", "left": "#6e7781", "right": "#3a424c", "accent": "#79c0ff"},
    },
    "light": {
        "bg": "#ffffff",
        "ink": "#1f2328",
        "dim": "#59636e",
        "prompt": "#1a7f37",
        "accent": "#0969da",
        "cube": {"top": "#d0d7de", "left": "#8b949e", "right": "#4b5563", "accent": "#0969da"},
    },
}


def svg(width, height, body, bg):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">\n'
        f'<rect width="{width}" height="{height}" rx="12" fill="{bg}"/>\n'
        + body + "\n</svg>\n"
    )


# --- the live number ------------------------------------------------------
def fetch_contributions(token):
    """Contributions in the last 12 months, or FALLBACK. Never fails the build."""
    if not token:
        return FALLBACK_CONTRIBUTIONS
    query = ('{"query":"{ user(login: \\"%s\\") { contributionsCollection '
             '{ contributionCalendar { totalContributions } } } }"}' % GITHUB_LOGIN)
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=query.encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
        return int(payload["data"]["user"]["contributionsCollection"]
                   ["contributionCalendar"]["totalContributions"])
    except Exception as error:                                  # noqa: BLE001 — never fail the build
        print(f"contributions: falling back to {FALLBACK_CONTRIBUTIONS} ({error})")
        return FALLBACK_CONTRIBUTIONS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=sorted(LAYOUTS), default="c")
    parser.add_argument("--prefix", default="profile-card")
    parser.add_argument("--out", default=str(ROOT))
    args = parser.parse_args()

    contributions = fetch_contributions(os.environ.get("GITHUB_TOKEN"))
    layout = LAYOUTS[args.variant]
    for name, theme in THEMES.items():
        width, height, body = layout(theme, contributions)
        path = Path(args.out) / f"{args.prefix}-{name}.svg"
        path.write_text(svg(width, height, body, theme["bg"]))
        print(f"{path.name}  {width}×{height}  {path.stat().st_size} B")


if __name__ == "__main__":
    main()
